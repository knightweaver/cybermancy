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

from rulebook_layout.ice_reference import compose_ice_reference, load_json
from rulebook_layout.ice_reference_geometry import validate_ice_reference_pdf
from rulebook_layout.ice_reference_images import (
    attach_ice_reference_images,
    ice_reference_publication_images,
)
from rulebook_layout.ice_reference_refined import render_ice_reference_tex
from rulebook_layout.render_assets import prepare_lualatex_render_assets

DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/ice/ice-reference-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build/rulebook/layout/ice-reference-prototype"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/ice-reference-package-h2.json"
SCRIPT_LABEL = SCRIPT_PATH.name


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
            cwd=str(tex_path.parent), text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
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


def _run(args: argparse.Namespace, verbose: bool) -> int:
    config, sidecar, output_dir, report_path = _load_inputs(args)
    view, report = compose_ice_reference(sidecar, config)
    attach_ice_reference_images(view, sidecar, config, report)
    report["command"] = args.command
    report["prototypeScope"] = (
        "Standalone Step H2 ICEReferencePackage design proof consuming only Step 4 normalized ICE semantics and staged publication images. "
        "Full Chapter 29/Pandoc integration is deferred until the proof grammar is visually accepted."
    )

    if args.command == "inspect":
        if view is not None:
            report["inspection"] = {
                "chapter": view.get("chapter"),
                "entryCount": view.get("prototype", {}).get("entryCount"),
                "fullIceCount": view.get("prototype", {}).get("fullIceCount"),
                "groups": [
                    {
                        "iceType": row.get("iceType"),
                        "title": row.get("title"),
                        "entries": [
                            {
                                "name": entry.get("name"),
                                "image": entry.get("image"),
                            }
                            for entry in row.get("entries", [])
                            if isinstance(entry, dict)
                        ],
                    }
                    for row in view.get("groups", []) if isinstance(row, dict)
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
    view_path = output_dir / "ice-reference-package-view.json"
    tex_path = output_dir / "Cybermancy_Chapter29_ICE_Reference_H2.tex"
    pdf_path = output_dir / "Cybermancy_Chapter29_ICE_Reference_H2.pdf"
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
        (
            f"Prepared {asset_report.get('references', 0)} ICE publication image(s) for LuaLaTeX."
            if asset_report.get("status") == "PASS"
            else "ICE publication images could not be prepared for LuaLaTeX."
        ),
        asset_report,
    )
    if report.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, verbose)

    _write_json(view_path, view)
    _append_check(report, "ICE_REFERENCE_VIEW", "PASS", f"Wrote composed ICEReferencePackage view to {view_path}.")
    tex_path.write_text(render_ice_reference_tex(view, config, render_assets), encoding="utf-8")
    _append_check(report, "ICE_REFERENCE_LATEX", "PASS", f"Wrote standalone H2 ICEReferencePackage LaTeX to {tex_path}.")

    if args.tex_only:
        _append_check(report, "ICE_REFERENCE_PDF", "WARNING", "--tex-only requested; LuaLaTeX rendering was skipped.")
    else:
        ok, log = _compile_lualatex(tex_path)
        if ok and pdf_path.is_file():
            overfull = [line.strip() for line in log.splitlines() if "Overfull \\hbox" in line or "Overfull \\vbox" in line]
            _append_check(report, "ICE_REFERENCE_PDF", "PASS", f"Rendered standalone H2 ICEReferencePackage proof to {pdf_path}.")
            _append_check(report, "ICE_REFERENCE_LATEX_OVERFLOW", "ERROR" if overfull else "PASS", f"{len(overfull)} overfull LaTeX box warning(s) detected." if overfull else "No overfull LaTeX boxes detected.", overfull or None)
            rendered = validate_ice_reference_pdf(pdf_path, view)
            _append_check(report, str(rendered.get("code") or "ICE_REFERENCE_RENDER_CONTENT"), str(rendered.get("status") or "ERROR"), str(rendered.get("message") or "Rendered content validation returned no message."), rendered.get("details"))
        else:
            _append_check(report, "ICE_REFERENCE_PDF", "ERROR", "LuaLaTeX failed to render the standalone H2 ICEReferencePackage proof.", log[-12000:])

    _write_json(report_path, report)
    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Cybermancy Step H2 ICEReferencePackage proof builder. Consumes Step 4 normalized ICE semantics and staged publication images only.")
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate", "build"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="ICEReferencePackage v1 H2 config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument("--report", help="Validation report JSON path.")
        if command == "build":
            p.add_argument("--output-dir", help="Standalone H2 proof output directory.")
            p.add_argument("--tex-only", action="store_true", help="Generate view-model JSON and LaTeX but skip LuaLaTeX.")
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
        report = {"status": "FAIL", "errors": [{"code": "ICE_REFERENCE_BUILDER_EXCEPTION", "status": "ERROR", "message": str(exc)}], "warnings": [], "checks": []}
        return _emit(report, verbose)


if __name__ == "__main__":
    raise SystemExit(main())
