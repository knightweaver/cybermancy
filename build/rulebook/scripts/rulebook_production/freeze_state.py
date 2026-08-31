from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .contract import selected_manifests, version_key
from .reporting import load_json

INVENTORY_ROOT_RELATIVE = Path("build/rulebook/inventory")
INVENTORY_VALIDATION_ROLES = ("inventoryJson", "inventoryCsv", "inventoryReport")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_tracked(repo_root: Path, path: Path) -> bool:
    repo_root = repo_root.resolve()
    try:
        relative = path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def select_freeze_artifacts(repo_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    return selected_manifests(repo_root, contract)


def freeze_compatibility_details(
    manifests: dict[str, Path],
    publication: dict[str, Any],
    assembly: dict[str, Any],
    normalization: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    publication_path = manifests["publicationManifest"]
    assembly_path = manifests["assemblyManifest"]
    normalization_path = manifests["normalizationConfig"]
    publication_commit = str(publication.get("repository", {}).get("gitCommit") or "")
    assembly_authority = assembly.get("authority") if isinstance(assembly.get("authority"), dict) else {}
    normalization_authority = (
        normalization.get("authority") if isinstance(normalization.get("authority"), dict) else {}
    )
    baseline = normalization.get("baseline") if isinstance(normalization.get("baseline"), dict) else {}
    keys = {
        "publicationManifest": version_key(publication_path),
        "assemblyManifest": version_key(assembly_path),
        "normalizationConfig": version_key(normalization_path),
    }
    same_version = len(set(keys.values())) == 1
    checks = {
        "sameSelectedVersion": same_version,
        "publicationFrozen": publication.get("status") == "FROZEN",
        "assemblyNormative": assembly.get("status") == "NORMATIVE",
        "assemblyParent": assembly_authority.get("parentPublicationManifest") == publication_path.name,
        "assemblyCommit": assembly_authority.get("sourceCommit") == publication_commit,
        "normalizationPublication": normalization_authority.get("publicationManifest") == publication_path.name,
        "normalizationAssembly": normalization_authority.get("assemblyManifest") == assembly_path.name,
        "normalizationCommit": baseline.get("commit") == publication_commit,
    }
    return all(checks.values()), {
        "selected": {role: path.name for role, path in manifests.items()},
        "versionKeys": {role: [list(key[0]), key[1]] for role, key in keys.items()},
        "repositoryCommit": publication_commit,
        "checks": checks,
    }


def _safe_inventory_path(repo_root: Path, filename: str) -> tuple[Path, str]:
    raw = filename.strip()
    if not raw:
        raise ValueError("inventory validation source filename is empty")
    windows = PureWindowsPath(raw)
    normalized = raw.replace("\\", "/")
    posix = PurePosixPath(normalized)
    if windows.is_absolute() or bool(windows.drive) or posix.is_absolute():
        raise ValueError(f"absolute inventory validation source path is not allowed: {filename}")
    if any(part == ".." for part in posix.parts):
        raise ValueError(f"inventory validation source path traversal is not allowed: {filename}")
    if not posix.parts or any(part in {"", "."} for part in posix.parts):
        raise ValueError(f"invalid inventory validation source path: {filename}")

    inventory_root = (repo_root / INVENTORY_ROOT_RELATIVE).resolve()
    candidate = inventory_root.joinpath(*posix.parts).resolve(strict=False)
    try:
        candidate.relative_to(inventory_root)
    except ValueError as exc:
        raise ValueError(
            f"inventory validation source escapes {INVENTORY_ROOT_RELATIVE.as_posix()}: {filename}"
        ) from exc
    return candidate, candidate.relative_to(repo_root.resolve()).as_posix()


def verify_inventory_freeze_binding(
    repo_root: Path,
    publication: dict[str, Any],
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    publication_commit = str((publication.get("repository") or {}).get("gitCommit") or "")
    validation_sources = publication.get("validationSources")
    if not isinstance(validation_sources, dict):
        validation_sources = {}

    artifacts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for role in INVENTORY_VALIDATION_ROLES:
        source = validation_sources.get(role)
        row: dict[str, Any] = {"status": "FAIL"}
        artifacts[role] = row
        if not isinstance(source, dict):
            message = f"selected publication manifest has no validationSources.{role} object"
            row["error"] = message
            errors.append(message)
            continue

        filename = source.get("file")
        expected = str(source.get("sha256") or "").lower()
        row["file"] = filename
        row["expectedSha256"] = expected
        if not isinstance(filename, str) or not filename.strip():
            message = f"selected publication manifest has no validationSources.{role}.file"
            row["error"] = message
            errors.append(message)
            continue
        try:
            path, relative = _safe_inventory_path(repo_root, filename)
        except ValueError as exc:
            row["error"] = str(exc)
            errors.append(str(exc))
            continue

        exists = path.exists()
        regular = path.is_file() and not path.is_symlink()
        tracked = git_tracked(repo_root, path) if regular else False
        actual = sha256_file(path) if regular else None
        hash_matches = bool(_SHA256_RE.fullmatch(expected)) and actual == expected
        row.update(
            path=relative,
            exists=exists,
            regularFile=regular,
            tracked=tracked,
            actualSha256=actual,
            hashMatches=hash_matches,
        )
        row["status"] = "PASS" if exists and regular and tracked and hash_matches else "FAIL"
        if row["status"] != "PASS":
            if not exists:
                errors.append(f"{role} is missing: {relative}")
            elif not regular:
                errors.append(f"{role} is not a regular file: {relative}")
            elif not tracked:
                errors.append(f"{role} is not tracked by Git: {relative}")
            elif not hash_matches:
                errors.append(
                    f"{role} SHA-256 mismatch: expected {expected or '<missing>'}, actual {actual or '<unavailable>'}"
                )

    inventory_commit = ""
    inventory_row = artifacts.get("inventoryJson") or {}
    inventory_path_text = inventory_row.get("path")
    if inventory_path_text and inventory_row.get("regularFile"):
        try:
            inventory_json = load_json(repo_root / str(inventory_path_text))
            inventory_commit = str((inventory_json.get("repository") or {}).get("git_commit") or "")
        except Exception as exc:
            errors.append(f"inventoryJson could not be parsed: {type(exc).__name__}: {exc}")

    commit_matches = bool(publication_commit) and inventory_commit == publication_commit
    if not commit_matches:
        errors.append(
            "inventory/publication source commit mismatch: "
            f"inventory={inventory_commit or '<missing>'}, publication={publication_commit or '<missing>'}"
        )

    status = "PASS" if all(row.get("status") == "PASS" for row in artifacts.values()) and commit_matches else "FAIL"
    return {
        "status": status,
        "inventoryRoot": INVENTORY_ROOT_RELATIVE.as_posix(),
        "publicationCommit": publication_commit,
        "inventoryCommit": inventory_commit,
        "sourceCommitMatches": commit_matches,
        "artifacts": artifacts,
        "errors": errors,
    }


def load_selected_freeze(
    repo_root: Path,
    contract: dict[str, Any],
    manifests: dict[str, Path] | None = None,
) -> dict[str, Any]:
    paths = manifests or select_freeze_artifacts(repo_root, contract)
    publication = load_json(paths["publicationManifest"])
    assembly = load_json(paths["assemblyManifest"])
    normalization = load_json(paths["normalizationConfig"])
    compatible, compatibility = freeze_compatibility_details(
        paths, publication, assembly, normalization
    )
    return {
        "paths": paths,
        "publication": publication,
        "assembly": assembly,
        "normalization": normalization,
        "compatible": compatible,
        "compatibility": compatibility,
        "inventoryBinding": verify_inventory_freeze_binding(repo_root, publication),
    }
