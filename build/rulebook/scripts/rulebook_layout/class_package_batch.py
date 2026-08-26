from __future__ import annotations

import re
from typing import Any


def slugify_class_name(name: Any) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(name or "").casefold()).strip("-")
    return value or "class"


def class_package_output_stem(name: Any) -> str:
    words = re.findall(r"[A-Za-z0-9]+", str(name or "Class"))
    safe = "_".join(words) or "Class"
    return f"Cybermancy_Chapter12_{safe}_ClassPackage_Step6"


def discover_class_package_targets(sidecar: dict[str, Any]) -> list[dict[str, str]]:
    rows = sidecar.get("entities")
    if not isinstance(rows, list):
        raise ValueError("Step 4 sidecar has no entities array.")

    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or str(row.get("family") or "") != "classes":
            continue
        semantic_id = str(row.get("semanticId") or "").strip()
        name = str(row.get("name") or "").strip()
        if not semantic_id:
            raise ValueError("Class entity is missing semanticId.")
        if not name:
            raise ValueError(f"Class entity {semantic_id} is missing name.")
        if semantic_id in seen:
            raise ValueError(f"Duplicate Class semanticId in Step 4 sidecar: {semantic_id}")
        seen.add(semantic_id)
        targets.append(
            {
                "semanticId": semantic_id,
                "name": name,
                "slug": slugify_class_name(name),
                "outputStem": class_package_output_stem(name),
            }
        )

    if not targets:
        raise ValueError("Step 4 sidecar contains no Class entities.")

    targets.sort(key=lambda row: (row["name"].casefold(), row["semanticId"]))
    return targets
