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

from .foundry_folders import FOLDER_TIER_FAMILIES, register_folder_context


STRUCTURED_DIGEST_VERSION = 3
STRUCTURED_DIGEST_ALGORITHM = (
    "cybermancy-structured-family-digest-v3: "
    "sha256(sorted record-kind + tab + stable-source-id + tab + repo-path + tab + "
    "file-sha256 over logical publication entities, plus Foundry folder records "
    "for Equipment families with folder-derived publication semantics)"
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
    folder_records: tuple[StructuredRecord, ...]
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


def _source_family(source_path: str) -> str:
    normalized = str(source_path or "").replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1].casefold() if normalized else ""


def structured_family_snapshot(
    repo_root: Path,
    source_path: str,
    actor_type: str | None = None,
) -> StructuredFamilySnapshot:
    """Return the canonical logical snapshot for one structured family.

    Logical publication entities determine entity counts. Foundry folder
    records remain non-entities. Beginning with digest v3, folder records are
    included in the digest only for Equipment families whose publication
    semantics can derive Tier from Foundry folder ancestry.

    Every digest record contributes a record kind, stable source ID,
    repository-relative path, and raw file SHA-256. Equipment-family digests are
    therefore sensitive to entity content/location and to folder names/ancestry
    without inflating logical publication entity counts. Organizational folders
    in unrelated structured families do not change their frozen digest.
    """
    repo_root = Path(repo_root).resolve()
    family_root = repo_root / source_path
    if not family_root.is_dir():
        raise SnapshotError(f"STRUCTURED_SOURCE_DIR_MISSING: {source_path}")

    json_files = sorted(p for p in family_root.rglob("*.json") if p.is_file())
    records: list[StructuredRecord] = []
    folder_records: list[StructuredRecord] = []
    seen_ids: dict[str, str] = {}
    seen_folder_ids: dict[str, str] = {}

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
            try:
                folder_id = stable_source_id(doc)
            except SnapshotError as exc:
                raise SnapshotError(f"{exc}: {repo_rel}") from exc
            previous = seen_folder_ids.get(folder_id)
            if previous is not None and previous != repo_rel:
                raise SnapshotError(
                    "STRUCTURED_FOLDER_ID_DUPLICATE: "
                    f"{folder_id!r} occurs in both {previous!r} and {repo_rel!r}"
                )
            seen_folder_ids[folder_id] = repo_rel
            folder_records.append(
                StructuredRecord(
                    source_id=folder_id,
                    path=path,
                    repo_path=repo_rel,
                    sha256=sha256_file(path),
                    document=doc,
                )
            )
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
    folder_records.sort(key=lambda r: (r.source_id, r.repo_path))
    folder_semantics = _source_family(source_path) in FOLDER_TIER_FAMILIES
    digest_rows = [
        f"entity\t{r.source_id}\t{r.repo_path}\t{r.sha256}"
        for r in records
    ]
    if folder_semantics:
        digest_rows.extend(
            f"folder\t{r.source_id}\t{r.repo_path}\t{r.sha256}"
            for r in folder_records
        )
    digest_rows.sort()
    digest = hashlib.sha256("\n".join(digest_rows).encode("utf-8")).hexdigest()

    # Register only folder semantics that Step 4 is allowed to consume. The
    # registration is derived, in-process state and never mutates source data.
    register_folder_context(source_path, folder_records if folder_semantics else ())

    return StructuredFamilySnapshot(
        source_path=source_path,
        digest_sha256=digest,
        logical_records=tuple(records),
        folder_records=tuple(folder_records),
        foundry_folder_count=len(folder_records),
        json_file_count=len(json_files),
    )
