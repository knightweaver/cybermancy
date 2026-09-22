#!/usr/bin/env python3
"""Build a deterministic Cybermancy Foundry runtime-candidate ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

FIXED_DT = (1980, 1, 1, 0, 0, 0)
RUNTIME_DIRS = ("scripts", "styles", "templates", "lang", "assets")
OPTIONAL_ROOT_FILES = ("LICENSE", "README.md")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_db(value: str) -> str:
    return value[:-3] if value.endswith(".db") else value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()

    manifest = json.loads((repo / "module.json").read_text(encoding="utf-8"))
    if manifest.get("id") != "cybermancy":
        raise ValueError("module.json id must be cybermancy")
    version = str(manifest.get("version") or "")
    if not version:
        raise ValueError("module.json version is required")

    runtime_files = [repo / "module.json"]

    for name in OPTIONAL_ROOT_FILES:
        candidate = repo / name
        if candidate.is_file():
            runtime_files.append(candidate)

    for dirname in RUNTIME_DIRS:
        root = repo / dirname
        if root.is_dir():
            runtime_files.extend(sorted(p for p in root.rglob("*") if p.is_file()))

    pack_dirs = []
    for pack in manifest.get("packs", []):
        compiled_rel = strip_db(str(pack.get("path") or ""))
        compiled = repo / compiled_rel
        if not compiled.is_dir():
            raise ValueError(f"Compiled pack missing: {compiled_rel}")
        pack_dirs.append(compiled)
        runtime_files.extend(sorted(p for p in compiled.rglob("*") if p.is_file()))

    runtime_files = [p for p in runtime_files if p.name != ".gitkeep"]
    rel_map = {}
    for file_path in runtime_files:
        rel = file_path.relative_to(repo).as_posix()
        if rel in rel_map:
            raise ValueError(f"Duplicate runtime path: {rel}")
        rel_map[rel] = file_path

    for rel in manifest.get("esmodules", []):
        if rel not in rel_map:
            raise ValueError(f"Declared esmodule missing from runtime package: {rel}")
    for rel in manifest.get("styles", []):
        if rel not in rel_map:
            raise ValueError(f"Declared stylesheet missing from runtime package: {rel}")
    for language in manifest.get("languages", []):
        rel = language.get("path")
        if rel and rel not in rel_map:
            raise ValueError(f"Declared language file missing from runtime package: {rel}")

    release_dir = repo / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    archive = release_dir / f"cybermancy-v{version}.zip"

    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for rel in sorted(rel_map):
            file_path = rel_map[rel]
            info = zipfile.ZipInfo(rel, FIXED_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, file_path.read_bytes())

    digest = sha256(archive)
    report_dir = repo / "build" / "release"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "PASS",
        "moduleId": "cybermancy",
        "moduleVersion": version,
        "archive": archive.name,
        "archiveSha256": digest,
        "runtimeFileCount": len(rel_map),
        "compiledCompendiumCount": len(pack_dirs),
        "canonical": False,
        "purpose": "clean-install Foundry runtime qualification candidate",
    }
    (report_dir / "runtime-package.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
