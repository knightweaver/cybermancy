from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .orchestrator import build_profile
from .reporting import add_check, new_report, timestamp, write_json


def compare_signatures(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(first) | set(second))
    comparisons = {
        key: {"first": first.get(key), "second": second.get(key), "equal": first.get(key) == second.get(key)}
        for key in keys
    }
    return {
        "status": "PASS" if all(item["equal"] for item in comparisons.values()) else "FAIL",
        "comparisons": comparisons,
    }


def run_reproducibility(
    repo_root: Path,
    profile: str,
    report_path: Path,
    *,
    builder: Callable[..., dict[str, Any]] = build_profile,
) -> dict[str, Any]:
    report = new_report(
        "cybermancy-production-reproducibility-v1",
        profile=profile,
        buildTimestamp=timestamp(),
        contract="semantic-and-render-structure-equivalence",
    )
    first = builder(repo_root, profile)
    if first.get("status") != "PASS":
        add_check(report, "FIRST_BUILD", "FAIL", "First clean production build failed.")
        write_json(report_path, report)
        return report
    second = builder(repo_root, profile)
    if second.get("status") != "PASS":
        add_check(report, "SECOND_BUILD", "FAIL", "Second clean production build failed.")
        write_json(report_path, report)
        return report
    comparison = compare_signatures(first.get("signature", {}), second.get("signature", {}))
    report["comparison"] = comparison
    add_check(
        report,
        "REPRODUCIBILITY",
        comparison["status"],
        "Repeated clean builds have equivalent semantic and rendered structure."
        if comparison["status"] == "PASS"
        else "Repeated clean builds produced unexplained semantic or rendered-structure drift.",
        comparison["comparisons"],
    )
    write_json(report_path, report)
    return report
