from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def evaluate_ice_reference_text(text: str, view: dict[str, Any]) -> dict[str, Any]:
    required: list[str] = []
    for group in view.get("groups", []):
        if not isinstance(group, dict):
            continue
        title = str(group.get("title") or "").strip()
        if title:
            required.append(title)
        for entry in group.get("entries", []):
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if name:
                required.append(name)

    missing: list[str] = []
    positions: list[tuple[int, str]] = []
    for token in required:
        pos = text.find(token)
        if pos < 0:
            missing.append(token)
        else:
            positions.append((pos, token))

    actual_order = [token for _, token in sorted(positions)]
    expected_order = [token for token in required if token not in missing]
    order_ok = actual_order == expected_order

    errors: list[str] = []
    if missing:
        errors.append("missing-content")
    if not order_ok:
        errors.append("content-order")

    return {
        "code": "ICE_REFERENCE_RENDER_CONTENT",
        "status": "ERROR" if errors else "PASS",
        "message": (
            "Rendered ICEReferencePackage content regression failed."
            if errors
            else "Rendered ICEReferencePackage contains every group and proof entry heading with first occurrences in view order."
        ),
        "details": {
            "missing": missing,
            "expectedOrder": expected_order,
            "actualOrder": actual_order,
        },
    }


def validate_ice_reference_pdf(pdf_path: Path, view: dict[str, Any]) -> dict[str, Any]:
    exe = shutil.which("pdftotext")
    if not exe:
        return {
            "code": "ICE_REFERENCE_RENDER_CONTENT",
            "status": "WARNING",
            "message": "pdftotext was not found on PATH; rendered content regression was skipped.",
            "details": {"pdf": str(pdf_path)},
        }
    proc = subprocess.run(
        [exe, "-layout", str(pdf_path), "-"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return {
            "code": "ICE_REFERENCE_RENDER_CONTENT",
            "status": "ERROR",
            "message": "pdftotext failed while validating the rendered ICEReferencePackage proof.",
            "details": {"returncode": proc.returncode, "stderr": (proc.stderr or "")[-4000:]},
        }
    return evaluate_ice_reference_text(proc.stdout or "", view)
