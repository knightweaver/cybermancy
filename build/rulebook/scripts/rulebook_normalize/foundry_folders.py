from __future__ import annotations

"""Foundry folder semantics shared by Step 4 publication normalization.

Foundry folder records are not logical publication entities, but selected folder
names can carry publication semantics. Cybermancy uses ``Tier N`` folders as a
fallback Tier source for Equipment item types whose Daggerheart JSON model has
no intrinsic tier field.
"""

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Any, Iterable


_TIER_FOLDER_RE = re.compile(r"^\s*Tier\s*([1-4])\s*$", re.IGNORECASE)
_TIER_VALUE_RE = re.compile(r"^\s*(?:Tier\s*)?([1-4])\s*$", re.IGNORECASE)
_FOLDER_CONTEXTS: dict[str, dict[str, dict[str, Any]]] = {}
FOLDER_TIER_FAMILIES = frozenset({
    "weapons",
    "ammo",
    "armors",
    "cybernetics",
    "drones-devices",
    "consumables",
    "mods",
    "loot",
})


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _folder_id(doc: dict[str, Any]) -> str:
    value = doc.get("_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    key = doc.get("_key")
    if isinstance(key, str) and key.strip():
        tail = key.rsplit("!", 1)[-1].strip()
        if tail and tail != key:
            return tail
    return ""


def normalize_tier(value: Any) -> int | None:
    """Normalize a Cybermancy/Daggerheart Tier value to integer 1..4."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 4 else None
    if isinstance(value, float):
        if value.is_integer() and 1 <= int(value) <= 4:
            return int(value)
        return None
    if isinstance(value, str):
        match = _TIER_VALUE_RE.match(value)
        return int(match.group(1)) if match else None
    return None


def folder_tier(name: Any) -> int | None:
    if not isinstance(name, str):
        return None
    match = _TIER_FOLDER_RE.match(name)
    return int(match.group(1)) if match else None


def build_folder_map(folder_records: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Index Foundry folder records by stable folder ID.

    ``folder_records`` may contain snapshot StructuredRecord objects or raw
    dictionaries to keep this helper dependency-light and easy to test.
    """
    result: dict[str, dict[str, Any]] = {}
    for record in folder_records:
        doc = getattr(record, "document", record)
        if not isinstance(doc, dict):
            continue
        folder_id = _folder_id(doc)
        if not folder_id:
            continue
        result[folder_id] = {
            "id": folder_id,
            "name": str(doc.get("name") or "").strip(),
            "parent": str(doc.get("folder") or "").strip() or None,
            "document": doc,
            "repoPath": getattr(record, "repo_path", None),
        }
    return result


def register_folder_context(source_path: str, folder_records: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Register the current snapshot's folder map for publication helpers.

    Step 2 and Step 4 share the snapshot primitive. Registration is a derived,
    in-process convenience only; no source document is mutated. Family IDs in
    the current manifests match the final component of their source paths.
    """
    folder_map = build_folder_map(folder_records)
    normalized_path = str(source_path or "").replace("\\", "/").strip("/")
    if normalized_path:
        _FOLDER_CONTEXTS[normalized_path.casefold()] = folder_map
        basename = PurePosixPath(normalized_path).name
        if basename:
            _FOLDER_CONTEXTS[basename.casefold()] = folder_map
    return folder_map


def registered_folder_map(family: str) -> dict[str, dict[str, Any]]:
    return _FOLDER_CONTEXTS.get(str(family or "").strip().casefold(), {})


@dataclass(frozen=True)
class TierResolution:
    value: int | None
    source: str
    intrinsic_path: str | None = None
    intrinsic_raw: Any = None
    folder_id: str | None = None
    folder_name: str | None = None
    folder_path: tuple[str, ...] = ()
    folder_tier: int | None = None
    conflict: bool = False
    unresolved_folder_id: str | None = None
    malformed_intrinsic: bool = False

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "value": self.value,
            "source": self.source,
        }
        if self.intrinsic_path:
            data["intrinsicPath"] = self.intrinsic_path
            data["intrinsicRaw"] = self.intrinsic_raw
        if self.folder_id:
            data["folderId"] = self.folder_id
        if self.folder_name:
            data["folderName"] = self.folder_name
        if self.folder_path:
            data["folderPath"] = list(self.folder_path)
        if self.folder_tier is not None:
            data["folderTier"] = self.folder_tier
        if self.conflict:
            data["conflict"] = True
        if self.unresolved_folder_id:
            data["unresolvedFolderId"] = self.unresolved_folder_id
        if self.malformed_intrinsic:
            data["malformedIntrinsic"] = True
        return data


def _intrinsic_tier(doc: dict[str, Any]) -> tuple[str | None, Any]:
    identity = doc.get("identity") if isinstance(doc.get("identity"), dict) else {}
    if _nonempty(identity.get("tier")):
        return "identity.tier", identity.get("tier")
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    if _nonempty(system.get("tier")):
        return "system.tier", system.get("tier")
    return None, None


def _resolve_folder_tier(
    folder_id: Any,
    folder_map: dict[str, dict[str, Any]],
) -> tuple[int | None, str | None, str | None, tuple[str, ...], str | None]:
    current = str(folder_id or "").strip()
    if not current:
        return None, None, None, (), None

    seen: set[str] = set()
    path_names: list[str] = []
    unresolved: str | None = None
    matched_id: str | None = None
    matched_name: str | None = None
    matched_tier: int | None = None

    while current:
        if current in seen:
            unresolved = current
            break
        seen.add(current)
        meta = folder_map.get(current)
        if not meta:
            unresolved = current
            break
        name = str(meta.get("name") or "").strip()
        if name:
            path_names.append(name)
        candidate = folder_tier(name)
        if candidate is not None and matched_tier is None:
            matched_tier = candidate
            matched_id = current
            matched_name = name
        parent = str(meta.get("parent") or "").strip()
        current = parent

    return matched_tier, matched_id, matched_name, tuple(path_names), unresolved


def resolve_publication_tier(
    doc: dict[str, Any],
    folder_map: dict[str, dict[str, Any]],
) -> TierResolution:
    """Resolve reader-facing Tier with intrinsic-first Cybermancy precedence.

    Precedence:
      1. identity.tier
      2. system.tier
      3. nearest recognized Foundry ``Tier N`` folder in the ancestry
      4. absent

    An intrinsic Tier remains authoritative if its folder disagrees. The
    disagreement is surfaced through ``conflict`` rather than silently changing
    the intrinsic value.
    """
    intrinsic_path, intrinsic_raw = _intrinsic_tier(doc)
    intrinsic_value = normalize_tier(intrinsic_raw) if intrinsic_path else None
    folder_value, matched_id, matched_name, folder_path, unresolved = _resolve_folder_tier(
        doc.get("folder"), folder_map
    )

    if intrinsic_path:
        malformed = intrinsic_value is None
        return TierResolution(
            value=intrinsic_value,
            source=intrinsic_path if not malformed else "invalid-intrinsic",
            intrinsic_path=intrinsic_path,
            intrinsic_raw=intrinsic_raw,
            folder_id=matched_id,
            folder_name=matched_name,
            folder_path=folder_path,
            folder_tier=folder_value,
            conflict=(
                intrinsic_value is not None
                and folder_value is not None
                and intrinsic_value != folder_value
            ),
            unresolved_folder_id=unresolved,
            malformed_intrinsic=malformed,
        )

    if folder_value is not None:
        return TierResolution(
            value=folder_value,
            source="foundry-folder",
            folder_id=matched_id,
            folder_name=matched_name,
            folder_path=folder_path,
            folder_tier=folder_value,
            unresolved_folder_id=unresolved,
        )

    return TierResolution(
        value=None,
        source="absent",
        folder_path=folder_path,
        unresolved_folder_id=unresolved,
    )


def resolve_registered_publication_tier(family: str, doc: dict[str, Any]) -> TierResolution:
    normalized_family = str(family or "").strip().casefold()
    folder_map = registered_folder_map(normalized_family) if normalized_family in FOLDER_TIER_FAMILIES else {}
    return resolve_publication_tier(doc, folder_map)
