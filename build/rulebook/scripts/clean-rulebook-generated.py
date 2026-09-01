#!/usr/bin/env python3
"""Safely remove generated Cybermancy rulebook render artifacts.

Default is dry-run. Pass --apply to delete.

Never removes:
- build/rulebook/inventory/**
- build/rulebook/manifests/**
- build/rulebook/source/**
- build/rulebook/production/**
- canonical layout/config/source files
- rulebook scripts, except Python __pycache__ directories
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RULEBOOK = Path("build/rulebook")

EXACT_DIRS = (
    RULEBOOK / "work",
    RULEBOOK / "reports",
    RULEBOOK / "output",
    RULEBOOK / "layout" / "reports",
    RULEBOOK / "layout" / "prototype",
    RULEBOOK / "layout" / "class-packages",
    RULEBOOK / "layout" / "domain-packages",
    RULEBOOK / "layout" / "ice-reference",
    RULEBOOK / "layout" / "encounters" / "chapter-output",
)

DIR_GLOBS = (
    "build/rulebook/layout/chapter*",
    "build/rulebook/layout/*-prototype",
    "build/rulebook/layout/**/output",
    "build/rulebook/layout/**/work",
    "build/rulebook/layout/**/reports",
    "build/rulebook/layout/**/_render-assets",
    "build/rulebook/scripts/**/__pycache__",
)

FILE_GLOBS = ("integrate-*.txt",)

PROTECTED_ROOTS = (
    RULEBOOK / "inventory",
    RULEBOOK / "manifests",
    RULEBOOK / "source",
    RULEBOOK / "production",
)


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def find_repo_root(start: Path) -> Path:
    result = run_git(start, "rev-parse", "--show-toplevel")
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Run this command from inside the Cybermancy Git repository.")
    return Path(result.stdout.strip()).resolve()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_safe(repo_root: Path, candidate: Path) -> None:
    resolved = candidate.resolve(strict=False)
    if resolved == repo_root or not is_within(resolved, repo_root):
        raise RuntimeError(f"Refusing unsafe cleanup target: {candidate}")

    for protected in PROTECTED_ROOTS:
        protected_abs = (repo_root / protected).resolve(strict=False)
        if resolved == protected_abs or is_within(resolved, protected_abs):
            raise RuntimeError(f"Refusing protected rulebook path: {candidate}")


def tracked_files(repo_root: Path, candidate: Path) -> list[str]:
    rel = candidate.relative_to(repo_root).as_posix()
    result = run_git(repo_root, "ls-files", "--", rel)
    if result.returncode != 0:
        raise RuntimeError(f"Could not verify Git tracking state for {rel}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def discover(repo_root: Path, keep_release: bool) -> list[Path]:
    found: set[Path] = set()

    for relative in EXACT_DIRS:
        if keep_release and relative == RULEBOOK / "output":
            continue
        target = repo_root / relative
        if target.exists() or target.is_symlink():
            found.add(target)

    for pattern in DIR_GLOBS:
        for target in repo_root.glob(pattern):
            if target.exists() or target.is_symlink():
                found.add(target)

    for pattern in FILE_GLOBS:
        for target in repo_root.glob(pattern):
            if target.exists() or target.is_symlink():
                found.add(target)

    ordered = sorted(
        found,
        key=lambda p: (len(p.relative_to(repo_root).parts), p.as_posix().lower()),
    )
    reduced: list[Path] = []
    for candidate in ordered:
        resolved = candidate.resolve(strict=False)
        if any(is_within(resolved, parent.resolve(strict=False)) for parent in reduced):
            continue
        reduced.append(candidate)
    return reduced


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove known generated Cybermancy rulebook artifacts. Default: dry-run."
    )
    parser.add_argument("--apply", action="store_true", help="Actually delete the generated artifacts.")
    parser.add_argument(
        "--keep-release",
        action="store_true",
        help="Keep build/rulebook/output while cleaning other generated artifacts.",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = find_repo_root(Path.cwd())
        candidates = discover(repo_root, args.keep_release)

        if not candidates:
            print("No generated rulebook artifacts found.")
            return 0

        blocked: list[tuple[Path, list[str]]] = []
        safe: list[Path] = []

        for candidate in candidates:
            assert_safe(repo_root, candidate)
            tracked = tracked_files(repo_root, candidate)
            if tracked:
                blocked.append((candidate, tracked))
            else:
                safe.append(candidate)

        if blocked:
            print("ERROR: cleanup stopped because candidate paths contain Git-tracked files.", file=sys.stderr)
            for candidate, tracked in blocked:
                print(f"  BLOCKED {candidate.relative_to(repo_root)}", file=sys.stderr)
                for item in tracked[:20]:
                    print(f"    tracked: {item}", file=sys.stderr)
                if len(tracked) > 20:
                    print(f"    ... {len(tracked) - 20} more", file=sys.stderr)
            print("No files were deleted.", file=sys.stderr)
            return 2

        label = "REMOVE" if args.apply else "DRY-RUN"
        for candidate in safe:
            print(f"{label:7} {candidate.relative_to(repo_root)}")

        if not args.apply:
            print(f"\nDry run: {len(safe)} generated path(s) would be removed.")
            print("Re-run with --apply to delete them.")
            return 0

        for candidate in safe:
            remove_path(candidate)

        print(f"\nRemoved {len(safe)} generated rulebook path(s).")
        return 0

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
