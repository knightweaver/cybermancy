from __future__ import annotations

import json
from typing import Any


def _report_payload(payload: Any) -> dict:
    if not isinstance(payload, dict):
        return {}
    nested = payload.get("report")
    if isinstance(nested, dict) and "status" in nested:
        return nested
    return payload


def extract_errors(payload: Any) -> list[Any]:
    """Return the report errors that matter to a concise CLI failure."""
    report = _report_payload(payload)
    errors = report.get("errors") if isinstance(report, dict) else None
    return list(errors) if isinstance(errors, list) else []


def emit_result(payload: Any, *, verbose: bool, returncode: int | None = None) -> None:
    """Emit full historical JSON in verbose mode, otherwise PASS/FAIL only.

    Concise failures retain the structured error list so the operator can see
    why the command failed without scrolling through successful checks, inputs,
    rows, warnings, and other diagnostic detail.
    """
    if verbose:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    report = _report_payload(payload)
    status = str(report.get("status") or "").upper() if report else ""
    failed = (returncode is not None and returncode != 0) or status == "FAIL"
    print("FAIL" if failed else "PASS")
    if failed:
        errors = extract_errors(payload)
        if errors:
            print(json.dumps(errors, indent=2, ensure_ascii=False))


def parse_captured_payload(text: str) -> Any:
    value = str(text or "").strip()
    if not value:
        return {}
    return json.loads(value)
