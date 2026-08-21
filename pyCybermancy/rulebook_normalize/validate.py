from __future__ import annotations
from pathlib import Path
import hashlib, json

def tree_hash_manifest(root: Path) -> list[dict]:
    records = []
    if not root.exists():
        return records
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({"path": path.relative_to(root).as_posix(), "sha256": h})
    return records

def compare_trees(a: Path, b: Path) -> bool:
    return tree_hash_manifest(a) == tree_hash_manifest(b)

def sum_expected_family_counts(config: dict) -> int:
    return sum(int(v["expected"]) for v in config["families"].values())

def new_report():
    return {"status": "PASS", "errors": [], "warnings": [], "checks": []}

def add_check(report, code, status, message, details=None):
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status == "ERROR":
        report["errors"].append(item)
        report["status"] = "FAIL"
    elif status == "BLOCKED":
        report["errors"].append(item)
        report["status"] = "BLOCKED" if report["status"] != "FAIL" else report["status"]
    elif status == "WARNING":
        report["warnings"].append(item)
    return item
