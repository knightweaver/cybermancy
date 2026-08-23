#!/usr/bin/env python3
"""Cybermancy Rulebook Step 6 layout builder.

C implements the reusable Equipment Catalog Table primitive and validates it with
Chapter 16 / Tier 1 Weapons. It consumes only Step 4 normalized outputs:

    build/rulebook/source/assembled/player-guide.md
    build/rulebook/source/metadata/structured-entities.json

It never reads canonical Foundry pack JSON directly.

Typical usage from repository root:

    python build/rulebook/scripts/build-rulebook-layout.py validate
    python build/rulebook/scripts/build-rulebook-layout.py build
    python build/rulebook/scripts/build-rulebook-layout.py build --tex-only
    python build/rulebook/scripts/build-rulebook-layout.py inspect
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
DEFAULT_REPORT_DIR = LAYOUT_DIR / "reports"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_catalog import (  # noqa: E402
    build_catalog_rows,
    render_equipment_catalog_latex,
)
from rulebook_layout.latex import render_tier_prototype_document  # noqa: E402


DAMAGE_FORMULA_RE = re.compile(r"^(?:\d*d\d+(?:[+-]\d+)?)(?:; \d*d\d+(?:[+-]\d+)?)*$", re.I)
HTML_TAG_RE = re.compile(r"<[^>]+>")


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


def resolve_path(value: str | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value else default.resolve()


def validate_catalog(
    config_path: Path,
    sidecar_path: Path,
    manuscript_path: Path,
    tier: int,
) -> tuple[dict, dict | None, dict | None, list]:
    report = report_shell(config_path, sidecar_path, manuscript_path, tier)

    for code, path in (
        ("CONFIG_PRESENT", config_path),
        ("STRUCTURED_SIDECAR_PRESENT", sidecar_path),
        ("ASSEMBLED_MANUSCRIPT_PRESENT", manuscript_path),
    ):
        if path.is_file():
            add_check(report, code, "PASS", str(path))
        else:
            add_check(report, code, "BLOCKED", f"Required Step 6 input is missing: {path}")
    if report["status"] != "PASS":
        return report, None, None, []

    try:
        config = load_json(config_path)
        sidecar = load_json(sidecar_path)
    except Exception as exc:
        add_check(report, "INPUT_JSON", "ERROR", f"Could not load Step 6 JSON input: {exc}")
        return report, None, None, []

    if sidecar.get("schema") == "cybermancy-step4-structured-entities-v1.0":
        add_check(report, "SIDECAR_SCHEMA", "PASS", sidecar["schema"])
    else:
        add_check(report, "SIDECAR_SCHEMA", "ERROR", "Unexpected Step 4 structured entity sidecar schema.", sidecar.get("schema"))

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

    columns = list(config.get("columns", []))
    labels = [col.get("label") for col in columns]
    expected_labels = ["Name", "Tier", "Trait", "Range", "Burden", "Damage", "Action", "Critical Effect", "Description"]
    if labels == expected_labels:
        add_check(report, "WEAPON_COLUMN_CONTRACT", "PASS", "Approved nine-column Weapons schema is configured.")
    else:
        add_check(report, "WEAPON_COLUMN_CONTRACT", "ERROR", "Weapons columns differ from the approved C schema.", labels)

    width_sum = sum(float(col.get("widthIn", 0)) for col in columns)
    # Eight internal gaps, each with left+right tabcolsep=1.4pt. The prototype
    # uses 0.46in margins on US Letter, giving a 7.58in text block.
    spacing_in = max(0, len(columns) - 1) * (2 * 1.4 / 72.27)
    occupied = width_sum + spacing_in
    if occupied <= 7.58:
        add_check(report, "TABLE_WIDTH_BUDGET", "PASS", f"Configured table width budget is {occupied:.3f}in within 7.58in.")
    else:
        add_check(report, "TABLE_WIDTH_BUDGET", "ERROR", f"Configured table requires {occupied:.3f}in; only 7.58in is available.")

    critical_prefix_rows = [r.name for r in rows if "Critical Effect:" in r.cells.get("criticalEffect", "")]
    if critical_prefix_rows:
        add_check(report, "CRITICAL_EFFECT_DISPLAY", "ERROR", "Critical Effect prefix leaked into Step 6 display.", critical_prefix_rows)
    else:
        add_check(report, "CRITICAL_EFFECT_DISPLAY", "PASS", "Critical Effect display names contain no Foundry prefix.")

    invalid_damage = []
    for row in rows:
        damage = row.cells.get("publicationData.attack.damageFormula", "—")
        if damage != "—" and not DAMAGE_FORMULA_RE.fullmatch(damage):
            invalid_damage.append({"name": row.name, "damage": damage})
    if invalid_damage:
        add_check(report, "DAMAGE_FORMULA_ONLY", "ERROR", "Damage cells contain values other than formula-only publication data.", invalid_damage)
    else:
        add_check(report, "DAMAGE_FORMULA_ONLY", "PASS", "Damage cells contain formula only; damage types are absent.")

    html_descriptions = [
        r.name for r in rows
        if HTML_TAG_RE.search(r.cells.get("publicationData.description", ""))
    ]
    if html_descriptions:
        add_check(report, "PLAIN_TEXT_DESCRIPTIONS", "ERROR", "HTML remains in normalized descriptions.", html_descriptions)
    else:
        add_check(report, "PLAIN_TEXT_DESCRIPTIONS", "PASS", "Catalog descriptions are normalized plain text.")

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
            absent_mechanics.append({
                "name": name,
                "action": row.cells.get("action"),
                "criticalEffect": row.cells.get("criticalEffect"),
            })
    if absent_mechanics:
        add_check(report, "ABSENT_MECHANICS_DISPLAY", "ERROR", "Weapons with no Action/Critical Effect must render em dashes.", absent_mechanics)
    else:
        add_check(report, "ABSENT_MECHANICS_DISPLAY", "PASS", "Absent Action/Critical Effect mechanics render as em dashes.")

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


def command_inspect(args: argparse.Namespace) -> int:
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    sidecar_path = resolve_path(args.sidecar, DEFAULT_SIDECAR)
    manuscript_path = resolve_path(args.manuscript, DEFAULT_MANUSCRIPT)
    report, config, _, rows = validate_catalog(config_path, sidecar_path, manuscript_path, args.tier)
    result = {
        "report": report,
        "family": config.get("family") if config else None,
        "tier": args.tier,
        "rows": [
            {"semanticId": row.semantic_id, "name": row.name, "group": row.group, "cells": row.cells}
            for row in rows
        ],
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
            "rows": [
                {"semanticId": row.semantic_id, "name": row.name, "group": row.group, "cells": row.cells}
                for row in rows
            ],
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
            add_check(report, "PDF_RENDER", "ERROR", "LuaLaTeX failed to render the Tier 1 Equipment Catalog prototype.", log[-12000:])

    write_json(report_dir / f"equipment-catalog-weapons-tier{args.tier}.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Cybermancy Step 6 Equipment Catalog layout builder")
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
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "validate":
        return command_validate(args)
    if args.command == "build":
        return command_build(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
