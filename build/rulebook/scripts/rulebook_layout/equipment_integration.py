from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rulebook_layout.equipment_catalog import (
    build_catalog_rows,
    get_path,
    render_equipment_catalog_latex,
)
from rulebook_layout.latex import render_weapons_family_latex
from rulebook_layout.mechanics_reference import (
    collect_weapon_references,
    render_mechanics_reference_latex,
)


SUPPORTED_SIDECAR_SCHEMA = "cybermancy-step4-structured-entities-v1.3"
REGISTRY_SCHEMA = "cybermancy-step6-equipment-section-v1.0"
CONFIG_SCHEMA = "cybermancy-step6-equipment-catalog-config-v1.1"
EQUIPMENT_FAMILIES = (
    (15, "weapons", "weapons-v1.json"),
    (16, "ammo", "ammo-v1.json"),
    (17, "armors", "armors-v1.json"),
    (18, "cybernetics", "cybernetics-v1.json"),
    (19, "drones-devices", "drones-devices-v1.json"),
    (20, "consumables", "consumables-v1.json"),
    (21, "mods", "mods-v1.json"),
    (22, "loot", "loot-v1.json"),
)


@dataclass(frozen=True)
class EquipmentPayload:
    chapter: int
    family: str
    title: str
    config_path: str
    entity_count: int
    latex: str

    @property
    def latex_sha256(self) -> str:
        return hashlib.sha256(self.latex.encode("utf-8")).hexdigest()

    def summary(self) -> dict[str, Any]:
        return {
            "chapter": self.chapter,
            "family": self.family,
            "title": self.title,
            "config": self.config_path,
            "entityCount": self.entity_count,
            "latexSha256": self.latex_sha256,
        }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def _report() -> dict[str, Any]:
    return {
        "schema": "cybermancy-step6-equipment-integration-compose-v1",
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        "families": [],
    }


def _check(
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
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def _contract_equipment_targets(contract: dict[str, Any]) -> list[tuple[int, str]]:
    targets: list[tuple[int, str]] = []
    for item in contract.get("structuredTargets", []):
        if not isinstance(item, dict) or item.get("adapter") != "equipment":
            continue
        families = item.get("families")
        if not isinstance(families, list) or len(families) != 1:
            continue
        targets.append((int(item.get("chapter")), str(families[0])))
    return targets


def _registry_rows(registry: dict[str, Any]) -> list[tuple[int, str, str, str]]:
    rows: list[tuple[int, str, str, str]] = []
    values = registry.get("families")
    if not isinstance(values, list):
        return rows
    for item in values:
        if not isinstance(item, dict):
            continue
        rows.append(
            (
                int(item.get("chapter")),
                str(item.get("family") or ""),
                str(item.get("title") or ""),
                str(item.get("config") or ""),
            )
        )
    return rows


def _family_entities(sidecar: dict[str, Any], family: str) -> list[dict[str, Any]]:
    rows = sidecar.get("entities")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("family") == family]


def _identity_issues(entities: list[dict[str, Any]]) -> dict[str, Any]:
    semantic = [str(row.get("semanticId") or "").strip() for row in entities]
    source = [str(row.get("sourceId") or "").strip() for row in entities]
    duplicate_semantic = sorted({value for value in semantic if value and semantic.count(value) > 1})
    duplicate_source = sorted({value for value in source if value and source.count(value) > 1})
    missing = [
        str(row.get("name") or row.get("semanticId") or "<unnamed>")
        for row in entities
        if not str(row.get("semanticId") or "").strip() or not str(row.get("sourceId") or "").strip()
    ]
    return {
        "duplicateSemanticIds": duplicate_semantic,
        "duplicateSourceIds": duplicate_source,
        "missingIds": missing,
    }


def _required_field_issues(entities: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    required = config.get("requiredPublicationFields")
    if not isinstance(required, list):
        return []
    issues: list[dict[str, Any]] = []
    for entity in entities:
        for path in required:
            value = get_path(entity, str(path))
            if value in (None, "", [], {}):
                issues.append(
                    {
                        "semanticId": entity.get("semanticId"),
                        "name": entity.get("name"),
                        "field": path,
                    }
                )
    return issues


def _render_weapons(
    entities: list[dict[str, Any]],
    config: dict[str, Any],
    report: dict[str, Any],
) -> str | None:
    expected_tiers = config.get("expectedTierCounts")
    if not isinstance(expected_tiers, dict) or not expected_tiers:
        _check(
            report,
            "EQUIPMENT_WEAPON_TIERS",
            "ERROR",
            "Weapons integration requires the frozen expectedTierCounts contract.",
        )
        return None

    tier_tables: dict[int, str] = {}
    tier_mismatches: list[dict[str, Any]] = []
    for tier_text, expected_value in sorted(expected_tiers.items(), key=lambda item: int(item[0])):
        tier = int(tier_text)
        rows = build_catalog_rows(entities, config, tier=tier)
        expected = int(expected_value)
        if len(rows) != expected:
            tier_mismatches.append({"tier": tier, "expected": expected, "actual": len(rows)})
        tier_tables[tier] = render_equipment_catalog_latex(rows, config)

    _check(
        report,
        "EQUIPMENT_WEAPON_TIERS",
        "ERROR" if tier_mismatches else "PASS",
        "Weapons Tier tables match the frozen 1–4 corpus counts."
        if not tier_mismatches
        else "Weapons Tier counts differ from the frozen Equipment contract.",
        tier_mismatches or None,
    )
    if tier_mismatches:
        return None

    refs = collect_weapon_references(entities)
    reference_issues = {
        "collisions": refs.get("collisions") or [],
        "missingDefinitions": refs.get("missingDefinitions") or [],
        "orphanDefinitions": refs.get("orphanDefinitions") or [],
    }
    reference_ok = not any(reference_issues.values())
    _check(
        report,
        "EQUIPMENT_WEAPON_REFERENCES",
        "PASS" if reference_ok else "ERROR",
        "Weapon Actions and Critical Effects resolve to unique complete reference definitions."
        if reference_ok
        else "Weapon mechanic references are incomplete, ambiguous, or orphaned.",
        reference_issues if not reference_ok else None,
    )
    if not reference_ok:
        return None

    actions = render_mechanics_reference_latex(refs["actions"], config)
    critical = render_mechanics_reference_latex(refs["criticalEffects"], config)
    return render_weapons_family_latex(tier_tables, actions, critical, config)


def compose_equipment_stage(
    sidecar: dict[str, Any],
    registry: dict[str, Any],
    config_dir: Path,
    contract: dict[str, Any],
) -> tuple[list[EquipmentPayload], dict[str, Any]]:
    """Compose all accepted Equipment family bodies without a standalone document shell."""
    report = _report()

    schema_ok = sidecar.get("schema") == SUPPORTED_SIDECAR_SCHEMA
    _check(
        report,
        "EQUIPMENT_SIDECAR_SCHEMA",
        "PASS" if schema_ok else "ERROR",
        f"Step 4 sidecar schema is {SUPPORTED_SIDECAR_SCHEMA}."
        if schema_ok
        else "Equipment integration requires the current Step 4 structured sidecar schema.",
        sidecar.get("schema"),
    )

    entities = sidecar.get("entities")
    _check(
        report,
        "EQUIPMENT_SIDECAR_ENTITIES",
        "PASS" if isinstance(entities, list) else "ERROR",
        f"Step 4 sidecar contains {len(entities)} semantic entities."
        if isinstance(entities, list)
        else "Step 4 sidecar has no entities array.",
    )

    registry_ok = registry.get("schema") == REGISTRY_SCHEMA
    _check(
        report,
        "EQUIPMENT_REGISTRY_SCHEMA",
        "PASS" if registry_ok else "ERROR",
        "Accepted Equipment section registry loaded."
        if registry_ok
        else "Equipment section registry schema is not the accepted v1.0 contract.",
        registry.get("schema"),
    )

    contract_targets = _contract_equipment_targets(contract)
    canonical_targets = [(chapter, family) for chapter, family, _ in EQUIPMENT_FAMILIES]
    registry_rows = _registry_rows(registry)
    registry_targets = [(chapter, family) for chapter, family, _title, _config in registry_rows]
    registry_configs = [(chapter, family, config) for chapter, family, _title, config in registry_rows]
    canonical_configs = list(EQUIPMENT_FAMILIES)
    architecture_ok = (
        contract_targets == canonical_targets
        and registry_targets == canonical_targets
        and registry_configs == canonical_configs
    )
    _check(
        report,
        "EQUIPMENT_ARCHITECTURE",
        "PASS" if architecture_ok else "ERROR",
        "Equipment Chapters 15–22 match the accepted contract and registry exactly."
        if architecture_ok
        else "Equipment contract, registry, or canonical chapter/family/config ordering differs.",
        {
            "contract": contract_targets,
            "registry": registry_configs,
            "expected": canonical_configs,
        },
    )

    regression = contract.get("regressionExpectations", {}).get("equipment", {})
    if not isinstance(regression, dict):
        regression = {}

    if report["status"] != "PASS":
        return [], report

    payloads: list[EquipmentPayload] = []
    for chapter, family, title, config_name in registry_rows:
        family_report: dict[str, Any] = {
            "chapter": chapter,
            "family": family,
            "title": title,
            "config": config_name,
            "status": "PASS",
            "checks": [],
        }
        config_path = config_dir / config_name
        if not config_path.is_file():
            family_report["status"] = "FAIL"
            family_report["checks"].append({"code": "CONFIG_PRESENT", "status": "ERROR", "message": str(config_path)})
            report["families"].append(family_report)
            _check(report, "EQUIPMENT_CONFIG_PRESENT", "ERROR", f"Missing Equipment config for {family}: {config_path}")
            continue

        try:
            config = load_json(config_path)
        except Exception as exc:
            family_report["status"] = "FAIL"
            family_report["checks"].append({"code": "CONFIG_JSON", "status": "ERROR", "message": str(exc)})
            report["families"].append(family_report)
            _check(report, "EQUIPMENT_CONFIG_JSON", "ERROR", f"Could not load Equipment config for {family}: {exc}")
            continue

        expected_count = int(regression.get(family) or 0)
        family_entities = _family_entities(sidecar, family)
        config_status = config.get("configStatus")
        config_ok = (
            config.get("schema") == CONFIG_SCHEMA
            and str(config.get("family") or "") == family
            and int(config.get("chapter") or 0) == chapter
            and int(config.get("expectedEntityCount") or 0) == expected_count
            and (config_status in (None, "accepted"))
        )
        family_report["checks"].append(
            {
                "code": "CONFIG_CONTRACT",
                "status": "PASS" if config_ok else "ERROR",
                "message": "Config matches accepted Equipment metadata." if config_ok else "Config differs from accepted Equipment metadata.",
                "details": {
                    "schema": config.get("schema"),
                    "chapter": config.get("chapter"),
                    "family": config.get("family"),
                    "expectedEntityCount": config.get("expectedEntityCount"),
                    "contractEntityCount": expected_count,
                    "configStatus": config_status,
                },
            }
        )

        count_ok = len(family_entities) == expected_count
        family_report["checks"].append(
            {
                "code": "ENTITY_COUNT",
                "status": "PASS" if count_ok else "ERROR",
                "message": f"Found {len(family_entities)} {family} entities; expected {expected_count}.",
            }
        )

        identity = _identity_issues(family_entities)
        identity_ok = not any(identity.values())
        family_report["checks"].append(
            {
                "code": "ENTITY_IDENTITY",
                "status": "PASS" if identity_ok else "ERROR",
                "message": "Semantic/source IDs are unique and complete." if identity_ok else "Semantic/source IDs are missing or duplicated.",
                "details": identity if not identity_ok else None,
            }
        )

        required_issues = _required_field_issues(family_entities, config)
        family_report["checks"].append(
            {
                "code": "REQUIRED_PUBLICATION_FIELDS",
                "status": "PASS" if not required_issues else "ERROR",
                "message": "Required publication fields are complete." if not required_issues else "Required publication fields are missing.",
                "details": required_issues or None,
            }
        )

        rows = build_catalog_rows(family_entities, config)
        rows_ok = len(rows) == expected_count
        family_report["checks"].append(
            {
                "code": "CATALOG_ROW_COUNT",
                "status": "PASS" if rows_ok else "ERROR",
                "message": f"Rendered catalog row source contains {len(rows)} rows; expected {expected_count}.",
            }
        )

        column_labels = [str(column.get("label") or "") for column in config.get("columns", []) if isinstance(column, dict)]
        expected_labels = config.get("expectedColumnLabels")
        columns_ok = bool(column_labels) and (
            not isinstance(expected_labels, list) or column_labels == [str(value) for value in expected_labels]
        )
        family_report["checks"].append(
            {
                "code": "COLUMN_CONTRACT",
                "status": "PASS" if columns_ok else "ERROR",
                "message": "Configured publication columns are complete." if columns_ok else "Configured publication columns differ from the accepted labels.",
                "details": {"expected": expected_labels, "actual": column_labels} if not columns_ok else None,
            }
        )

        local_ok = config_ok and count_ok and identity_ok and not required_issues and rows_ok and columns_ok
        if not local_ok:
            family_report["status"] = "FAIL"
            report["families"].append(family_report)
            _check(
                report,
                "EQUIPMENT_FAMILY_CONTRACT",
                "ERROR",
                f"Equipment family {family} failed its composition preconditions.",
                family_report,
            )
            continue

        if family == "weapons":
            latex = _render_weapons(family_entities, config, report)
        else:
            latex = render_equipment_catalog_latex(rows, config)

        if not latex or report["status"] != "PASS":
            family_report["status"] = "FAIL"
            report["families"].append(family_report)
            if not latex:
                _check(report, "EQUIPMENT_FAMILY_RENDER", "ERROR", f"Equipment family {family} produced no integration LaTeX.")
            continue

        payload = EquipmentPayload(
            chapter=chapter,
            family=family,
            title=title,
            config_path=str(config_path),
            entity_count=len(family_entities),
            latex=latex,
        )
        family_report["payload"] = payload.summary()
        report["families"].append(family_report)
        payloads.append(payload)

    complete = (
        report["status"] == "PASS"
        and [(payload.chapter, payload.family) for payload in payloads] == canonical_targets
    )
    _check(
        report,
        "EQUIPMENT_STAGE_COMPOSITION",
        "PASS" if complete else "ERROR",
        "Composed all eight frozen Equipment family bodies in Chapters 15–22 order."
        if complete
        else "Equipment stage composition did not produce the complete Chapters 15–22 payload set.",
        [payload.summary() for payload in payloads],
    )
    if not complete:
        return [], report
    return payloads, report
