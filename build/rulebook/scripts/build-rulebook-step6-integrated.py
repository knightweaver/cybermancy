#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.ice_reference import load_json
from rulebook_layout.ice_reference_images import (
    attach_ice_reference_images,
    ice_reference_publication_images,
)
from rulebook_layout.ice_reference_package import (
    compose_ice_reference_package,
    render_integration_fragments,
)
from rulebook_layout.integration import (
    integrate_chapter29_with_adapter,
    structural_preflight,
)
from rulebook_layout.integration_ast import canonical_ast_bytes, canonical_ast_sha256
from rulebook_layout.render_assets import prepare_lualatex_render_assets


DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_ICE_CONFIG = RULEBOOK_DIR / "layout" / "ice" / "ice-reference-package-v1.json"
DEFAULT_SIDECAR = RULEBOOK_DIR / "source" / "metadata" / "structured-entities.json"
DEFAULT_SOURCE_ROOT = RULEBOOK_DIR / "source"
DEFAULT_WORK = RULEBOOK_DIR / "layout" / "integration" / "work"
DEFAULT_OUTPUT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"
PROFILE_SOURCE = {
    "complete-rulebook": RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md",
    "player-guide": RULEBOOK_DIR / "source" / "assembled" / "player-guide.md",
}
PANDOC_FROM = (
    "markdown-yaml_metadata_block-implicit_figures-simple_tables-multiline_tables"
    "+fenced_divs+bracketed_spans+pipe_tables+grid_tables+definition_lists"
    "+raw_attribute+raw_html+markdown_in_html_blocks"
)


def _resolve(value: str | None, default: Path) -> Path:
    if value:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path.resolve()
    return default.resolve()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _emit(report: dict[str, Any], verbose: bool) -> int:
    status = str(report.get("status") or "FAIL")
    if verbose:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif status == "PASS":
        print(f"{SCRIPT_PATH.name}: PASS")
    else:
        print(f"{SCRIPT_PATH.name}: FAIL")
        errors = report.get("errors") or []
        if errors:
            print(json.dumps(errors, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


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


def _report(profile: str, command: str) -> dict[str, Any]:
    return {
        "schema": "cybermancy-step6-integration-runtime-v1",
        "status": "PASS",
        "phase": "C",
        "milestone": "structural-preflight-common-adapter-ch29-proof",
        "command": command,
        "profile": profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "adapters": [],
    }


def _pandoc_executable() -> str | None:
    override = os.environ.get("CYBERMANCY_PANDOC_PATH")
    if override and Path(override).is_file():
        return str(Path(override).resolve())
    return shutil.which("pandoc")


def _pandoc_ast(source: Path) -> dict[str, Any]:
    pandoc = _pandoc_executable()
    if not pandoc:
        raise RuntimeError("Pandoc was not found. Set CYBERMANCY_PANDOC_PATH or install Pandoc.")
    proc = subprocess.run(
        [pandoc, "--from", PANDOC_FROM, "--to=json", "--wrap=none", str(source)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        tail = "\n".join(((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines()[-80:])
        raise RuntimeError(f"Pandoc AST generation failed for {source}:\n{tail}")
    value = json.loads(proc.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("Pandoc returned a non-object JSON document.")
    return value


def _load_base_ast(
    args: argparse.Namespace,
    profile: str,
    report: dict[str, Any],
) -> tuple[dict[str, Any] | None, Path | None]:
    if args.ast_input:
        ast_path = _resolve(args.ast_input, Path(args.ast_input))
        if not ast_path.is_file():
            _append_check(report, "BASE_AST_INPUT", "ERROR", f"Pandoc AST input does not exist: {ast_path}")
            return None, None
        try:
            ast = load_json(ast_path)
        except Exception as exc:
            _append_check(report, "BASE_AST_INPUT", "ERROR", f"Could not load Pandoc AST input: {exc}")
            return None, ast_path
        _append_check(report, "BASE_AST_INPUT", "PASS", f"Loaded one base Pandoc AST for {profile}.", str(ast_path))
        return ast, ast_path

    source_path = _resolve(args.source, PROFILE_SOURCE[profile])
    if not source_path.is_file():
        _append_check(report, "ASSEMBLED_SOURCE", "ERROR", f"Step 4 assembled source is missing: {source_path}")
        return None, source_path
    try:
        ast = _pandoc_ast(source_path)
    except Exception as exc:
        _append_check(report, "BASE_AST_GENERATION", "ERROR", str(exc))
        return None, source_path

    work_dir = _resolve(args.work_dir, DEFAULT_WORK)
    base_path = work_dir / f"{profile}-base.ast.json"
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_bytes(canonical_ast_bytes(ast))
    _append_check(
        report,
        "BASE_AST_GENERATION",
        "PASS",
        f"Generated exactly one base Pandoc AST for {profile}.",
        {"source": str(source_path), "ast": str(base_path), "sha256": canonical_ast_sha256(ast)},
    )
    return ast, base_path


def _merge_preflight(report: dict[str, Any], preflight: dict[str, Any]) -> None:
    report["preflight"] = preflight
    _append_check(
        report,
        "STRUCTURAL_PREFLIGHT",
        "PASS" if preflight.get("status") == "PASS" else "ERROR",
        "Structural preflight passed; package adapters may run."
        if preflight.get("status") == "PASS"
        else "Structural preflight failed; no package adapter was run.",
        {"inputAstSha256": preflight.get("inputAstSha256"), "inventory": preflight.get("inventory")},
    )


def _compose_ice(args: argparse.Namespace, report: dict[str, Any]) -> tuple[str, str] | None:
    config_path = _resolve(args.ice_config, DEFAULT_ICE_CONFIG)
    sidecar_path = _resolve(args.sidecar, DEFAULT_SIDECAR)
    source_root = _resolve(args.source_root, DEFAULT_SOURCE_ROOT)
    work_dir = _resolve(args.work_dir, DEFAULT_WORK)

    for code, path in (("ICE_CONFIG", config_path), ("STRUCTURED_SIDECAR", sidecar_path)):
        if not path.is_file():
            _append_check(report, code, "ERROR", f"Required integration input is missing: {path}")
    if report["status"] != "PASS":
        return None

    config = load_json(config_path)
    sidecar = load_json(sidecar_path)
    view, package_report, compat = compose_ice_reference_package(sidecar, config)
    attach_ice_reference_images(view, sidecar, compat, package_report)

    package_ok = package_report.get("status") == "PASS" and isinstance(view, dict)
    if package_ok:
        policy = config.get("publicationPolicy") if isinstance(config.get("publicationPolicy"), dict) else {}
        package = view.get("package") if isinstance(view.get("package"), dict) else {}
        expected_total = int(policy.get("expectedIceTotal") or 0)
        actual_total = int(package.get("entryCount") or 0)
        full_total = int(package.get("fullIceCount") or 0)
        package_ok = expected_total == actual_total == full_total == 13

    _append_check(
        report,
        "ICE_REFERENCE_PACKAGE",
        "PASS" if package_ok else "ERROR",
        "Frozen Chapter 29 ICEReferencePackage composed from the complete 13-entry Step 4 ICE corpus."
        if package_ok
        else "Frozen Chapter 29 ICEReferencePackage did not satisfy its semantic/corpus contract.",
        {
            "packageReport": package_report,
            "entryCount": (view or {}).get("package", {}).get("entryCount") if isinstance(view, dict) else None,
        },
    )
    if not package_ok or not isinstance(view, dict):
        return None

    render_root = work_dir / "ice-render-assets"
    render_assets, asset_report = prepare_lualatex_render_assets(
        ice_reference_publication_images(view),
        source_root,
        render_root,
    )
    _append_check(
        report,
        "ICE_REFERENCE_RENDER_ASSETS",
        "PASS" if asset_report.get("status") == "PASS" else "ERROR",
        "Prepared Chapter 29 integration render assets."
        if asset_report.get("status") == "PASS"
        else "Could not prepare Chapter 29 integration render assets.",
        asset_report,
    )
    if report["status"] != "PASS":
        return None
    return render_integration_fragments(view, config, render_assets)


def _run(args: argparse.Namespace) -> int:
    profile = args.profile
    report = _report(profile, args.command)
    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    report_path = _resolve(args.report, DEFAULT_REPORTS / f"{profile}-{args.command}.json")

    if not contract_path.is_file():
        _append_check(report, "INTEGRATION_CONTRACT", "ERROR", f"Step 6 integration contract is missing: {contract_path}")
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    contract = load_json(contract_path)
    contract_ok = (
        contract.get("schema") == "cybermancy-step6-integration-contract-v1"
        and contract.get("version") == "1.0"
        and contract.get("status") == "accepted"
    )
    _append_check(
        report,
        "INTEGRATION_CONTRACT",
        "PASS" if contract_ok else "ERROR",
        "Accepted Step 6 integration contract v1.0 loaded." if contract_ok else "Step 6 integration contract is not accepted v1.0.",
        str(contract_path),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    if profile not in (contract.get("profiles") or {}):
        _append_check(report, "PROFILE_CONTRACT", "ERROR", f"Profile is not defined by the integration contract: {profile}")
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    ast, ast_source = _load_base_ast(args, profile, report)
    if ast is None:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    report["paths"] = {"contract": str(contract_path), "baseAstOrSource": str(ast_source) if ast_source else None}
    preflight = structural_preflight(ast, contract, profile)
    _merge_preflight(report, preflight)
    if report["status"] != "PASS" or args.command == "preflight":
        if args.command == "preflight" and report["status"] == "PASS":
            output_path = _resolve(args.ast_output, DEFAULT_OUTPUT / f"{profile}-preflight.ast.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(canonical_ast_bytes(ast))
            report["paths"]["outputAst"] = str(output_path)
            report["outputAstSha256"] = canonical_ast_sha256(ast)
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    fragments = _compose_ice(args, report)
    if fragments is None or report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    header_latex, body_latex = fragments
    adapter = integrate_chapter29_with_adapter(ast, profile, header_latex, body_latex)
    report["adapters"].append(adapter.as_dict())
    _append_check(
        report,
        "ICE_REFERENCE_ADAPTER",
        "PASS" if adapter.status == "PASS" else "ERROR",
        "Chapter 29 adapter satisfied exact semantic replacement and postconditions."
        if adapter.status == "PASS"
        else "Chapter 29 adapter failed exact semantic replacement; integrated AST was not written.",
        adapter.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    digest_before_repeat = canonical_ast_sha256(ast)
    repeated = integrate_chapter29_with_adapter(ast, profile, header_latex, body_latex)
    digest_after_repeat = canonical_ast_sha256(ast)
    idempotent_ok = repeated.status == "PASS" and repeated.idempotent and digest_before_repeat == digest_after_repeat
    _append_check(
        report,
        "ICE_REFERENCE_ADAPTER_IDEMPOTENCY",
        "PASS" if idempotent_ok else "ERROR",
        "Repeated Chapter 29 adapter execution is a byte-stable no-op."
        if idempotent_ok
        else "Repeated Chapter 29 adapter execution was not a byte-stable no-op.",
        repeated.as_dict(),
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output_path = _resolve(args.ast_output, DEFAULT_OUTPUT / f"{profile}-phase-c-ch29.ast.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_ast_bytes(ast))
    report["paths"]["outputAst"] = str(output_path)
    report["outputAstSha256"] = canonical_ast_sha256(ast)
    _append_check(
        report,
        "INTEGRATED_AST_OUTPUT",
        "PASS",
        "Wrote deterministic Phase C AST with Chapter 29 integrated.",
        {"path": str(output_path), "sha256": report["outputAstSha256"]},
    )

    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Cybermancy Rulebook Step 6 Phase C integration runtime: structural preflight "
            "and Chapter 29 first adapter proof."
        )
    )
    p.add_argument("command", choices=["preflight", "integrate-ice"])
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--source")
    p.add_argument("--ast-input")
    p.add_argument("--ast-output")
    p.add_argument("--work-dir")
    p.add_argument("--report")
    p.add_argument("--ice-config")
    p.add_argument("--sidecar")
    p.add_argument("--source-root")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
