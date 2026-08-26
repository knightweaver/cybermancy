#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
CHILD = SCRIPT_DIR / "build-rulebook-class-package.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.class_package import load_json
from rulebook_layout.class_package_batch import discover_class_package_targets

DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/classes/class-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build/rulebook/layout/class-packages"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/class-packages-all.json"
DEFAULT_REPORT_DIR = REPO_ROOT / "build/rulebook/layout/reports/class-packages"
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


def _emit(report: dict[str, Any], verbose: bool) -> int:
    status = str(report.get("status") or "FAIL")
    if verbose:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif status == "PASS":
        print(f"{SCRIPT_LABEL}: PASS")
    else:
        print(f"{SCRIPT_LABEL}: FAIL")
        failures = [row for row in report.get("classes", []) if row.get("status") != "PASS"]
        if failures:
            print(json.dumps(failures, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


def _child_command(
    command: str,
    target: dict[str, str],
    *,
    config: Path,
    sidecar: Path,
    source_root: Path,
    output_dir: Path,
    report_path: Path,
    tex_only: bool,
) -> list[str]:
    values = [
        sys.executable,
        str(CHILD),
        command,
        "--config",
        str(config),
        "--sidecar",
        str(sidecar),
        "--source-root",
        str(source_root),
        "--class-id",
        target["semanticId"],
        "--report",
        str(report_path),
    ]
    if command == "build":
        values.extend(["--output-dir", str(output_dir)])
        if tex_only:
            values.append("--tex-only")
    return values


def _run(args: argparse.Namespace, verbose: bool) -> int:
    config_path = _path(args.config, DEFAULT_CONFIG)
    sidecar_path = _path(args.sidecar, DEFAULT_SIDECAR)
    source_root = _path(args.source_root, DEFAULT_SOURCE_ROOT)
    output_dir = _path(getattr(args, "output_dir", None), DEFAULT_OUTPUT_DIR)
    aggregate_report_path = _path(args.report, DEFAULT_REPORT)
    per_class_report_dir = _path(getattr(args, "report_dir", None), DEFAULT_REPORT_DIR)

    sidecar = load_json(sidecar_path)
    targets = discover_class_package_targets(sidecar)
    report: dict[str, Any] = {
        "status": "PASS",
        "command": args.command,
        "targetCount": len(targets),
        "classes": [],
        "outputDirectory": str(output_dir),
        "step6Scope": (
            "Apply the accepted Razz Hacker ClassPackage publication grammar to every Class in the Step 4 semantic corpus. "
            "Full Chapter 12/Pandoc AST integration remains a subsequent step."
        ),
    }

    if args.command == "inspect":
        report["classes"] = [dict(target, status="PASS") for target in targets]
        return _emit(report, verbose)

    output_dir.mkdir(parents=True, exist_ok=True)
    per_class_report_dir.mkdir(parents=True, exist_ok=True)

    for target in targets:
        class_report_path = per_class_report_dir / f"{target['slug']}.json"
        command = _child_command(
            args.command,
            target,
            config=config_path,
            sidecar=sidecar_path,
            source_root=source_root,
            output_dir=output_dir,
            report_path=class_report_path,
            tex_only=bool(getattr(args, "tex_only", False)),
        )
        proc = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        class_report: dict[str, Any] = {}
        if class_report_path.is_file():
            try:
                loaded = json.loads(class_report_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    class_report = loaded
            except (OSError, json.JSONDecodeError):
                class_report = {}

        status = "PASS" if proc.returncode == 0 and str(class_report.get("status") or "PASS") == "PASS" else "FAIL"
        row: dict[str, Any] = {
            **target,
            "status": status,
            "report": str(class_report_path),
        }
        if args.command == "build":
            row["pdf"] = str(output_dir / f"{target['outputStem']}.pdf")
            row["tex"] = str(output_dir / f"{target['outputStem']}.tex")
            row["view"] = str(output_dir / f"{target['slug']}-class-package-view.json")
        if status != "PASS":
            report["status"] = "FAIL"
            row["childOutput"] = (proc.stdout or "")[-12000:]
            if class_report:
                row["errors"] = class_report.get("errors", [])
        elif verbose and class_report:
            row["warnings"] = class_report.get("warnings", [])
        report["classes"].append(row)

    _write_json(aggregate_report_path, report)
    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Build or validate the accepted Step 6 ClassPackage grammar across every Class in the Step 4 corpus."
    )
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate", "build"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="Accepted ClassPackage Step 6 config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument("--source-root", help="Step 4 build/rulebook/source root containing staged assets.")
        p.add_argument("--report", help="Aggregate all-Class report JSON path.")
        if command != "inspect":
            p.add_argument("--report-dir", help="Directory for per-Class validation reports.")
        if command == "build":
            p.add_argument("--output-dir", help="Directory for all generated ClassPackage artifacts.")
            p.add_argument("--tex-only", action="store_true", help="Generate view-model JSON and LaTeX for every Class but skip LuaLaTeX.")
    root.epilog = "Global option: --verbose may appear anywhere and prints the aggregate JSON report instead of terse PASS/FAIL output."
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
        return _emit(
            {
                "status": "FAIL",
                "classes": [],
                "errors": [
                    {
                        "code": "CLASS_PACKAGE_BATCH_EXCEPTION",
                        "status": "ERROR",
                        "message": f"{type(exc).__name__}: {exc}",
                    }
                ],
            },
            verbose,
        )


if __name__ == "__main__":
    raise SystemExit(main())
