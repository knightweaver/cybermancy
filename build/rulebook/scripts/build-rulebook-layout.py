#!/usr/bin/env python3
"""Cybermancy Rulebook Step 6 Equipment & Technology layout builder.

Consumes only Step 4 normalized outputs. The generic ``*-equipment`` commands
select a family configuration from ``build/rulebook/layout/equipment``. Weapons
retain their accepted Chapter 16 specialist contract; Ammunition is the first
single-catalog family using the generic path.

Generic Equipment commands accept either ``--family <name>`` or ``--all``.
``--all`` discovers every approved ``*-v1.json`` Equipment config, executes the
configured families in chapter order, and writes an aggregate equipment-all.json
report for validation/build operations.
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
EQUIPMENT_CONFIG_DIR = LAYOUT_DIR / "equipment"
DEFAULT_SECTION_REGISTRY = EQUIPMENT_CONFIG_DIR / "equipment-section-v1.json"
DEFAULT_WEAPONS_CONFIG = EQUIPMENT_CONFIG_DIR / "weapons-v1.json"
DEFAULT_CONFIG = DEFAULT_WEAPONS_CONFIG
DEFAULT_SIDECAR = METADATA_DIR / "structured-entities.json"
DEFAULT_MANUSCRIPT = ASSEMBLED_DIR / "player-guide.md"
DEFAULT_PROTOTYPE_DIR = LAYOUT_DIR / "prototype"
DEFAULT_CHAPTER16_DIR = LAYOUT_DIR / "chapter16"
DEFAULT_REPORT_DIR = LAYOUT_DIR / "reports"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_batch import run_all_equipment_command  # noqa: E402
from rulebook_layout.equipment_bootstrap import inspect_equipment_bootstrap  # noqa: E402
from rulebook_layout.equipment_catalog import (  # noqa: E402
    build_catalog_rows, get_path, render_equipment_catalog_latex,
    replace_family_div_with_latex,
)
from rulebook_layout.latex import (  # noqa: E402
    render_equipment_chapter_document, render_tier_prototype_document,
    render_weapons_family_latex,
)
from rulebook_layout.mechanics_reference import (  # noqa: E402
    collect_weapon_references, render_mechanics_reference_latex,
)

DAMAGE_FORMULA_RE = re.compile(r"^(?:\d*d\d+(?:[+-]\d+)?)(?:; \d*d\d+(?:[+-]\d+)?)*$", re.I)
HTML_TAG_RE = re.compile(r"<[^>]+>")
CAMEL_CODE_RE = re.compile(r"[a-z][A-Z]")
PANDOC_FROM = "markdown+fenced_divs+bracketed_spans+pipe_tables+grid_tables+definition_lists+raw_attribute"
SIDECAR_SCHEMA_C = "cybermancy-step4-structured-entities-v1.0"
SIDECAR_SCHEMA_D = "cybermancy-step4-structured-entities-v1.1"
FAMILY_ALIASES = {"ammunition": "ammo", "armor": "armors"}


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


def resolve_path(value: str | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value else default.resolve()


def canonical_family(value: str) -> str:
    key = str(value or "").strip().casefold()
    return FAMILY_ALIASES.get(key, key)


def default_family_config(family: str) -> Path:
    return EQUIPMENT_CONFIG_DIR / f"{canonical_family(family)}-v1.json"


def _report(schema: str, config: Path, sidecar: Path, manuscript: Path, **extra) -> dict:
    return {
        "schema": schema, "status": "PASS", "checks": [], "warnings": [], "errors": [],
        "inputs": {"config": str(config), "structuredEntities": str(sidecar), "assembledManuscript": str(manuscript)},
        **extra,
    }


def _inputs_ok(report: dict, config: Path, sidecar: Path, manuscript: Path) -> bool:
    for code, path in (("CONFIG_PRESENT", config), ("STRUCTURED_SIDECAR_PRESENT", sidecar), ("ASSEMBLED_MANUSCRIPT_PRESENT", manuscript)):
        add_check(report, code, "PASS" if path.is_file() else "BLOCKED", str(path) if path.is_file() else f"Required Step 6 input is missing: {path}")
    return report["status"] == "PASS"


def _family_entities(sidecar: dict, family: str) -> list[dict]:
    values = sidecar.get("entities") if isinstance(sidecar.get("entities"), list) else []
    return [entity for entity in values if entity.get("family") == family]


def _identity_check(entities: list[dict], report: dict, code: str) -> None:
    semantic = [str(e.get("semanticId") or "") for e in entities]
    source = [str(e.get("sourceId") or "") for e in entities]
    dup_sem = sorted({v for v in semantic if v and semantic.count(v) > 1})
    dup_src = sorted({v for v in source if v and source.count(v) > 1})
    missing = [e.get("name") for e in entities if not e.get("semanticId") or not e.get("sourceId")]
    bad = bool(dup_sem or dup_src or missing)
    add_check(report, code, "ERROR" if bad else "PASS", "Structured sidecar identity is unique and complete." if not bad else "Structured sidecar contains duplicate or missing identities.", {"duplicateSemanticIds": dup_sem, "duplicateSourceIds": dup_src, "missingIds": missing} if bad else None)


def _table_width(config: dict) -> float:
    columns = list(config.get("columns", []))
    table_style = config.get("tableStyle", {}) if isinstance(config.get("tableStyle"), dict) else {}
    tabcolsep = float(table_style.get("tabcolsepPt", 1.4) or 1.4)
    return sum(float(c.get("widthIn", 0)) for c in columns) + max(0, len(columns) - 1) * (2 * tabcolsep / 72.27)


def _column_check(config: dict, report: dict, expected: list[str] | None, code: str) -> None:
    labels = [str(c.get("label") or "") for c in config.get("columns", [])]
    ok = bool(labels) and (expected is None or labels == expected)
    add_check(report, code, "PASS" if ok else "ERROR", f"Configured column contract: {' | '.join(labels)}" if ok else "Configured columns differ from the family publication contract.", None if ok else {"expected": expected, "actual": labels})
    occupied = _table_width(config)
    add_check(report, "TABLE_WIDTH_BUDGET", "PASS" if occupied <= 7.58 else "ERROR", f"Configured table width budget is {occupied:.3f}in within 7.58in." if occupied <= 7.58 else f"Configured table requires {occupied:.3f}in; only 7.58in is available.")


def _weapon_row_checks(rows: list, report: dict, prefix: str = "") -> None:
    p = f"{prefix}_" if prefix else ""
    bad_crit = [r.name for r in rows if "Critical Effect:" in r.cells.get("criticalEffect", "")]
    add_check(report, f"{p}CRITICAL_EFFECT_DISPLAY", "ERROR" if bad_crit else "PASS", "Critical Effect display names contain no Foundry prefix." if not bad_crit else "Critical Effect prefix leaked into Step 6 display.", bad_crit or None)
    bad_damage = []
    for row in rows:
        value = row.cells.get("publicationData.attack.damageFormula", "—")
        if value != "—" and not DAMAGE_FORMULA_RE.fullmatch(value):
            bad_damage.append({"name": row.name, "damage": value})
    add_check(report, f"{p}DAMAGE_FORMULA_ONLY", "ERROR" if bad_damage else "PASS", "Damage cells contain formula only; damage types are absent." if not bad_damage else "Damage cells contain values other than formula-only publication data.", bad_damage or None)
    html = [r.name for r in rows if HTML_TAG_RE.search(r.cells.get("publicationData.description", ""))]
    add_check(report, f"{p}PLAIN_TEXT_DESCRIPTIONS", "ERROR" if html else "PASS", "Catalog descriptions are normalized plain text." if not html else "HTML remains in normalized descriptions.", html or None)
    code_style = []
    for row in rows:
        for key in ("publicationData.attack.trait", "publicationData.attack.range", "publicationData.burden"):
            value = row.cells.get(key, "")
            if CAMEL_CODE_RE.search(value) or "_" in value:
                code_style.append({"name": row.name, "field": key, "value": value})
    add_check(report, f"{p}HUMANIZED_ENUM_DISPLAY", "ERROR" if code_style else "PASS", "Trait, Range, and Burden use reader-facing grammar." if not code_style else "Code-style enum values remain in Trait/Range/Burden display.", code_style or None)


def validate_catalog(config_path: Path, sidecar_path: Path, manuscript_path: Path, tier: int):
    """Backward-compatible Step 6C single-tier Weapons validator."""
    report = _report("cybermancy-rulebook-step6-equipment-catalog-validation-v1.0", config_path, sidecar_path, manuscript_path, tier=tier)
    if not _inputs_ok(report, config_path, sidecar_path, manuscript_path):
        return report, None, None, []
    try:
        config, sidecar = load_json(config_path), load_json(sidecar_path)
    except Exception as exc:
        add_check(report, "INPUT_JSON", "ERROR", f"Could not load Step 6 JSON input: {exc}")
        return report, None, None, []
    schema = sidecar.get("schema")
    add_check(report, "SIDECAR_SCHEMA", "PASS" if schema in {SIDECAR_SCHEMA_C, SIDECAR_SCHEMA_D} else "ERROR", str(schema))
    family = str(config.get("family") or "")
    add_check(report, "CATALOG_FAMILY", "PASS" if family else "ERROR", family or "Equipment catalog configuration has no family.")
    marker = f"family:{family}"
    manuscript = manuscript_path.read_text(encoding="utf-8")
    add_check(report, "MANUSCRIPT_FAMILY_ALIGNMENT", "PASS" if marker in manuscript else "ERROR", f"Assembled manuscript contains {marker}." if marker in manuscript else f"Assembled manuscript does not contain {marker}.")
    entities = sidecar.get("entities") if isinstance(sidecar.get("entities"), list) else []
    rows = build_catalog_rows(entities, config, tier=tier)
    expected = config.get("expectedTierCounts", {}).get(str(tier))
    add_check(report, "TIER_ENTITY_COUNT", "WARNING" if expected is None else ("PASS" if len(rows) == int(expected) else "ERROR"), f"Tier {tier} contains {len(rows)} catalog rows." if expected is not None else f"No expected count configured for Tier {tier}; found {len(rows)} rows.")
    _column_check(config, report, ["Name", "Tier", "Trait", "Range", "Burden", "Damage", "Action", "Critical Effect", "Description"], "WEAPON_COLUMN_CONTRACT")
    _weapon_row_checks(rows, report)
    by_name = {r.name: r for r in rows}
    spur = by_name.get("Cyber Spur")
    if spur is not None:
        actual = spur.cells.get("action")
        add_check(report, "CYBER_SPUR_ACTION_COMPOSITION", "PASS" if actual == "Retractable, Concealed" else "ERROR", actual or "missing")
    absent = []
    for name in ("Light Semi-auto pistol", "Heavy Semi-auto pistol"):
        row = by_name.get(name)
        if row and (row.cells.get("action") != "—" or row.cells.get("criticalEffect") != "—"):
            absent.append(name)
    add_check(report, "ABSENT_MECHANICS_DISPLAY", "ERROR" if absent else "PASS", "Absent Action/Critical Effect mechanics render as em dashes." if not absent else "Weapons with absent mechanics did not render em dashes.", absent or None)
    groups = []
    for row in rows:
        if not groups or groups[-1] != row.group:
            groups.append(row.group)
    expected_groups = config.get("expectedTierGroups", {}).get(str(tier))
    add_check(report, "TRAIT_GROUPS", "INFO" if expected_groups is None else ("PASS" if groups == expected_groups else "ERROR"), "No expected Trait group sequence configured." if expected_groups is None else f"Tier {tier} groups follow the approved Trait sequence." if groups == expected_groups else "Tier Trait group sequence differs from the approved configuration.", groups if expected_groups is None else None if groups == expected_groups else {"expected": expected_groups, "actual": groups})
    return report, config, sidecar, rows


def validate_chapter16(config_path: Path, sidecar_path: Path, manuscript_path: Path):
    report = _report("cybermancy-rulebook-step6-chapter16-validation-v1.0", config_path, sidecar_path, manuscript_path, chapter=16, family="weapons")
    if not _inputs_ok(report, config_path, sidecar_path, manuscript_path):
        return report, None, None, {}, None
    try:
        config, sidecar = load_json(config_path), load_json(sidecar_path)
    except Exception as exc:
        add_check(report, "INPUT_JSON", "ERROR", f"Could not load Step 6 JSON input: {exc}")
        return report, None, None, {}, None
    add_check(report, "SIDECAR_SCHEMA", "PASS" if sidecar.get("schema") == SIDECAR_SCHEMA_D else "ERROR", str(sidecar.get("schema")))
    add_check(report, "CATALOG_FAMILY", "PASS" if config.get("family") == "weapons" else "ERROR", str(config.get("family") or "missing"))
    manuscript = manuscript_path.read_text(encoding="utf-8")
    add_check(report, "MANUSCRIPT_FAMILY_ALIGNMENT", "PASS" if "family:weapons" in manuscript else "ERROR", "Assembled manuscript contains family:weapons." if "family:weapons" in manuscript else "Assembled manuscript does not contain family:weapons.")
    weapons = _family_entities(sidecar, "weapons")
    expected_total = int(config.get("expectedEntityCount", 47))
    add_check(report, "WEAPON_ENTITY_COUNT", "PASS" if len(weapons) == expected_total else "ERROR", f"Structured sidecar contains {len(weapons)} Weapons; expected {expected_total}.")
    _identity_check(weapons, report, "WEAPON_ENTITY_IDENTITY")
    _column_check(config, report, ["Name", "Tier", "Trait", "Range", "Burden", "Damage", "Action", "Critical Effect", "Description"], "WEAPON_COLUMN_CONTRACT")

    tier_rows, all_rows = {}, []
    for tier_text, expected in sorted(config.get("expectedTierCounts", {}).items(), key=lambda x: int(x[0])):
        tier = int(tier_text)
        rows = build_catalog_rows(weapons, config, tier=tier)
        tier_rows[tier] = rows; all_rows.extend(rows)
        add_check(report, f"TIER_{tier}_ENTITY_COUNT", "PASS" if len(rows) == int(expected) else "ERROR", f"Tier {tier} contains {len(rows)} Weapons; expected {expected}.")
        keys = [(r.group.casefold(), r.name.casefold(), r.name) for r in rows]
        missing_traits = [r.name for r in rows if r.group == str(config.get("display", {}).get("missing", "—"))]
        ok = keys == sorted(keys) and not missing_traits
        add_check(report, f"TIER_{tier}_TRAIT_NAME_ORDER", "PASS" if ok else "ERROR", f"Tier {tier} follows Trait → Name ordering." if ok else f"Tier {tier} does not follow Trait → Name ordering or has missing Traits.", {"missingTraits": missing_traits} if not ok else None)
    _weapon_row_checks(all_rows, report, prefix="CHAPTER16")
    by_name = {r.name: r for r in all_rows}
    spur = by_name.get("Cyber Spur")
    add_check(report, "CYBER_SPUR_ACTION_COMPOSITION", "PASS" if spur and spur.cells.get("action") == "Retractable, Concealed" else "ERROR", "Retractable, Concealed" if spur and spur.cells.get("action") == "Retractable, Concealed" else "Cyber Spur must display Retractable, Concealed.")
    absent = [name for name in ("Light Semi-auto pistol", "Heavy Semi-auto pistol") if (by_name.get(name) and (by_name[name].cells.get("action") != "—" or by_name[name].cells.get("criticalEffect") != "—"))]
    add_check(report, "ABSENT_MECHANICS_DISPLAY", "ERROR" if absent else "PASS", "Absent Action/Critical Effect mechanics render as em dashes." if not absent else "Weapons with absent mechanics did not render em dashes.", absent or None)

    refs = collect_weapon_references(weapons)
    collisions, missing, orphans = refs["collisions"], refs["missingDefinitions"], refs["orphanDefinitions"]
    add_check(report, "WEAPON_MECHANIC_NAME_COLLISION", "ERROR" if collisions else "PASS", "No mechanic display name resolves to materially different definitions." if not collisions else f"{len(collisions)} mechanic display name(s) have materially different definitions.", collisions or None)
    add_check(report, "WEAPON_MECHANIC_DEFINITION_MISSING", "ERROR" if missing else "PASS", "Every displayed Weapon Action/Critical Effect has normalized reference text." if not missing else f"{len(missing)} displayed mechanic(s) lack a unique normalized definition.", missing or None)
    add_check(report, "WEAPON_MECHANIC_ORPHAN_DEFINITION", "ERROR" if orphans else "PASS", "No unused mechanic definitions remain in the Weapon sidecar." if not orphans else f"{len(orphans)} mechanic definition(s) are not displayed by any Weapon.", orphans or None)
    actions = [r.to_dict() for r in refs["actions"]]; critical = [r.to_dict() for r in refs["criticalEffects"]]
    dup_a = sorted({r["name"] for r in actions if [x["name"].casefold() for x in actions].count(r["name"].casefold()) > 1})
    dup_c = sorted({r["name"] for r in critical if [x["name"].casefold() for x in critical].count(r["name"].casefold()) > 1})
    add_check(report, "WEAPON_REFERENCE_UNIQUENESS", "ERROR" if dup_a or dup_c else "PASS", "Each deduplicated mechanic appears exactly once in its reference section." if not dup_a and not dup_c else "Duplicate mechanic names remain after reference normalization.", {"actions": dup_a, "criticalEffects": dup_c} if dup_a or dup_c else None)
    bad_names = [r["name"] for r in critical if r["name"].casefold().startswith("critical effect:")]
    html_refs = [r["name"] for r in actions + critical if HTML_TAG_RE.search(r["description"])]
    add_check(report, "CRITICAL_REFERENCE_DISPLAY", "ERROR" if bad_names else "PASS", "Critical Effect reference names contain no Foundry prefix." if not bad_names else "Critical Effect prefix leaked into reference names.", bad_names or None)
    add_check(report, "REFERENCE_PLAIN_TEXT", "ERROR" if html_refs else "PASS", "Mechanic reference definitions are normalized plain text." if not html_refs else "HTML remains in mechanic reference definitions.", html_refs or None)
    return report, config, sidecar, tier_rows, refs


def validate_equipment_family(family: str, config_path: Path, sidecar_path: Path, manuscript_path: Path):
    family = canonical_family(family)
    if family == "weapons":
        report, config, sidecar, tier_rows, refs = validate_chapter16(config_path, sidecar_path, manuscript_path)
        return report, config, {"sidecar": sidecar, "tierRows": tier_rows, "references": refs}, []
    report = _report("cybermancy-rulebook-step6-equipment-family-validation-v1.0", config_path, sidecar_path, manuscript_path, family=family, chapter=None)
    if not _inputs_ok(report, config_path, sidecar_path, manuscript_path):
        return report, None, None, []
    try:
        config, sidecar = load_json(config_path), load_json(sidecar_path)
    except Exception as exc:
        add_check(report, "INPUT_JSON", "ERROR", f"Could not load Step 6 JSON input: {exc}")
        return report, None, None, []
    report["chapter"] = config.get("chapter")
    add_check(report, "SIDECAR_SCHEMA", "PASS" if sidecar.get("schema") == SIDECAR_SCHEMA_D else "ERROR", str(sidecar.get("schema")))
    actual_family = str(config.get("family") or "")
    add_check(report, "CATALOG_FAMILY", "PASS" if actual_family == family else "ERROR", actual_family if actual_family == family else f"Config family {actual_family!r} does not match requested family {family!r}.")
    marker = f"family:{family}"
    manuscript = manuscript_path.read_text(encoding="utf-8")
    add_check(report, "MANUSCRIPT_FAMILY_ALIGNMENT", "PASS" if marker in manuscript else "ERROR", f"Assembled manuscript contains {marker}." if marker in manuscript else f"Assembled manuscript does not contain {marker}.")
    entities = _family_entities(sidecar, family)
    expected = config.get("expectedEntityCount")
    status = "PASS" if expected is not None and len(entities) == int(expected) else "ERROR" if expected is not None else "INFO"
    add_check(report, "EQUIPMENT_ENTITY_COUNT", status, f"Structured sidecar contains {len(entities)} {config.get('title', family)} entities; expected {expected}." if expected is not None else f"Structured sidecar contains {len(entities)} {family} entities; no expected count configured.")
    _identity_check(entities, report, "EQUIPMENT_ENTITY_IDENTITY")
    expected_labels = config.get("expectedColumnLabels") if isinstance(config.get("expectedColumnLabels"), list) else None
    _column_check(config, report, expected_labels, "EQUIPMENT_COLUMN_CONTRACT")
    rows = build_catalog_rows(entities, config)
    add_check(report, "CATALOG_ROW_COUNT", "PASS" if len(rows) == len(entities) else "ERROR", f"Catalog contains {len(rows)} rows for {len(entities)} source entities.")
    missing_required = []
    for entity in entities:
        for field in [str(x) for x in config.get("requiredPublicationFields", [])]:
            if get_path(entity, field) in (None, "", [], {}):
                missing_required.append({"name": entity.get("name"), "field": field})
    add_check(report, "REQUIRED_PUBLICATION_FIELDS", "ERROR" if missing_required else "PASS", "All required publication fields are populated." if not missing_required else f"{len(missing_required)} required publication field value(s) are missing.", missing_required or None)
    html = [r.name for r in rows if HTML_TAG_RE.search(r.cells.get("publicationData.description", ""))]
    add_check(report, "PLAIN_TEXT_DESCRIPTIONS", "ERROR" if html else "PASS", "Catalog descriptions are normalized plain text." if not html else "HTML remains in normalized descriptions.", html or None)
    tier_mode = str(config.get("tierMode") or "optional")
    if tier_mode == "absent":
        bad_tiers = [e.get("name") for e in entities if get_path(e, "publicationData.tier") not in (None, "")]
        add_check(report, "TIER_CONTRACT", "ERROR" if bad_tiers else "PASS", "This family has no canonical Tier values; no Tier column/grouping will be synthesized." if not bad_tiers else "Tier values appeared in a family configured as tierless.", bad_tiers or None)
    else:
        add_check(report, "TIER_CONTRACT", "INFO", f"Tier mode is {tier_mode}; family-specific validation is deferred to its config.")
    if not config.get("groupBy") and tier_mode == "absent":
        names = [r.name for r in rows]
        expected_names = sorted(names, key=lambda v: (v.casefold(), v))
        add_check(report, "CATALOG_ORDER", "PASS" if names == expected_names else "ERROR", "Tierless catalog is alphabetized by Name." if names == expected_names else "Tierless catalog is not alphabetized by Name.")
    return report, config, sidecar, rows


def compile_lualatex(tex_path: Path) -> tuple[bool, str]:
    exe = shutil.which("lualatex")
    if not exe:
        return False, "LuaLaTeX was not found on PATH."
    output = []
    for _ in range(2):
        proc = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", tex_path.name], cwd=str(tex_path.parent), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output.append(proc.stdout or "")
        if proc.returncode != 0:
            return False, "\n".join(output)
    return True, "\n".join(output)


def _chapter16_latex(tier_rows: dict[int, list], refs: dict, config: dict) -> tuple[str, str]:
    tier_tables = {tier: render_equipment_catalog_latex(rows, config) for tier, rows in sorted(tier_rows.items())}
    family_latex = render_weapons_family_latex(tier_tables, render_mechanics_reference_latex(refs["actions"], config), render_mechanics_reference_latex(refs["criticalEffects"], config), config)
    return family_latex, render_equipment_chapter_document(family_latex, config)


def _catalog_family_latex(rows: list, config: dict) -> tuple[str, str]:
    family_latex = render_equipment_catalog_latex(rows, config)
    return family_latex, render_equipment_chapter_document(family_latex, config)


def _pandoc_transform_family(manuscript: Path, family: str, family_latex: str, report: dict, output: Path | None = None) -> None:
    exe = shutil.which("pandoc")
    if not exe:
        add_check(report, "TOOL_PANDOC", "BLOCKED", "Pandoc was not found on PATH.")
        return
    add_check(report, "TOOL_PANDOC", "PASS", exe)
    proc = subprocess.run([exe, str(manuscript), "--from", PANDOC_FROM, "--to", "json"], text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        add_check(report, "PANDOC_AST_PARSE", "ERROR", "Pandoc could not parse the assembled player manuscript.", (proc.stderr or "")[-12000:]); return
    try:
        ast = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        add_check(report, "PANDOC_AST_PARSE", "ERROR", f"Pandoc returned invalid AST JSON: {exc}"); return
    add_check(report, "PANDOC_AST_PARSE", "PASS", "Assembled player manuscript parsed into a Pandoc AST.")
    replaced = replace_family_div_with_latex(ast, family, family_latex)
    code = "WEAPON_FAMILY_AST_REPLACEMENT" if family == "weapons" else f"{family.upper().replace('-', '_')}_FAMILY_AST_REPLACEMENT"
    add_check(report, code, "PASS" if replaced == 1 else "ERROR", f"Semantic family:{family} replacement count is {replaced}; expected exactly 1.")
    if output is not None and replaced == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(ast, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def _validate_pdf(pdf: Path, report: dict, chapter: int) -> None:
    if not pdf.is_file() or pdf.stat().st_size == 0:
        add_check(report, "PDF_EXISTS", "ERROR", f"Chapter {chapter} PDF is missing or empty: {pdf}"); return
    add_check(report, "PDF_EXISTS", "PASS", f"Chapter {chapter} PDF exists ({pdf.stat().st_size} bytes).")
    exe = shutil.which("pdfinfo")
    if not exe:
        add_check(report, "PDF_PAGE_SIZE", "INFO", "pdfinfo is unavailable; page-size validation skipped."); return
    proc = subprocess.run([exe, str(pdf)], text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        add_check(report, "PDF_OPEN", "ERROR", f"pdfinfo could not open the Chapter {chapter} PDF.", proc.stderr[-4000:]); return
    add_check(report, "PDF_OPEN", "PASS", f"pdfinfo opens the Chapter {chapter} PDF.")
    size = next((line for line in proc.stdout.splitlines() if line.startswith("Page size:")), "")
    add_check(report, "PDF_PAGE_SIZE", "PASS" if ("612 x 792" in size or "letter" in size.casefold()) else "ERROR", size or "Page size unknown.")


def _rows(rows: list) -> list[dict]:
    return [{"semanticId": r.semantic_id, "name": r.name, "group": r.group, "cells": r.cells} for r in rows]


def command_inspect(args) -> int:
    config = resolve_path(args.config, DEFAULT_CONFIG); sidecar = resolve_path(args.sidecar, DEFAULT_SIDECAR); manuscript = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT)
    report, cfg, _, rows = validate_catalog(config, sidecar, manuscript, args.tier)
    print(json.dumps({"report": report, "family": cfg.get("family") if cfg else None, "tier": args.tier, "rows": _rows(rows)}, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def command_validate(args) -> int:
    config = resolve_path(args.config, DEFAULT_CONFIG); sidecar = resolve_path(args.sidecar, DEFAULT_SIDECAR); manuscript = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT); report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)
    report, _, _, _ = validate_catalog(config, sidecar, manuscript, args.tier)
    write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def command_build(args) -> int:
    config = resolve_path(args.config, DEFAULT_CONFIG); sidecar = resolve_path(args.sidecar, DEFAULT_SIDECAR); manuscript = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT); out = resolve_path(args.output_dir, DEFAULT_PROTOTYPE_DIR); report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)
    report, cfg, _, rows = validate_catalog(config, sidecar, manuscript, args.tier)
    if report["status"] != "PASS" or cfg is None:
        write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 2
    out.mkdir(parents=True, exist_ok=True); stem = f"Cybermancy_Chapter16_Tier{args.tier}_Weapons_Table_Step6C"; tex = out / f"{stem}.tex"; pdf = out / f"{stem}.pdf"
    tex.write_text(render_tier_prototype_document(render_equipment_catalog_latex(rows, cfg), cfg, args.tier), encoding="utf-8")
    write_json(out / f"weapons-tier{args.tier}-rows.json", {"schema": "cybermancy-step6-equipment-catalog-rows-v1.0", "family": "weapons", "tier": args.tier, "rows": _rows(rows)})
    add_check(report, "LATEX_SOURCE", "PASS", f"Generated {tex} from normalized Step 4 data.")
    if args.tex_only: add_check(report, "PDF_RENDER", "INFO", "--tex-only requested; LuaLaTeX render was skipped.")
    else:
        ok, log = compile_lualatex(tex); add_check(report, "PDF_RENDER", "PASS" if ok and pdf.is_file() else "ERROR", f"Rendered {pdf}." if ok and pdf.is_file() else "LuaLaTeX failed to render the Tier Equipment Catalog prototype.", None if ok and pdf.is_file() else log[-12000:])
    write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def _chapter16_paths(args):
    return resolve_path(args.config, DEFAULT_WEAPONS_CONFIG), resolve_path(args.sidecar, DEFAULT_SIDECAR), resolve_path(args.manuscript, DEFAULT_MANUSCRIPT), resolve_path(getattr(args, "output_dir", None), DEFAULT_CHAPTER16_DIR), resolve_path(args.report_dir, DEFAULT_REPORT_DIR)


def command_inspect_chapter16(args) -> int:
    config, sidecar, manuscript, _, _ = _chapter16_paths(args); report, cfg, _, tiers, refs = validate_chapter16(config, sidecar, manuscript)
    print(json.dumps({"report": report, "config": cfg, "tiers": {str(t): _rows(r) for t, r in sorted(tiers.items())}, "references": None if refs is None else {"actions": [r.to_dict() for r in refs["actions"]], "criticalEffects": [r.to_dict() for r in refs["criticalEffects"]], "collisions": refs["collisions"], "missingDefinitions": refs["missingDefinitions"], "orphanDefinitions": refs["orphanDefinitions"]}}, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def command_validate_chapter16(args) -> int:
    config, sidecar, manuscript, _, report_dir = _chapter16_paths(args); report, cfg, _, tiers, refs = validate_chapter16(config, sidecar, manuscript)
    if report["status"] == "PASS" and cfg is not None and refs is not None:
        family_latex, _ = _chapter16_latex(tiers, refs, cfg); _pandoc_transform_family(manuscript, "weapons", family_latex, report)
    else: add_check(report, "WEAPON_FAMILY_AST_REPLACEMENT", "INFO", "AST replacement check deferred until semantic/reference validation passes.")
    write_json(report_dir / "chapter16-weapons.json", report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def command_build_chapter16(args) -> int:
    config, sidecar, manuscript, out, report_dir = _chapter16_paths(args); report, cfg, _, tiers, refs = validate_chapter16(config, sidecar, manuscript); report_path = report_dir / "chapter16-weapons.json"
    if report["status"] != "PASS" or cfg is None or refs is None:
        add_check(report, "CHAPTER16_BUILD", "BLOCKED", "Complete Chapter 16 rendering is blocked by semantic/reference validation errors."); write_json(report_path, report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 2
    out.mkdir(parents=True, exist_ok=True); family_latex, document = _chapter16_latex(tiers, refs, cfg); stem = "Cybermancy_Chapter16_Weapons_Step6D"; tex = out / f"{stem}.tex"; pdf = out / f"{stem}.pdf"; ast = out / "player-guide-step6-weapons.ast.json"
    tex.write_text(document, encoding="utf-8"); (out / "weapons-family-step6.tex").write_text(family_latex, encoding="utf-8")
    write_json(out / "weapons-all-tiers-rows.json", {"schema": "cybermancy-step6-weapons-chapter-rows-v1.0", "tiers": {str(t): _rows(r) for t, r in sorted(tiers.items())}}); write_json(out / "weapon-actions.json", {"schema": "cybermancy-step6-mechanic-reference-v1.0", "references": [r.to_dict() for r in refs["actions"]]}); write_json(out / "critical-effects.json", {"schema": "cybermancy-step6-mechanic-reference-v1.0", "references": [r.to_dict() for r in refs["criticalEffects"]]})
    add_check(report, "LATEX_SOURCE", "PASS", f"Generated complete Chapter 16 LaTeX at {tex}."); _pandoc_transform_family(manuscript, "weapons", family_latex, report, ast)
    if report["status"] != "PASS": add_check(report, "CHAPTER16_BUILD", "BLOCKED", "PDF rendering blocked because semantic AST integration failed.")
    elif args.tex_only: add_check(report, "PDF_RENDER", "INFO", "--tex-only requested; LuaLaTeX render was skipped.")
    else:
        ok, log = compile_lualatex(tex)
        if ok and pdf.is_file():
            add_check(report, "PDF_RENDER", "PASS", f"Rendered complete Chapter 16 PDF at {pdf}."); overflow = [x.strip() for x in log.splitlines() if "Overfull \\hbox" in x or "Overfull \\vbox" in x]; add_check(report, "LATEX_OVERFLOW", "ERROR" if overflow else "PASS", f"{len(overflow)} overfull LaTeX box warning(s) detected." if overflow else "No overfull LaTeX boxes detected.", overflow or None); _validate_pdf(pdf, report, 16)
        else: add_check(report, "PDF_RENDER", "ERROR", "LuaLaTeX failed to render the complete Chapter 16 Weapons artifact.", log[-12000:])
    add_check(report, "CHAPTER16_BUILD", "PASS" if report["status"] == "PASS" else "ERROR", "Complete Chapter 16 build completed." if report["status"] == "PASS" else "Complete Chapter 16 build produced validation errors."); write_json(report_path, report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def _equipment_paths(args):
    family = canonical_family(args.family); config = resolve_path(args.config, default_family_config(family)); sidecar = resolve_path(args.sidecar, DEFAULT_SIDECAR); manuscript = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT); cfg = load_json(config) if config.is_file() else {}; chapter = int(cfg.get("chapter") or 0); out = resolve_path(getattr(args, "output_dir", None), LAYOUT_DIR / (f"chapter{chapter}" if chapter else family)); report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR); return family, config, sidecar, manuscript, out, report_dir


def _run_all(operation: str, args: argparse.Namespace) -> int:
    return run_all_equipment_command(
        operation,
        args,
        script_path=SCRIPT_PATH,
        config_dir=EQUIPMENT_CONFIG_DIR,
        default_sidecar=DEFAULT_SIDECAR,
        default_manuscript=DEFAULT_MANUSCRIPT,
        default_report_dir=DEFAULT_REPORT_DIR,
    )


def command_inspect_equipment(args) -> int:
    if getattr(args, "all", False):
        return _run_all("inspect", args)
    family, config, sidecar, manuscript, _, _ = _equipment_paths(args)
    if not config.is_file():
        payload = inspect_equipment_bootstrap(family, config, sidecar, manuscript, DEFAULT_SECTION_REGISTRY)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload["report"]["status"] == "PASS" else 2
    if family == "weapons": args.config = str(config); return command_inspect_chapter16(args)
    report, cfg, _, rows = validate_equipment_family(family, config, sidecar, manuscript); print(json.dumps({"report": report, "config": cfg, "rows": _rows(rows)}, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def command_validate_equipment(args) -> int:
    if getattr(args, "all", False):
        return _run_all("validate", args)
    family, config, sidecar, manuscript, _, report_dir = _equipment_paths(args)
    if family == "weapons": args.config = str(config); return command_validate_chapter16(args)
    report, cfg, _, rows = validate_equipment_family(family, config, sidecar, manuscript)
    if report["status"] == "PASS" and cfg is not None:
        family_latex, _ = _catalog_family_latex(rows, cfg); _pandoc_transform_family(manuscript, family, family_latex, report)
    else: add_check(report, f"{family.upper().replace('-', '_')}_FAMILY_AST_REPLACEMENT", "INFO", "AST replacement check deferred until family validation passes.")
    write_json(report_dir / f"equipment-{family}.json", report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def _safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def command_build_equipment(args) -> int:
    if getattr(args, "all", False):
        return _run_all("build", args)
    family, config, sidecar, manuscript, out, report_dir = _equipment_paths(args)
    if family == "weapons": args.config = str(config); args.output_dir = str(out); return command_build_chapter16(args)
    report, cfg, _, rows = validate_equipment_family(family, config, sidecar, manuscript); report_path = report_dir / f"equipment-{family}.json"
    if report["status"] != "PASS" or cfg is None:
        add_check(report, "EQUIPMENT_BUILD", "BLOCKED", f"{family} rendering is blocked by family validation errors."); write_json(report_path, report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 2
    out.mkdir(parents=True, exist_ok=True); family_latex, document = _catalog_family_latex(rows, cfg); chapter = int(cfg.get("chapter") or 0); title = str(cfg.get("title") or family); stem = str(cfg.get("outputStem") or f"Cybermancy_Chapter{chapter}_{_safe_stem(title)}_Step6"); tex = out / f"{stem}.tex"; pdf = out / f"{stem}.pdf"; ast = out / f"player-guide-step6-{family}.ast.json"
    tex.write_text(document, encoding="utf-8"); (out / f"{family}-family-step6.tex").write_text(family_latex, encoding="utf-8"); write_json(out / f"{family}-rows.json", {"schema": "cybermancy-step6-equipment-family-rows-v1.0", "family": family, "chapter": chapter, "rows": _rows(rows)}); add_check(report, "LATEX_SOURCE", "PASS", f"Generated Chapter {chapter} {title} LaTeX at {tex}."); _pandoc_transform_family(manuscript, family, family_latex, report, ast)
    if report["status"] != "PASS": add_check(report, "EQUIPMENT_BUILD", "BLOCKED", "PDF rendering blocked because semantic AST integration failed.")
    elif args.tex_only: add_check(report, "PDF_RENDER", "INFO", "--tex-only requested; LuaLaTeX render was skipped.")
    else:
        ok, log = compile_lualatex(tex)
        if ok and pdf.is_file():
            add_check(report, "PDF_RENDER", "PASS", f"Rendered Chapter {chapter} {title} PDF at {pdf}."); overflow = [x.strip() for x in log.splitlines() if "Overfull \\hbox" in x or "Overfull \\vbox" in x]; add_check(report, "LATEX_OVERFLOW", "ERROR" if overflow else "PASS", f"{len(overflow)} overfull LaTeX box warning(s) detected." if overflow else "No overfull LaTeX boxes detected.", overflow or None); _validate_pdf(pdf, report, chapter)
        else: add_check(report, "PDF_RENDER", "ERROR", f"LuaLaTeX failed to render Chapter {chapter} {title}.", log[-12000:])
    add_check(report, "EQUIPMENT_BUILD", "PASS" if report["status"] == "PASS" else "ERROR", f"Chapter {chapter} {title} build completed." if report["status"] == "PASS" else f"Chapter {chapter} {title} build produced validation errors."); write_json(report_path, report); print(json.dumps(report, indent=2, ensure_ascii=False)); return 0 if report["status"] == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Cybermancy Step 6 Equipment Catalog and chapter layout builder"); sub = root.add_subparsers(dest="command", required=True)
    for name in ("inspect", "validate", "build"):
        p = sub.add_parser(name); p.add_argument("--tier", type=int, default=1); p.add_argument("--config"); p.add_argument("--sidecar"); p.add_argument("--manuscript"); p.add_argument("--report-dir")
        if name == "build": p.add_argument("--output-dir"); p.add_argument("--tex-only", action="store_true")
    for name in ("inspect-chapter16", "validate-chapter16", "build-chapter16"):
        p = sub.add_parser(name); p.add_argument("--config"); p.add_argument("--sidecar"); p.add_argument("--manuscript"); p.add_argument("--report-dir")
        if name == "build-chapter16": p.add_argument("--output-dir"); p.add_argument("--tex-only", action="store_true")
    for name in ("inspect-equipment", "validate-equipment", "build-equipment"):
        p = sub.add_parser(name)
        selector = p.add_mutually_exclusive_group(required=True)
        selector.add_argument("--family")
        selector.add_argument("--all", action="store_true", help="Process every configured Equipment family in chapter order.")
        p.add_argument("--config")
        p.add_argument("--sidecar")
        p.add_argument("--manuscript")
        p.add_argument("--report-dir")
        if name == "build-equipment":
            p.add_argument("--output-dir", help="For --all, base directory under which chapterNN directories are created.")
            p.add_argument("--tex-only", action="store_true")
    return root


def main() -> int:
    command_parser = parser()
    args = command_parser.parse_args()
    if getattr(args, "all", False) and getattr(args, "config", None):
        command_parser.error("--config cannot be used with --all; batch mode discovers *-v1.json configs automatically.")
    return {"inspect": command_inspect, "validate": command_validate, "build": command_build, "inspect-chapter16": command_inspect_chapter16, "validate-chapter16": command_validate_chapter16, "build-chapter16": command_build_chapter16, "inspect-equipment": command_inspect_equipment, "validate-equipment": command_validate_equipment, "build-equipment": command_build_equipment}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
