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

from rulebook_layout.encounter_adapters import integrate_encounter_stage
from rulebook_layout.encounter_integration import compose_encounter_stage
from rulebook_layout.integration import structural_preflight
from rulebook_layout.integration_ast import canonical_ast_sha256

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_SIDECAR = RULEBOOK_DIR / "source" / "metadata" / "structured-entities.json"
DEFAULT_SOURCE_ROOT = RULEBOOK_DIR / "source"
DEFAULT_CONFIG_ROOT = RULEBOOK_DIR / "layout" / "encounters"
DEFAULT_BUILDER = SCRIPT_DIR / "build-rulebook-encounters.py"
DEFAULT_WORK = RULEBOOK_DIR / "layout" / "integration" / "work"
DEFAULT_OUTPUT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"


def _load_master():
    spec = importlib.util.spec_from_file_location("cybermancy_step6_master_runtime", MASTER_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Step 6 master runtime: {MASTER_RUNNER}")
    module = importlib.util.module_from_spec(spec)
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


def _adapter_by_name(stage: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in stage.get("adapters") or []:
        if isinstance(item, dict) and item.get("adapter") == name:
            return item
    return None


def _run(args: argparse.Namespace) -> int:
    master = _load_master()
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-integration-runtime-v1",
        "status": "PASS",
        "phase": "C",
        "milestone": "encounter-toolkit-chapters-30-32-proof",
        "command": "integrate-encounters",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "adapters": [],
    }
    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-integrate-encounters.json",
    )

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
        "Structural preflight passed; Encounter Toolkit adapters may run."
        if preflight.get("status") == "PASS"
        else "Structural preflight failed; Encounter Toolkit adapters were not run.",
        {"inputAstSha256": preflight.get("inputAstSha256"), "inventory": preflight.get("inventory")},
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    if args.profile != "complete-rulebook":
        _append_check(report, "ENCOUNTER_PROFILE", "ERROR", "Chapters 30-32 are Complete Rulebook only.")
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    sidecar = _resolve(args.sidecar, DEFAULT_SIDECAR)
    source_root = _resolve(args.source_root, DEFAULT_SOURCE_ROOT)
    config_root = _resolve(args.encounter_config_root, DEFAULT_CONFIG_ROOT)
    builder = _resolve(args.encounter_builder, DEFAULT_BUILDER)
    work = _resolve(args.work_dir, DEFAULT_WORK) / "encounters"
    payloads, composition = compose_encounter_stage(
        builder,
        sidecar,
        source_root,
        config_root,
        work,
        contract,
    )
    report["encounterComposition"] = composition
    composition_ok = composition.get("status") == "PASS" and len(payloads) == 3
    _append_check(
        report,
        "ENCOUNTER_STAGE_COMPOSITION",
        "PASS" if composition_ok else "ERROR",
        "Composed all three frozen Encounter Toolkit chapters from the accepted standalone producers."
        if composition_ok
        else "Encounter Toolkit composition failed its frozen production contract.",
        [payload.summary() for payload in payloads] if payloads else composition.get("errors"),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    stage = integrate_encounter_stage(ast, args.profile, payloads)
    report["encounterStage"] = stage
    report["adapters"].extend(stage.get("adapters") or [])
    for name, code, chapter in (
        ("adversary-package", "ADVERSARY_STAGE_ADAPTER", 30),
        ("environment-package", "ENVIRONMENT_STAGE_ADAPTER", 31),
        ("adversary-feature-reference", "ADVERSARY_FEATURE_STAGE_ADAPTER", 32),
    ):
        adapter = _adapter_by_name(stage, name)
        ok = bool(adapter and adapter.get("status") == "PASS")
        _append_check(
            report,
            code,
            "PASS" if ok else "ERROR",
            f"Chapter {chapter} adapter satisfied exact header and family-body replacement postconditions."
            if ok
            else f"Chapter {chapter} adapter failed exact replacement postconditions.",
            adapter or stage,
        )
    _append_check(
        report,
        "ENCOUNTER_STAGE_ADAPTER",
        "PASS" if stage.get("status") == "PASS" else "ERROR",
        "Orders 100-120 committed atomically through the common exact-adapter contract."
        if stage.get("status") == "PASS"
        else "Encounter Toolkit stage failed; all staged Chapters 30-32 mutations were discarded.",
        stage,
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    before = canonical_ast_sha256(ast)
    repeated = integrate_encounter_stage(ast, args.profile, payloads)
    after = canonical_ast_sha256(ast)
    idempotent_ok = (
        repeated.get("status") == "PASS"
        and bool(repeated.get("idempotent"))
        and before == after
    )
    _append_check(
        report,
        "ENCOUNTER_STAGE_IDEMPOTENCY",
        "PASS" if idempotent_ok else "ERROR",
        "Repeated Chapters 30-32 integration is a byte-stable no-op."
        if idempotent_ok
        else "Repeated Chapters 30-32 integration was not a byte-stable no-op.",
        repeated,
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output = _resolve(
        args.ast_output,
        DEFAULT_OUTPUT / f"{args.profile}-phase-c-encounters.ast.json",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(master.canonical_ast_bytes(ast))
    report["paths"]["outputAst"] = str(output)
    report["outputAstSha256"] = canonical_ast_sha256(ast)
    _append_check(
        report,
        "INTEGRATED_AST_OUTPUT",
        "PASS",
        "Wrote deterministic Phase C AST with Chapters 30-32 integrated.",
        {"path": str(output), "sha256": report["outputAstSha256"]},
    )
    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cybermancy Step 6 Phase C proof for Encounter Toolkit Chapters 30-32."
    )
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--source")
    p.add_argument("--ast-input")
    p.add_argument("--ast-output")
    p.add_argument("--work-dir")
    p.add_argument("--report")
    p.add_argument("--sidecar")
    p.add_argument("--source-root")
    p.add_argument("--encounter-config-root")
    p.add_argument("--encounter-builder")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
