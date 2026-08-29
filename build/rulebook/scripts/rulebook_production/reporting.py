from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_report(schema: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": schema,
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        **fields,
    }


def add_check(
    report: dict[str, Any],
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status == "FAIL":
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status == "WARNING":
        report["warnings"].append(item)


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
