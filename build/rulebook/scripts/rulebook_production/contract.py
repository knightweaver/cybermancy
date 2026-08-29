from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .reporting import load_json


CONTRACT_RELATIVE_PATH = Path("build/rulebook/production/production-renderer-v1.json")
METADATA_RELATIVE_PATH = Path("build/rulebook/production/publication-metadata-v1.json")
VERSION_RE = re.compile(r"-v(?P<version>\d+(?:\.\d+)*)(?:-r(?P<revision>\d+))?", re.I)


def canonical_text_sha256(payload: bytes) -> str:
    text = payload.decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_production_contract(repo_root: Path, path: Path | None = None) -> dict[str, Any]:
    contract_path = path or repo_root / CONTRACT_RELATIVE_PATH
    contract = load_json(contract_path)
    if contract.get("schema") != "cybermancy-production-renderer-contract-v1":
        raise ValueError(f"Unsupported production contract schema: {contract_path}")
    if contract.get("version") != "1.0" or contract.get("contractStatus") != "ACCEPTED":
        raise ValueError(f"Production Renderer v1 contract is not accepted: {contract_path}")
    return contract


def load_publication_metadata(repo_root: Path) -> dict[str, Any]:
    metadata = load_json(repo_root / METADATA_RELATIVE_PATH)
    if metadata.get("schema") != "cybermancy-publication-metadata-v1":
        raise ValueError("Unsupported publication metadata schema")
    return metadata


def version_key(path: Path) -> tuple[tuple[int, ...], int]:
    match = VERSION_RE.search(path.name)
    if not match:
        raise ValueError(f"Could not parse version from {path.name}")
    return (
        tuple(int(part) for part in match.group("version").split(".")),
        int(match.group("revision") or 0),
    )


def select_latest(directory: Path, pattern: str) -> Path:
    candidates = []
    for path in directory.glob(pattern) if directory.is_dir() else []:
        if not path.is_file():
            continue
        try:
            candidates.append((version_key(path), path.resolve()))
        except ValueError:
            continue
    if not candidates:
        raise FileNotFoundError(f"No files match {pattern} in {directory}")
    top_key = max(key for key, _ in candidates)
    top = [path for key, path in candidates if key == top_key]
    if len(top) != 1:
        raise ValueError(
            f"Ambiguous latest version for {pattern}: "
            + ", ".join(path.name for path in top)
        )
    return top[0]


def selected_manifests(repo_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for role in ("publicationManifest", "assemblyManifest", "normalizationConfig"):
        authority = contract["authorities"][role]
        directory = repo_root / authority["directory"]
        result[role] = select_latest(directory, authority["pattern"])
    return result


def verify_frozen_bindings(repo_root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = [contract["authorities"]["step6IntegrationContract"]]
    bindings.extend(contract["frozenPackageBindings"])
    results = []
    for binding in bindings:
        path = repo_root / binding["path"]
        actual = canonical_text_sha256(path.read_bytes()) if path.is_file() else None
        results.append(
            {
                "path": binding["path"],
                "expectedSha256": binding["sha256"],
                "actualSha256": actual,
                "status": "PASS" if actual == binding["sha256"] else "FAIL",
            }
        )
    return results
