from __future__ import annotations

"""Shared frozen-source snapshot primitives for Cybermancy rulebook tooling.

This module is intentionally dependency-light so both the Step 2 publication
manifest generator and the Step 4 normalizer can use the exact same digest and
structured-identity implementation.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


STRUCTURED_DIGEST_ALGORITHM = (
    "cybermancy-structured-family-digest-v2: "
    "sha256(sorted stable-source-id + tab + repo-path + tab + file-sha256 "
    "over logical publication entities)"
)


class SnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class StructuredRecord:
    source_id: str
    path: Path
    repo_path: str
    sha256: str
    document: dict[str, Any]


@dataclass(frozen=True)
class StructuredFamilySnapshot:
    source_path: str
    digest_sha256: str
    logical_records: tuple[StructuredRecord, ...]
    foundry_folder_count: int
    json_file_count: int

    @property
    def entity_count(self) -> int:
        return len(self.logical_records)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_foundry_folder(doc: dict[str, Any]) -> bool:
    return str(doc.get("_key") or "").startswith("!folders!")


def stable_source_id(doc: dict[str, Any]) -> str:
    value = doc.get("_id")
    if isinstance(value, str) and value.strip():
        return value.strip()

    key = doc.get("_key")
    if isinstance(key, str) and key.strip():
        tail = key.rsplit("!", 1)[-1].strip()
        if tail and tail != key:
            return tail

    raise SnapshotError("STRUCTURED_ID_MISSING")


def structured_family_snapshot(
    repo_root: Path,
    source_path: str,
    actor_type: str | None = None,
) -> StructuredFamilySnapshot:
    """Return the canonical logical snapshot for one structured family.

    The digest is deliberately based on logical publication entities rather
    than every JSON file under the directory. Foundry folder records and actor
    records outside an explicitly selected actor type are not publication
    entities and therefore do not influence the family publication digest.

    Every logical record contributes its stable source ID, repository-relative
    path, and raw file SHA-256. This makes the digest sensitive to identity,
    location, and content while remaining independent of filesystem traversal
    order and display-name slug collisions.
    """
    repo_root = Path(repo_root).resolve()
    family_root = repo_root / source_path
    if not family_root.is_dir():
        raise SnapshotError(f"STRUCTURED_SOURCE_DIR_MISSING: {source_path}")

    json_files = sorted(p for p in family_root.rglob("*.json") if p.is_file())
    folder_count = 0
    records: list[StructuredRecord] = []
    seen_ids: dict[str, str] = {}

    normalized_actor_type = str(actor_type or "").strip()

    for path in json_files:
        repo_rel = path.relative_to(repo_root).as_posix()
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SnapshotError(f"STRUCTURED_JSON_PARSE: {repo_rel}: {exc}") from exc
        if not isinstance(doc, dict):
            raise SnapshotError(f"STRUCTURED_JSON_NOT_OBJECT: {repo_rel}")

        if is_foundry_folder(doc):
            folder_count += 1
            continue

        if normalized_actor_type and str(doc.get("type") or "") != normalized_actor_type:
            continue

        try:
            source_id = stable_source_id(doc)
        except SnapshotError as exc:
            raise SnapshotError(f"{exc}: {repo_rel}") from exc

        previous = seen_ids.get(source_id)
        if previous is not None and previous != repo_rel:
            raise SnapshotError(
                "STRUCTURED_ID_DUPLICATE: "
                f"{source_id!r} occurs in both {previous!r} and {repo_rel!r}"
            )
        seen_ids[source_id] = repo_rel

        records.append(
            StructuredRecord(
                source_id=source_id,
                path=path,
                repo_path=repo_rel,
                sha256=sha256_file(path),
                document=doc,
            )
        )

    records.sort(key=lambda r: (r.source_id, r.repo_path))
    rows = [f"{r.source_id}\t{r.repo_path}\t{r.sha256}" for r in records]
    digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()

    return StructuredFamilySnapshot(
        source_path=source_path,
        digest_sha256=digest,
        logical_records=tuple(records),
        foundry_folder_count=folder_count,
        json_file_count=len(json_files),
    )
