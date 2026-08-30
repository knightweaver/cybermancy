#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rulebook_production import PROFILES
from rulebook_production.baseline import run_baseline_check
from rulebook_production.contract import load_production_contract
from rulebook_production.orchestrator import build_profile
from rulebook_production.preflight import run_preflight
from rulebook_production.reproducibility import run_reproducibility
from rulebook_production.reporting import write_json
from rulebook_production.workspace import invalidate_release


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[3]


def _selected_profiles(value: str) -> tuple[str, ...]:
    return PROFILES if value == "all" else (value,)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Cybermancy Production Renderer v1")
    subcommands = root.add_subparsers(dest="command", required=True)

    baseline = subcommands.add_parser(
        "baseline-check", help="Verify the code/freeze maintenance baseline without rendering."
    )
    baseline.add_argument("--verbose", action="store_true")

    preflight = subcommands.add_parser("preflight", help="Validate production readiness without rendering.")
    preflight.add_argument("--verbose", action="store_true")

    build = subcommands.add_parser("build", help="Build one or both production profiles.")
    build.add_argument("--profile", choices=[*PROFILES, "all"], required=True)
    build.add_argument("--verbose", action="store_true")

    reproducibility = subcommands.add_parser(
        "reproducibility", help="Run two clean builds and compare semantic/render structure."
    )
    reproducibility.add_argument("--profile", choices=[*PROFILES, "all"], required=True)
    reproducibility.add_argument("--verbose", action="store_true")
    return root


def _emit(report: dict, verbose: bool) -> None:
    if verbose or report.get("status") != "PASS":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"build-rulebook.py: {report['status']}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "baseline-check":
        report = run_baseline_check(REPO_ROOT)
        _emit(report, args.verbose)
        return 0 if report["status"] == "PASS" else 2

    contract = load_production_contract(REPO_ROOT)
    report_root = REPO_ROOT / contract["workspace"]["reportRoot"]
    if args.command != "preflight":
        for profile in _selected_profiles(args.profile):
            invalidate_release(REPO_ROOT, contract, profile)
    preflight_report = run_preflight(REPO_ROOT, report_root / "preflight.json")
    if args.command == "preflight":
        _emit(preflight_report, args.verbose)
        return 0 if preflight_report["status"] == "PASS" else 2
    if preflight_report["status"] != "PASS":
        _emit(preflight_report, args.verbose)
        return 2

    results = []
    for profile in _selected_profiles(args.profile):
        if args.command == "build":
            result = build_profile(REPO_ROOT, profile)
        else:
            result = run_reproducibility(
                REPO_ROOT,
                profile,
                report_root / profile / "reproducibility.json",
            )
        results.append(result)
    aggregate = {
        "schema": "cybermancy-production-command-result-v1",
        "status": "PASS" if all(item.get("status") == "PASS" for item in results) else "FAIL",
        "command": args.command,
        "profiles": [item.get("profile") for item in results],
        "results": results,
    }
    write_json(report_root / f"{args.command}-{args.profile}.json", aggregate)
    _emit(aggregate, args.verbose)
    return 0 if aggregate["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
