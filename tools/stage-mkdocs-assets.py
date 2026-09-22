#!/usr/bin/env python3
"""
Stage MkDocs source trees so published documentation consumes canonical module
assets from repository /assets instead of requiring duplicate tracked copies
under docs/<audience>/assets.

The staging tree is generated under build/mkdocs/docs and is ignored by Git.

Source precedence for one logical docs asset path is:
  1. /assets                         (canonical module/shared runtime art)
  2. docs/_shared/assets             (canonical docs-only shared art)
  3. docs/<audience>/assets          (audience-specific docs-only art)

If the same logical path exists in more than one source with different bytes,
staging fails rather than silently choosing one.

During the transition away from duplicated docs assets, every currently tracked
audience asset is staged. In addition, textual documentation is scanned for
asset references so root /assets files continue to be staged after redundant
copies are removed from docs/.
"""

from __future__ import annotations

import argparse
import hashlib
import posixpath
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


AUDIENCES = ("player-facing", "gm-facing")
TEXT_SUFFIXES = {
    ".md", ".html", ".htm", ".css", ".js", ".mjs", ".json", ".geojson",
    ".yml", ".yaml", ".csv", ".txt",
}
ASSET_SUFFIXES = {
    ".png", ".webp", ".jpg", ".jpeg", ".svg", ".gif", ".bmp", ".tif",
    ".tiff", ".avif", ".ico", ".geojson", ".json", ".pmtiles",
}
REFERENCE_RE = re.compile(
    r"""(?P<ref>
        (?:(?:\.\./|\./)*)assets/[^\s"'<>]+
        |modules/cybermancy/assets/[^\s"'<>]+
        |worlds/cybermancer/assets/[^\s"'<>]+
        |worlds/cybermancy/assets/[^\s"'<>]+
    )""",
    re.IGNORECASE | re.VERBOSE,
)


class StageError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage Cybermancy MkDocs sources with canonical shared assets."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--audience",
        choices=("all",) + AUDIENCES,
        default="all",
        help="Audience to stage (default: all).",
    )
    parser.add_argument(
        "--keep-stage",
        action="store_true",
        help="Do not clean build/mkdocs before staging.",
    )
    parser.add_argument(
        "--strict-missing",
        action="store_true",
        help="Fail on documentation references whose asset source is already missing.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_map(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def docs_ignore_factory(docs_root: Path):
    audience_roots = {docs_root / audience for audience in AUDIENCES}

    def ignore(directory: str, names: list[str]) -> list[str]:
        current = Path(directory)
        if current in audience_roots and "assets" in names:
            return ["assets"]
        return []

    return ignore


def copy_docs_shell(docs_root: Path, stage_docs_root: Path) -> None:
    shutil.copytree(
        docs_root,
        stage_docs_root,
        dirs_exist_ok=True,
        ignore=docs_ignore_factory(docs_root),
    )


def strip_reference_noise(value: str) -> str:
    value = value.rstrip(").,;:]}!")
    split = urlsplit(value)
    return unquote(split.path)


def output_directory_for(source_rel: Path) -> str:
    """
    Resolve the directory from which a relative URL is evaluated in the built
    site. MkDocs directory URLs render foo.md as foo/index.html, while an
    existing index.md renders in its parent directory.
    """
    suffix = source_rel.suffix.lower()

    if suffix == ".md":
        if source_rel.name.lower() == "index.md":
            return source_rel.parent.as_posix()
        return source_rel.with_suffix("").as_posix()

    return source_rel.parent.as_posix()


def logical_asset_from_reference(raw: str, source_rel: Path) -> str | None:
    ref = strip_reference_noise(raw).replace("\\", "/")
    lower = ref.lower()

    for prefix in (
        "modules/cybermancy/assets/",
        "worlds/cybermancer/assets/",
        "worlds/cybermancy/assets/",
    ):
        if lower.startswith(prefix.lower()):
            logical = ref[len(prefix):]
            return logical.lstrip("/") or None

    if lower.startswith("/assets/"):
        return ref[len("/assets/"):].lstrip("/") or None

    if "assets/" not in lower:
        return None

    base = output_directory_for(source_rel)
    joined = posixpath.normpath(posixpath.join(base, ref))
    if joined == "assets":
        return None
    if joined.startswith("assets/"):
        return joined[len("assets/"):]

    return None


def referenced_assets(audience_root: Path) -> set[str]:
    refs: set[str] = set()

    for path in sorted(audience_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if "assets" in path.relative_to(audience_root).parts:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        source_rel = path.relative_to(audience_root)
        for match in REFERENCE_RE.finditer(text):
            logical = logical_asset_from_reference(match.group("ref"), source_rel)
            if not logical:
                continue
            if "*" in logical or "{" in logical or "}" in logical:
                continue
            if Path(logical).suffix.lower() not in ASSET_SUFFIXES:
                continue
            refs.add(logical)

    return refs


def resolve_source(
    logical: str,
    root_assets: dict[str, Path],
    shared_assets: dict[str, Path],
    audience_assets: dict[str, Path],
) -> tuple[Path | None, str]:
    candidates = [
        ("root-assets", root_assets.get(logical)),
        ("docs-shared", shared_assets.get(logical)),
        ("audience-specific", audience_assets.get(logical)),
    ]
    existing = [(kind, path) for kind, path in candidates if path is not None]

    if not existing:
        return None, "missing"

    hashes = {sha256(path) for _, path in existing}
    if len(hashes) > 1:
        detail = ", ".join(f"{kind}={path}" for kind, path in existing)
        raise StageError(
            f"Conflicting sources for logical asset assets/{logical}: {detail}"
        )

    return existing[0][1], existing[0][0]


def stage_audience(
    repo_root: Path,
    docs_root: Path,
    stage_docs_root: Path,
    audience: str,
    strict_missing: bool,
) -> tuple[dict[str, int], list[str]]:
    root_assets = file_map(repo_root / "assets")
    shared_assets = file_map(docs_root / "_shared" / "assets")
    audience_assets = file_map(docs_root / audience / "assets")

    stage_audience_root = stage_docs_root / audience
    stage_asset_root = stage_audience_root / "assets"
    stage_asset_root.mkdir(parents=True, exist_ok=True)

    # Transitional manifest: preserve every currently published audience asset.
    baseline_assets = set(audience_assets)
    # Shared docs-only assets are deliberately available to both publications.
    baseline_assets.update(shared_assets)

    # Root assets remain available after tracked duplicates are removed from
    # docs/ by deriving requirements from documentation references.
    discovered_references = referenced_assets(stage_audience_root)
    logical_assets = baseline_assets | discovered_references

    counts = {
        "root-assets": 0,
        "docs-shared": 0,
        "audience-specific": 0,
        "total": 0,
    }

    missing_references: list[str] = []

    for logical in sorted(logical_assets):
        source, kind = resolve_source(
            logical,
            root_assets=root_assets,
            shared_assets=shared_assets,
            audience_assets=audience_assets,
        )

        if source is None:
            # A textual docs reference can already be broken in the historical
            # source tree. Preserve current MkDocs behavior by warning rather
            # than making canonicalization fail for unrelated pre-existing
            # content debt. --strict-missing is available for a future cleanup
            # gate. Baseline tracked assets can never legitimately land here.
            if logical in baseline_assets or strict_missing:
                raise StageError(
                    f"Referenced docs asset has no source: assets/{logical}"
                )
            missing_references.append(logical)
            continue

        destination = stage_asset_root / Path(logical)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        counts[kind] += 1
        counts["total"] += 1

    return counts, missing_references


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    docs_root = repo_root / "docs"
    build_root = repo_root / "build" / "mkdocs"
    stage_docs_root = build_root / "docs"

    if not docs_root.is_dir():
        raise StageError(f"Docs source root not found: {docs_root}")
    if not (repo_root / "assets").is_dir():
        raise StageError(f"Canonical asset root not found: {repo_root / 'assets'}")

    if not args.keep_stage and build_root.exists():
        shutil.rmtree(build_root)

    stage_docs_root.mkdir(parents=True, exist_ok=True)
    copy_docs_shell(docs_root, stage_docs_root)

    audiences = AUDIENCES if args.audience == "all" else (args.audience,)

    print("Cybermancy MkDocs asset staging")
    print(f" - source docs: {docs_root.relative_to(repo_root)}")
    print(f" - canonical module assets: {(repo_root / 'assets').relative_to(repo_root)}")
    print(f" - staged docs: {stage_docs_root.relative_to(repo_root)}")

    for audience in audiences:
        counts, missing_references = stage_audience(
            repo_root=repo_root,
            docs_root=docs_root,
            stage_docs_root=stage_docs_root,
            audience=audience,
            strict_missing=args.strict_missing,
        )
        print(
            f" - {audience}: {counts['total']} assets "
            f"(root /assets={counts['root-assets']}, "
            f"docs shared={counts['docs-shared']}, "
            f"audience-only={counts['audience-specific']}, "
            f"pre-existing missing refs={len(missing_references)})"
        )
        for logical in missing_references[:20]:
            print(
                f"   WARNING: referenced asset has no current source: "
                f"assets/{logical}"
            )
        if len(missing_references) > 20:
            print(
                f"   WARNING: {len(missing_references) - 20} additional "
                f"missing references omitted"
            )

    print("MkDocs asset staging PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StageError as error:
        print("MkDocs asset staging FAILED", file=sys.stderr)
        print(f" - {error}", file=sys.stderr)
        raise SystemExit(1)
