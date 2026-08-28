#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.ice_reference import load_json
from rulebook_layout.ice_reference_geometry import validate_ice_reference_pdf
from rulebook_layout.ice_reference_images import (
    attach_ice_reference_images,
    ice_reference_publication_images,
)
from rulebook_layout.ice_reference_package import (
    compose_ice_reference_package,
    integrate_chapter29_ast,
    render_integration_fragments,
)
from rulebook_layout.ice_reference_refined import render_ice_reference_tex
from rulebook_layout.render_assets import prepare_lualatex_render_assets

DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/ice/ice-reference-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build/rulebook/layout/ice-reference"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/ice-reference-package-v1.json"
DEFAULT_AST_OUTPUT = DEFAULT_OUTPUT_DIR / "complete-rulebook-step6-ice-reference.ast.json"
SCRIPT_LABEL = SCRIPT_PATH.name

VIEW_NAME = "ice-reference-package-view.json"
TEX_NAME = "Cybermancy_Chapter29_ICE_Reference_Step6.tex"
PDF_NAME = "Cybermancy_Chapter29_ICE_Reference_Step6.pdf"
HEADER_FRAGMENT_NAME = "ice-reference-chapter-header.tex"
BODY_FRAGMENT_NAME = "ice-reference-family-features.tex"


def _path(value: str | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_check(report: dict[str, Any], code: str, status: str, message: str, details: Any = None) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report.setdefault("checks", []).append(item)
    if status == "ERROR":
        report["status"] = "FAIL"
        report.setdefault("errors", []).append(item)
    elif status == "WARNING":
        report.setdefault("warnings", []).append(item)


def _compile_lualatex(tex_path: Path) -> tuple[bool, str]:
    exe = shutil.which("lualatex")
    if not exe:
        return False, "LuaLaTeX was not found on PATH."
    output: list[str] = []
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


def _emit(report: dict[str, Any], verbose: bool) -> int:
    status = str(report.get("status") or "FAIL")
    if verbose:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif status == "PASS":
        print(f"{SCRIPT_LABEL}: PASS")
    else:
        print(f"{SCRIPT_LABEL}: FAIL")
        errors = report.get("errors") or []
        if errors:
            print(json.dumps(errors, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


def _load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    config_path = _path(args.config, DEFAULT_CONFIG)
    sidecar_path = _path(args.sidecar, DEFAULT_SIDECAR)
    output_dir = _path(getattr(args, "output_dir", None), DEFAULT_OUTPUT_DIR)
    report_path = _path(args.report, DEFAULT_REPORT)
    return load_json(config_path), load_json(sidecar_path), output_dir, report_path


def _publication_policy(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("publicationPolicy")
    return value if isinstance(value, dict) else {}


def _is_frozen_contract(config: dict[str, Any]) -> bool:
    return "publicationPolicy" in config or "selection" in config


def _enforce_frozen_contract(
    view: dict[str, Any] | None,
    config: dict[str, Any],
    report: dict[str, Any],
) -> None:
    # Legacy synthetic fixtures exercise the semantic engine through the CLI.
    # They predate the frozen config vocabulary and are not production contracts.
    if not _is_frozen_contract(config):
        return

    lifecycle = config.get("lifecycle") if isinstance(config.get("lifecycle"), dict) else {}
    policy = _publication_policy(config)
    frozen = str(lifecycle.get("status") or "") == "frozen"
    version = str(lifecycle.get("version") or "")
    _append_check(
        report,
        "ICE_REFERENCE_FROZEN_CONTRACT",
        "PASS" if frozen and version == "v1.0" else "ERROR",
        "ICEReferencePackage v1 is the frozen Chapter 29 publication contract."
        if frozen and version == "v1.0"
        else "Chapter 29 requires frozen ICEReferencePackage v1.",
        {"version": version, "status": lifecycle.get("status")},
    )

    if not bool(policy.get("requireFullCorpusSelection", False)) or view is None:
        return

    meta = view.get("package") if isinstance(view.get("package"), dict) else {}
    actual = int(meta.get("entryCount") or 0)
    full = int(meta.get("fullIceCount") or 0)
    try:
        expected_total = int(policy.get("expectedIceTotal"))
    except (TypeError, ValueError):
        expected_total = full

    groups = view.get("groups") if isinstance(view.get("groups"), list) else []
    actual_by_type = {
        str(group.get("iceType") or ""): len(group.get("entries") or [])
        for group in groups
        if isinstance(group, dict)
    }
    expected_by_type = policy.get("expectedIceCounts") if isinstance(policy.get("expectedIceCounts"), dict) else {}

    ok = actual == full == expected_total
    for ice_type, expected_count in expected_by_type.items():
        try:
            required = int(expected_count)
        except (TypeError, ValueError):
            continue
        if actual_by_type.get(str(ice_type)) != required:
            ok = False

    _append_check(
        report,
        "ICE_REFERENCE_FULL_CORPUS_SELECTION",
        "PASS" if ok else "ERROR",
        f"ICEReferencePackage v1 contains the complete {actual}-entry Step 4 ICE corpus."
        if ok
        else "ICEReferencePackage v1 requires the complete Step 4 ICE corpus.",
        {
            "selected": actual,
            "fullIceCount": full,
            "expectedTotal": expected_total,
            "selectedByType": actual_by_type,
            "expectedByType": expected_by_type,
        },
    )


def _compose(args: argparse.Namespace):
    config, sidecar, output_dir, report_path = _load_inputs(args)
    view, report, compat = compose_ice_reference_package(sidecar, config)
    attach_ice_reference_images(view, sidecar, compat, report)
    _enforce_frozen_contract(view, config, report)
    report["command"] = args.command
    report["packageScope"] = (
        "Frozen ICEReferencePackage v1 for Complete Rulebook Chapter 29. "
        "Consumes only Step 4 normalized ICE semantics and staged publication images; "
        "missing artwork uses the accepted blank identity fallback."
    )
    return config, sidecar, compat, view, report, output_dir, report_path


def _prepare_render_assets(view: dict[str, Any], output_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    render_root = output_dir / "_render-assets" / "ice"
    render_assets, asset_report = prepare_lualatex_render_assets(
        ice_reference_publication_images(view),
        DEFAULT_SOURCE_ROOT,
        render_root,
    )
    _append_check(
        report,
        "ICE_REFERENCE_RENDER_ASSETS",
        "PASS" if asset_report.get("status") == "PASS" else "ERROR",
        f"Prepared {asset_report.get('references', 0)} ICE publication image(s) for LuaLaTeX."
        if asset_report.get("status") == "PASS"
        else "ICE publication images could not be prepared for LuaLaTeX.",
        asset_report,
    )
    return render_assets


def _write_package_artifacts(
    view: dict[str, Any],
    config: dict[str, Any],
    output_dir: Path,
    render_assets: dict[str, str],
    report: dict[str, Any],
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    view_path = output_dir / VIEW_NAME
    tex_path = output_dir / TEX_NAME
    pdf_path = output_dir / PDF_NAME
    header_path = output_dir / HEADER_FRAGMENT_NAME
    body_path = output_dir / BODY_FRAGMENT_NAME

    _write_json(view_path, view)
    _append_check(report, "ICE_REFERENCE_VIEW", "PASS", f"Wrote ICEReferencePackage view to {view_path}.")

    standalone_tex = render_ice_reference_tex(view, config, render_assets)
    tex_path.write_text(standalone_tex, encoding="utf-8")
    header_latex, body_latex = render_integration_fragments(view, config, render_assets)
    header_path.write_text(header_latex + "\n", encoding="utf-8")
    body_path.write_text(body_latex + "\n", encoding="utf-8")

    # Preserve old synthetic CLI regression fixtures without restoring legacy
    # naming to the frozen production contract or default output tree.
    if not _is_frozen_contract(config):
        (output_dir / "Cybermancy_Chapter29_ICE_Reference_H2.tex").write_text(
            standalone_tex,
            encoding="utf-8",
        )

    _append_check(
        report,
        "ICE_REFERENCE_LATEX",
        "PASS",
        f"Wrote production Chapter 29 LaTeX and integration fragments to {output_dir}.",
        {
            "standalone": str(tex_path),
            "chapterHeader": str(header_path),
            "familyBody": str(body_path),
        },
    )
    return view_path, tex_path, pdf_path


def _integrate_ast(
    ast_input: Path,
    ast_output: Path,
    view: dict[str, Any],
    config: dict[str, Any],
    render_assets: dict[str, str],
    report: dict[str, Any],
) -> None:
    if not ast_input.is_file():
        _append_check(report, "ICE_REFERENCE_AST_INPUT", "ERROR", f"Pandoc AST input does not exist: {ast_input}")
        return
    try:
        ast = load_json(ast_input)
    except Exception as exc:
        _append_check(report, "ICE_REFERENCE_AST_INPUT", "ERROR", f"Could not read Pandoc AST input: {exc}")
        return

    header_latex, body_latex = render_integration_fragments(view, config, render_assets)
    counts = integrate_chapter29_ast(ast, header_latex, body_latex)
    ok = counts.get("chapterHeader") == 1 and counts.get("familyFeatures") == 1
    _append_check(
        report,
        "ICE_REFERENCE_AST_REPLACEMENT",
        "PASS" if ok else "ERROR",
        "Replaced Chapter 29 heading and family:features body with frozen ICEReferencePackage v1."
        if ok
        else "Chapter 29 AST integration did not find exactly one chapter heading and one family:features Div.",
        counts,
    )
    if not ok:
        return
    _write_json(ast_output, ast)
    _append_check(report, "ICE_REFERENCE_AST_OUTPUT", "PASS", f"Wrote Chapter 29 integrated Pandoc AST to {ast_output}.")


def _run(args: argparse.Namespace, verbose: bool) -> int:
    config, sidecar, compat, view, report, output_dir, report_path = _compose(args)

    if args.command == "inspect":
        if view is not None:
            report["inspection"] = {
                "chapter": view.get("chapter"),
                "entryCount": view.get("package", {}).get("entryCount"),
                "fullIceCount": view.get("package", {}).get("fullIceCount"),
                "groups": [
                    {
                        "iceType": row.get("iceType"),
                        "title": row.get("title"),
                        "entries": [
                            {
                                "name": entry.get("name"),
                                "image": entry.get("image"),
                                "imageFallback": entry.get("imageFallback"),
                            }
                            for entry in row.get("entries", [])
                            if isinstance(entry, dict)
                        ],
                    }
                    for row in view.get("groups", [])
                    if isinstance(row, dict)
                ],
            }
        return _emit(report, verbose)

    if args.command == "validate":
        _write_json(report_path, report)
        return _emit(report, verbose)

    if view is None or report.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, verbose)

    output_dir.mkdir(parents=True, exist_ok=True)
    render_assets = _prepare_render_assets(view, output_dir, report)
    if report.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, verbose)

    _view_path, tex_path, pdf_path = _write_package_artifacts(view, config, output_dir, render_assets, report)

    if args.command == "integrate":
        ast_input = _path(args.ast_input, Path(args.ast_input))
        ast_output = _path(args.ast_output, DEFAULT_AST_OUTPUT)
        _integrate_ast(ast_input, ast_output, view, config, render_assets, report)
        _write_json(report_path, report)
        return _emit(report, verbose)

    if args.tex_only:
        _append_check(report, "ICE_REFERENCE_PDF", "WARNING", "--tex-only requested; LuaLaTeX rendering was skipped.")
    else:
        ok, log = _compile_lualatex(tex_path)
        if ok and pdf_path.is_file():
            overfull = [
                line.strip()
                for line in log.splitlines()
                if "Overfull \\hbox" in line or "Overfull \\vbox" in line
            ]
            _append_check(report, "ICE_REFERENCE_PDF", "PASS", f"Rendered frozen Chapter 29 ICE Reference to {pdf_path}.")
            _append_check(
                report,
                "ICE_REFERENCE_LATEX_OVERFLOW",
                "ERROR" if overfull else "PASS",
                f"{len(overfull)} overfull LaTeX box warning(s) detected." if overfull else "No overfull LaTeX boxes detected.",
                overfull or None,
            )
            rendered = validate_ice_reference_pdf(pdf_path, view)
            _append_check(
                report,
                str(rendered.get("code") or "ICE_REFERENCE_RENDER_CONTENT"),
                str(rendered.get("status") or "ERROR"),
                str(rendered.get("message") or "Rendered content validation returned no message."),
                rendered.get("details"),
            )
        else:
            _append_check(
                report,
                "ICE_REFERENCE_PDF",
                "ERROR",
                "LuaLaTeX failed to render frozen Chapter 29 ICEReferencePackage v1.",
                log[-12000:],
            )

    _write_json(report_path, report)
    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Cybermancy ICEReferencePackage v1 production builder for Complete Rulebook Chapter 29. "
            "Consumes Step 4 normalized ICE semantics and staged publication images only."
        )
    )
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate", "build", "integrate"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="Frozen ICEReferencePackage v1 config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument("--report", help="Validation report JSON path.")
        if command in {"build", "integrate"}:
            p.add_argument("--output-dir", help="Chapter 29 production output directory.")
        if command == "build":
            p.add_argument("--tex-only", action="store_true", help="Generate production view/LaTeX but skip LuaLaTeX.")
        if command == "integrate":
            p.add_argument("--ast-input", required=True, help="Complete Rulebook Pandoc AST before Chapter 29 Step 6 replacement.")
            p.add_argument("--ast-output", help="Integrated Complete Rulebook Pandoc AST output path.")
    root.epilog = "Global option: --verbose may appear anywhere and prints the complete JSON report."
    return root


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    verbose = "--verbose" in raw
    raw = [value for value in raw if value != "--verbose"]
    try:
        args = parser().parse_args(raw)
        return _run(args, verbose)
    except SystemExit:
        raise
    except Exception as exc:
        report = {
            "status": "FAIL",
            "errors": [
                {
                    "code": "ICE_REFERENCE_BUILDER_EXCEPTION",
                    "status": "ERROR",
                    "message": str(exc),
                }
            ],
            "warnings": [],
            "checks": [],
        }
        return _emit(report, verbose)


if __name__ == "__main__":
    raise SystemExit(main())
