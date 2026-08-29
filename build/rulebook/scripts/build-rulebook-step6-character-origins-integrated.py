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
from rulebook_layout.integration import structural_preflight
from rulebook_layout.integration_ast import canonical_ast_sha256

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_ORIGIN_CONFIG = RULEBOOK_DIR / "layout" / "character-origins" / "character-origins-layout-v1.json"
DEFAULT_ORIGIN_FILTER = RULEBOOK_DIR / "layout" / "character-origins" / "pandoc" / "character-origins.lua"
DEFAULT_ORIGIN_BUILDER = SCRIPT_DIR / "build-rulebook-character-origins.py"
DEFAULT_PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"
DEFAULT_PLAYER_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "player-guide.md"
DEFAULT_ASSET_ROOT = RULEBOOK_DIR / "source" / "assets"
DEFAULT_WORK = RULEBOOK_DIR / "layout" / "integration" / "work"
DEFAULT_OUTPUT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"


def _load_master():
    spec = importlib.util.spec_from_file_location("cybermancy_step6_master_runtime_origins", MASTER_RUNNER)
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
        "milestone": "character-origins-chapters-10-11-proof",
        "command": "integrate-character-origins",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "adapters": [],
    }
    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-integrate-character-origins.json",
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
        "Structural preflight passed; Character Origins adapter may run."
        if preflight.get("status") == "PASS"
        else "Structural preflight failed; Character Origins adapter was not run.",
        {"inputAstSha256": preflight.get("inputAstSha256"), "inventory": preflight.get("inventory")},
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    builder = _resolve(args.character_origins_builder, DEFAULT_ORIGIN_BUILDER)
    prose_builder = _resolve(args.prose_builder, DEFAULT_PROSE_BUILDER)
    config = _resolve(args.character_origins_config, DEFAULT_ORIGIN_CONFIG)
    lua_filter = _resolve(args.character_origins_filter, DEFAULT_ORIGIN_FILTER)
    complete_source = _resolve(
        args.source,
        RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md",
    )
    player_source = _resolve(args.player_source, DEFAULT_PLAYER_SOURCE)
    asset_root = _resolve(args.asset_root, DEFAULT_ASSET_ROOT)
    work = _resolve(args.work_dir, DEFAULT_WORK) / "character-origins"
    pandoc = master._pandoc_executable()
    if not pandoc:
        _append_check(report, "PANDOC", "ERROR", "Pandoc was not found for Character Origins fragment generation.")
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    payload, composition = compose_character_origins_stage(
        builder,
        prose_builder,
        config,
        lua_filter,
        complete_source,
        player_source,
        asset_root,
        work,
        contract,
        pandoc,
        master.PANDOC_FROM,
    )
    report["characterOriginsComposition"] = composition
    composition_ok = payload is not None and composition.get("status") == "PASS"
    _append_check(
        report,
        "CHARACTER_ORIGINS_STAGE_COMPOSITION",
        "PASS" if composition_ok else "ERROR",
        "Composed the complete frozen Character Origins v1.0 Chapter 10-11 bodies."
        if composition_ok
        else "Character Origins composition failed its frozen corpus/profile/artwork contract.",
        payload.summary() if payload else composition.get("errors"),
    )
    if report["status"] != "PASS" or payload is None:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    adapter = integrate_character_origins_stage(ast, args.profile, payload)
    report["adapters"].append(adapter.as_dict())
    _append_check(
        report,
        "CHARACTER_ORIGINS_STAGE_ADAPTER",
        "PASS" if adapter.status == "PASS" else "ERROR",
        "Order 40 replaced Chapters 10-11 bodies exactly while preserving their semantic chapter headers."
        if adapter.status == "PASS"
        else "Character Origins order-40 adapter failed exact body-replacement postconditions.",
        adapter.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    before = canonical_ast_sha256(ast)
    repeated = integrate_character_origins_stage(ast, args.profile, payload)
    after = canonical_ast_sha256(ast)
    idempotent_ok = repeated.status == "PASS" and repeated.idempotent and before == after
    _append_check(
        report,
        "CHARACTER_ORIGINS_STAGE_IDEMPOTENCY",
        "PASS" if idempotent_ok else "ERROR",
        "Repeated Character Origins integration is a byte-stable no-op."
        if idempotent_ok
        else "Repeated Character Origins integration was not a byte-stable no-op.",
        repeated.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output = _resolve(
        args.ast_output,
        DEFAULT_OUTPUT / f"{args.profile}-phase-c-character-origins.ast.json",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(master.canonical_ast_bytes(ast))
    report["paths"]["outputAst"] = str(output)
    report["outputAstSha256"] = canonical_ast_sha256(ast)
    _append_check(
        report,
        "INTEGRATED_AST_OUTPUT",
        "PASS",
        "Wrote deterministic Phase C AST with Chapters 10-11 integrated.",
        {"path": str(output), "sha256": report["outputAstSha256"]},
    )
    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cybermancy Step 6 Phase C proof for Character Origins Chapters 10-11."
    )
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--source")
    p.add_argument("--player-source")
    p.add_argument("--ast-input")
    p.add_argument("--ast-output")
    p.add_argument("--work-dir")
    p.add_argument("--report")
    p.add_argument("--asset-root")
    p.add_argument("--character-origins-builder")
    p.add_argument("--character-origins-config")
    p.add_argument("--character-origins-filter")
    p.add_argument("--prose-builder")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
