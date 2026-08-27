#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package import compose_domain_package, load_json


DEFAULT_CONFIG = REPO_ROOT / "build/rulebook/layout/domains/domain-package-v1.json"
DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_REPORT = REPO_ROOT / "build/rulebook/layout/reports/domain-package-maker.json"
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
        errors = report.get("errors") or []
        if errors:
            print(json.dumps(errors, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


def _load_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, str]:
    config_path = _path(args.config, DEFAULT_CONFIG)
    sidecar_path = _path(args.sidecar, DEFAULT_SIDECAR)
    source_root = _path(args.source_root, DEFAULT_SOURCE_ROOT)
    report_path = _path(args.report, DEFAULT_REPORT)

    config = load_json(config_path)
    sidecar = load_json(sidecar_path)
    prototype = config.get("prototype") if isinstance(config.get("prototype"), dict) else {}
    domain_key = str(args.domain_key or prototype.get("domainKey") or "").strip().casefold()
    if not domain_key:
        raise ValueError("No Domain key was supplied by --domain-key or config prototype.domainKey.")

    return config, sidecar, source_root, report_path, domain_key


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
        "Standalone Step 6 DomainPackage semantic design proof consuming only Step 4 "
        "normalized Domain semantics and staged assets; LaTeX/PDF layout and Chapter 14 "
        "AST integration are intentionally deferred."
    )


def _run(args: argparse.Namespace, verbose: bool) -> int:
    config, sidecar, source_root, report_path, domain_key = _load_inputs(args)
    view, report = compose_domain_package(sidecar, source_root, domain_key, config)
    _decorate_report(report, args, source_root, domain_key)

    if args.command == "inspect" and view is not None:
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

    if args.command == "validate":
        _write_json(report_path, report)

    return _emit(report, verbose)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Cybermancy Step 6 DomainPackage semantic prototype validator. "
            "Consumes Step 4 normalized semantics only; rendering is not yet implemented."
        )
    )
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate"):
        p = sub.add_parser(command)
        p.add_argument("--config", help="DomainPackage Step 6 semantic prototype config.")
        p.add_argument("--sidecar", help="Step 4 structured-entities.json.")
        p.add_argument("--source-root", help="Step 4 build/rulebook/source root containing staged assets.")
        p.add_argument("--domain-key", help="Override prototype Domain key (for example maker).")
        p.add_argument("--report", help="Validation report JSON path.")
    root.epilog = (
        "Global option: --verbose may appear anywhere and prints the complete JSON report. "
        "A build command will be added with the visual-grammar implementation."
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
