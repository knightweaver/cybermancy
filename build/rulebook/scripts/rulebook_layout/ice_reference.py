from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_SIDECAR_SCHEMA = "cybermancy-step4-structured-entities-v1.3"
SUPPORTED_ICE_SEMANTICS_SCHEMA = "cybermancy-step4-ice-semantics-v1.0"
VIEW_SCHEMA = "cybermancy-step6-ice-reference-package-view-v1.0"
ICE_TYPES = ("sentry", "wall")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def new_report() -> dict[str, Any]:
    return {"status": "PASS", "errors": [], "warnings": [], "checks": []}


def _add_check(
    report: dict[str, Any],
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status == "ERROR":
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status == "WARNING":
        report["warnings"].append(item)


def _publication(entity: dict[str, Any]) -> dict[str, Any]:
    value = entity.get("publicationData")
    return value if isinstance(value, dict) else {}


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("+-").isdigit():
            return int(text)
    return None


def _index_entities(
    sidecar: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = sidecar.get("entities")
    if not isinstance(rows, list):
        _add_check(report, "ICE_REFERENCE_ENTITIES", "ERROR", "Step 4 sidecar has no entities array.")
        return {}
    index: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        semantic_id = str(row.get("semanticId") or "").strip()
        if not semantic_id:
            continue
        if semantic_id in index:
            duplicates.append(semantic_id)
        else:
            index[semantic_id] = row
    _add_check(
        report,
        "ICE_REFERENCE_ENTITY_IDENTITY",
        "ERROR" if duplicates else "PASS",
        "Step 4 sidecar contains duplicate semantic IDs." if duplicates else f"Indexed {len(index)} unique Step 4 semantic entities.",
        sorted(set(duplicates)) if duplicates else None,
    )
    return index


def _ice_semantics(
    sidecar: dict[str, Any],
    config: dict[str, Any],
    report: dict[str, Any],
) -> tuple[list[str], dict[str, int]]:
    policy = config.get("prototypePolicy") if isinstance(config.get("prototypePolicy"), dict) else {}
    required_schema = str(policy.get("requireIceSemanticsSchema") or SUPPORTED_ICE_SEMANTICS_SCHEMA)
    required_status = str(policy.get("requireIceSemanticsStatus") or "PASS")
    semantics = sidecar.get("iceSemantics") if isinstance(sidecar.get("iceSemantics"), dict) else {}
    schema = str(semantics.get("schema") or "")
    status = str(semantics.get("status") or "")
    ok = schema == required_schema and status == required_status
    _add_check(
        report,
        "ICE_REFERENCE_ICE_SEMANTICS",
        "PASS" if ok else "ERROR",
        "Step 4 ICE semantics are available for ICEReferencePackage composition." if ok else "Step 4 ICE semantics are missing, stale, or failed.",
        {"actualSchema": schema, "requiredSchema": required_schema, "actualStatus": status, "requiredStatus": required_status},
    )
    raw_ids = semantics.get("semanticIds")
    semantic_ids = [str(value).strip() for value in raw_ids if str(value).strip()] if isinstance(raw_ids, list) else []
    if not semantic_ids:
        _add_check(report, "ICE_REFERENCE_SEMANTIC_IDS", "ERROR", "Step 4 iceSemantics.semanticIds is missing or empty.")
    raw_counts = semantics.get("counts")
    counts: dict[str, int] = {}
    if isinstance(raw_counts, dict):
        for ice_type in ICE_TYPES:
            count = _integer(raw_counts.get(ice_type))
            if count is not None:
                counts[ice_type] = count
    expected_counts = policy.get("expectedIceCounts") if isinstance(policy.get("expectedIceCounts"), dict) else {}
    expected_total = _integer(policy.get("expectedIceTotal"))
    count_errors: list[dict[str, Any]] = []
    for ice_type in ICE_TYPES:
        expected = _integer(expected_counts.get(ice_type))
        if expected is not None and counts.get(ice_type) != expected:
            count_errors.append({"iceType": ice_type, "expected": expected, "actual": counts.get(ice_type)})
    if expected_total is not None and len(semantic_ids) != expected_total:
        count_errors.append({"iceType": "total", "expected": expected_total, "actual": len(semantic_ids)})
    _add_check(
        report,
        "ICE_REFERENCE_CORPUS_COUNT",
        "ERROR" if count_errors else "PASS",
        "Step 4 ICE corpus counts do not match the H2 contract." if count_errors else f"Step 4 exposes {len(semantic_ids)} ICE entities with the expected type counts.",
        count_errors if count_errors else {"counts": counts, "total": len(semantic_ids)},
    )
    return semantic_ids, counts


def _selected_ids(all_ice_ids: list[str], config: dict[str, Any], report: dict[str, Any]) -> list[str]:
    prototype = config.get("prototype") if isinstance(config.get("prototype"), dict) else {}
    raw = prototype.get("semanticIds")
    if not isinstance(raw, list) or not raw:
        return list(all_ice_ids)
    selected = [str(value).strip() for value in raw if str(value).strip()]
    duplicates = sorted({sid for sid in selected if selected.count(sid) > 1})
    unknown = sorted(set(selected) - set(all_ice_ids))
    if duplicates:
        _add_check(report, "ICE_REFERENCE_PROTOTYPE_DUPLICATE", "ERROR", "H2 prototype selection contains duplicate semantic IDs.", duplicates)
    if unknown:
        _add_check(report, "ICE_REFERENCE_PROTOTYPE_SCOPE", "ERROR", "H2 prototype selection contains entities outside Step 4 ICE semantics.", unknown)
    if not duplicates and not unknown:
        _add_check(report, "ICE_REFERENCE_PROTOTYPE_SCOPE", "PASS", f"Selected {len(selected)} representative ICE entities for the H2 proof.")
    return selected


def _has_reader_rules(publication: dict[str, Any]) -> bool:
    if str(publication.get("rulesMarkdown") or "").strip():
        return True
    actions = publication.get("actions")
    if not isinstance(actions, list):
        return False
    for action in actions:
        if not isinstance(action, dict):
            continue
        if str(action.get("rulesMarkdown") or "").strip() or action.get("damage") or action.get("cost") or action.get("range") or action.get("target"):
            return True
    return False


def _public_action(action: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("name", "type", "actionType", "rulesMarkdown", "cost", "uses", "range", "target", "damage"):
        value = action.get(key)
        if value not in (None, "", [], {}):
            result[key] = value
    return result


def _entry_view(
    entity: dict[str, Any],
    report: dict[str, Any],
    *,
    require_gm: bool,
    require_rules: bool,
) -> dict[str, Any] | None:
    semantic_id = str(entity.get("semanticId") or "").strip()
    name = str(entity.get("name") or "").strip()
    source_id = str(entity.get("sourceId") or "").strip()
    family = str(entity.get("family") or "").strip()
    audience = str(entity.get("audience") or "").strip()
    publication = _publication(entity)
    errors: list[str] = []
    if family != "features":
        errors.append(f"family={family!r}")
    if require_gm and audience != "gm":
        errors.append(f"audience={audience!r}")
    if str(publication.get("featureCategory") or "") != "ice":
        errors.append("publicationData.featureCategory is not 'ice'")
    ice_type = str(publication.get("iceType") or "").strip().casefold()
    if ice_type not in ICE_TYPES:
        errors.append(f"publicationData.iceType={ice_type!r}")
    if publication.get("standalonePublication") is not True:
        errors.append("publicationData.standalonePublication is not true")
    if not name:
        errors.append("name is missing")
    if require_rules and not _has_reader_rules(publication):
        errors.append("reader-facing rules are missing")
    if errors:
        _add_check(report, "ICE_REFERENCE_ENTRY_SEMANTICS", "ERROR", f"{semantic_id or '<unknown ICE>'} is not publication-complete.", errors)
        return None
    actions = publication.get("actions")
    public_actions = [_public_action(action) for action in actions if isinstance(action, dict)] if isinstance(actions, list) else []
    result: dict[str, Any] = {
        "semanticId": semantic_id,
        "name": name,
        "iceType": ice_type,
        "rulesMarkdown": str(publication.get("rulesMarkdown") or "").strip(),
        "actions": [row for row in public_actions if row],
    }
    resource = publication.get("resource")
    if isinstance(resource, dict) and resource:
        result["resource"] = {key: resource.get(key) for key in ("type", "value", "max") if resource.get(key) not in (None, "")}
    result["_sortSourceId"] = source_id
    return result


def _source_leakage(view: dict[str, Any]) -> list[str]:
    raw = json.dumps(view, ensure_ascii=False)
    forbidden = ("Compendium.", "modules/", "worlds/", "src/packs/", "src-loadable/", "docs/", "!folders!", "systemPath", "chatDisplay", "originItem")
    return [token for token in forbidden if token in raw]


def compose_ice_reference(
    sidecar: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Compose the H2 ICEReferencePackage proof entirely from Step 4 semantics."""
    report = new_report()
    config = config or {}
    policy = config.get("prototypePolicy") if isinstance(config.get("prototypePolicy"), dict) else {}
    required_sidecar_schema = str(policy.get("requireStructuredSidecarSchema") or SUPPORTED_SIDECAR_SCHEMA)
    actual_sidecar_schema = str(sidecar.get("schema") or "")
    _add_check(report, "ICE_REFERENCE_SIDECAR_SCHEMA", "PASS" if actual_sidecar_schema == required_sidecar_schema else "ERROR", f"Step 4 sidecar schema is {actual_sidecar_schema or '<missing>'}.", {"required": required_sidecar_schema})
    all_ice_ids, counts = _ice_semantics(sidecar, config, report)
    index = _index_entities(sidecar, report)
    selected_ids = _selected_ids(all_ice_ids, config, report)
    require_gm = bool(policy.get("requireGmAudience", True))
    require_rules = bool(policy.get("requireReaderRules", True))
    entries: list[dict[str, Any]] = []
    missing: list[str] = []
    for semantic_id in selected_ids:
        entity = index.get(semantic_id)
        if entity is None:
            missing.append(semantic_id)
            continue
        entry = _entry_view(entity, report, require_gm=require_gm, require_rules=require_rules)
        if entry is not None:
            entries.append(entry)
    if missing:
        _add_check(report, "ICE_REFERENCE_RESOLUTION", "ERROR", "One or more selected ICE semantic IDs do not resolve in Step 4 entities.", missing)
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    group_order = composition.get("groupOrder")
    if not isinstance(group_order, list) or not group_order:
        group_order = list(ICE_TYPES)
    clean_group_order = [str(value).strip().casefold() for value in group_order]
    if clean_group_order != list(ICE_TYPES):
        _add_check(report, "ICE_REFERENCE_GROUP_ORDER", "ERROR", "ICEReferencePackage v1 group order must be Sentry ICE then Wall ICE.", {"actual": clean_group_order, "required": list(ICE_TYPES)})
    group_titles = composition.get("groupTitles") if isinstance(composition.get("groupTitles"), dict) else {}
    groups: list[dict[str, Any]] = []
    for ice_type in ICE_TYPES:
        group_entries = [entry for entry in entries if entry["iceType"] == ice_type]
        group_entries.sort(key=lambda row: (str(row.get("name") or "").casefold(), str(row.get("_sortSourceId") or ""), str(row.get("semanticId") or "")))
        for entry in group_entries:
            entry.pop("_sortSourceId", None)
        groups.append({
            "iceType": ice_type,
            "title": str(group_titles.get(ice_type) or ("Sentry ICE" if ice_type == "sentry" else "Wall ICE")),
            "entries": group_entries,
        })
    if entries and not report["errors"]:
        _add_check(report, "ICE_REFERENCE_ORDERING", "PASS", "ICE entries are grouped Sentry/Wall and sorted by case-insensitive name with stable source-ID tie-break.")
    view: dict[str, Any] = {
        "schema": VIEW_SCHEMA,
        "chapter": int(config.get("chapter") or 29),
        "chapterId": str(config.get("chapterId") or "ch29-ice-reference"),
        "partLabel": str(config.get("partLabel") or "GM ENCOUNTER TOOLKIT"),
        "title": str(config.get("title") or "ICE Reference"),
        "chapterIntro": str(config.get("chapterIntro") or "").strip(),
        "audience": "gm",
        "prototype": {
            "mode": str((config.get("prototype") if isinstance(config.get("prototype"), dict) else {}).get("mode") or "representative-proof"),
            "entryCount": sum(len(group["entries"]) for group in groups),
            "fullIceCount": len(all_ice_ids),
            "fullIceCounts": counts,
        },
        "groups": groups,
    }
    if bool(policy.get("failOnRawSourceReferences", True)):
        leakage = _source_leakage(view)
        _add_check(report, "ICE_REFERENCE_NO_SOURCE_LEAKAGE", "ERROR" if leakage else "PASS", "ICEReferencePackage view contains raw implementation/source references." if leakage else "ICEReferencePackage view contains no raw Foundry/source references.", leakage if leakage else None)
    expected_selected = len(selected_ids)
    actual_selected = sum(len(group["entries"]) for group in groups)
    _add_check(report, "ICE_REFERENCE_PROOF_COUNT", "PASS" if expected_selected == actual_selected else "ERROR", f"H2 proof contains {actual_selected} of {expected_selected} selected ICE entries.", {"expected": expected_selected, "actual": actual_selected})
    return (view if report["status"] == "PASS" else None), report
