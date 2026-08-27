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

from rulebook_layout.class_package import compose_class_package, load_json
from rulebook_layout.class_package_batch import class_package_output_stem, slugify_class_name
from rulebook_layout.class_package_geometry import validate_class_package_pdf_geometry
from rulebook_layout.class_package_refined import render_class_package_tex

DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/classes/class-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build/rulebook/layout/class-package-prototype"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/class-package-razz-hacker.json"
SCRIPT_LABEL = SCRIPT_PATH.name
REQUIRED_LATEX_PACKAGES = {"paracol.sty": "paracol"}


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


def _probe_latex_package(package_file: str) -> tuple[bool | None, list[dict[str, Any]]]:
    probes: list[dict[str, Any]] = []
    for tool in ("kpsewhich", "findtexmf"):
        exe = shutil.which(tool)
        if not exe:
            continue
        proc = subprocess.run(
            [exe, package_file],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        probes.append(
            {
                "tool": tool,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        if proc.returncode == 0 and stdout:
            return True, probes
    if probes:
        return False, probes
    return None, probes


def _preflight_latex_dependencies(tex_path: Path) -> dict[str, Any]:
    source = tex_path.read_text(encoding="utf-8")
    required = [
        package_file
        for package_file, package_name in REQUIRED_LATEX_PACKAGES.items()
        if rf"\usepackage{{{package_name}}}" in source
    ]
    details: dict[str, Any] = {"required": required, "packages": []}
    if not required:
        return {
            "code": "CLASS_PACKAGE_LATEX_DEPENDENCIES",
            "status": "PASS",
            "message": "No additional ClassPackage LaTeX package dependencies were detected.",
            "details": details,
        }

    missing: list[str] = []
    unknown: list[str] = []
    for package_file in required:
        available, probes = _probe_latex_package(package_file)
        details["packages"].append(
            {
                "package": package_file,
                "available": available,
                "probes": probes,
            }
        )
        if available is False:
            missing.append(package_file)
        elif available is None:
            unknown.append(package_file)

    if missing:
        names = ", ".join(REQUIRED_LATEX_PACKAGES[name] for name in missing)
        return {
            "code": "CLASS_PACKAGE_LATEX_DEPENDENCIES",
            "status": "ERROR",
            "message": (
                "Required ClassPackage LaTeX package(s) are not installed: "
                f"{names}. Install them in MiKTeX/TeX Live before rebuilding."
            ),
            "details": details,
        }
    if unknown:
        return {
            "code": "CLASS_PACKAGE_LATEX_DEPENDENCIES",
            "status": "WARNING",
            "message": (
                "Could not preflight all ClassPackage LaTeX dependencies because neither kpsewhich nor "
                "findtexmf was available; LuaLaTeX will resolve them during compilation."
            ),
            "details": details,
        }
    return {
        "code": "CLASS_PACKAGE_LATEX_DEPENDENCIES",
        "status": "PASS",
        "message": "Required ClassPackage LaTeX package dependencies are available.",
        "details": details,
    }


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


def _load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], Path, Path, Path, str]:
    config_path = _path(args.config, DEFAULT_CONFIG)
    sidecar_path = _path(args.sidecar, DEFAULT_SIDECAR)
    source_root = _path(args.source_root, DEFAULT_SOURCE_ROOT)
    output_dir = _path(getattr(args, "output_dir", None), DEFAULT_OUTPUT_DIR)
    report_path = _path(args.report, DEFAULT_REPORT)

    config = load_json(config_path)
    sidecar = load_json(sidecar_path)
    prototype = config.get("prototype") if isinstance(config.get("prototype"), dict) else {}
    class_semantic_id = str(args.class_id or prototype.get("classSemanticId") or "").strip()
    if not class_semantic_id:
        raise ValueError("No Class semantic ID was supplied by --class-id or config prototype.classSemanticId.")

    return config, sidecar, source_root, output_dir, report_path, class_semantic_id


def _decorate_report(
    report: dict[str, Any],
    args: argparse.Namespace,
    source_root: Path,
    class_semantic_id: str,
) -> None:
    report["command"] = args.command
    report["classSemanticId"] = class_semantic_id
    report["sourceRoot"] = str(source_root)
    report["prototypeScope"] = (
        "Standalone Step 6 ClassPackage design proof consuming only Step 4 normalized semantics; "
        "Pandoc AST/chapter replacement is intentionally deferred until the ClassPackage grammar is accepted."
    )


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


def _run(args: argparse.Namespace, verbose: bool) -> int:
    config, sidecar, source_root, output_dir, report_path, class_semantic_id = _load_inputs(args)
    view, report = compose_class_package(sidecar, source_root, class_semantic_id, config)
    _decorate_report(report, args, source_root, class_semantic_id)

    if args.command == "inspect":
        if view is not None:
            report["inspection"] = {
                "class": view.get("class", {}).get("name"),
                "subclasses": [row.get("name") for row in view.get("subclasses", [])],
                "classFeatureCounts": {
                    key: len(value)
                    for key, value in (view.get("class", {}).get("features") or {}).items()
                    if isinstance(value, list)
                },
                "subclassProgressionCounts": {
                    row.get("name"): {
                        key: len(value)
                        for key, value in (row.get("progression") or {}).items()
                        if isinstance(value, list)
                    }
                    for row in view.get("subclasses", [])
                },
            }
        return _emit(report, verbose)

    if args.command == "validate":
        _write_json(report_path, report)
        return _emit(report, verbose)

    if view is None or report.get("status") != "PASS":
        _write_json(report_path, report)
        return _emit(report, verbose)

    output_dir.mkdir(parents=True, exist_ok=True)
    class_name = str(view.get("class", {}).get("name") or "Class")
    slug = slugify_class_name(class_name)
    stem = class_package_output_stem(class_name)
    view_path = output_dir / f"{slug}-class-package-view.json"
    tex_path = output_dir / f"{stem}.tex"
    pdf_path = output_dir / f"{stem}.pdf"

    _write_json(view_path, view)
    tex_path.write_text(render_class_package_tex(view, config, source_root, output_dir), encoding="utf-8")
    _append_check(report, "CLASS_PACKAGE_VIEW", "PASS", f"Wrote composed ClassPackage view to {view_path}.")
    _append_check(report, "CLASS_PACKAGE_LATEX", "PASS", f"Wrote standalone ClassPackage prototype LaTeX to {tex_path}.")

    if args.tex_only:
        _append_check(report, "CLASS_PACKAGE_PDF", "WARNING", "--tex-only requested; LuaLaTeX rendering was skipped.")
    else:
        dependency = _preflight_latex_dependencies(tex_path)
        _append_check(
            report,
            str(dependency.get("code") or "CLASS_PACKAGE_LATEX_DEPENDENCIES"),
            str(dependency.get("status") or "ERROR"),
            str(dependency.get("message") or "LaTeX dependency preflight returned no message."),
            dependency.get("details"),
        )
        if report.get("status") != "PASS":
            _write_json(report_path, report)
            return _emit(report, verbose)

        ok, log = _compile_lualatex(tex_path)
        if ok and pdf_path.is_file():
            overfull = [
                line.strip()
                for line in log.splitlines()
                if "Overfull \\hbox" in line or "Overfull \\vbox" in line
            ]
            _append_check(report, "CLASS_PACKAGE_PDF", "PASS", f"Rendered standalone ClassPackage prototype to {pdf_path}.")
            _append_check(
                report,
                "CLASS_PACKAGE_LATEX_OVERFLOW",
                "ERROR" if overfull else "PASS",
                f"{len(overfull)} overfull LaTeX box warning(s) detected."
                if overfull
                else "No overfull LaTeX boxes detected.",
                overfull or None,
            )
            geometry = validate_class_package_pdf_geometry(pdf_path, view)
            _append_check(
                report,
                str(geometry.get("code") or "CLASS_PACKAGE_RENDER_GEOMETRY"),
                str(geometry.get("status") or "ERROR"),
                str(geometry.get("message") or "Rendered geometry validation returned no message."),
                geometry.get("details"),
            )
        else:
            _append_check(
                report,
                "CLASS_PACKAGE_PDF",
                "ERROR",
                "LuaLaTeX failed to render the standalone ClassPackage prototype.",
                log[-12000:],
            )

    _write_json(report_path, report)
    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Cybermancy Step 6 ClassPackage prototype builder. Consumes Step 4 normalized semantics only."
    )
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate", "build"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="ClassPackage Step 6 prototype config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument("--source-root", help="Step 4 build/rulebook/source root containing staged assets.")
        p.add_argument("--class-id", help="Override prototype Class semantic ID.")
        p.add_argument("--report", help="Validation report JSON path.")
        if command == "build":
            p.add_argument("--output-dir", help="Standalone prototype output directory.")
            p.add_argument("--tex-only", action="store_true", help="Generate view-model JSON and LaTeX but skip LuaLaTeX.")
    root.epilog = "Global option: --verbose may appear anywhere and prints the full JSON report instead of terse PASS/FAIL output."
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
                    "code": "CLASS_PACKAGE_EXCEPTION",
                    "status": "ERROR",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            ],
            "warnings": [],
            "checks": [],
        }
        return _emit(report, verbose)


if __name__ == "__main__":
    raise SystemExit(main())
