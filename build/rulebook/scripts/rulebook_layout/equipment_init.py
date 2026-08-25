from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .equipment_batch import resolve_equipment_section
from .equipment_bootstrap import inspect_equipment_bootstrap


INIT_SCHEMA = "cybermancy-rulebook-step6-equipment-init-v1.0"
CONFIG_SCHEMA = "cybermancy-step6-equipment-catalog-config-v1.1"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def _field_map(bootstrap: dict) -> dict[str, dict]:
    return {
        str(item.get("path")): item
        for item in bootstrap.get("publicationFields", [])
        if isinstance(item, dict) and item.get("path")
    }


def _is_populated(fields: dict[str, dict], path: str) -> bool:
    return int(fields.get(path, {}).get("populatedCount") or 0) > 0


def _is_complete(fields: dict[str, dict], path: str, entity_count: int) -> bool:
    return entity_count > 0 and int(fields.get(path, {}).get("populatedCount") or 0) == entity_count


def _column_widths(keys: list[str], tabcolsep_pt: float = 2.5) -> dict[str, float]:
    """Allocate a conservative Letter-page width budget for a first-pass catalog."""
    separator_budget = max(0, len(keys) - 1) * (2 * tabcolsep_pt / 72.27)
    raw_budget = 7.45 - separator_budget

    fixed = {
        "name": 1.50,
        "publicationData.tier": 0.48,
        "publicationData.range": 0.82,
        "publicationData.burden": 0.82,
    }
    widths: dict[str, float] = {}
    remaining = raw_budget
    for key in keys:
        if key == "publicationData.description":
            continue
        width = fixed.get(key, 0.90)
        widths[key] = width
        remaining -= width

    if "publicationData.description" in keys:
        widths["publicationData.description"] = max(2.80, remaining)
    elif keys:
        # Give any otherwise unused width to Name so a minimal scaffold is readable.
        widths["name"] = widths.get("name", 1.50) + max(0.0, remaining)

    return {key: round(value, 3) for key, value in widths.items()}


def generate_equipment_config(bootstrap: dict) -> dict:
    """Generate a conservative, usable first-pass Step 6 family config.

    The initializer only publishes normalized fields that are already present in
    Step 4. It does not infer family-specific mechanics or reach back into Foundry.
    """
    family = str(bootstrap["family"])
    chapter = int(bootstrap["chapter"])
    title = str(bootstrap["title"])
    entity_count = int(bootstrap["entityCount"])
    fields = _field_map(bootstrap)

    selected = ["name"]
    for path in (
        "publicationData.tier",
        "publicationData.range",
        "publicationData.burden",
    ):
        if _is_populated(fields, path):
            selected.append(path)
    if _is_populated(fields, "publicationData.description"):
        selected.append("publicationData.description")

    widths = _column_widths(selected)
    labels = {
        "name": "Name",
        "publicationData.tier": "Tier",
        "publicationData.range": "Range",
        "publicationData.burden": "Burden",
        "publicationData.description": "Description",
    }

    columns = []
    for key in selected:
        column = {
            "key": key,
            "label": labels[key],
            "widthIn": widths[key],
            "align": "center" if key == "publicationData.tier" else "left",
            "verticalPaddingPt": 2,
        }
        if key == "name":
            column["bold"] = True
        if key in {"publicationData.range", "publicationData.burden"}:
            column["transform"] = "human-label"
        columns.append(column)

    tier_populated = int(fields.get("publicationData.tier", {}).get("populatedCount") or 0)
    if tier_populated == 0:
        tier_mode = "absent"
    elif tier_populated == entity_count:
        tier_mode = "present"
    else:
        tier_mode = "optional"

    required = []
    for key in selected:
        if key != "name" and _is_complete(fields, key, entity_count):
            required.append(key)

    sort = ["publicationData.tier", "name"] if tier_populated else ["name"]

    return {
        "schema": CONFIG_SCHEMA,
        "layoutMode": "single-catalog",
        "family": family,
        "chapter": chapter,
        "partLabel": "EQUIPMENT & TECHNOLOGY",
        "title": title,
        "deck": "",
        "outputStem": f"Cybermancy_Chapter{chapter}_{_safe_stem(title)}_Step6",
        "expectedEntityCount": entity_count,
        "expectedColumnLabels": [labels[key] for key in selected],
        "tierMode": tier_mode,
        "sort": sort,
        "requiredPublicationFields": required,
        "display": {
            "missing": "—",
            "groupUppercase": True,
        },
        "columns": columns,
        "tableStyle": {
            "tabcolsepPt": 2.5,
            "arrayStretch": 1.08,
            "fontSizePt": 7.4,
            "leadingPt": 8.8,
        },
        "pagination": {
            "continuationLabel": title,
            "continuationTemplate": "{label} — CONTINUED",
        },
        "style": {
            "headerColor": "0B6573",
            "groupBandColor": "DDEEF0",
            "alternateRowColor": "EEF7F8",
            "textDarkColor": "183238",
            "ruleColor": "18A7B5",
        },
    }


def _result_shell(mode: str, sidecar: Path, manuscript: Path, section_registry: Path) -> dict:
    return {
        "schema": INIT_SCHEMA,
        "mode": mode,
        "status": "PASS",
        "inputs": {
            "structuredEntities": str(sidecar),
            "assembledManuscript": str(manuscript),
            "sectionRegistry": str(section_registry),
        },
        "families": [],
        "errors": [],
    }


def initialize_equipment_family(
    family: str,
    *,
    config_dir: Path,
    sidecar: Path,
    manuscript: Path,
    section_registry: Path,
) -> dict:
    section, errors = resolve_equipment_section(section_registry, config_dir)
    if errors:
        return {
            "family": family,
            "status": "FAIL",
            "errors": errors,
        }
    matches = [item for item in section if item["family"] == family]
    if len(matches) != 1:
        return {
            "family": family,
            "status": "FAIL",
            "errors": [{"issue": "family-not-in-section-contract", "family": family}],
        }

    item = matches[0]
    config_path = Path(item["config"])
    if config_path.is_file():
        return {
            "chapter": item["chapter"],
            "family": family,
            "title": item["title"],
            "config": str(config_path),
            "status": "EXISTS",
            "message": "Existing Equipment family config was preserved unchanged.",
        }

    payload = inspect_equipment_bootstrap(
        family,
        config_path,
        sidecar,
        manuscript,
        section_registry,
    )
    report = payload.get("report") or {}
    bootstrap = payload.get("bootstrap")
    if report.get("status") != "PASS" or not isinstance(bootstrap, dict):
        return {
            "chapter": item["chapter"],
            "family": family,
            "title": item["title"],
            "config": str(config_path),
            "status": "FAIL",
            "bootstrapReport": report,
            "errors": report.get("errors", []),
        }

    config = generate_equipment_config(bootstrap)
    _write_json(config_path, config)
    return {
        "chapter": item["chapter"],
        "family": family,
        "title": item["title"],
        "config": str(config_path),
        "status": "CREATED",
        "configData": config,
        "bootstrap": bootstrap,
    }


def initialize_equipment(
    *,
    family: str | None,
    all_families: bool,
    config_dir: Path,
    sidecar: Path,
    manuscript: Path,
    section_registry: Path,
    report_dir: Path,
) -> tuple[int, dict]:
    result = _result_shell("all" if all_families else "family", sidecar, manuscript, section_registry)

    section, section_errors = resolve_equipment_section(section_registry, config_dir)
    if section_errors:
        result["status"] = "FAIL"
        result["errors"].extend(section_errors)
        _write_json(report_dir / "equipment-init-all.json", result)
        return 2, result

    targets = section if all_families else [item for item in section if item["family"] == family]
    if not targets:
        result["status"] = "FAIL"
        result["errors"].append({"issue": "family-not-in-section-contract", "family": family})
    else:
        for item in targets:
            family_result = initialize_equipment_family(
                str(item["family"]),
                config_dir=config_dir,
                sidecar=sidecar,
                manuscript=manuscript,
                section_registry=section_registry,
            )
            result["families"].append(family_result)
            if family_result.get("status") == "FAIL":
                result["status"] = "FAIL"
                result["errors"].extend(family_result.get("errors", []))

    report_name = "equipment-init-all.json" if all_families else f"equipment-init-{family}.json"
    _write_json(report_dir / report_name, result)
    return (0 if result["status"] == "PASS" else 2), result
