#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent
MASTER_RUNNER = SCRIPT_DIR / "build-rulebook-step6-integrated.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.character_origins_adapters import integrate_character_origins_stage
from rulebook_layout.character_origins_integration import compose_character_origins_stage
from rulebook_layout.character_options_adapters import integrate_character_options_stage
from rulebook_layout.encounter_adapters import integrate_encounter_stage
from rulebook_layout.encounter_integration import compose_encounter_stage
from rulebook_layout.equipment_adapters import integrate_equipment_stage
from rulebook_layout.integration import integrate_chapter29_with_adapter, structural_preflight
from rulebook_layout.integration_ast import canonical_ast_sha256
from rulebook_layout.prose_adapters import integrate_gm_prose_stage, integrate_player_prose_stage
from rulebook_layout.prose_integration import GM_STAGE, PLAYER_STAGE, compose_prose_stage
from rulebook_layout.publication_shell import lower_publication_shell
from rulebook_layout.rules_adapters import integrate_rules_stage
from rulebook_layout.rules_integration import compose_rules_stage

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_PROSE_CONFIG = RULEBOOK_DIR / "layout" / "prose" / "prose-layout-v1.json"
DEFAULT_PROSE_FILTER = RULEBOOK_DIR / "layout" / "prose" / "pandoc" / "prose.lua"
DEFAULT_PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"
DEFAULT_RULES_CONFIG = RULEBOOK_DIR / "layout" / "rules" / "rules-layout-v1.json"
DEFAULT_RULES_FILTER = RULEBOOK_DIR / "layout" / "rules" / "pandoc" / "rules.lua"
DEFAULT_RULES_BUILDER = SCRIPT_DIR / "build-rulebook-rules.py"
DEFAULT_ORIGIN_CONFIG = RULEBOOK_DIR / "layout" / "character-origins" / "character-origins-layout-v1.json"
DEFAULT_ORIGIN_FILTER = RULEBOOK_DIR / "layout" / "character-origins" / "pandoc" / "character-origins.lua"
DEFAULT_ORIGIN_BUILDER = SCRIPT_DIR / "build-rulebook-character-origins.py"
DEFAULT_ENCOUNTER_CONFIG_ROOT = RULEBOOK_DIR / "layout" / "encounters"
DEFAULT_ENCOUNTER_BUILDER = SCRIPT_DIR / "build-rulebook-encounters.py"
DEFAULT_PLAYER_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "player-guide.md"
DEFAULT_COMPLETE_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md"
DEFAULT_ASSET_ROOT = RULEBOOK_DIR / "source" / "assets"
DEFAULT_SIDECAR = RULEBOOK_DIR / "source" / "metadata" / "structured-entities.json"
DEFAULT_SOURCE_ROOT = RULEBOOK_DIR / "source"
DEFAULT_CLASS_CONFIG = RULEBOOK_DIR / "layout" / "classes" / "class-package-v1.json"
DEFAULT_DOMAIN_CONFIG = RULEBOOK_DIR / "layout" / "domains" / "domain-package-v1.json"
DEFAULT_ICE_CONFIG = RULEBOOK_DIR / "layout" / "ice" / "ice-reference-package-v1.json"
DEFAULT_EQUIPMENT_REGISTRY = RULEBOOK_DIR / "layout" / "equipment" / "equipment-section-v1.json"
DEFAULT_EQUIPMENT_CONFIG_DIR = RULEBOOK_DIR / "layout" / "equipment"
DEFAULT_WORK = RULEBOOK_DIR / "layout" / "integration" / "work"
DEFAULT_OUTPUT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"


def _load_master():
    spec = importlib.util.spec_from_file_location("cybermancy_step6_master_runtime_shell", MASTER_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Step 6 master runtime: {MASTER_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _resolve(value: str | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_check(
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


def _emit(report: dict[str, Any], verbose: bool) -> int:
    if verbose:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif report.get("status") == "PASS":
        print(f"{SCRIPT_PATH.name}: PASS")
    else:
        print(f"{SCRIPT_PATH.name}: FAIL")
        if report.get("errors"):
            print(json.dumps(report["errors"], indent=2, ensure_ascii=False))
    return 0 if report.get("status") == "PASS" else 2


def _adapter_ok(report: dict[str, Any], code: str, order: Any, result: Any) -> bool:
    if hasattr(result, "as_dict"):
        details = result.as_dict()
        ok = getattr(result, "status", "FAIL") == "PASS"
    else:
        details = result
        ok = isinstance(result, dict) and result.get("status") == "PASS"
    _append_check(
        report,
        code,
        "PASS" if ok else "ERROR",
        f"Phase C order {order} committed successfully."
        if ok
        else f"Phase C order {order} failed; cumulative assembly stopped.",
        details,
    )
    if ok:
        if isinstance(order, (list, tuple)):
            report["appliedOrders"].extend(int(value) for value in order)
        else:
            report["appliedOrders"].append(int(order))
    return ok


def _run(args: argparse.Namespace) -> int:
    master = _load_master()
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage130-publication-shell-proof-v1",
        "status": "PASS",
        "milestone": "cumulative-orders-20-130-publication-shell",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "appliedOrders": [],
        "composition": {},
    }
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-stage130-publication-shell.json",
    )
    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    if not contract_path.is_file():
        _append_check(report, "INTEGRATION_CONTRACT", "ERROR", f"Missing integration contract: {contract_path}")
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    contract = _load_json(contract_path)
    contract_ok = (
        contract.get("schema") == "cybermancy-step6-integration-contract-v1"
        and contract.get("version") == "1.0"
        and contract.get("status") == "accepted"
    )
    _append_check(
        report,
        "INTEGRATION_CONTRACT",
        "PASS" if contract_ok else "ERROR",
        "Accepted Step 6 integration contract v1.0 loaded."
        if contract_ok
        else "Integration contract is not accepted v1.0.",
        str(contract_path),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    ast, ast_source = master._load_base_ast(args, args.profile, report)
    if ast is None:
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    report["paths"] = {
        "contract": str(contract_path),
        "baseAstOrSource": str(ast_source) if ast_source else None,
    }

    preflight = structural_preflight(ast, contract, args.profile)
    report["structuralPreflight"] = preflight
    _append_check(
        report,
        "STRUCTURAL_PREFLIGHT",
        "PASS" if preflight.get("status") == "PASS" else "ERROR",
        "Order 10 structural preflight passed."
        if preflight.get("status") == "PASS"
        else "Order 10 structural preflight failed.",
        {"inputAstSha256": preflight.get("inputAstSha256"), "inventory": preflight.get("inventory")},
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    report["appliedOrders"].append(10)

    pandoc = master._pandoc_executable()
    if not pandoc:
        _append_check(report, "PANDOC", "ERROR", "Pandoc was not found for Phase C fragment composition.")
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    player_source = _resolve(args.player_source, DEFAULT_PLAYER_SOURCE)
    complete_source = _resolve(args.complete_source, DEFAULT_COMPLETE_SOURCE)
    asset_root = _resolve(args.asset_root, DEFAULT_ASSET_ROOT)
    work_root = _resolve(args.work_dir, DEFAULT_WORK) / "stage130"
    work_root.mkdir(parents=True, exist_ok=True)

    prose_builder = _resolve(args.prose_builder, DEFAULT_PROSE_BUILDER)
    prose_config = _resolve(args.prose_config, DEFAULT_PROSE_CONFIG)
    prose_filter = _resolve(args.prose_filter, DEFAULT_PROSE_FILTER)
    player_prose, player_prose_report = compose_prose_stage(
        PLAYER_STAGE,
        prose_builder,
        prose_config,
        prose_filter,
        player_source,
        complete_source,
        asset_root,
        work_root / "prose-player",
        contract,
        pandoc,
        master.PANDOC_FROM,
    )
    report["composition"]["prosePlayer"] = player_prose_report
    if player_prose is None or player_prose_report.get("status") != "PASS":
        _append_check(report, "ORDER20_COMPOSITION", "ERROR", "Order 20 Player Prose composition failed.", player_prose_report.get("errors"))
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    if not _adapter_ok(report, "ORDER20_PLAYER_PROSE", 20, integrate_player_prose_stage(ast, args.profile, player_prose)):
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    rules_payload, rules_report = compose_rules_stage(
        _resolve(args.rules_builder, DEFAULT_RULES_BUILDER),
        _resolve(args.rules_config, DEFAULT_RULES_CONFIG),
        _resolve(args.rules_filter, DEFAULT_RULES_FILTER),
        player_source,
        complete_source,
        asset_root,
        work_root / "rules",
        contract,
        pandoc,
        master.PANDOC_FROM,
    )
    report["composition"]["rules"] = rules_report
    if rules_payload is None or rules_report.get("status") != "PASS":
        _append_check(report, "ORDER30_COMPOSITION", "ERROR", "Order 30 Rules composition failed.", rules_report.get("errors"))
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    if not _adapter_ok(report, "ORDER30_RULES", 30, integrate_rules_stage(ast, args.profile, rules_payload)):
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    origins_payload, origins_report = compose_character_origins_stage(
        _resolve(args.character_origins_builder, DEFAULT_ORIGIN_BUILDER),
        prose_builder,
        _resolve(args.character_origins_config, DEFAULT_ORIGIN_CONFIG),
        _resolve(args.character_origins_filter, DEFAULT_ORIGIN_FILTER),
        complete_source,
        player_source,
        asset_root,
        work_root / "character-origins",
        contract,
        pandoc,
        master.PANDOC_FROM,
    )
    report["composition"]["characterOrigins"] = origins_report
    if origins_payload is None or origins_report.get("status") != "PASS":
        _append_check(report, "ORDER40_COMPOSITION", "ERROR", "Order 40 Character Origins composition failed.", origins_report.get("errors"))
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    if not _adapter_ok(report, "ORDER40_CHARACTER_ORIGINS", 40, integrate_character_origins_stage(ast, args.profile, origins_payload)):
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    # Reuse the already accepted master helpers for structured Character Options,
    # Equipment, and ICE composition.  The parser exposes the same argument names
    # so these calls cannot silently fall back to a second implementation.
    character_options = master._compose_character_options(args, contract, report)
    if character_options is None or report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    class_payload, domain_payload = character_options
    character_stage = integrate_character_options_stage(ast, args.profile, class_payload, domain_payload)
    if not _adapter_ok(report, "ORDERS50_60_CHARACTER_OPTIONS", (50, 60), character_stage):
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    equipment_payloads = master._compose_equipment(args, contract, report)
    if equipment_payloads is None or report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    equipment_stage = integrate_equipment_stage(ast, args.profile, equipment_payloads)
    if not _adapter_ok(report, "ORDER70_EQUIPMENT", 70, equipment_stage):
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    if args.profile == "complete-rulebook":
        gm_prose, gm_prose_report = compose_prose_stage(
            GM_STAGE,
            prose_builder,
            prose_config,
            prose_filter,
            player_source,
            complete_source,
            asset_root,
            work_root / "prose-gm",
            contract,
            pandoc,
            master.PANDOC_FROM,
        )
        report["composition"]["proseGm"] = gm_prose_report
        if gm_prose is None or gm_prose_report.get("status") != "PASS":
            _append_check(report, "ORDER80_COMPOSITION", "ERROR", "Order 80 GM Prose composition failed.", gm_prose_report.get("errors"))
            _write_json(report_path, report)
            return _emit(report, args.verbose)
        if not _adapter_ok(report, "ORDER80_GM_PROSE", 80, integrate_gm_prose_stage(ast, args.profile, gm_prose)):
            _write_json(report_path, report)
            return _emit(report, args.verbose)

        ice = master._compose_ice(args, report)
        if ice is None or report["status"] != "PASS":
            _write_json(report_path, report)
            return _emit(report, args.verbose)
        ice_header, ice_body = ice
        if not _adapter_ok(report, "ORDER90_ICE_REFERENCE", 90, integrate_chapter29_with_adapter(ast, args.profile, ice_header, ice_body)):
            _write_json(report_path, report)
            return _emit(report, args.verbose)

        encounter_payloads, encounter_report = compose_encounter_stage(
            _resolve(args.encounter_builder, DEFAULT_ENCOUNTER_BUILDER),
            _resolve(args.sidecar, DEFAULT_SIDECAR),
            _resolve(args.source_root, DEFAULT_SOURCE_ROOT),
            _resolve(args.encounter_config_root, DEFAULT_ENCOUNTER_CONFIG_ROOT),
            work_root / "encounters",
            contract,
        )
        report["composition"]["encounters"] = encounter_report
        if encounter_report.get("status") != "PASS" or len(encounter_payloads) != 3:
            _append_check(report, "ORDERS100_120_COMPOSITION", "ERROR", "Encounter Toolkit composition failed.", encounter_report.get("errors"))
            _write_json(report_path, report)
            return _emit(report, args.verbose)
        encounter_stage = integrate_encounter_stage(ast, args.profile, encounter_payloads)
        if not _adapter_ok(report, "ORDERS100_120_ENCOUNTERS", (100, 110, 120), encounter_stage):
            _write_json(report_path, report)
            return _emit(report, args.verbose)
    else:
        _append_check(
            report,
            "GM_STAGE_PROFILE_GATE",
            "PASS",
            "Player Guide correctly skips orders 80 and 90-120 GM-only transforms.",
        )

    phase_c_hash = canonical_ast_sha256(ast)
    report["phaseCOutputAstSha256"] = phase_c_hash
    expected_order = [10, 20, 30, 40, 50, 60, 70]
    if args.profile == "complete-rulebook":
        expected_order += [80, 90, 100, 110, 120]
    order_ok = report["appliedOrders"] == expected_order
    _append_check(
        report,
        "PHASE_C_FIXED_ORDER",
        "PASS" if order_ok else "ERROR",
        "All applicable Phase C transforms executed in canonical order."
        if order_ok
        else "Cumulative Phase C transform order differs from the integration contract.",
        {"expected": expected_order, "actual": report["appliedOrders"]},
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    shell = lower_publication_shell(ast, contract, args.profile)
    report["publicationShell"] = shell.as_dict()
    shell_ok = shell.status == "PASS"
    _append_check(
        report,
        "STAGE130_PUBLICATION_SHELL",
        "PASS" if shell_ok else "ERROR",
        "Stage 130 lowered all remaining semantic Part/Chapter/divider nodes into the integrated publication shell."
        if shell_ok
        else "Stage 130 publication-shell lowering failed closed.",
        shell.as_dict(),
    )
    if not shell_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    report["appliedOrders"].append(130)

    before_repeat = canonical_ast_sha256(ast)
    repeated = lower_publication_shell(ast, contract, args.profile)
    after_repeat = canonical_ast_sha256(ast)
    idempotent = repeated.status == "PASS" and repeated.idempotent and before_repeat == after_repeat
    _append_check(
        report,
        "STAGE130_IDEMPOTENCY",
        "PASS" if idempotent else "ERROR",
        "Repeated Stage 130 lowering is a byte-stable no-op."
        if idempotent
        else "Repeated Stage 130 lowering changed the AST or failed its integrated probe.",
        repeated.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output = _resolve(
        args.ast_output,
        DEFAULT_OUTPUT / f"{args.profile}-stage130-publication-shell.ast.json",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(master.canonical_ast_bytes(ast))
    report["paths"]["outputAst"] = str(output)
    report["outputAstSha256"] = canonical_ast_sha256(ast)
    _append_check(
        report,
        "STAGE130_AST_OUTPUT",
        "PASS",
        "Wrote deterministic cumulative orders 20-130 AST.",
        {"path": str(output), "sha256": report["outputAstSha256"]},
    )

    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build the cumulative Phase C AST in fixed order and prove Stage 130 publication-shell lowering."
    )
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--source")
    p.add_argument("--ast-input")
    p.add_argument("--ast-output")
    p.add_argument("--report")
    p.add_argument("--work-dir")
    p.add_argument("--player-source")
    p.add_argument("--complete-source")
    p.add_argument("--asset-root")
    p.add_argument("--prose-builder")
    p.add_argument("--prose-config")
    p.add_argument("--prose-filter")
    p.add_argument("--rules-builder")
    p.add_argument("--rules-config")
    p.add_argument("--rules-filter")
    p.add_argument("--character-origins-builder")
    p.add_argument("--character-origins-config")
    p.add_argument("--character-origins-filter")
    p.add_argument("--sidecar")
    p.add_argument("--source-root")
    p.add_argument("--class-config")
    p.add_argument("--domain-config")
    p.add_argument("--equipment-registry")
    p.add_argument("--equipment-config-dir")
    p.add_argument("--ice-config")
    p.add_argument("--encounter-builder")
    p.add_argument("--encounter-config-root")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
