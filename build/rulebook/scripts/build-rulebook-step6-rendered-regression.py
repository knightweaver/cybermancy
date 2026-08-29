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

from rulebook_layout.rendered_regression import (
    STAGE_ORDER,
    contract_stage,
    copy_validated_pdf,
    deferred_output_vboxes,
    extract_bbox_layout,
    extract_layout_text,
    locate_rendered_structure,
    page_count_consistency,
    page_geometry_report,
    render_anchor_previews,
    rendered_bounds_report,
    run_pdfinfo,
    sha256_file,
    stage160_pdf_hash,
)

DEFAULT_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DEFAULT_STAGE160_ROOT = RULEBOOK_DIR / "layout" / "integration" / "output" / "stage160"
DEFAULT_OUTPUT_ROOT = RULEBOOK_DIR / "layout" / "integration" / "output" / "stage170"
DEFAULT_WORK_ROOT = RULEBOOK_DIR / "layout" / "integration" / "work" / "stage170"
DEFAULT_REPORTS = RULEBOOK_DIR / "layout" / "integration" / "reports"
DEFAULT_PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"

PROFILE_STEMS = {
    "player-guide": "Cybermancy_Player_Guide_Step6_Integrated",
    "complete-rulebook": "Cybermancy_Complete_Rulebook_Step6_Integrated",
}
FINAL_NAMES = {
    "player-guide": "Cybermancy_Player_Guide_Step6.pdf",
    "complete-rulebook": "Cybermancy_Complete_Rulebook_Step6.pdf",
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


def _check(report: dict[str, Any], code: str, ok: bool, message: str, details: Any = None) -> None:
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


def _warning(report: dict[str, Any], code: str, message: str, details: Any = None) -> None:
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
        print(json.dumps(report.get("errors") or [], indent=2, ensure_ascii=False))
    return 0 if report.get("status") == "PASS" else 2


def _load_prose_builder(path: Path):
    spec = importlib.util.spec_from_file_location("cybermancy_step6_stage170_prose", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load accepted tool resolver: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(args: argparse.Namespace) -> int:
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage170-rendered-regression-v1",
        "status": "PASS",
        "milestone": "stage170-rendered-output-regression",
        "profile": args.profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "paths": {},
    }
    report_path = _resolve(
        args.report,
        DEFAULT_REPORTS / f"{args.profile}-stage170-rendered-regression.json",
    )

    contract_path = _resolve(args.contract, DEFAULT_CONTRACT)
    if not contract_path.is_file():
        _check(report, "STAGE170_CONTRACT", False, f"Missing integration contract: {contract_path}")
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
    _check(
        report,
        "STAGE170_CONTRACT",
        contract_ok,
        "Accepted integration contract contains rendered regression at canonical order 170.",
        stage,
    )
    if not contract_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    stem = PROFILE_STEMS[args.profile]
    stage160_dir = _resolve(args.stage160_dir, DEFAULT_STAGE160_ROOT / args.profile)
    input_pdf = _resolve(args.pdf_input, stage160_dir / f"{stem}.pdf")
    stage160_report_path = _resolve(
        args.stage160_report,
        DEFAULT_REPORTS / f"{args.profile}-stage160-lualatex.json",
    )
    inputs_ok = input_pdf.is_file() and stage160_report_path.is_file()
    _check(
        report,
        "STAGE160_INPUTS",
        inputs_ok,
        "Loaded the accepted Stage 160 PDF and proof report."
        if inputs_ok
        else "Stage 170 requires a Stage 160 PDF and PASS proof report.",
        {"pdf": str(input_pdf), "stage160Report": str(stage160_report_path)},
    )
    if not inputs_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    stage160_report = _load_json(stage160_report_path)
    expected_sha = stage160_pdf_hash(stage160_report)
    input_sha = sha256_file(input_pdf)
    provenance_ok = (
        stage160_report.get("status") == "PASS"
        and bool(expected_sha)
        and expected_sha == input_sha
    )
    _check(
        report,
        "STAGE160_PDF_PROVENANCE",
        provenance_ok,
        "Stage 160 proof is PASS and its recorded PDF SHA-256 matches the exact rendered-regression input.",
        {
            "stage160Status": stage160_report.get("status"),
            "expectedPdfSha256": expected_sha,
            "actualPdfSha256": input_sha,
        },
    )
    if not provenance_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    prose_builder = _resolve(args.prose_builder, DEFAULT_PROSE_BUILDER)
    try:
        prose = _load_prose_builder(prose_builder)
        pdfinfo = prose.resolve_tool("pdfinfo")
        pdftotext = prose.resolve_tool("pdftotext")
        pdftoppm = prose.resolve_tool("pdftoppm")
    except Exception as exc:
        _check(
            report,
            "STAGE170_TOOLCHAIN",
            False,
            f"Could not initialize rendered-regression tools: {type(exc).__name__}: {exc}",
        )
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    required_tools_ok = bool(pdfinfo and pdftotext)
    _check(
        report,
        "STAGE170_TOOLCHAIN",
        required_tools_ok,
        "pdfinfo and pdftotext are available; pdftoppm is optional for preview rasterization."
        if required_tools_ok
        else "Stage 170 requires pdfinfo and pdftotext from the existing PDF toolchain.",
        {"pdfinfo": pdfinfo, "pdftotext": pdftotext, "pdftoppm": pdftoppm},
    )
    if not required_tools_ok:
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    work_dir = _resolve(args.work_dir, DEFAULT_WORK_ROOT / args.profile)
    work_dir.mkdir(parents=True, exist_ok=True)
    layout_text_path = work_dir / f"{args.profile}-layout.txt"
    bbox_path = work_dir / f"{args.profile}-bbox.html"

    info = run_pdfinfo(input_pdf, str(pdfinfo))
    report["pdfInfo"] = info
    _check(
        report,
        "STAGE170_PDFINFO",
        info.get("status") == "PASS",
        "pdfinfo successfully read the unified Stage 160 PDF.",
        info,
    )
    if info.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    layout = extract_layout_text(input_pdf, str(pdftotext), layout_text_path)
    report["layoutText"] = {k: v for k, v in layout.items() if k != "pages"}
    _check(
        report,
        "STAGE170_LAYOUT_TEXT",
        layout.get("status") == "PASS",
        "pdftotext extracted page-preserving rendered text from the full PDF.",
        report["layoutText"],
    )
    if layout.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    bbox = extract_bbox_layout(input_pdf, str(pdftotext), bbox_path)
    report["bboxExtraction"] = {k: v for k, v in bbox.items() if k != "pages"}
    _check(
        report,
        "STAGE170_BBOX_EXTRACTION",
        bbox.get("status") == "PASS",
        "pdftotext extracted page/word bounding boxes from the rendered PDF.",
        report["bboxExtraction"],
    )
    if bbox.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    counts = page_count_consistency(info, layout, bbox)
    _check(
        report,
        "STAGE170_PAGE_COUNT_CONSISTENCY",
        counts.get("status") == "PASS",
        "pdfinfo, layout text extraction, and bbox extraction agree on page count.",
        counts,
    )

    geometry = page_geometry_report(bbox["pages"])
    _check(
        report,
        "STAGE170_PAGE_GEOMETRY",
        geometry.get("status") == "PASS",
        "Every rendered page is US Letter within the accepted one-point engine tolerance.",
        geometry,
    )

    bounds = rendered_bounds_report(bbox["pages"])
    _check(
        report,
        "STAGE170_RENDERED_TEXT_BOUNDS",
        bounds.get("status") == "PASS",
        "No extracted rendered word bounding box extends beyond its PDF page boundary.",
        bounds,
    )
    if bounds.get("edgeWordCount"):
        _warning(
            report,
            "STAGE170_EDGE_TEXT",
            f"{bounds['edgeWordCount']} rendered word(s) lie within {bounds['edgeWarningPt']} pt of a page edge; recorded for visual spot review.",
            bounds.get("edgeWords"),
        )

    structure = locate_rendered_structure(layout["pages"], contract, args.profile)
    report["renderedStructure"] = structure
    _check(
        report,
        "STAGE170_RENDERED_STRUCTURE",
        structure.get("status") == "PASS",
        "Rendered Part, Chapter, reserved-Chapter-13, provenance-residue, audience, and GM-boundary anchors match the accepted architecture.",
        structure,
    )

    deferred = deferred_output_vboxes(stage160_report)
    deferred_ok = bounds.get("status") == "PASS" and geometry.get("status") == "PASS"
    _check(
        report,
        "STAGE170_DEFERRED_VBOX_GEOMETRY",
        deferred_ok,
        "Stage 160 output-routine vbox diagnostics are reconciled against the rendered PDF: page geometry is correct and no rendered text bbox leaves the page.",
        {"diagnosticCount": len(deferred), "diagnostics": deferred},
    )

    anchor_pages = [
        int(row["anchorPage"])
        for row in structure.get("parts") or []
        if row.get("anchorPage")
    ]
    anchor_pages.extend(
        int(row["anchorPage"])
        for row in structure.get("chapters") or []
        if row.get("anchorPage")
    )
    anchor_pages.extend(int(value) for value in structure.get("gmDivider", {}).get("pages") or [])
    previews = render_anchor_previews(
        input_pdf,
        str(pdftoppm) if pdftoppm else None,
        anchor_pages,
        work_dir / "previews",
        dpi=args.preview_dpi,
    )
    report["previews"] = previews
    if previews.get("status") == "PASS":
        _check(
            report,
            "STAGE170_ANCHOR_PREVIEWS",
            True,
            f"Rendered {previews.get('pageCount')} structural anchor-page preview(s) for optional human spot review.",
            {k: v for k, v in previews.items() if k != "previews"},
        )
    elif previews.get("status") == "SKIPPED":
        _warning(
            report,
            "STAGE170_ANCHOR_PREVIEWS",
            "pdftoppm is unavailable; automated bbox/text rendered regression remains complete, but PNG preview generation was skipped.",
            previews,
        )
    else:
        _check(
            report,
            "STAGE170_ANCHOR_PREVIEWS",
            False,
            "One or more structural anchor pages could not be rasterized by pdftoppm.",
            previews,
        )

    input_unchanged = sha256_file(input_pdf) == input_sha
    _check(
        report,
        "STAGE170_STAGE160_IMMUTABILITY",
        input_unchanged,
        "Stage 170 left the accepted Stage 160 PDF byte-stable.",
        {"before": input_sha, "after": sha256_file(input_pdf)},
    )

    if report["status"] != "PASS":
        _write_json(report_path, report)
        return _emit(report, args.verbose)

    output_dir = _resolve(args.output_dir, DEFAULT_OUTPUT_ROOT / args.profile)
    final_pdf = _resolve(args.output_pdf, output_dir / FINAL_NAMES[args.profile])
    final = copy_validated_pdf(input_pdf, final_pdf)
    report["finalPdf"] = final
    _check(
        report,
        "STAGE170_FINAL_PDF",
        final.get("status") == "PASS",
        "Published an exact byte-for-byte copy of the validated Stage 160 PDF at the deterministic Stage 170 final-artifact path.",
        final,
    )

    report["paths"] = {
        "contract": str(contract_path),
        "stage160Report": str(stage160_report_path),
        "stage160Pdf": str(input_pdf),
        "work": str(work_dir),
        "layoutText": str(layout_text_path),
        "bbox": str(bbox_path),
        "previews": str(work_dir / "previews"),
        "finalPdf": str(final_pdf),
        "report": str(report_path),
    }
    report["inputPdfSha256"] = input_sha
    report["finalPdfSha256"] = final.get("sha256")
    _write_json(report_path, report)
    return _emit(report, args.verbose)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Validate the rendered Stage 160 Cybermancy PDF through Stage 170 page/text/bbox regression."
    )
    p.add_argument("--profile", choices=["player-guide", "complete-rulebook"], required=True)
    p.add_argument("--contract")
    p.add_argument("--stage160-dir")
    p.add_argument("--stage160-report")
    p.add_argument("--pdf-input")
    p.add_argument("--prose-builder")
    p.add_argument("--work-dir")
    p.add_argument("--output-dir")
    p.add_argument("--output-pdf")
    p.add_argument("--report")
    p.add_argument("--preview-dpi", type=int, default=72)
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.preview_dpi < 36 or args.preview_dpi > 200:
        parser().error("--preview-dpi must be between 36 and 200")
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
