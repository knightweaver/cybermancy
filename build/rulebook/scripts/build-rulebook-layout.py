#!/usr/bin/env python3
"""Cybermancy Rulebook Step 6 layout builder.

Step 6C established the reusable Equipment Catalog Table primitive with a
single Tier 1 Weapons proof. Step 6D extends that same primitive to the complete
Chapter 16 Weapons publication: four Tier tables, Weapon Actions and Critical
Effects references, and semantic Pandoc-AST replacement of ``family:weapons``.

The builder consumes only normalized Step 4 outputs. It never reads canonical
Foundry pack JSON directly.

C compatibility commands:
    python build/rulebook/scripts/build-rulebook-layout.py validate
    python build/rulebook/scripts/build-rulebook-layout.py build
    python build/rulebook/scripts/build-rulebook-layout.py inspect

D complete-Chapter-16 commands:
    python build/rulebook/scripts/build-rulebook-layout.py validate-chapter16
    python build/rulebook/scripts/build-rulebook-layout.py build-chapter16
    python build/rulebook/scripts/build-rulebook-layout.py inspect-chapter16
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
SOURCE_DIR = RULEBOOK_DIR / "source"
METADATA_DIR = SOURCE_DIR / "metadata"
ASSEMBLED_DIR = SOURCE_DIR / "assembled"
LAYOUT_DIR = RULEBOOK_DIR / "layout"
DEFAULT_CONFIG = LAYOUT_DIR / "equipment" / "weapons-v1.json"
DEFAULT_SIDECAR = METADATA_DIR / "structured-entities.json"
DEFAULT_MANUSCRIPT = ASSEMBLED_DIR / "player-guide.md"
DEFAULT_PROTOTYPE_DIR = LAYOUT_DIR / "prototype"
DEFAULT_CHAPTER16_DIR = LAYOUT_DIR / "chapter16"
DEFAULT_REPORT_DIR = LAYOUT_DIR / "reports"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_catalog import (  # noqa: E402
    build_catalog_rows,
    render_equipment_catalog_latex,
    replace_family_div_with_latex,
)
from rulebook_layout.latex import (  # noqa: E402
    render_tier_prototype_document,
    render_weapons_chapter_document,
    render_weapons_family_latex,
)
from rulebook_layout.mechanics_reference import (  # noqa: E402
    collect_weapon_references,
    render_mechanics_reference_latex,
)


DAMAGE_FORMULA_RE = re.compile(r"^(?:\d*d\d+(?:[+-]\d+)?)(?:; \d*d\d+(?:[+-]\d+)?)*$", re.I)
HTML_TAG_RE = re.compile(r"<[^>]+>")
CAMEL_CODE_RE = re.compile(r"[a-z][A-Z]")
PANDOC_FROM = "markdown+fenced_divs+bracketed_spans+pipe_tables+grid_tables+definition_lists+raw_attribute"
SIDECAR_SCHEMA_C = "cybermancy-step4-structured-entities-v1.0"
SIDECAR_SCHEMA_D = "cybermancy-step4-structured-entities-v1.1"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def add_check(report: dict, code: str, status: str, message: str, details: Any = None) -> None:
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def report_shell(config_path: Path, sidecar_path: Path, manuscript_path: Path, tier: int) -> dict:
    return {
        "schema": "cybermancy-rulebook-step6-equipment-catalog-validation-v1.0",
        "status": "PASS",
        "tier": tier,
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputs": {
            "config": str(config_path),
            "structuredEntities": str(sidecar_path),
            "assembledManuscript": str(manuscript_path),
        },
    }


def chapter16_report_shell(config_path: Path, sidecar_path: Path, manuscript_path: Path) -> dict:
    return {
        "schema": "cybermancy-rulebook-step6-chapter16-validation-v1.0",
        "status": "PASS",
        "chapter": 16,
        "family": "weapons",
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputs": {
            "config": str(config_path),
            "structuredEntities": str(sidecar_path),
            "assembledManuscript": str(manuscript_path),
        },
    }


def resolve_path(value: str | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value else default.resolve()


def _check_common_inputs(report: dict, config_path: Path, sidecar_path: Path, manuscript_path: Path) -> bool:
    for code, path in (
        ("CONFIG_PRESENT", config_path),
        ("STRUCTURED_SIDECAR_PRESENT", sidecar_path),
        ("ASSEMBLED_MANUSCRIPT_PRESENT", manuscript_path),
    ):
        if path.is_file():
            add_check(report, code, "PASS", str(path))
        else:
            add_check(report, code, "BLOCKED", f"Required Step 6 input is missing: {path}")
    return report["status"] == "PASS"


def _column_contract(config: dict, report: dict) -> None:
    columns = list(config.get("columns", []))
    labels = [col.get("label") for col in columns]
    expected_labels = ["Name", "Tier", "Trait", "Range", "Burden", "Damage", "Action", "Critical Effect", "Description"]
    if labels == expected_labels:
        add_check(report, "WEAPON_COLUMN_CONTRACT", "PASS", "Approved nine-column Weapons schema is configured.")
    else:
        add_check(report, "WEAPON_COLUMN_CONTRACT", "ERROR", "Weapons columns differ from the approved C schema.", labels)

    width_sum = sum(float(col.get("widthIn", 0)) for col in columns)
    spacing_in = max(0, len(columns) - 1) * (2 * 1.4 / 72.27)
    occupied = width_sum + spacing_in
    if occupied <= 7.58:
        add_check(report, "TABLE_WIDTH_BUDGET", "PASS", f"Configured table width budget is {occupied:.3f}in within 7.58in.")
    else:
        add_check(report, "TABLE_WIDTH_BUDGET", "ERROR", f"Configured table requires {occupied:.3f}in; only 7.58in is available.")


def _validate_rows(rows: list, report: dict, *, prefix: str = "") -> None:
    code_prefix = f"{prefix}_" if prefix else ""
    critical_prefix_rows = [r.name for r in rows if "Critical Effect:" in r.cells.get("criticalEffect", "")]
    add_check(
        report,
        f"{code_prefix}CRITICAL_EFFECT_DISPLAY",
        "ERROR" if critical_prefix_rows else "PASS",
        "Critical Effect prefix leaked into Step 6 display." if critical_prefix_rows else "Critical Effect display names contain no Foundry prefix.",
        critical_prefix_rows or None,
    )

    invalid_damage = []
    for row in rows:
        damage = row.cells.get("publicationData.attack.damageFormula", "—")
        if damage != "—" and not DAMAGE_FORMULA_RE.fullmatch(damage):
            invalid_damage.append({"name": row.name, "damage": damage})
    add_check(
        report,
        f"{code_prefix}DAMAGE_FORMULA_ONLY",
        "ERROR" if invalid_damage else "PASS",
        "Damage cells contain values other than formula-only publication data." if invalid_damage else "Damage cells contain formula only; damage types are absent.",
        invalid_damage or None,
    )

    html_descriptions = [r.name for r in rows if HTML_TAG_RE.search(r.cells.get("publicationData.description", ""))]
    add_check(
        report,
        f"{code_prefix}PLAIN_TEXT_DESCRIPTIONS",
        "ERROR" if html_descriptions else "PASS",
        "HTML remains in normalized descriptions." if html_descriptions else "Catalog descriptions are normalized plain text.",
        html_descriptions or None,
    )

    code_style = []
    for row in rows:
        for key in ("publicationData.attack.trait", "publicationData.attack.range", "publicationData.burden"):
            value = row.cells.get(key, "")
            if CAMEL_CODE_RE.search(value) or "_" in value:
                code_style.append({"name": row.name, "field": key, "value": value})
    add_check(
        report,
        f"{code_prefix}HUMANIZED_ENUM_DISPLAY",
        "ERROR" if code_style else "PASS",
        "Code-style enum values remain in Trait/Range/Burden display." if code_style else "Trait, Range, and Burden use reader-facing grammar.",
        code_style or None,
    )


def validate_catalog(
    config_path: Path,
    sidecar_path: Path,
    manuscript_path: Path,
    tier: int,
) -> tuple[dict, dict | None, dict | None, list]:
    """Step 6C-compatible single-tier validation."""
    report = report_shell(config_path, sidecar_path, manuscript_path, tier)
    if not _check_common_inputs(report, config_path, sidecar_path, manuscript_path):
        return report, None, None, []

    try:
        config = load_json(config_path)
        sidecar = load_json(sidecar_path)
    except Exception as exc:
        add_check(report, "INPUT_JSON", "ERROR", f"Could not load Step 6 JSON input: {exc}")
        return report, None, None, []

    schema = sidecar.get("schema")
    if schema in {SIDECAR_SCHEMA_C, SIDECAR_SCHEMA_D}:
        add_check(report, "SIDECAR_SCHEMA", "PASS", str(schema))
    else:
        add_check(report, "SIDECAR_SCHEMA", "ERROR", "Unexpected Step 4 structured entity sidecar schema.", schema)

    family = str(config.get("family") or "")
    if family:
        add_check(report, "CATALOG_FAMILY", "PASS", family)
    else:
        add_check(report, "CATALOG_FAMILY", "ERROR", "Equipment catalog configuration has no family.")

    manuscript = manuscript_path.read_text(encoding="utf-8")
    family_marker = f"family:{family}"
    if family_marker in manuscript:
        add_check(report, "MANUSCRIPT_FAMILY_ALIGNMENT", "PASS", f"Assembled manuscript contains {family_marker}.")
    else:
        add_check(report, "MANUSCRIPT_FAMILY_ALIGNMENT", "ERROR", f"Assembled manuscript does not contain {family_marker}.")

    entities = sidecar.get("entities") if isinstance(sidecar.get("entities"), list) else []
    rows = build_catalog_rows(entities, config, tier=tier)
    expected = config.get("expectedTierCounts", {}).get(str(tier))
    if expected is None:
        add_check(report, "TIER_ENTITY_COUNT", "WARNING", f"No expected count configured for Tier {tier}; found {len(rows)} rows.")
    elif len(rows) == int(expected):
        add_check(report, "TIER_ENTITY_COUNT", "PASS", f"Tier {tier} contains {len(rows)} catalog rows.")
    else:
        add_check(report, "TIER_ENTITY_COUNT", "ERROR", f"Tier {tier} contains {len(rows)} rows; expected {expected}.")

    _column_contract(config, report)
    _validate_rows(rows, report)

    by_name = {row.name: row for row in rows}
    cyber_spur = by_name.get("Cyber Spur")
    if cyber_spur is not None:
        actual = cyber_spur.cells.get("action")
        if actual == "Retractable, Concealed":
            add_check(report, "CYBER_SPUR_ACTION_COMPOSITION", "PASS", actual)
        else:
            add_check(report, "CYBER_SPUR_ACTION_COMPOSITION", "ERROR", "Cyber Spur Action composition is incorrect.", actual)

    absent_mechanics = []
    for name in ("Light Semi-auto pistol", "Heavy Semi-auto pistol"):
        row = by_name.get(name)
        if row is None:
            continue
        if row.cells.get("action") != "—" or row.cells.get("criticalEffect") != "—":
            absent_mechanics.append({"name": name, "action": row.cells.get("action"), "criticalEffect": row.cells.get("criticalEffect")})
    add_check(
        report,
        "ABSENT_MECHANICS_DISPLAY",
        "ERROR" if absent_mechanics else "PASS",
        "Weapons with no Action/Critical Effect must render em dashes." if absent_mechanics else "Absent Action/Critical Effect mechanics render as em dashes.",
        absent_mechanics or None,
    )

    group_names = []
    for row in rows:
        if not group_names or group_names[-1] != row.group:
            group_names.append(row.group)
    expected_groups = config.get("expectedTierGroups", {}).get(str(tier))
    if expected_groups is None:
        add_check(report, "TRAIT_GROUPS", "INFO", "No expected Trait group sequence configured.", group_names)
    elif group_names == expected_groups:
        add_check(report, "TRAIT_GROUPS", "PASS", f"Tier {tier} groups follow the approved Trait sequence.", group_names)
    else:
        add_check(report, "TRAIT_GROUPS", "ERROR", "Tier Trait group sequence differs from the approved configuration.", {"expected": expected_groups, "actual": group_names})

    return report, config, sidecar, rows


def _weapon_entities(sidecar: dict) -> list[dict]:
    entities = sidecar.get("entities") if isinstance(sidecar.get("entities"), list) else []
    return [entity for entity in entities if entity.get("family") == "weapons"]


def _reference_dicts(reference_bundle: dict) -> tuple[list[dict], list[dict]]:
    return (
        [ref.to_dict() for ref in reference_bundle["actions"]],
        [ref.to_dict() for ref in reference_bundle["criticalEffects"]],
    )


def validate_chapter16(
    config_path: Path,
    sidecar_path: Path,
    manuscript_path: Path,
) -> tuple[dict, dict | None, dict | None, dict[int, list], dict | None]:
    report = chapter16_report_shell(config_path, sidecar_path, manuscript_path)
    if not _check_common_inputs(report, config_path, sidecar_path, manuscript_path):
        return report, None, None, {}, None

    try:
        config = load_json(config_path)
        sidecar = load_json(sidecar_path)
    except Exception as exc:
        add_check(report, "INPUT_JSON", "ERROR", f"Could not load Step 6 JSON input: {exc}")
        return report, None, None, {}, None

    if sidecar.get("schema") == SIDECAR_SCHEMA_D:
        add_check(report, "SIDECAR_SCHEMA", "PASS", SIDECAR_SCHEMA_D)
    else:
        add_check(
            report,
            "SIDECAR_SCHEMA",
            "ERROR",
            "Step 6D requires a rebuilt Step 4 structured entity sidecar with reference definitions.",
            {"required": SIDECAR_SCHEMA_D, "actual": sidecar.get("schema")},
        )

    family = str(config.get("family") or "")
    add_check(report, "CATALOG_FAMILY", "PASS" if family == "weapons" else "ERROR", family or "missing")

    manuscript = manuscript_path.read_text(encoding="utf-8")
    marker = "family:weapons"
    add_check(
        report,
        "MANUSCRIPT_FAMILY_ALIGNMENT",
        "PASS" if marker in manuscript else "ERROR",
        f"Assembled manuscript contains {marker}." if marker in manuscript else f"Assembled manuscript does not contain {marker}.",
    )

    weapons = _weapon_entities(sidecar)
    expected_total = int(config.get("expectedEntityCount", 47))
    add_check(
        report,
        "WEAPON_ENTITY_COUNT",
        "PASS" if len(weapons) == expected_total else "ERROR",
        f"Structured sidecar contains {len(weapons)} Weapons; expected {expected_total}.",
    )

    semantic_ids = [str(entity.get("semanticId") or "") for entity in weapons]
    source_ids = [str(entity.get("sourceId") or "") for entity in weapons]
    duplicate_semantic = sorted({value for value in semantic_ids if value and semantic_ids.count(value) > 1})
    duplicate_source = sorted({value for value in source_ids if value and source_ids.count(value) > 1})
    missing_ids = [entity.get("name") for entity in weapons if not entity.get("semanticId") or not entity.get("sourceId")]
    id_problems = {"duplicateSemanticIds": duplicate_semantic, "duplicateSourceIds": duplicate_source, "missingIds": missing_ids}
    has_id_problems = bool(duplicate_semantic or duplicate_source or missing_ids)
    add_check(
        report,
        "WEAPON_ENTITY_IDENTITY",
        "ERROR" if has_id_problems else "PASS",
        "Weapon sidecar identity is unique and complete." if not has_id_problems else "Weapon sidecar contains duplicate or missing identities.",
        id_problems if has_id_problems else None,
    )

    _column_contract(config, report)

    expected_tiers = config.get("expectedTierCounts", {}) if isinstance(config.get("expectedTierCounts"), dict) else {}
    tier_rows: dict[int, list] = {}
    all_rows = []
    for tier_text, expected_count in sorted(expected_tiers.items(), key=lambda item: int(item[0])):
        tier = int(tier_text)
        rows = build_catalog_rows(weapons, config, tier=tier)
        tier_rows[tier] = rows
        all_rows.extend(rows)
        add_check(
            report,
            f"TIER_{tier}_ENTITY_COUNT",
            "PASS" if len(rows) == int(expected_count) else "ERROR",
            f"Tier {tier} contains {len(rows)} Weapons; expected {expected_count}.",
        )
        sort_keys = [(row.group.casefold(), row.name.casefold(), row.name) for row in rows]
        missing_traits = [row.name for row in rows if row.group == str(config.get("display", {}).get("missing", "—"))]
        sorted_ok = sort_keys == sorted(sort_keys) and not missing_traits
        add_check(
            report,
            f"TIER_{tier}_TRAIT_NAME_ORDER",
            "PASS" if sorted_ok else "ERROR",
            f"Tier {tier} follows Trait → Name ordering." if sorted_ok else f"Tier {tier} does not follow Trait → Name ordering or has missing Traits.",
            {"missingTraits": missing_traits} if not sorted_ok else None,
        )

    _validate_rows(all_rows, report, prefix="CHAPTER16")

    by_name = {row.name: row for row in all_rows}
    cyber_spur = by_name.get("Cyber Spur")
    if cyber_spur and cyber_spur.cells.get("action") == "Retractable, Concealed":
        add_check(report, "CYBER_SPUR_ACTION_COMPOSITION", "PASS", "Retractable, Concealed")
    else:
        add_check(report, "CYBER_SPUR_ACTION_COMPOSITION", "ERROR", "Cyber Spur must display Retractable, Concealed.", cyber_spur.cells.get("action") if cyber_spur else None)

    absent_problems = []
    for name in ("Light Semi-auto pistol", "Heavy Semi-auto pistol"):
        row = by_name.get(name)
        if row and (row.cells.get("action") != "—" or row.cells.get("criticalEffect") != "—"):
            absent_problems.append({"name": name, "action": row.cells.get("action"), "criticalEffect": row.cells.get("criticalEffect")})
    add_check(
        report,
        "ABSENT_MECHANICS_DISPLAY",
        "ERROR" if absent_problems else "PASS",
        "Absent Action/Critical Effect mechanics render as em dashes." if not absent_problems else "Weapons with absent mechanics did not render em dashes.",
        absent_problems or None,
    )

    reference_bundle = collect_weapon_references(weapons)
    collisions = reference_bundle["collisions"]
    missing_definitions = reference_bundle["missingDefinitions"]
    orphans = reference_bundle["orphanDefinitions"]
    add_check(
        report,
        "WEAPON_MECHANIC_NAME_COLLISION",
        "ERROR" if collisions else "PASS",
        "No mechanic display name resolves to materially different definitions." if not collisions else f"{len(collisions)} mechanic display name(s) have materially different definitions.",
        collisions or None,
    )
    add_check(
        report,
        "WEAPON_MECHANIC_DEFINITION_MISSING",
        "ERROR" if missing_definitions else "PASS",
        "Every displayed Weapon Action/Critical Effect has normalized reference text." if not missing_definitions else f"{len(missing_definitions)} displayed mechanic(s) lack a unique normalized definition.",
        missing_definitions or None,
    )
    add_check(
        report,
        "WEAPON_MECHANIC_ORPHAN_DEFINITION",
        "ERROR" if orphans else "PASS",
        "No unused mechanic definitions remain in the Weapon sidecar." if not orphans else f"{len(orphans)} mechanic definition(s) are not displayed by any Weapon.",
        orphans or None,
    )

    action_refs, critical_refs = _reference_dicts(reference_bundle)
    duplicate_action_refs = sorted({r["name"] for r in action_refs if [x["name"].casefold() for x in action_refs].count(r["name"].casefold()) > 1})
    duplicate_critical_refs = sorted({r["name"] for r in critical_refs if [x["name"].casefold() for x in critical_refs].count(r["name"].casefold()) > 1})
    duplicate_refs = {"actions": duplicate_action_refs, "criticalEffects": duplicate_critical_refs}
    add_check(
        report,
        "WEAPON_REFERENCE_UNIQUENESS",
        "ERROR" if duplicate_action_refs or duplicate_critical_refs else "PASS",
        "Each deduplicated mechanic appears exactly once in its reference section." if not duplicate_action_refs and not duplicate_critical_refs else "Duplicate mechanic names remain after reference normalization.",
        duplicate_refs if duplicate_action_refs or duplicate_critical_refs else None,
    )

    bad_reference_names = [r["name"] for r in critical_refs if r["name"].casefold().startswith("critical effect:")]
    html_reference_text = [r["name"] for r in action_refs + critical_refs if HTML_TAG_RE.search(r["description"])]
    add_check(
        report,
        "CRITICAL_REFERENCE_DISPLAY",
        "ERROR" if bad_reference_names else "PASS",
        "Critical Effect reference names contain no Foundry prefix." if not bad_reference_names else "Critical Effect prefix leaked into reference names.",
        bad_reference_names or None,
    )
    add_check(
        report,
        "REFERENCE_PLAIN_TEXT",
        "ERROR" if html_reference_text else "PASS",
        "Mechanic reference definitions are normalized plain text." if not html_reference_text else "HTML remains in mechanic reference definitions.",
        html_reference_text or None,
    )

    return report, config, sidecar, tier_rows, reference_bundle


def compile_lualatex(tex_path: Path) -> tuple[bool, str]:
    exe = shutil.which("lualatex")
    if not exe:
        return False, "LuaLaTeX was not found on PATH."
    output = []
    for _ in range(2):
        proc = subprocess.run(
            [exe, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=str(tex_path.parent),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output.append(proc.stdout or "")
        if proc.returncode != 0:
            return False, "\n".join(output)
    return True, "\n".join(output)


def _chapter16_latex(tier_rows: dict[int, list], reference_bundle: dict, config: dict) -> tuple[str, str]:
    tier_tables = {
        tier: render_equipment_catalog_latex(rows, config)
        for tier, rows in sorted(tier_rows.items())
    }
    actions_reference = render_mechanics_reference_latex(reference_bundle["actions"], config)
    critical_reference = render_mechanics_reference_latex(reference_bundle["criticalEffects"], config)
    family_latex = render_weapons_family_latex(tier_tables, actions_reference, critical_reference, config)
    document = render_weapons_chapter_document(family_latex, config)
    return family_latex, document


def _pandoc_transform_family(manuscript_path: Path, family_latex: str, report: dict, output_path: Path | None = None) -> dict | None:
    exe = shutil.which("pandoc")
    if not exe:
        add_check(report, "TOOL_PANDOC", "BLOCKED", "Pandoc was not found on PATH.")
        return None
    add_check(report, "TOOL_PANDOC", "PASS", exe)
    proc = subprocess.run(
        [exe, str(manuscript_path), "--from", PANDOC_FROM, "--to", "json"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        add_check(report, "PANDOC_AST_PARSE", "ERROR", "Pandoc could not parse the assembled player manuscript.", (proc.stderr or "")[-12000:])
        return None
    try:
        ast = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        add_check(report, "PANDOC_AST_PARSE", "ERROR", f"Pandoc returned invalid AST JSON: {exc}")
        return None
    add_check(report, "PANDOC_AST_PARSE", "PASS", "Assembled player manuscript parsed into a Pandoc AST.")
    replaced = replace_family_div_with_latex(ast, "weapons", family_latex)
    add_check(
        report,
        "WEAPON_FAMILY_AST_REPLACEMENT",
        "PASS" if replaced == 1 else "ERROR",
        f"Semantic family:weapons replacement count is {replaced}; expected exactly 1.",
    )
    if output_path is not None and replaced == 1:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(ast, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return ast


def _validate_pdf_output(pdf_path: Path, report: dict) -> None:
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        add_check(report, "PDF_EXISTS", "ERROR", f"Chapter 16 PDF is missing or empty: {pdf_path}")
        return
    add_check(report, "PDF_EXISTS", "PASS", f"Chapter 16 PDF exists ({pdf_path.stat().st_size} bytes).")
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        add_check(report, "PDF_PAGE_SIZE", "INFO", "pdfinfo is unavailable; page-size validation skipped.")
        return
    proc = subprocess.run([pdfinfo, str(pdf_path)], text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        add_check(report, "PDF_OPEN", "ERROR", "pdfinfo could not open the Chapter 16 PDF.", proc.stderr[-4000:])
        return
    add_check(report, "PDF_OPEN", "PASS", "pdfinfo opens the Chapter 16 PDF.")
    size_line = next((line for line in proc.stdout.splitlines() if line.startswith("Page size:")), "")
    letter = "612 x 792" in size_line or "letter" in size_line.casefold()
    add_check(report, "PDF_PAGE_SIZE", "PASS" if letter else "ERROR", size_line or "Page size unknown.")


def command_inspect(args: argparse.Namespace) -> int:
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    sidecar_path = resolve_path(args.sidecar, DEFAULT_SIDECAR)
    manuscript_path = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT)
    report, config, _, rows = validate_catalog(config_path, sidecar_path, manuscript_path, args.tier)
    result = {
        "report": report,
        "family": config.get("family") if config else None,
        "tier": args.tier,
        "rows": [{"semanticId": row.semantic_id, "name": row.name, "group": row.group, "cells": row.cells} for row in rows],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def command_validate(args: argparse.Namespace) -> int:
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    sidecar_path = resolve_path(args.sidecar, DEFAULT_SIDECAR)
    manuscript_path = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT)
    report, _, _, _ = validate_catalog(config_path, sidecar_path, manuscript_path, args.tier)
    report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)
    write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def command_build(args: argparse.Namespace) -> int:
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    sidecar_path = resolve_path(args.sidecar, DEFAULT_SIDECAR)
    manuscript_path = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT)
    prototype_dir = resolve_path(args.output_dir, DEFAULT_PROTOTYPE_DIR)
    report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)

    report, config, _, rows = validate_catalog(config_path, sidecar_path, manuscript_path, args.tier)
    if report["status"] != "PASS" or config is None:
        write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    prototype_dir.mkdir(parents=True, exist_ok=True)
    table_latex = render_equipment_catalog_latex(rows, config)
    document = render_tier_prototype_document(table_latex, config, args.tier)
    stem = f"Cybermancy_Chapter16_Tier{args.tier}_Weapons_Table_Step6C"
    tex_path = prototype_dir / f"{stem}.tex"
    tex_path.write_text(document, encoding="utf-8")
    write_json(
        prototype_dir / f"weapons-tier{args.tier}-rows.json",
        {
            "schema": "cybermancy-step6-equipment-catalog-rows-v1.0",
            "family": config["family"],
            "tier": args.tier,
            "rows": [{"semanticId": row.semantic_id, "name": row.name, "group": row.group, "cells": row.cells} for row in rows],
        },
    )
    add_check(report, "LATEX_SOURCE", "PASS", f"Generated {tex_path} from normalized Step 4 data.")

    if args.tex_only:
        add_check(report, "PDF_RENDER", "INFO", "--tex-only requested; LuaLaTeX render was skipped.")
    else:
        ok, log = compile_lualatex(tex_path)
        pdf_path = prototype_dir / f"{stem}.pdf"
        if ok and pdf_path.is_file():
            add_check(report, "PDF_RENDER", "PASS", f"Rendered {pdf_path}.")
        else:
            add_check(report, "PDF_RENDER", "ERROR", "LuaLaTeX failed to render the Tier Equipment Catalog prototype.", log[-12000:])

    write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def _chapter16_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    sidecar_path = resolve_path(args.sidecar, DEFAULT_SIDECAR)
    manuscript_path = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT)
    output_dir = resolve_path(getattr(args, "output_dir", None), DEFAULT_CHAPTER16_DIR)
    report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)
    return config_path, sidecar_path, manuscript_path, output_dir, report_dir


def command_inspect_chapter16(args: argparse.Namespace) -> int:
    config_path, sidecar_path, manuscript_path, _, _ = _chapter16_paths(args)
    report, config, _, tier_rows, refs = validate_chapter16(config_path, sidecar_path, manuscript_path)
    result = {
        "report": report,
        "config": config,
        "tiers": {
            str(tier): [{"semanticId": row.semantic_id, "name": row.name, "group": row.group, "cells": row.cells} for row in rows]
            for tier, rows in sorted(tier_rows.items())
        },
        "references": None if refs is None else {
            "actions": [ref.to_dict() for ref in refs["actions"]],
            "criticalEffects": [ref.to_dict() for ref in refs["criticalEffects"]],
            "collisions": refs["collisions"],
            "missingDefinitions": refs["missingDefinitions"],
            "orphanDefinitions": refs["orphanDefinitions"],
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def command_validate_chapter16(args: argparse.Namespace) -> int:
    config_path, sidecar_path, manuscript_path, _, report_dir = _chapter16_paths(args)
    report, config, _, tier_rows, refs = validate_chapter16(config_path, sidecar_path, manuscript_path)
    if report["status"] == "PASS" and config is not None and refs is not None:
        family_latex, _ = _chapter16_latex(tier_rows, refs, config)
        _pandoc_transform_family(manuscript_path, family_latex, report)
    else:
        add_check(report, "WEAPON_FAMILY_AST_REPLACEMENT", "INFO", "AST replacement check deferred until semantic/reference validation passes.")
    write_json(report_dir / "chapter16-weapons.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def command_build_chapter16(args: argparse.Namespace) -> int:
    config_path, sidecar_path, manuscript_path, output_dir, report_dir = _chapter16_paths(args)
    report, config, _, tier_rows, refs = validate_chapter16(config_path, sidecar_path, manuscript_path)
    report_path = report_dir / "chapter16-weapons.json"
    if report["status"] != "PASS" or config is None or refs is None:
        add_check(report, "CHAPTER16_BUILD", "BLOCKED", "Complete Chapter 16 rendering is blocked by semantic/reference validation errors.")
        write_json(report_path, report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    family_latex, document = _chapter16_latex(tier_rows, refs, config)
    stem = "Cybermancy_Chapter16_Weapons_Step6D"
    tex_path = output_dir / f"{stem}.tex"
    pdf_path = output_dir / f"{stem}.pdf"
    family_path = output_dir / "weapons-family-step6.tex"
    ast_path = output_dir / "player-guide-step6-weapons.ast.json"
    tex_path.write_text(document, encoding="utf-8")
    family_path.write_text(family_latex, encoding="utf-8")

    write_json(
        output_dir / "weapons-all-tiers-rows.json",
        {
            "schema": "cybermancy-step6-weapons-chapter-rows-v1.0",
            "tiers": {
                str(tier): [{"semanticId": row.semantic_id, "name": row.name, "group": row.group, "cells": row.cells} for row in rows]
                for tier, rows in sorted(tier_rows.items())
            },
        },
    )
    write_json(output_dir / "weapon-actions.json", {"schema": "cybermancy-step6-mechanic-reference-v1.0", "references": [ref.to_dict() for ref in refs["actions"]]})
    write_json(output_dir / "critical-effects.json", {"schema": "cybermancy-step6-mechanic-reference-v1.0", "references": [ref.to_dict() for ref in refs["criticalEffects"]]})
    add_check(report, "LATEX_SOURCE", "PASS", f"Generated complete Chapter 16 LaTeX at {tex_path}.")

    _pandoc_transform_family(manuscript_path, family_latex, report, ast_path)
    if report["status"] != "PASS":
        add_check(report, "CHAPTER16_BUILD", "BLOCKED", "PDF rendering blocked because semantic AST integration failed.")
        write_json(report_path, report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    if args.tex_only:
        add_check(report, "PDF_RENDER", "INFO", "--tex-only requested; LuaLaTeX render was skipped.")
    else:
        ok, log = compile_lualatex(tex_path)
        if ok and pdf_path.is_file():
            add_check(report, "PDF_RENDER", "PASS", f"Rendered complete Chapter 16 PDF at {pdf_path}.")
            overflow = [line.strip() for line in log.splitlines() if "Overfull \\hbox" in line or "Overfull \\vbox" in line]
            add_check(
                report,
                "LATEX_OVERFLOW",
                "ERROR" if overflow else "PASS",
                f"{len(overflow)} overfull LaTeX box warning(s) detected." if overflow else "No overfull LaTeX boxes detected.",
                overflow[:100] if overflow else None,
            )
            _validate_pdf_output(pdf_path, report)
        else:
            add_check(report, "PDF_RENDER", "ERROR", "LuaLaTeX failed to render the complete Chapter 16 Weapons artifact.", log[-12000:])

    add_check(report, "CHAPTER16_BUILD", "PASS" if report["status"] == "PASS" else "ERROR", "Complete Chapter 16 build completed." if report["status"] == "PASS" else "Complete Chapter 16 build produced validation errors.")
    write_json(report_path, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Cybermancy Step 6 Equipment Catalog and Chapter layout builder")
    sub = root.add_subparsers(dest="command", required=True)

    for name in ("inspect", "validate", "build"):
        p = sub.add_parser(name)
        p.add_argument("--tier", type=int, default=1)
        p.add_argument("--config")
        p.add_argument("--sidecar")
        p.add_argument("--manuscript")
        p.add_argument("--report-dir")
        if name == "build":
            p.add_argument("--output-dir")
            p.add_argument("--tex-only", action="store_true")

    for name in ("inspect-chapter16", "validate-chapter16", "build-chapter16"):
        p = sub.add_parser(name)
        p.add_argument("--config")
        p.add_argument("--sidecar")
        p.add_argument("--manuscript")
        p.add_argument("--report-dir")
        if name == "build-chapter16":
            p.add_argument("--output-dir")
            p.add_argument("--tex-only", action="store_true")

    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "validate":
        return command_validate(args)
    if args.command == "build":
        return command_build(args)
    if args.command == "inspect-chapter16":
        return command_inspect_chapter16(args)
    if args.command == "validate-chapter16":
        return command_validate_chapter16(args)
    if args.command == "build-chapter16":
        return command_build_chapter16(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
