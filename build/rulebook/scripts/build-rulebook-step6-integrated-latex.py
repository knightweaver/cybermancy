#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.integration_ast import canonical_ast_sha256
from rulebook_layout.integrated_latex import EQUIPMENT_FAMILIES, generate_integrated_latex
from rulebook_layout.post_transform_validation import validate_post_transform
from rulebook_production.publication_shell import apply_publication_shell

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_INPUT_ROOT = RULEBOOK_DIR / "layout" / "integration" / "output"
DEFAULT_OUTPUT_ROOT = DEFAULT_INPUT_ROOT / "stage150"
DEFAULT_WORK_ROOT = RULEBOOK_DIR / "layout" / "integration" / "work" / "stage150"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"
DEFAULT_INTEGRATION_WORK = RULEBOOK_DIR / "layout" / "integration" / "work"
DEFAULT_PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"
DEFAULT_PROSE_CONFIG = RULEBOOK_DIR / "layout" / "prose" / "prose-layout-v1.json"
DEFAULT_ORIGIN_CONFIG = RULEBOOK_DIR / "layout" / "character-origins" / "character-origins-layout-v1.json"
DEFAULT_CLASS_CONFIG = RULEBOOK_DIR / "layout" / "classes" / "class-package-v1.json"
DEFAULT_DOMAIN_CONFIG = RULEBOOK_DIR / "layout" / "domains" / "domain-package-v1.json"
DEFAULT_EQUIPMENT_REGISTRY = RULEBOOK_DIR / "layout" / "equipment" / "equipment-section-v1.json"
DEFAULT_EQUIPMENT_CONFIG_DIR = RULEBOOK_DIR / "layout" / "equipment"
DEFAULT_ICE_CONFIG = RULEBOOK_DIR / "layout" / "ice" / "ice-reference-package-v1.json"
DEFAULT_PRODUCTION_CONTRACT = RULEBOOK_DIR / "production" / "production-renderer-v1.json"
DEFAULT_PUBLICATION_METADATA = RULEBOOK_DIR / "production" / "publication-metadata-v1.json"
DEFAULT_SIDECAR = RULEBOOK_DIR / "source" / "metadata" / "structured-entities.json"


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
    ok: bool,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {
        "code": code,
        "status": "PASS" if ok else "ERROR",
        "message": message,
    }
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if not ok:
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


def _load_prose_builder(path: Path):
    spec = importlib.util.spec_from_file_location("cybermancy_step6_stage150_prose", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load accepted Long-Form Prose builder: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _validate_configs(
    paths: dict[str, Path], report: dict[str, Any]
) -> dict[str, Any] | None:
    for label, path in paths.items():
        if label == "equipmentConfigDir":
            ok = path.is_dir()
        else:
            ok = path.is_file()
        if not ok:
            _append_check(
                report,
                "STAGE150_CONFIG_INPUTS",
                False,
                f"Required Stage 150 input is missing: {label}={path}",
            )
            return None

    try:
        prose = _load_json(paths["proseConfig"])
        origins = _load_json(paths["originConfig"])
        class_config = _load_json(paths["classConfig"])
        domain = _load_json(paths["domainConfig"])
        registry = _load_json(paths["equipmentRegistry"])
        ice = _load_json(paths["iceConfig"])
    except Exception as exc:
        _append_check(
            report,
            "STAGE150_CONFIG_INPUTS",
            False,
            f"Could not load accepted Stage 150 layout inputs: {type(exc).__name__}: {exc}",
        )
        return None

    static_ok = (
        prose.get("schema") == "cybermancy-rulebook-prose-layout-v1"
        and prose.get("version") == "1.0"
        and prose.get("status") == "ACCEPTED"
        and origins.get("schema") == "cybermancy-rulebook-character-origins-layout-v1"
        and origins.get("version") == "1.0"
        and origins.get("status") == "ACCEPTED"
        and class_config.get("schema") == "cybermancy-step6-class-package-config-v1.0"
        and int(class_config.get("chapter") or 0) == 12
        and domain.get("schema") == "cybermancy-step6-domain-package-config-v1.0"
        and int(domain.get("chapter") or 0) == 14
        and registry.get("schema") == "cybermancy-step6-equipment-section-v1.0"
        and ice.get("schema") == "cybermancy-step6-ice-reference-package-config-v1.0"
        and int(ice.get("chapter") or 0) == 29
    )
    if not static_ok:
        _append_check(
            report,
            "STAGE150_CONFIG_INPUTS",
            False,
            "One or more Stage 150 layout inputs differ from the accepted/frozen contracts.",
            {
                "prose": {"schema": prose.get("schema"), "version": prose.get("version"), "status": prose.get("status")},
                "origins": {"schema": origins.get("schema"), "version": origins.get("version"), "status": origins.get("status")},
                "class": {"schema": class_config.get("schema"), "chapter": class_config.get("chapter")},
                "domain": {"schema": domain.get("schema"), "chapter": domain.get("chapter")},
                "equipment": {"schema": registry.get("schema")},
                "ice": {"schema": ice.get("schema"), "chapter": ice.get("chapter")},
            },
        )
        return None

    equipment: dict[str, Any] = {}
    ordered_families: list[str] = []
    for row in registry.get("families") or []:
        if not isinstance(row, dict):
            continue
        family = str(row.get("family") or "")
        config_name = str(row.get("config") or "")
        config_path = paths["equipmentConfigDir"] / config_name
        if family not in EQUIPMENT_FAMILIES or not config_name or not config_path.is_file():
            _append_check(
                report,
                "STAGE150_CONFIG_INPUTS",
                False,
                f"Equipment registry entry cannot be resolved for Stage 150: {row}",
            )
            return None
        config = _load_json(config_path)
        if str(config.get("family") or "") != family or int(config.get("chapter") or 0) != int(row.get("chapter") or 0):
            _append_check(
                report,
                "STAGE150_CONFIG_INPUTS",
                False,
                f"Equipment config identity differs from the accepted registry: {config_path}",
            )
            return None
        equipment[family] = config
        ordered_families.append(family)

    equipment_ok = set(ordered_families) == EQUIPMENT_FAMILIES and len(ordered_families) == 8
    if not equipment_ok:
        _append_check(
            report,
            "STAGE150_CONFIG_INPUTS",
            False,
            "Stage 150 did not resolve exactly the eight accepted Equipment family configurations.",
            ordered_families,
        )
        return None

    configs = {
        "prose": prose,
        "origins": origins,
        "class": class_config,
        "domain": domain,
        "equipment": equipment,
        "ice": ice,
    }
    _append_check(
        report,
        "STAGE150_CONFIG_INPUTS",
        True,
        "Loaded the accepted Prose, Origins, Class, Domain, Equipment, and ICE layout contracts required by the one-document preamble.",
        {"equipmentFamilies": ordered_families},
    )
    return configs


def _run(args: argparse.Namespace) -> int:
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage150-integrated-latex-proof-v1",
        "status": "PASS",
        "milestone": "stage150-integrated-latex-generation",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "paths": {},
    }
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-stage150-integrated-latex.json",
    )

    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    if not contract_path.is_file():
        _append_check(report, "INTEGRATION_CONTRACT", False, f"Missing integration contract: {contract_path}")
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
        contract_ok,
        "Accepted Step 6 integration contract v1.0 loaded.",
        str(contract_path),
    )
    if not contract_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    default_ast = DEFAULT_INPUT_ROOT / f"{args.profile}-stage140-validated.ast.json"
    ast_path = _resolve(args.ast_input, default_ast)
    if not ast_path.is_file():
        _append_check(
            report,
            "STAGE140_AST_INPUT",
            False,
            f"Accepted Stage 140 AST is missing: {ast_path}",
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    try:
        ast = _load_json(ast_path)
    except Exception as exc:
        _append_check(
            report,
            "STAGE140_AST_INPUT",
            False,
            f"Could not read Stage 140 AST: {type(exc).__name__}: {exc}",
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    ast_sha = canonical_ast_sha256(ast)
    _append_check(
        report,
        "STAGE140_AST_INPUT",
        True,
        "Loaded the accepted Stage 140 validated AST.",
        {"path": str(ast_path), "sha256": ast_sha},
    )

    stage140 = validate_post_transform(ast, contract, args.profile)
    stage140_ok = stage140.get("status") == "PASS"
    report["stage140Revalidation"] = stage140
    _append_check(
        report,
        "STAGE140_REVALIDATION",
        stage140_ok,
        "Stage 140 semantic validation passes immediately before Stage 150.",
        {"inputAstSha256": stage140.get("inputAstSha256"), "outputAstSha256": stage140.get("outputAstSha256")},
    )
    if not stage140_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    config_paths = {
        "proseConfig": _resolve(args.prose_config, DEFAULT_PROSE_CONFIG),
        "originConfig": _resolve(args.character_origins_config, DEFAULT_ORIGIN_CONFIG),
        "classConfig": _resolve(args.class_config, DEFAULT_CLASS_CONFIG),
        "domainConfig": _resolve(args.domain_config, DEFAULT_DOMAIN_CONFIG),
        "equipmentRegistry": _resolve(args.equipment_registry, DEFAULT_EQUIPMENT_REGISTRY),
        "equipmentConfigDir": _resolve(args.equipment_config_dir, DEFAULT_EQUIPMENT_CONFIG_DIR),
        "iceConfig": _resolve(args.ice_config, DEFAULT_ICE_CONFIG),
    }
    configs = _validate_configs(config_paths, report)
    if configs is None or report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    prose_builder_path = _resolve(args.prose_builder, DEFAULT_PROSE_BUILDER)
    if not prose_builder_path.is_file():
        _append_check(report, "STAGE150_PROSE_RUNTIME", False, f"Accepted Long-Form Prose runtime is missing: {prose_builder_path}")
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    try:
        prose = _load_prose_builder(prose_builder_path)
        prose_preamble = prose.document_preamble()
    except Exception as exc:
        _append_check(
            report,
            "STAGE150_PROSE_RUNTIME",
            False,
            f"Could not load accepted Long-Form Prose preamble: {type(exc).__name__}: {exc}",
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    _append_check(
        report,
        "STAGE150_PROSE_RUNTIME",
        True,
        "Loaded the accepted Long-Form Prose v1.0 document shell as the Stage 150 preamble base.",
        str(prose_builder_path),
    )

    pandoc = prose.resolve_tool("pandoc")
    _append_check(
        report,
        "STAGE150_PANDOC_AVAILABLE",
        bool(pandoc),
        "Pandoc is available for Stage 150 JSON-AST to LaTeX lowering." if pandoc else "Pandoc was not found through the accepted Long-Form Prose tool resolver.",
        pandoc,
    )
    if not pandoc:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output_dir = _resolve(args.output_dir, DEFAULT_OUTPUT_ROOT / args.profile)
    work_dir = _resolve(args.work_dir, DEFAULT_WORK_ROOT / args.profile)
    integration_work = _resolve(args.integration_work_root, DEFAULT_INTEGRATION_WORK)

    try:
        document, generation = generate_integrated_latex(
            ast,
            contract,
            args.profile,
            configs,
            prose_preamble,
            str(pandoc),
            REPO_ROOT.resolve(),
            RULEBOOK_DIR.resolve(),
            integration_work,
            output_dir,
            work_dir,
        )
    except Exception as exc:
        generation = {
            "schema": "cybermancy-step6-stage150-integrated-latex-v1",
            "status": "FAIL",
            "errors": [
                {
                    "code": "STAGE150_EXCEPTION",
                    "status": "ERROR",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            ],
        }
        document = None

    if document is not None and args.production_contract:
        try:
            production_contract_path = _resolve(
                args.production_contract, DEFAULT_PRODUCTION_CONTRACT
            )
            metadata_path = _resolve(
                args.publication_metadata, DEFAULT_PUBLICATION_METADATA
            )
            sidecar_path = _resolve(args.sidecar, DEFAULT_SIDECAR)
            production_contract = _load_json(production_contract_path)
            metadata = _load_json(metadata_path)
            sidecar = _load_json(sidecar_path)
            document, shell_report = apply_publication_shell(
                document,
                args.profile,
                production_contract,
                metadata,
                sidecar,
            )
            output_tex = Path(str(generation.get("outputTex") or ""))
            output_tex.write_text(document, encoding="utf-8")
            output_sha = hashlib.sha256(output_tex.read_bytes()).hexdigest()
            generation["outputTexSha256"] = output_sha
            for check in generation.get("checks", []):
                if check.get("code") == "STAGE150_TEX_OUTPUT" and isinstance(
                    check.get("details"), dict
                ):
                    check["details"]["sha256"] = output_sha
            generation["productionShell"] = shell_report
            generation["checks"].append(
                {
                    "code": "STAGE150_PRODUCTION_PUBLICATION_SHELL",
                    "status": "PASS",
                    "message": "Applied the accepted Phase D title, navigation, pagination, and publication shell.",
                    "details": shell_report,
                }
            )
        except Exception as exc:
            generation["status"] = "FAIL"
            generation.setdefault("errors", []).append(
                {
                    "code": "STAGE150_PRODUCTION_PUBLICATION_SHELL",
                    "status": "ERROR",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
    report["generation"] = generation

    for item in generation.get("checks", []):
        if not isinstance(item, dict):
            continue
        report["checks"].append(item)
        if item.get("status") == "ERROR":
            report["errors"].append(item)
            report["status"] = "FAIL"
    if generation.get("status") != "PASS" or document is None:
        report["status"] = "FAIL"
        for item in generation.get("errors", []):
            if isinstance(item, dict) and item not in report["errors"]:
                report["errors"].append(item)
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output_tex = Path(str(generation.get("outputTex") or ""))
    report["paths"] = {
        "contract": str(contract_path),
        "stage140Ast": str(ast_path),
        "outputDirectory": str(output_dir),
        "workDirectory": str(work_dir),
        "outputTex": str(output_tex),
        "assets": str(output_dir / "assets"),
    }
    output_ok = output_tex.is_file() and output_tex.stat().st_size > 0
    _append_check(
        report,
        "STAGE150_TEX_OUTPUT",
        output_ok,
        "Stage 150 produced one body-complete integrated LaTeX document and did not invoke LuaLaTeX.",
        {"path": str(output_tex), "sha256": generation.get("outputTexSha256")},
    )

    ast_immutable = canonical_ast_sha256(ast) == ast_sha
    _append_check(
        report,
        "STAGE150_AST_INPUT_IDENTITY",
        ast_immutable,
        "The serialized Stage 140 input remained byte-stable throughout Stage 150 generation.",
        {"before": ast_sha, "after": canonical_ast_sha256(ast)},
    )

    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate one integrated Stage 150 LaTeX document from the accepted Stage 140 AST without compiling it."
    )
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--ast-input")
    p.add_argument("--output-dir")
    p.add_argument("--work-dir")
    p.add_argument("--report")
    p.add_argument("--integration-work-root")
    p.add_argument("--prose-builder")
    p.add_argument("--prose-config")
    p.add_argument("--character-origins-config")
    p.add_argument("--class-config")
    p.add_argument("--domain-config")
    p.add_argument("--equipment-registry")
    p.add_argument("--equipment-config-dir")
    p.add_argument("--ice-config")
    p.add_argument("--production-contract")
    p.add_argument("--publication-metadata")
    p.add_argument("--sidecar")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    return _run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
