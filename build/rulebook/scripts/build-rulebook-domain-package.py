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

from rulebook_layout.domain_package import compose_domain_package, load_json
from rulebook_layout.domain_package_geometry import validate_domain_package_pdf_geometry
from rulebook_layout.domain_package_refined import (
    domain_package_output_stem,
    domain_package_view_filename,
    render_domain_package_tex,
)


DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/domains/domain-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build/rulebook/layout/domain-package-prototype"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/domain-package-maker.json"
SCRIPT_LABEL = SCRIPT_PATH.name
REQUIRED_LATEX_PACKAGES = {
    "multicol.sty": "multicol",
    "needspace.sty": "needspace",
}


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
            "code": "DOMAIN_PACKAGE_LATEX_DEPENDENCIES",
            "status": "ERROR",
            "message": f"Required DomainPackage LaTeX package(s) are not installed: {names}.",
            "details": details,
        }
    if unknown:
        return {
            "code": "DOMAIN_PACKAGE_LATEX_DEPENDENCIES",
            "status": "WARNING",
            "message": (
                "Could not preflight all DomainPackage LaTeX dependencies because neither kpsewhich nor "
                "findtexmf was available; LuaLaTeX will resolve them during compilation."
            ),
            "details": details,
        }
    return {
        "code": "DOMAIN_PACKAGE_LATEX_DEPENDENCIES",
        "status": "PASS",
        "message": "Required DomainPackage LaTeX package dependencies are available.",
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


def _load_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, Path, str]:
    config_path = _path(args.config, DEFAULT_CONFIG)
    sidecar_path = _path(args.sidecar, DEFAULT_SIDECAR)
    source_root = _path(args.source_root, DEFAULT_SOURCE_ROOT)
    output_dir = _path(getattr(args, "output_dir", None), DEFAULT_OUTPUT_DIR)
    report_path = _path(args.report, DEFAULT_REPORT)

    config = load_json(config_path)
    sidecar = load_json(sidecar_path)
    prototype = config.get("prototype") if isinstance(config.get("prototype"), dict) else {}
    domain_key = str(args.domain_key or prototype.get("domainKey") or "").strip().casefold()
    if not domain_key:
        raise ValueError("No Domain key was supplied by --domain-key or config prototype.domainKey.")

    return config, sidecar, source_root, output_dir, report_path, domain_key


def _decorate_report(
    report: dict[str, Any],
    args: argparse.Namespace,
    source_root: Path,
    domain_key: str,
) -> None:
    report["command"] = args.command
    report["domainKey"] = domain_key
    report["sourceRoot"] = str(source_root)
    report["prototypeScope"] = (
        "Standalone Step 6 DomainPackage design proof consuming only Step 4 normalized Domain semantics "
        "and staged assets. Full Chapter 14/Pandoc AST integration remains deferred until the Maker "
        "visual grammar is accepted."
    )


def _run(args: argparse.Namespace, verbose: bool) -> int:
    config, sidecar, source_root, output_dir, report_path, domain_key = _load_inputs(args)
    view, report = compose_domain_package(sidecar, source_root, domain_key, config)
    _decorate_report(report, args, source_root, domain_key)

    if args.command == "inspect":
        if view is not None:
            report["inspection"] = {
                "domain": view.get("domain", {}).get("name"),
                "cardCount": view.get("domain", {}).get("cardCount"),
                "levels": [
                    {
                        "level": row.get("level"),
                        "cardCount": len(row.get("cards", [])),
                        "cards": [card.get("name") for card in row.get("cards", [])],
                    }
                    for row in view.get("levels", [])
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
    domain_name = str(view.get("domain", {}).get("name") or domain_key.title())
    stem = domain_package_output_stem(domain_name)
    view_path = output_dir / domain_package_view_filename(domain_name)
    tex_path = output_dir / f"{stem}.tex"
    pdf_path = output_dir / f"{stem}.pdf"

    _write_json(view_path, view)
    tex_path.write_text(
        render_domain_package_tex(view, config, source_root, output_dir),
        encoding="utf-8",
    )
    _append_check(
        report,
        "DOMAIN_PACKAGE_VIEW",
        "PASS",
        f"Wrote composed DomainPackage view to {view_path}.",
    )
    _append_check(
        report,
        "DOMAIN_PACKAGE_LATEX",
        "PASS",
        f"Wrote standalone DomainPackage prototype LaTeX to {tex_path}.",
    )

    if args.tex_only:
        _append_check(
            report,
            "DOMAIN_PACKAGE_PDF",
            "WARNING",
            "--tex-only requested; LuaLaTeX rendering was skipped.",
        )
    else:
        dependency = _preflight_latex_dependencies(tex_path)
        _append_check(
            report,
            str(dependency.get("code") or "DOMAIN_PACKAGE_LATEX_DEPENDENCIES"),
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
            _append_check(
                report,
                "DOMAIN_PACKAGE_PDF",
                "PASS",
                f"Rendered standalone DomainPackage prototype to {pdf_path}.",
            )
            _append_check(
                report,
                "DOMAIN_PACKAGE_LATEX_OVERFLOW",
                "ERROR" if overfull else "PASS",
                f"{len(overfull)} overfull LaTeX box warning(s) detected."
                if overfull
                else "No overfull LaTeX boxes detected.",
                overfull or None,
            )
            geometry = validate_domain_package_pdf_geometry(pdf_path, view, config)
            _append_check(
                report,
                str(geometry.get("code") or "DOMAIN_PACKAGE_RENDER_GEOMETRY"),
                str(geometry.get("status") or "ERROR"),
                str(geometry.get("message") or "Rendered geometry/content validation returned no message."),
                geometry.get("details"),
            )
        else:
            _append_check(
                report,
                "DOMAIN_PACKAGE_PDF",
                "ERROR",
                "LuaLaTeX failed to render the standalone DomainPackage prototype.",
                log[-12000:],
            )

    _write_json(report_path, report)
    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Cybermancy Step 6 DomainPackage prototype builder. Consumes Step 4 normalized semantics only."
    )
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate", "build"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="DomainPackage Step 6 prototype config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument(
            "--source-root",
            help="Step 4 build/rulebook/source root containing staged assets.",
        )
        p.add_argument("--domain-key", help="Override prototype Domain key (for example maker).")
        p.add_argument("--report", help="Validation report JSON path.")
        if command == "build":
            p.add_argument("--output-dir", help="Standalone prototype output directory.")
            p.add_argument(
                "--tex-only",
                action="store_true",
                help="Generate view-model JSON and LaTeX but skip LuaLaTeX.",
            )
    root.epilog = (
        "Global option: --verbose may appear anywhere and prints the complete JSON report."
    )
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
                    "code": "DOMAIN_PACKAGE_EXCEPTION",
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
