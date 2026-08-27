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
CHILD = SCRIPT_DIR / "build-rulebook-domain-package.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package import load_json
from rulebook_layout.domain_package_batch import discover_domain_package_targets

DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/domains/domain-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build/rulebook/layout/domain-packages"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/domain-packages-all.json"
DEFAULT_REPORT_DIR = REPO_ROOT / "build/rulebook/layout/reports/domain-packages"
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
        failures = [row for row in report.get("domains", []) if row.get("status") != "PASS"]
        if failures:
            print(json.dumps(failures, indent=2, ensure_ascii=False))
        elif report.get("errors"):
            print(json.dumps(report["errors"], indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


def _child_command(
    command: str,
    target: dict[str, Any],
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
        "--domain-key",
        str(target["domainKey"]),
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
    per_domain_report_dir = _path(getattr(args, "report_dir", None), DEFAULT_REPORT_DIR)

    sidecar = load_json(sidecar_path)
    targets = discover_domain_package_targets(sidecar)
    total_cards = sum(int(row.get("cardCount") or 0) for row in targets)
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-domain-package-batch-report-v1.0",
        "status": "PASS",
        "command": args.command,
        "targetCount": len(targets),
        "cardCount": total_cards,
        "domains": [],
        "outputDirectory": str(output_dir),
        "step6Scope": (
            "Apply the visually accepted Maker DomainPackage publication grammar unchanged to every DomainPackage "
            "in the Step 4 semantic corpus. Chapter 14/Pandoc integration remains deferred until all-Domain "
            "regression and visual review are accepted."
        ),
    }

    if args.command == "inspect":
        report["domains"] = [dict(target, status="PASS") for target in targets]
        return _emit(report, verbose)

    output_dir.mkdir(parents=True, exist_ok=True)
    per_domain_report_dir.mkdir(parents=True, exist_ok=True)

    passed = 0
    failed = 0
    for target in targets:
        domain_report_path = per_domain_report_dir / f"{target['slug']}.json"
        command = _child_command(
            args.command,
            target,
            config=config_path,
            sidecar=sidecar_path,
            source_root=source_root,
            output_dir=output_dir,
            report_path=domain_report_path,
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

        domain_report: dict[str, Any] = {}
        if domain_report_path.is_file():
            try:
                loaded = json.loads(domain_report_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    domain_report = loaded
            except (OSError, json.JSONDecodeError):
                domain_report = {}

        child_status = str(domain_report.get("status") or "PASS")
        status = "PASS" if proc.returncode == 0 and child_status == "PASS" else "FAIL"
        row: dict[str, Any] = {
            **target,
            "status": status,
            "report": str(domain_report_path),
        }
        if args.command == "build":
            row["pdf"] = str(output_dir / f"{target['outputStem']}.pdf")
            row["tex"] = str(output_dir / f"{target['outputStem']}.tex")
            row["view"] = str(output_dir / f"{target['slug']}-domain-package-view.json")

        if status == "PASS":
            passed += 1
            if verbose and domain_report:
                row["warnings"] = domain_report.get("warnings", [])
                row["checks"] = [
                    item
                    for item in domain_report.get("checks", [])
                    if isinstance(item, dict)
                    and item.get("code")
                    in {
                        "DOMAIN_PACKAGE_RENDER_ASSETS",
                        "DOMAIN_PACKAGE_PDF",
                        "DOMAIN_PACKAGE_LATEX_OVERFLOW",
                        "DOMAIN_PACKAGE_RENDER_GEOMETRY",
                    }
                ]
        else:
            failed += 1
            report["status"] = "FAIL"
            row["childOutput"] = (proc.stdout or "")[-12000:]
            if domain_report:
                row["errors"] = domain_report.get("errors", [])
        report["domains"].append(row)

    report["summary"] = {
        "domains": len(targets),
        "cards": total_cards,
        "passed": passed,
        "failed": failed,
    }
    _write_json(aggregate_report_path, report)
    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Build or validate the accepted Step 6 DomainPackage grammar across every DomainPackage "
            "discovered in the Step 4 corpus."
        )
    )
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate", "build"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="Accepted DomainPackage Step 6 config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument("--source-root", help="Step 4 build/rulebook/source root containing staged assets.")
        p.add_argument("--report", help="Aggregate all-Domain report JSON path.")
        if command != "inspect":
            p.add_argument("--report-dir", help="Directory for per-Domain validation reports.")
        if command == "build":
            p.add_argument("--output-dir", help="Directory for all generated DomainPackage artifacts.")
            p.add_argument(
                "--tex-only",
                action="store_true",
                help="Generate view-model JSON and LaTeX for every Domain but skip LuaLaTeX.",
            )
    root.epilog = (
        "Global option: --verbose may appear anywhere and prints the aggregate JSON report instead of terse PASS/FAIL output."
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
        return _emit(
            {
                "schema": "cybermancy-step6-domain-package-batch-report-v1.0",
                "status": "FAIL",
                "domains": [],
                "errors": [
                    {
                        "code": "DOMAIN_PACKAGE_BATCH_EXCEPTION",
                        "status": "ERROR",
                        "message": f"{type(exc).__name__}: {exc}",
                    }
                ],
            },
            verbose,
        )


if __name__ == "__main__":
    raise SystemExit(main())
