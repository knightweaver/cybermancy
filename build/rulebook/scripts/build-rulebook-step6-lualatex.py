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

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.stage160_policy import (
    compile_unified_lualatex_stage160,
    strip_publication_provenance_residue,
)
from rulebook_layout.unified_lualatex import (
    DEFAULT_PASSES,
    STAGE_ORDER,
    contract_stage,
    copy_compiled_pdf,
    pdf_page_count,
    prepare_compile_tree,
    probe_tex_packages,
    sha256_file,
    sha256_tree,
    validate_static_graphics,
)
from rulebook_production.publication_shell import bookmark_structure

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_STAGE150_ROOT = RULEBOOK_DIR / "layout" / "integration" / "output" / "stage150"
DEFAULT_OUTPUT_ROOT = RULEBOOK_DIR / "layout" / "integration" / "output" / "stage160"
DEFAULT_WORK_ROOT = RULEBOOK_DIR / "layout" / "integration" / "work" / "stage160"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"
DEFAULT_PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"
DEFAULT_PRODUCTION_CONTRACT = RULEBOOK_DIR / "production" / "production-renderer-v1.json"

PROFILE_STEMS = {
    "player-guide": "Cybermancy_Player_Guide_Step6_Integrated",
    "complete-rulebook": "Cybermancy_Complete_Rulebook_Step6_Integrated",
}


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


def _append_warning(
    report: dict[str, Any],
    code: str,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {"code": code, "status": "WARNING", "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
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


def _load_prose_builder(path: Path):
    spec = importlib.util.spec_from_file_location("cybermancy_step6_stage160_prose", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load accepted Long-Form Prose runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _expected_stage150_hash(stage150_report: dict[str, Any]) -> str:
    generation = stage150_report.get("generation")
    if isinstance(generation, dict):
        value = str(generation.get("outputTexSha256") or "").strip()
        if value:
            return value
    for check in stage150_report.get("checks") or []:
        if not isinstance(check, dict) or check.get("code") != "STAGE150_TEX_OUTPUT":
            continue
        details = check.get("details")
        if isinstance(details, dict):
            value = str(details.get("sha256") or "").strip()
            if value:
                return value
    return ""


def _run(args: argparse.Namespace) -> int:
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage160-lualatex-proof-v1",
        "status": "PASS",
        "milestone": "stage160-unified-lualatex",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "paths": {},
    }
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-stage160-lualatex.json",
    )

    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    if not contract_path.is_file():
        _append_check(report, "INTEGRATION_CONTRACT", False, f"Missing integration contract: {contract_path}")
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    contract = _load_json(contract_path)
    stage = contract_stage(contract)
    contract_ok = (
        contract.get("schema") == "cybermancy-step6-integration-contract-v1"
        and contract.get("version") == "1.0"
        and contract.get("status") == "accepted"
        and isinstance(stage, dict)
        and int(stage.get("order") or -1) == STAGE_ORDER
    )
    _append_check(
        report,
        "STAGE160_CONTRACT",
        contract_ok,
        "Accepted integration contract contains LuaLaTeX at canonical order 160.",
        stage,
    )
    if not contract_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    stem = PROFILE_STEMS[args.profile]
    source_dir = _resolve(args.stage150_dir, DEFAULT_STAGE150_ROOT / args.profile)
    source_tex = _resolve(args.tex_input, source_dir / f"{stem}.tex")
    source_assets = source_dir / "assets"
    stage150_report_path = _resolve(
        args.stage150_report,
        DEFAULT_REPORTS / f"{args.profile}-stage150-integrated-latex.json",
    )

    required = source_tex.is_file() and source_assets.is_dir() and stage150_report_path.is_file()
    _append_check(
        report,
        "STAGE150_INPUTS",
        required,
        "Loaded the accepted Stage 150 integrated TeX, self-contained assets, and proof report."
        if required
        else "Stage 160 requires a clean Stage 150 TeX output, assets directory, and proof report.",
        {
            "tex": str(source_tex),
            "assets": str(source_assets),
            "stage150Report": str(stage150_report_path),
        },
    )
    if not required:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    stage150_report = _load_json(stage150_report_path)
    expected_tex_sha = _expected_stage150_hash(stage150_report)
    actual_tex_sha = sha256_file(source_tex)
    stage150_ok = (
        stage150_report.get("status") == "PASS"
        and bool(expected_tex_sha)
        and expected_tex_sha == actual_tex_sha
    )
    _append_check(
        report,
        "STAGE150_PROVENANCE",
        stage150_ok,
        "Stage 150 proof is PASS and its recorded TeX SHA-256 matches the exact compile input."
        if stage150_ok
        else "Stage 150 provenance does not match the TeX selected for Stage 160.",
        {
            "stage150Status": stage150_report.get("status"),
            "expectedTexSha256": expected_tex_sha,
            "actualTexSha256": actual_tex_sha,
        },
    )
    if not stage150_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    prose_builder_path = _resolve(args.prose_builder, DEFAULT_PROSE_BUILDER)
    if not prose_builder_path.is_file():
        _append_check(report, "STAGE160_TOOLCHAIN", False, f"Accepted tool resolver is missing: {prose_builder_path}")
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    try:
        prose = _load_prose_builder(prose_builder_path)
        lualatex = prose.resolve_tool("lualatex")
        kpsewhich = prose.resolve_tool("kpsewhich")
        pdfinfo = prose.resolve_tool("pdfinfo")
    except Exception as exc:
        _append_check(
            report,
            "STAGE160_TOOLCHAIN",
            False,
            f"Could not initialize the accepted Step 6 tool resolver: {type(exc).__name__}: {exc}",
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    _append_check(
        report,
        "STAGE160_LUALATEX_AVAILABLE",
        bool(lualatex),
        "LuaLaTeX is available for the first unified whole-book compilation."
        if lualatex
        else "LuaLaTeX was not found through the accepted Windows/toolchain resolver.",
        {
            "path": lualatex,
            "version": prose.executable_version("lualatex") if lualatex else None,
            "kpsewhich": kpsewhich,
            "pdfinfo": pdfinfo,
        },
    )
    if not lualatex:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    work_dir = _resolve(args.work_dir, DEFAULT_WORK_ROOT / args.profile)
    output_dir = _resolve(args.output_dir, DEFAULT_OUTPUT_ROOT / args.profile)
    output_pdf = _resolve(args.output_pdf, output_dir / f"{stem}.pdf")

    source_assets_sha_before, source_asset_rows_before = sha256_tree(source_assets)
    try:
        prepared = prepare_compile_tree(source_tex, source_assets, work_dir)
    except Exception as exc:
        _append_check(
            report,
            "STAGE160_COMPILE_TREE",
            False,
            f"Could not create the isolated Stage 160 compile root: {type(exc).__name__}: {exc}",
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)
    report["compileTree"] = prepared
    compile_tree_ok = prepared.get("status") == "PASS"
    _append_check(
        report,
        "STAGE160_COMPILE_TREE",
        compile_tree_ok,
        "Copied the exact Stage 150 TeX and asset tree into an isolated Stage 160 compile root.",
        prepared,
    )
    if not compile_tree_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    compile_tex = Path(prepared["compileTex"])
    provenance_cleanup = strip_publication_provenance_residue(
        compile_tex, args.profile
    )
    prepared["publicationProvenanceCleanup"] = provenance_cleanup
    prepared["compileTexSha256"] = sha256_file(compile_tex)
    provenance_ok = provenance_cleanup.get("status") == "PASS"
    _append_check(
        report,
        "STAGE160_PROVENANCE_RESIDUE",
        provenance_ok,
        "Removed the exact generated publication-provenance residue from the isolated compile copy while preserving the accepted Stage 150 handoff."
        if provenance_cleanup.get("stripped")
        else "No generated publication-provenance residue required removal from the isolated compile copy."
        if provenance_ok
        else "Publication provenance-like residue did not match the exact fail-closed Stage 160 cleanup contract.",
        provenance_cleanup,
    )
    if not provenance_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    tex_text = compile_tex.read_text(encoding="utf-8")
    graphics = validate_static_graphics(tex_text, work_dir)
    report["graphicsPreflight"] = graphics
    graphics_ok = graphics.get("status") == "PASS"
    _append_check(
        report,
        "STAGE160_GRAPHICS_PREFLIGHT",
        graphics_ok,
        "Every concrete integrated graphics reference is relative, contained in the compile root, and present."
        if graphics_ok
        else "One or more integrated graphics references are missing, absolute, or escape the compile root.",
        graphics,
    )
    if not graphics_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    package_probe = probe_tex_packages(tex_text, kpsewhich, work_dir)
    report["packageProbe"] = package_probe
    package_ok = package_probe.get("status") in {"PASS", "SKIPPED"}
    _append_check(
        report,
        "STAGE160_TEX_DEPENDENCIES",
        package_ok,
        "Required LaTeX packages are resolvable before unified compilation."
        if package_probe.get("status") == "PASS"
        else "kpsewhich is unavailable; package resolution will be enforced by LuaLaTeX itself."
        if package_probe.get("status") == "SKIPPED"
        else "One or more required LaTeX packages could not be resolved.",
        package_probe,
    )
    if not package_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    try:
        compilation = compile_unified_lualatex_stage160(
            compile_tex,
            str(lualatex),
            work_dir,
            passes=args.passes,
        )
    except Exception as exc:
        compilation = {
            "status": "FAIL",
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    report["compilation"] = compilation
    compile_ok = compilation.get("status") == "PASS"
    _append_check(
        report,
        "STAGE160_LUALATEX",
        compile_ok,
        f"LuaLaTeX completed {args.passes} unified pass(es) and produced a PDF without blocking compiler diagnostics."
        if compile_ok
        else "Unified LuaLaTeX compilation failed or emitted a blocking overfull/missing-character diagnostic.",
        compilation,
    )
    if not compile_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    if args.production_contract:
        production_contract_path = _resolve(
            args.production_contract, DEFAULT_PRODUCTION_CONTRACT
        )
        production_contract = _load_json(production_contract_path)
        bookmark_report = bookmark_structure(
            work_dir / f"{compile_tex.stem}.out",
            work_dir / f"{compile_tex.stem}.toc",
            production_contract,
            contract,
            args.profile,
        )
        report["bookmarkStructure"] = bookmark_report
        bookmark_ok = bookmark_report.get("status") == "PASS"
        _append_check(
            report,
            "STAGE160_PRODUCTION_BOOKMARKS",
            bookmark_ok,
            "PDF bookmark evidence contains only Parts, Chapters, and Appendix B."
            if bookmark_ok
            else "Production bookmark evidence is incomplete or contains lower-level headings.",
            bookmark_report,
        )
        if not bookmark_ok:
            _write_json(report_path, report)
            return _emit(report, args.verbose)

    diagnostics = compilation.get("diagnostics") if isinstance(compilation.get("diagnostics"), dict) else {}
    blocking_overfull = (
        diagnostics.get("blockingOverfull")
        if isinstance(diagnostics.get("blockingOverfull"), list)
        else diagnostics.get("overfull")
        if isinstance(diagnostics.get("overfull"), list)
        else []
    )
    output_routine_vboxes = (
        diagnostics.get("outputRoutineVboxes")
        if isinstance(diagnostics.get("outputRoutineVboxes"), list)
        else []
    )
    missing_characters = diagnostics.get("missingCharacters") if isinstance(diagnostics.get("missingCharacters"), list) else []
    _append_check(
        report,
        "STAGE160_OVERFULL_BOXES",
        not blocking_overfull,
        "Unified LuaLaTeX emitted no blocking overfull hboxes or non-output-routine vboxes.",
        blocking_overfull or None,
    )
    if output_routine_vboxes:
        _append_warning(
            report,
            "STAGE160_OUTPUT_ROUTINE_VBOXES",
            f"LuaLaTeX emitted {len(output_routine_vboxes)} output-routine overfull vbox diagnostic(s). They are preserved for Stage 170 rendered/page-level regression rather than suppressed or treated as a Stage 160 compile failure.",
            output_routine_vboxes,
        )
    else:
        _append_check(
            report,
            "STAGE160_OUTPUT_ROUTINE_VBOXES",
            True,
            "LuaLaTeX emitted no output-routine overfull vbox diagnostics requiring Stage 170 review.",
        )
    _append_check(
        report,
        "STAGE160_MISSING_CHARACTERS",
        not missing_characters,
        "Unified LuaLaTeX emitted no missing-character diagnostics.",
        missing_characters or None,
    )
    material_warnings = sorted(
        set(
            (diagnostics.get("latexWarnings") or [])
            + (diagnostics.get("packageWarnings") or [])
            + (diagnostics.get("fontWarnings") or [])
        )
    )
    if material_warnings:
        _append_warning(
            report,
            "STAGE160_MATERIAL_WARNINGS",
            f"LuaLaTeX emitted {len(material_warnings)} non-blocking warning(s); preserved for Stage 170 review.",
            material_warnings[:200],
        )
    else:
        _append_check(
            report,
            "STAGE160_MATERIAL_WARNINGS",
            True,
            "LuaLaTeX emitted no additional material LaTeX/package/font warnings.",
        )

    compiled_pdf = Path(str(compilation.get("pdf") or ""))
    pdf_result = copy_compiled_pdf(compiled_pdf, output_pdf)
    report["pdfOutput"] = pdf_result
    pdf_ok = pdf_result.get("status") == "PASS"
    _append_check(
        report,
        "STAGE160_PDF_OUTPUT",
        pdf_ok,
        "Copied the unified compiled PDF to the deterministic Stage 160 output path."
        if pdf_ok
        else "Unified compilation did not yield a valid Stage 160 PDF artifact.",
        pdf_result,
    )
    if not pdf_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    pages = pdf_page_count(output_pdf, pdfinfo)
    report["pageCount"] = pages
    if pages:
        _append_check(
            report,
            "STAGE160_PAGE_COUNT",
            True,
            f"Unified PDF contains {pages} page(s). Page-count regression is deferred to Stage 170.",
            pages,
        )
    else:
        _append_warning(
            report,
            "STAGE160_PAGE_COUNT",
            "Could not determine PDF page count; rendered regression remains Stage 170 responsibility.",
        )

    source_assets_sha_after, source_asset_rows_after = sha256_tree(source_assets)
    source_immutable = (
        sha256_file(source_tex) == actual_tex_sha
        and source_assets_sha_before == source_assets_sha_after
        and source_asset_rows_before == source_asset_rows_after
    )
    _append_check(
        report,
        "STAGE160_STAGE150_IMMUTABILITY",
        source_immutable,
        "Stage 160 left the accepted Stage 150 TeX and asset tree byte-stable.",
        {
            "texSha256": sha256_file(source_tex),
            "assetsBefore": source_assets_sha_before,
            "assetsAfter": source_assets_sha_after,
        },
    )

    report["paths"] = {
        "contract": str(contract_path),
        "stage150Report": str(stage150_report_path),
        "stage150Tex": str(source_tex),
        "stage150Assets": str(source_assets),
        "compileRoot": str(work_dir),
        "compileTex": str(compile_tex),
        "logs": str(work_dir / "logs"),
        "outputPdf": str(output_pdf),
        "report": str(report_path),
    }
    report["inputTexSha256"] = actual_tex_sha
    report["outputPdfSha256"] = pdf_result.get("sha256")
    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compile one accepted Stage 150 integrated LaTeX document through unified LuaLaTeX Stage 160."
    )
    p.add_argument("--profile", choices=["complete-rulebook", "player-guide"], required=True)
    p.add_argument("--contract")
    p.add_argument("--stage150-dir")
    p.add_argument("--stage150-report")
    p.add_argument("--tex-input")
    p.add_argument("--prose-builder")
    p.add_argument("--work-dir")
    p.add_argument("--output-dir")
    p.add_argument("--output-pdf")
    p.add_argument("--report")
    p.add_argument("--passes", type=int, default=DEFAULT_PASSES)
    p.add_argument("--production-contract")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.passes < 1 or args.passes > 4:
        parser().error("--passes must be between 1 and 4")
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
