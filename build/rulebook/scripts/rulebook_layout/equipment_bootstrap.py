from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BOOTSTRAP_SCHEMA = "cybermancy-rulebook-step6-equipment-bootstrap-inspection-v1.1"
SECTION_SCHEMA = "cybermancy-step6-equipment-section-v1.0"
SIDECAR_SCHEMAS = {
    "cybermancy-step4-structured-entities-v1.1",
    "cybermancy-step4-structured-entities-v1.2",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _add_check(report: dict, code: str, status: str, message: str, details: Any = None) -> None:
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def _populated(value: Any) -> bool:
    return value not in (None, "", [], {})


def _flatten_publication_data(value: Any, prefix: str = "publicationData"):
    if isinstance(value, dict):
        if not value:
            yield prefix, value
            return
        for key in sorted(value, key=lambda item: str(item).casefold()):
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_publication_data(value[key], child)
        return
    yield prefix, value


def _sample_value(value: Any, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _section_entry(section_registry: Path, family: str) -> tuple[dict | None, list[dict]]:
    if not section_registry.is_file():
        return None, [{"issue": "section-registry-missing", "path": str(section_registry)}]
    try:
        data = _load_json(section_registry)
    except Exception as exc:
        return None, [{"issue": "section-registry-json-invalid", "path": str(section_registry), "error": str(exc)}]
    errors: list[dict] = []
    if data.get("schema") != SECTION_SCHEMA:
        errors.append({"issue": "section-registry-schema", "expected": SECTION_SCHEMA, "actual": data.get("schema")})
    entries = data.get("families") if isinstance(data.get("families"), list) else []
    matches = [entry for entry in entries if isinstance(entry, dict) and str(entry.get("family") or "") == family]
    if len(matches) != 1:
        errors.append({"issue": "section-family-resolution", "family": family, "matches": len(matches)})
        return None, errors
    entry = matches[0]
    try:
        chapter = int(entry.get("chapter"))
    except (TypeError, ValueError):
        chapter = 0
    if chapter <= 0:
        errors.append({"issue": "section-family-chapter-invalid", "family": family, "chapter": entry.get("chapter")})
    if errors:
        return None, errors
    return {
        "family": family,
        "chapter": chapter,
        "title": str(entry.get("title") or family),
        "config": str(entry.get("config") or f"{family}-v1.json"),
    }, []


def _identity_details(entities: list[dict]) -> dict:
    semantic = [str(entity.get("semanticId") or "") for entity in entities]
    source = [str(entity.get("sourceId") or "") for entity in entities]
    duplicate_semantic = sorted({value for value in semantic if value and semantic.count(value) > 1})
    duplicate_source = sorted({value for value in source if value and source.count(value) > 1})
    missing = [entity.get("name") for entity in entities if not entity.get("semanticId") or not entity.get("sourceId")]
    return {
        "duplicateSemanticIds": duplicate_semantic,
        "duplicateSourceIds": duplicate_source,
        "missingIds": missing,
    }


def publication_field_inventory(entities: list[dict]) -> list[dict]:
    """Return coverage and representative values for normalized publication fields."""
    fields: dict[str, dict] = {}
    entity_count = len(entities)
    for entity in entities:
        publication_data = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
        seen_in_entity: set[str] = set()
        for path, value in _flatten_publication_data(publication_data):
            item = fields.setdefault(path, {"path": path, "availableCount": 0, "populatedCount": 0, "sampleValues": []})
            if path not in seen_in_entity:
                item["availableCount"] += 1
                seen_in_entity.add(path)
            if _populated(value):
                item["populatedCount"] += 1
                sample = _sample_value(value)
                if sample not in item["sampleValues"] and len(item["sampleValues"]) < 3:
                    item["sampleValues"].append(sample)
    result = []
    for path in sorted(fields, key=str.casefold):
        item = fields[path]
        item["entityCount"] = entity_count
        item["missingCount"] = entity_count - item["populatedCount"]
        item["coveragePct"] = round((item["populatedCount"] / entity_count) * 100, 1) if entity_count else 0.0
        result.append(item)
    return result


def inspect_equipment_bootstrap(
    family: str,
    config_path: Path,
    sidecar_path: Path,
    manuscript_path: Path,
    section_registry: Path,
    *,
    config_status: str = "NOT_IMPLEMENTED",
) -> dict:
    """Inspect normalized Equipment semantics before/while configuring Step 6.

    Config absence is intentionally informational. ``config_status`` also lets
    the initializer inspect an existing recognized scaffold before safely
    refreshing it from a newer Step 4 sidecar.
    """
    report = {
        "schema": BOOTSTRAP_SCHEMA,
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        "family": family,
        "chapter": None,
        "inputs": {
            "config": str(config_path),
            "structuredEntities": str(sidecar_path),
            "assembledManuscript": str(manuscript_path),
            "sectionRegistry": str(section_registry),
        },
    }
    normalized_status = str(config_status or "NOT_IMPLEMENTED").strip().upper()
    if normalized_status == "REFRESHING_SCAFFOLD":
        config_message = f"Existing recognized Step 6 scaffold is being inspected for refresh: {config_path}"
    else:
        normalized_status = "NOT_IMPLEMENTED"
        config_message = f"Step 6 family config is not yet implemented: {config_path}"
    _add_check(
        report,
        "CONFIG_STATUS",
        "INFO",
        config_message,
        {"status": normalized_status, "expectedConfig": str(config_path)},
    )

    contract, contract_errors = _section_entry(section_registry, family)
    if contract_errors:
        _add_check(report, "EQUIPMENT_SECTION_CONTRACT", "ERROR", "Could not resolve this family in the Equipment section registry.", contract_errors)
    else:
        report["chapter"] = contract["chapter"]
        _add_check(report, "EQUIPMENT_SECTION_CONTRACT", "PASS", f"Resolved Chapter {contract['chapter']} {contract['title']} from the Equipment section registry.")

    for code, path in (
        ("STRUCTURED_SIDECAR_PRESENT", sidecar_path),
        ("ASSEMBLED_MANUSCRIPT_PRESENT", manuscript_path),
    ):
        _add_check(report, code, "PASS" if path.is_file() else "BLOCKED", str(path) if path.is_file() else f"Required bootstrap inspection input is missing: {path}")
    if report["status"] != "PASS":
        return {"report": report, "config": None, "bootstrap": None}

    try:
        sidecar = _load_json(sidecar_path)
    except Exception as exc:
        _add_check(report, "STRUCTURED_SIDECAR_JSON", "ERROR", f"Could not load Step 4 structured sidecar: {exc}")
        return {"report": report, "config": None, "bootstrap": None}

    sidecar_schema = sidecar.get("schema")
    _add_check(report, "SIDECAR_SCHEMA", "PASS" if sidecar_schema in SIDECAR_SCHEMAS else "ERROR", str(sidecar_schema))
    entities_source = sidecar.get("entities") if isinstance(sidecar.get("entities"), list) else []
    entities = [entity for entity in entities_source if entity.get("family") == family]
    _add_check(report, "EQUIPMENT_ENTITY_COUNT", "PASS" if entities else "ERROR", f"Structured sidecar contains {len(entities)} {family} entities.")

    identity = _identity_details(entities)
    identity_bad = bool(identity["duplicateSemanticIds"] or identity["duplicateSourceIds"] or identity["missingIds"])
    _add_check(report, "EQUIPMENT_ENTITY_IDENTITY", "ERROR" if identity_bad else "PASS", "Structured sidecar identity is unique and complete." if not identity_bad else "Structured sidecar contains duplicate or missing identities.", identity if identity_bad else None)

    manuscript = manuscript_path.read_text(encoding="utf-8")
    marker = f"family:{family}"
    _add_check(report, "MANUSCRIPT_FAMILY_ALIGNMENT", "PASS" if marker in manuscript else "ERROR", f"Assembled manuscript contains {marker}." if marker in manuscript else f"Assembled manuscript does not contain {marker}.")

    fields = publication_field_inventory(entities)
    _add_check(report, "PUBLICATION_FIELD_INVENTORY", "PASS" if fields else "ERROR", f"Found {len(fields)} normalized publicationData field path(s) for inspection.", fields)

    examples = []
    for entity in sorted(entities, key=lambda value: (str(value.get("name") or "").casefold(), str(value.get("name") or "")))[:5]:
        examples.append({
            "semanticId": entity.get("semanticId"),
            "sourceId": entity.get("sourceId"),
            "name": entity.get("name"),
            "sourcePath": entity.get("sourcePath"),
            "publicationData": entity.get("publicationData"),
            "publicationProvenance": entity.get("publicationProvenance"),
        })

    bootstrap = {
        "configStatus": normalized_status,
        "expectedConfig": str(config_path),
        "family": family,
        "chapter": contract["chapter"] if contract else None,
        "title": contract["title"] if contract else family,
        "entityCount": len(entities),
        "sidecarSchema": sidecar_schema,
        "publicationFields": fields,
        "representativeEntities": examples,
    }
    return {"report": report, "config": None, "bootstrap": bootstrap}
