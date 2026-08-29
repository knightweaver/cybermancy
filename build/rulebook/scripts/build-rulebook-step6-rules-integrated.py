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

from rulebook_layout.integration import structural_preflight
from rulebook_layout.integration_ast import canonical_ast_sha256
from rulebook_layout.rules_adapters import integrate_rules_stage
from rulebook_layout.rules_integration import compose_rules_stage

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_RULES_CONFIG = RULEBOOK_DIR / "layout" / "rules" / "rules-layout-v1.json"
DEFAULT_RULES_FILTER = RULEBOOK_DIR / "layout" / "rules" / "pandoc" / "rules.lua"
DEFAULT_RULES_BUILDER = SCRIPT_DIR / "build-rulebook-rules.py"
DEFAULT_PLAYER_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "player-guide.md"
DEFAULT_COMPLETE_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md"
DEFAULT_ASSET_ROOT = RULEBOOK_DIR / "source" / "assets"
DEFAULT_WORK = RULEBOOK_DIR / "layout" / "integration" / "work"
DEFAULT_OUTPUT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"


def _load_master():
    spec = importlib.util.spec_from_file_location("cybermancy_step6_master_runtime_rules", MASTER_RUNNER)
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


def _append_check(report: dict[str, Any], code: str, status: str, message: str, details: Any = None) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)


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


def _run(args: argparse.Namespace) -> int:
    master = _load_master()
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-integration-runtime-v1",
        "status": "PASS",
        "phase": "C",
        "milestone": "rules-chapters-4-9-proof",
        "command": "integrate-rules",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "adapters": [],
    }
    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    report_path = _resolve(args.report, DEFAULT_REPORTS / f"{args.profile}-integrate-rules.json")

    if not contract_path.is_file():
        _append_check(report, "INTEGRATION_CONTRACT", "ERROR", f"Step 6 integration contract is missing: {contract_path}")
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
        else "Step 6 integration contract is not accepted v1.0.",
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
    report["preflight"] = preflight
    _append_check(
        report,
        "STRUCTURAL_PREFLIGHT",
        "PASS" if preflight.get("status") == "PASS" else "ERROR",
        "Structural preflight passed; Rules adapter may run."
        if preflight.get("status") == "PASS"
        else "Structural preflight failed; Rules adapter was not run.",
        {"inputAstSha256": preflight.get("inputAstSha256"), "inventory": preflight.get("inventory")},
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    rules_builder = _resolve(args.rules_builder, DEFAULT_RULES_BUILDER)
    config = _resolve(args.rules_config, DEFAULT_RULES_CONFIG)
    lua_filter = _resolve(args.rules_filter, DEFAULT_RULES_FILTER)
    player_source = _resolve(args.rules_player_source, DEFAULT_PLAYER_SOURCE)
    complete_source = _resolve(args.rules_complete_source, DEFAULT_COMPLETE_SOURCE)
    asset_root = _resolve(args.asset_root, DEFAULT_ASSET_ROOT)
    work = _resolve(args.work_dir, DEFAULT_WORK) / "rules"
    pandoc = master._pandoc_executable()
    if not pandoc:
        _append_check(report, "PANDOC", "ERROR", "Pandoc was not found for Rules fragment generation.")
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    payload, composition = compose_rules_stage(
        rules_builder,
        config,
        lua_filter,
        player_source,
        complete_source,
        asset_root,
        work,
        contract,
        pandoc,
        master.PANDOC_FROM,
    )
    report["rulesComposition"] = composition
    composition_ok = payload is not None and composition.get("status") == "PASS"
    _append_check(
        report,
        "RULES_STAGE_COMPOSITION",
        "PASS" if composition_ok else "ERROR",
        "Composed the accepted Rules v1.0 bodies for all Chapters 4-9."
        if composition_ok
        else "Rules composition failed its accepted contract/profile/asset gate.",
        payload.summary() if payload else composition.get("errors"),
    )
    if report["status"] != "PASS" or payload is None:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    adapter = integrate_rules_stage(ast, args.profile, payload)
    report["adapters"].append(adapter.as_dict())
    _append_check(
        report,
        "RULES_STAGE_ADAPTER",
        "PASS" if adapter.status == "PASS" else "ERROR",
        "Order 30 replaced all six Chapter 4-9 bodies exactly while preserving their semantic chapter headers."
        if adapter.status == "PASS"
        else "Rules order-30 adapter failed exact body-replacement postconditions.",
        adapter.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    before = canonical_ast_sha256(ast)
    repeated = integrate_rules_stage(ast, args.profile, payload)
    after = canonical_ast_sha256(ast)
    idempotent_ok = repeated.status == "PASS" and repeated.idempotent and before == after
    _append_check(
        report,
        "RULES_STAGE_IDEMPOTENCY",
        "PASS" if idempotent_ok else "ERROR",
        "Repeated Rules integration is a byte-stable no-op."
        if idempotent_ok
        else "Repeated Rules integration was not a byte-stable no-op.",
        repeated.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output = _resolve(args.ast_output, DEFAULT_OUTPUT / f"{args.profile}-phase-c-rules.ast.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(master.canonical_ast_bytes(ast))
    report["paths"]["outputAst"] = str(output)
    report["outputAstSha256"] = canonical_ast_sha256(ast)
    _append_check(
        report,
        "INTEGRATED_AST_OUTPUT",
        "PASS",
        "Wrote deterministic Phase C AST with Rules Chapters 4-9 integrated.",
        {"path": str(output), "sha256": report["outputAstSha256"]},
    )
    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cybermancy Step 6 Phase C proof for Rules Chapters 4-9.")
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--source")
    p.add_argument("--ast-input")
    p.add_argument("--ast-output")
    p.add_argument("--work-dir")
    p.add_argument("--report")
    p.add_argument("--asset-root")
    p.add_argument("--rules-builder")
    p.add_argument("--rules-config")
    p.add_argument("--rules-filter")
    p.add_argument("--rules-player-source")
    p.add_argument("--rules-complete-source")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
