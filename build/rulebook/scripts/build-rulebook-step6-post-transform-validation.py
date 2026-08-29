#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.integration_ast import canonical_ast_bytes, canonical_ast_sha256
from rulebook_layout.post_transform_validation import validate_post_transform

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_OUTPUT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"


def _resolve(value: str | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
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


def _run(args: argparse.Namespace) -> int:
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage140-proof-v1",
        "status": "PASS",
        "milestone": "post-transform-semantic-validation",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
    }

    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-stage140-post-transform-validation.json",
    )
    ast_input = _resolve(
        args.ast_input,
        DEFAULT_OUTPUT / f"{args.profile}-stage130-publication-shell.ast.json",
    )
    ast_output = _resolve(
        args.ast_output,
        DEFAULT_OUTPUT / f"{args.profile}-stage140-validated.ast.json",
    )

    if not contract_path.is_file():
        _append_check(
            report,
            "INTEGRATION_CONTRACT",
            "ERROR",
            f"Missing integration contract: {contract_path}",
        )
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

    if not ast_input.is_file():
        _append_check(
            report,
            "STAGE130_AST_INPUT",
            "ERROR",
            "Stage 130 cumulative AST is missing. Run the accepted Stage 130 proof first.",
            str(ast_input),
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    ast = _load_json(ast_input)
    input_sha = canonical_ast_sha256(ast)
    _append_check(
        report,
        "STAGE130_AST_INPUT",
        "PASS",
        "Loaded deterministic Stage 130 cumulative AST for Stage 140 inspection.",
        {"path": str(ast_input), "sha256": input_sha},
    )

    validation = validate_post_transform(ast, contract, args.profile)
    report["validation"] = validation
    validation_ok = validation.get("status") == "PASS"
    _append_check(
        report,
        "STAGE140_POST_TRANSFORM_VALIDATION",
        "PASS" if validation_ok else "ERROR",
        "Stage 140 post-transform semantic validation passed."
        if validation_ok
        else "Stage 140 post-transform semantic validation failed closed.",
        validation,
    )
    if not validation_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output_sha = canonical_ast_sha256(ast)
    non_mutating = input_sha == output_sha
    _append_check(
        report,
        "STAGE140_INPUT_OUTPUT_IDENTITY",
        "PASS" if non_mutating else "ERROR",
        "Stage 140 preserved the exact Stage 130 AST bytes semantically."
        if non_mutating
        else "Stage 140 unexpectedly changed the AST.",
        {"inputSha256": input_sha, "outputSha256": output_sha},
    )
    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    ast_output.parent.mkdir(parents=True, exist_ok=True)
    ast_output.write_bytes(canonical_ast_bytes(ast))
    written = _load_json(ast_output)
    written_sha = canonical_ast_sha256(written)
    write_ok = written_sha == input_sha
    _append_check(
        report,
        "STAGE140_VALIDATED_AST_OUTPUT",
        "PASS" if write_ok else "ERROR",
        "Wrote deterministic Stage 140 validated AST for Stage 150."
        if write_ok
        else "Written Stage 140 AST does not match the validated input AST.",
        {"path": str(ast_output), "sha256": written_sha},
    )

    report["paths"] = {
        "contract": str(contract_path),
        "inputAst": str(ast_input),
        "outputAst": str(ast_output),
        "report": str(report_path),
    }
    report["inputAstSha256"] = input_sha
    report["outputAstSha256"] = written_sha
    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Validate the accepted Stage 130 shell-lowered AST without mutation "
            "and emit the deterministic Stage 140 input for integrated LaTeX."
        )
    )
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--ast-input")
    p.add_argument("--ast-output")
    p.add_argument("--report")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
