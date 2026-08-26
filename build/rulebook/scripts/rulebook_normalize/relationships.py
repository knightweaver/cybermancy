from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


COMPENDIUM_ITEM_RE = re.compile(
    r"^Compendium\.cybermancy\.(?P<pack>[^.]+)\.Item\.(?P<source_id>[^.]+)$"
)

PACK_FAMILY_OVERRIDES = {
    "cybermancy-classes": "classes",
    "cybermancy-subclasses": "subclasses",
    "cybermancy-features": "features",
    "cybermancy-weapons": "weapons",
    "cybermancy-armors": "armors",
    "cybermancy-consumables": "consumables",
    "cybermancy-loot": "loot",
    "cybermancy-cybernetics": "cybernetics",
    "cybermancy-mods": "mods",
    "cybermancy-ammo": "ammo",
    "cybermancy-drones-devices": "drones-devices",
}

CLASS_FEATURE_TYPES = {"hope", "class"}
SUBCLASS_FEATURE_TYPES = {"foundation", "specialization", "mastery"}


def _family_from_pack(pack: str) -> str:
    if pack in PACK_FAMILY_OVERRIDES:
        return PACK_FAMILY_OVERRIDES[pack]
    if pack.startswith("cybermancy-"):
        return pack[len("cybermancy-") :]
    return pack


def _semantic_parts(value: str) -> tuple[str, str] | None:
    if not value.startswith("entity:"):
        return None
    parts = value.split(":", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        return None
    return parts[1], parts[2]


def _reference_parts(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    semantic = _semantic_parts(text)
    if semantic is not None:
        return semantic
    match = COMPENDIUM_ITEM_RE.fullmatch(text)
    if not match:
        return None
    return _family_from_pack(match.group("pack")), match.group("source_id")


def _issue(
    code: str,
    owner: dict,
    field: str,
    message: str,
    raw_reference: Any = None,
    **details: Any,
) -> dict:
    item = {
        "code": code,
        "ownerSemanticId": owner.get("semanticId"),
        "ownerFamily": owner.get("family"),
        "ownerName": owner.get("name"),
        "field": field,
        "message": message,
    }
    if raw_reference not in (None, ""):
        item["rawReference"] = raw_reference
    if details:
        item.update(details)
    return item


def _resolve_reference(
    raw_reference: Any,
    index: dict[tuple[str, str], dict],
    owner: dict,
    field: str,
    errors: list[dict],
    expected_family: str | None = None,
) -> str | None:
    parts = _reference_parts(raw_reference)
    if parts is None:
        errors.append(
            _issue(
                "RELATION_REFERENCE_INVALID",
                owner,
                field,
                "Reference is not a supported Foundry Item UUID or semantic entity ID.",
                raw_reference,
            )
        )
        return None
    family, source_id = parts
    if expected_family is not None and family != expected_family:
        errors.append(
            _issue(
                "RELATION_REFERENCE_FAMILY",
                owner,
                field,
                f"Reference resolves to family {family!r}; expected {expected_family!r}.",
                raw_reference,
                resolvedFamily=family,
                expectedFamily=expected_family,
            )
        )
        return None
    target = index.get((family, source_id))
    if target is None:
        errors.append(
            _issue(
                "RELATION_REFERENCE_UNRESOLVED",
                owner,
                field,
                f"Reference target entity:{family}:{source_id} is not present in the Step 4 structured corpus.",
                raw_reference,
                resolvedFamily=family,
                resolvedSourceId=source_id,
            )
        )
        return None
    return str(target["semanticId"])


def _resolve_list(
    values: Any,
    index: dict[tuple[str, str], dict],
    owner: dict,
    field: str,
    errors: list[dict],
    expected_family: str | None = None,
) -> list[str]:
    if values in (None, ""):
        return []
    if not isinstance(values, list):
        errors.append(
            _issue(
                "RELATION_LIST_INVALID",
                owner,
                field,
                "Relationship field must be a list.",
            )
        )
        return []
    resolved: list[str] = []
    for idx, value in enumerate(values):
        semantic = _resolve_reference(
            value,
            index,
            owner,
            f"{field}[{idx}]",
            errors,
            expected_family=expected_family,
        )
        if semantic is not None:
            resolved.append(semantic)
    return resolved


def _resolve_typed_features(
    values: Any,
    allowed_types: set[str],
    index: dict[tuple[str, str], dict],
    owner: dict,
    field: str,
    errors: list[dict],
    feature_usage: dict[str, list[dict]],
) -> list[dict]:
    if values in (None, ""):
        return []
    if not isinstance(values, list):
        errors.append(_issue("RELATION_FEATURE_LIST_INVALID", owner, field, "Feature relationship field must be a list."))
        return []
    resolved: list[dict] = []
    for idx, value in enumerate(values):
        if not isinstance(value, dict):
            errors.append(
                _issue(
                    "RELATION_FEATURE_ENTRY_INVALID",
                    owner,
                    f"{field}[{idx}]",
                    "Feature relationship entry must be an object containing type and item.",
                )
            )
            continue
        feature_type = str(value.get("type") or "").strip().casefold()
        if feature_type not in allowed_types:
            errors.append(
                _issue(
                    "RELATION_FEATURE_TYPE_INVALID",
                    owner,
                    f"{field}[{idx}].type",
                    f"Feature relationship type {feature_type!r} is not valid for {owner.get('family')}.",
                    value.get("type"),
                    allowedTypes=sorted(allowed_types),
                )
            )
            continue
        semantic = _resolve_reference(
            value.get("item"),
            index,
            owner,
            f"{field}[{idx}].item",
            errors,
            expected_family="features",
        )
        if semantic is None:
            continue
        resolved.append({"type": feature_type, "semanticId": semantic})
        feature_usage[semantic].append(
            {
                "ownerSemanticId": owner["semanticId"],
                "ownerFamily": owner["family"],
                "relationship": feature_type,
            }
        )
    return resolved


def _resolve_inventory(
    system: dict,
    index: dict[tuple[str, str], dict],
    owner: dict,
    errors: list[dict],
) -> dict:
    inventory = system.get("inventory")
    if not isinstance(inventory, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key in ("take", "choiceA", "choiceB"):
        values = inventory.get(key)
        if not isinstance(values, list):
            if values not in (None, ""):
                errors.append(_issue("RELATION_INVENTORY_INVALID", owner, f"system.inventory.{key}", "Inventory relationship field must be a list."))
            continue
        resolved: list[str] = []
        for idx, value in enumerate(values):
            semantic = _resolve_reference(
                value,
                index,
                owner,
                f"system.inventory.{key}[{idx}]",
                errors,
            )
            if semantic is not None:
                resolved.append(semantic)
        if resolved:
            result[key] = resolved
    return result


def _resolve_character_guide(
    system: dict,
    index: dict[tuple[str, str], dict],
    owner: dict,
    errors: list[dict],
) -> dict:
    guide = system.get("characterGuide")
    if not isinstance(guide, dict):
        return {}
    result: dict[str, Any] = {}
    traits = guide.get("suggestedTraits")
    if isinstance(traits, dict) and traits:
        result["suggestedTraits"] = dict(traits)
    for key, family in (
        ("suggestedPrimaryWeapon", "weapons"),
        ("suggestedSecondaryWeapon", "weapons"),
        ("suggestedArmor", "armors"),
    ):
        raw = guide.get(key)
        if raw in (None, ""):
            result[key] = None
            continue
        result[key] = _resolve_reference(
            raw,
            index,
            owner,
            f"system.characterGuide.{key}",
            errors,
            expected_family=family,
        )
    return result


def apply_class_relationship_semantics(
    source_records: list[dict],
    sidecar_entities: list[dict],
) -> dict:
    """Resolve Class -> Subclass -> Feature relationships into semantic IDs.

    ``source_records`` retain the canonical Foundry documents only for this
    deterministic Step 4 pass. ``sidecar_entities`` are the derived publication
    records and are enriched in place. No Foundry UUID is copied into the
    publication relationship fields.
    """
    errors: list[dict] = []
    source_by_semantic = {
        str(record.get("semanticId")): record
        for record in source_records
        if record.get("semanticId")
    }
    sidecar_by_semantic = {
        str(entity.get("semanticId")): entity
        for entity in sidecar_entities
        if entity.get("semanticId")
    }
    index: dict[tuple[str, str], dict] = {}
    for entity in sidecar_entities:
        family = str(entity.get("family") or "")
        source_id = str(entity.get("sourceId") or "")
        if not family or not source_id:
            continue
        key = (family, source_id)
        if key in index:
            errors.append(
                {
                    "code": "RELATION_INDEX_DUPLICATE",
                    "family": family,
                    "sourceId": source_id,
                    "message": f"Multiple Step 4 entities share {family}:{source_id}.",
                }
            )
            continue
        index[key] = entity

    feature_usage: dict[str, list[dict]] = defaultdict(list)
    class_declared_subclasses: dict[str, list[str]] = {}
    subclass_linked_class: dict[str, str] = {}
    class_count = 0
    subclass_count = 0
    feature_edge_count = 0

    for semantic_id, record in sorted(source_by_semantic.items()):
        family = str(record.get("family") or "")
        if family not in {"classes", "subclasses"}:
            continue
        sidecar = sidecar_by_semantic.get(semantic_id)
        if sidecar is None:
            errors.append(
                {
                    "code": "RELATION_SIDECAR_MISSING",
                    "ownerSemanticId": semantic_id,
                    "message": "Structured source has no matching sidecar entity.",
                }
            )
            continue
        owner = {
            "semanticId": semantic_id,
            "family": family,
            "name": sidecar.get("name"),
        }
        doc = record.get("document") if isinstance(record.get("document"), dict) else {}
        system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
        publication = sidecar.setdefault("publicationData", {})

        if family == "classes":
            class_count += 1
            typed_features = _resolve_typed_features(
                system.get("features"),
                CLASS_FEATURE_TYPES,
                index,
                owner,
                "system.features",
                errors,
                feature_usage,
            )
            publication["features"] = typed_features
            feature_edge_count += len(typed_features)

            subclasses = _resolve_list(
                system.get("subclasses"),
                index,
                owner,
                "system.subclasses",
                errors,
                expected_family="subclasses",
            )
            publication["subclasses"] = subclasses
            class_declared_subclasses[semantic_id] = subclasses

            class_items = _resolve_list(
                system.get("classItems"),
                index,
                owner,
                "system.classItems",
                errors,
            )
            if class_items:
                publication["classItems"] = class_items

            inventory = _resolve_inventory(system, index, owner, errors)
            if inventory:
                publication["startingInventory"] = inventory

            guide = _resolve_character_guide(system, index, owner, errors)
            if guide:
                publication["characterGuide"] = guide

        else:
            subclass_count += 1
            linked_class = _resolve_reference(
                system.get("linkedClass"),
                index,
                owner,
                "system.linkedClass",
                errors,
                expected_family="classes",
            )
            if linked_class is not None:
                publication["linkedClass"] = linked_class
                subclass_linked_class[semantic_id] = linked_class

            typed_features = _resolve_typed_features(
                system.get("features"),
                SUBCLASS_FEATURE_TYPES,
                index,
                owner,
                "system.features",
                errors,
                feature_usage,
            )
            progression = {key: [] for key in ("foundation", "specialization", "mastery")}
            for item in typed_features:
                progression[item["type"]].append(item["semanticId"])
            publication["progression"] = progression
            feature_edge_count += len(typed_features)

    declared_by_subclass: dict[str, list[str]] = defaultdict(list)
    for class_semantic, subclass_semantics in class_declared_subclasses.items():
        for subclass_semantic in subclass_semantics:
            declared_by_subclass[subclass_semantic].append(class_semantic)

    all_subclasses = sorted(
        entity["semanticId"]
        for entity in sidecar_entities
        if entity.get("family") == "subclasses" and entity.get("semanticId")
    )
    for subclass_semantic in all_subclasses:
        owners = sorted(set(declared_by_subclass.get(subclass_semantic, [])))
        linked = subclass_linked_class.get(subclass_semantic)
        sidecar = sidecar_by_semantic[subclass_semantic]
        owner = {
            "semanticId": subclass_semantic,
            "family": "subclasses",
            "name": sidecar.get("name"),
        }
        if linked is None:
            errors.append(_issue("SUBCLASS_LINKED_CLASS_MISSING", owner, "system.linkedClass", "Subclass does not resolve to exactly one linked Class."))
        if len(owners) != 1:
            errors.append(
                _issue(
                    "SUBCLASS_CLASS_DECLARATION_COUNT",
                    owner,
                    "system.linkedClass",
                    f"Subclass is declared by {len(owners)} Class records; exactly one is required.",
                    declaringClasses=owners,
                )
            )
        elif linked is not None and owners[0] != linked:
            errors.append(
                _issue(
                    "SUBCLASS_CLASS_BIDIRECTIONAL_MISMATCH",
                    owner,
                    "system.linkedClass",
                    "Subclass linkedClass and Class subclasses declarations disagree.",
                    linkedClass=linked,
                    declaringClass=owners[0],
                )
            )

    for feature_semantic, usages in sorted(feature_usage.items()):
        feature = sidecar_by_semantic.get(feature_semantic)
        if feature is None:
            continue
        publication = feature.setdefault("publicationData", {})
        publication["usedBy"] = sorted(
            usages,
            key=lambda item: (
                str(item.get("ownerFamily") or "").casefold(),
                str(item.get("ownerSemanticId") or ""),
                str(item.get("relationship") or ""),
            ),
        )

    return {
        "errors": errors,
        "classCount": class_count,
        "subclassCount": subclass_count,
        "featureEdgeCount": feature_edge_count,
        "featureTargetCount": len(feature_usage),
    }
