from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from rulebook_cli import _load_namespace

SCRIPT_DIR = Path(__file__).resolve().parent
PUBLIC_SCRIPT = SCRIPT_DIR / "build-rulebook-inventory.py"
LEGACY_IMPL = SCRIPT_DIR / "build-rulebook-inventory.py.impl"


class StrictInventoryError(RuntimeError):
    pass


def _git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _decode(data: bytes) -> str:
    return os.fsdecode(data).strip()


def _require_git_root(root: Path) -> None:
    result = _git_bytes(root, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise StrictInventoryError(
            "strict inventory requires a valid Git repository: "
            + _decode(result.stderr or result.stdout)
        )
    top = Path(_decode(result.stdout)).resolve()
    if top != root.resolve():
        raise StrictInventoryError(
            f"strict inventory requires the repository root; got {root}, Git root is {top}"
        )


def _head(root: Path) -> str:
    result = _git_bytes(root, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise StrictInventoryError(
            "could not resolve Git HEAD: " + _decode(result.stderr or result.stdout)
        )
    return _decode(result.stdout)


def _worktree_porcelain(root: Path) -> bytes:
    result = _git_bytes(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if result.returncode != 0:
        raise StrictInventoryError(
            "could not inspect Git working tree: " + _decode(result.stderr or result.stdout)
        )
    return result.stdout or b""


def _status_summary(data: bytes, limit: int = 12) -> str:
    parts = [os.fsdecode(part) for part in data.split(b"\0") if part]
    if not parts:
        return ""
    shown = parts[:limit]
    suffix = "" if len(parts) <= limit else f"; ... ({len(parts) - limit} more)"
    return "; ".join(shown) + suffix


def _require_clean_worktree(root: Path) -> None:
    status = _worktree_porcelain(root)
    if status:
        raise StrictInventoryError(
            "strict inventory requires a clean working tree; commit or discard staged, "
            "modified, deleted, or untracked non-ignored files: " + _status_summary(status)
        )


def _git_ls_files(root: Path) -> list[str]:
    result = _git_bytes(root, "ls-files", "-z", "--cached")
    if result.returncode != 0:
        raise StrictInventoryError(
            "could not enumerate tracked Git files: " + _decode(result.stderr or result.stdout)
        )
    return [os.fsdecode(part) for part in (result.stdout or b"").split(b"\0") if part]


def _git_ignored_tracked_files(root: Path) -> set[str]:
    """Return tracked paths excluded by the repository's standard ignore rules."""
    result = _git_bytes(
        root,
        "ls-files",
        "-z",
        "--cached",
        "--ignored",
        "--exclude-standard",
    )
    if result.returncode != 0:
        raise StrictInventoryError(
            "could not enumerate tracked ignored Git files: "
            + _decode(result.stderr or result.stdout)
        )
    return {os.fsdecode(part) for part in (result.stdout or b"").split(b"\0") if part}


def _legacy_excluded(rel: str, excluded_dirs: set[str]) -> bool:
    normalized = rel.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts:
        return True
    if parts[-1].startswith("."):
        return True
    return any(part.startswith(".") or part in excluded_dirs for part in parts[:-1])


def _repo_relative_or_none(root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix().strip("/")
    except ValueError:
        return None


def _under(rel: str, base_rel: str | None) -> bool:
    if not base_rel:
        return False
    rel = rel.replace("\\", "/").strip("/")
    base_rel = base_rel.replace("\\", "/").strip("/")
    return rel == base_rel or rel.startswith(base_rel + "/")


def _validate_tracked_presence(root: Path, tracked: list[str]) -> None:
    missing: list[str] = []
    for rel in tracked:
        path = root / PurePosixPath(rel)
        if not path.exists() and not path.is_symlink():
            missing.append(rel)
    if missing:
        sample = "; ".join(missing[:12])
        suffix = "" if len(missing) <= 12 else f"; ... ({len(missing) - 12} more)"
        raise StrictInventoryError("tracked Git paths are missing from the worktree: " + sample + suffix)


def strict_snapshot(root: Path, output_dir: Path, excluded_dirs: set[str]) -> tuple[str, list[str]]:
    """Validate strict startup state and return HEAD plus committed inventory candidates.

    Ignored local files may exist, but both untracked ignored files and tracked files
    matched by standard Git ignore rules are excluded from strict inventory candidates.
    """
    root = root.resolve()
    _require_git_root(root)
    _require_clean_worktree(root)
    head = _head(root)
    tracked = _git_ls_files(root)
    _validate_tracked_presence(root, tracked)
    ignored_tracked = _git_ignored_tracked_files(root)
    output_rel = _repo_relative_or_none(root, output_dir)
    candidates = [
        rel
        for rel in tracked
        if rel not in ignored_tracked
        and not _legacy_excluded(rel, excluded_dirs)
        and not _under(rel, output_rel)
    ]
    candidates.sort(key=lambda value: value.casefold())
    return head, candidates


def _revalidate_snapshot(root: Path, expected_head: str) -> None:
    _require_git_root(root)
    _require_clean_worktree(root)
    actual_head = _head(root)
    if actual_head != expected_head:
        raise StrictInventoryError(
            f"Git HEAD changed during strict inventory generation: {expected_head} -> {actual_head}"
        )


def _checkout_index(root: Path, export_root: Path) -> None:
    export_root.mkdir(parents=True, exist_ok=True)
    prefix = export_root.as_posix().rstrip("/") + "/"
    result = _git_bytes(root, "checkout-index", "--all", "--force", f"--prefix={prefix}")
    if result.returncode != 0:
        raise StrictInventoryError(
            "could not materialize committed Git index for strict scan: "
            + _decode(result.stderr or result.stdout)
        )


def _legacy_namespace() -> dict[str, Any]:
    return _load_namespace(
        PUBLIC_SCRIPT,
        LEGACY_IMPL,
        module_name="_rulebook_inventory_strict_legacy",
    )


def _build_from_committed_index(
    root: Path,
    head: str,
    candidate_relpaths: list[str],
) -> dict[str, Any]:
    legacy = _legacy_namespace()
    excluded_dirs = set(legacy["DEFAULT_EXCLUDED_DIRS"])
    if any(_legacy_excluded(rel, excluded_dirs) for rel in candidate_relpaths):
        raise StrictInventoryError("internal error: excluded path reached strict candidate set")

    with tempfile.TemporaryDirectory(prefix="cybermancy-rulebook-inventory-") as td:
        export_root = Path(td) / root.name
        _checkout_index(root, export_root)
        candidate_paths: list[Path] = []
        missing_export: list[str] = []
        for rel in candidate_relpaths:
            path = export_root / PurePosixPath(rel)
            if not path.exists() and not path.is_symlink():
                missing_export.append(rel)
            else:
                candidate_paths.append(path)
        if missing_export:
            raise StrictInventoryError(
                "tracked paths were not materialized from the Git index: "
                + "; ".join(missing_export[:12])
            )

        # Keep all existing inventory classification/reconciliation logic intact.
        # Only the item candidate enumerator is replaced in strict mode. Running
        # against a committed-only checkout prevents ignored/untracked files from
        # entering inventory items or the legacy reconciliation filesystem walk.
        legacy["walk_repo"] = lambda _root: iter(candidate_paths)
        inv = legacy["build_inventory"](export_root)

    inv.setdefault("repository", {})["root_name"] = root.name
    inv["repository"]["git_commit"] = head
    return inv


def main() -> int:
    legacy = _legacy_namespace()
    args = legacy["parse_args"]()
    if not getattr(args, "strict", False):
        return int(legacy["main"]() or 0)

    root = Path(args.repo_root).expanduser().resolve()
    if not root.exists():
        print(f"ERROR: repository root does not exist: {root}", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir = out_dir.resolve()

    try:
        excluded_dirs = set(legacy["DEFAULT_EXCLUDED_DIRS"])
        head, candidates = strict_snapshot(root, out_dir, excluded_dirs)
        inv = _build_from_committed_index(root, head, candidates)
        _revalidate_snapshot(root, head)
    except StrictInventoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    legacy["write_json"](inv, out_dir / "rulebook-inventory.json")
    legacy["write_csv"](inv, out_dir / "rulebook-inventory.csv")
    legacy["write_report"](inv, out_dir / "rulebook-inventory-report.md")

    print(f"Wrote inventory to: {out_dir}")
    print(
        f"Files={inv['counts']['total_files']} "
        f"Documents={inv['counts']['documents']} "
        f"GeneratedDocs={inv['counts']['generated_documents']} "
        f"PlayerDocs={inv['counts']['documents_player_site']} "
        f"GMDocs={inv['counts']['documents_gm_site']}"
    )

    bad = bool(inv["mkdocs_config_warnings"]) or inv["counts"]["unresolved_dependency_files"] > 0
    return 1 if bad else 0
