#!/usr/bin/env python3
"""Validate and stage an exact manually qualified Cybermancy release artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--control", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    control_path = (
        (repo / args.control).resolve()
        if not args.control.is_absolute()
        else args.control.resolve()
    )

    control = json.loads(control_path.read_text(encoding="utf-8"))
    module = json.loads((repo / "module.json").read_text(encoding="utf-8"))
    runtime = json.loads(
        (repo / "build" / "release" / "runtime-package.json").read_text(encoding="utf-8")
    )
    equivalence = json.loads(
        (repo / "build" / "release" / "runtime-equivalence.json").read_text(encoding="utf-8")
    )

    version = str(control.get("version") or "")
    tag = str(control.get("tag") or "")
    if control.get("publish") is not True:
        raise ValueError("release control must explicitly set publish=true")
    if version != module.get("version"):
        raise ValueError(f"release version {version} != module version {module.get('version')}")
    if tag != f"v{version}":
        raise ValueError(f"release tag must be v{version}, got {tag}")

    qualification = control.get("qualification") or {}
    if qualification.get("status") != "PASS":
        raise ValueError("manual clean-install qualification PASS is required")

    runtime_target = control.get("runtime") or {}
    if str(runtime_target.get("foundryCore")) != "14.368":
        raise ValueError("release-control Foundry qualification target must be 14.368")
    if str(runtime_target.get("system")) != "daggerheart":
        raise ValueError("release-control system must be daggerheart")
    if str(runtime_target.get("systemVersion")) != "2.10.5":
        raise ValueError("release-control Daggerheart qualification target must be 2.10.5")

    pack_paths = [str(pack.get("path") or "") for pack in module.get("packs", [])]
    if len(pack_paths) != 15:
        raise ValueError(f"v0.2.0 release must declare 15 Compendia, got {len(pack_paths)}")
    invalid_pack_paths = [p for p in pack_paths if not p.endswith(".db") or p.endswith(".db.db")]
    if invalid_pack_paths:
        raise ValueError(
            f"v0.2.0 release contains invalid Foundry 14 Compendium paths: {invalid_pack_paths}"
        )

    expected_hash = str(control.get("qualifiedRuntimeSha256") or "")
    if len(expected_hash) != 64:
        raise ValueError("qualifiedRuntimeSha256 must be a SHA-256 digest")
    if not control.get("qualifiedWorkflowRunId"):
        raise ValueError("qualifiedWorkflowRunId is required")
    if not control.get("qualifiedArtifactName"):
        raise ValueError("qualifiedArtifactName is required")

    if runtime.get("status") != "PASS":
        raise ValueError("fresh runtime rebuild is not PASS")
    if runtime.get("compiledCompendiumCount") != 15:
        raise ValueError("fresh runtime rebuild does not contain all 15 compiled Compendia")
    if runtime.get("foundry14DbManifestPathsValidated") is not True:
        raise ValueError("fresh runtime rebuild did not validate Foundry 14 .db manifest paths")
    if equivalence.get("status") != "PASS" or equivalence.get("forbiddenDifferenceCount") != 0:
        raise ValueError("fresh rebuild did not pass runtime equivalence validation")
    if equivalence.get("qualifiedSha256") != expected_hash:
        raise ValueError("downloaded qualified artifact hash differs from release control")

    archive_name = f"cybermancy-v{version}.zip"
    archive = repo / "release" / archive_name
    if not archive.is_file():
        raise ValueError(f"qualified runtime archive missing: {archive}")
    actual_hash = sha256(archive)
    if actual_hash != expected_hash:
        raise ValueError(
            f"published archive must be exact qualified candidate: expected {expected_hash}, got {actual_hash}"
        )

    expected_manifest = (
        "https://github.com/knightweaver/cybermancy/releases/latest/download/module.json"
    )
    expected_download = (
        f"https://github.com/knightweaver/cybermancy/releases/download/{tag}/{archive_name}"
    )
    if module.get("manifest") != expected_manifest:
        raise ValueError(f"module.json manifest URL mismatch: {module.get('manifest')}")
    if module.get("download") != expected_download:
        raise ValueError(f"module.json download URL mismatch: {module.get('download')}")

    release_dir = repo / "release"
    release_module = release_dir / "module.json"
    shutil.copy2(repo / "module.json", release_module)

    checksums = {
        archive_name: sha256(archive),
        "module.json": sha256(release_module),
    }
    (release_dir / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )

    summary = {
        "status": "READY_TO_PUBLISH",
        "version": version,
        "tag": tag,
        "qualifiedRuntimeSha256": expected_hash,
        "publishedArchiveIsExactQualifiedRuntime": True,
        "freshRebuildEquivalentExceptLevelDbLogs": True,
        "releaseAssets": [archive_name, "module.json", "SHA256SUMS.txt"],
        "manifestUrl": expected_manifest,
        "downloadUrl": expected_download,
    }
    report = repo / "build" / "release" / "prepublish.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
