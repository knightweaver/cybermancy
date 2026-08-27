from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def evaluate_ice_reference_text(text: str, view: dict[str, Any]) -> dict[str, Any]:
    required: list[tuple[str, int]] = []
    for group in view.get("groups", []):
        if not isinstance(group, dict):
            continue
        title = str(group.get("title") or "").strip()
        if title:
            required.append((title, 1))
        for entry in group.get("entries", []):
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if name:
                required.append((name, 1))

    missing: list[str] = []
    duplicates: list[dict[str, Any]] = []
    positions: list[tuple[int, str]] = []
    for token, expected_count in required:
        count = text.count(token)
        if count < expected_count:
            missing.append(token)
        elif count > expected_count:
            duplicates.append({"token": token, "expected": expected_count, "actual": count})
        pos = text.find(token)
        if pos >= 0:
            positions.append((pos, token))

    order = [token for _, token in sorted(positions)]
    expected_order = [token for token, _ in required if token in text]
    order_ok = order == expected_order
    errors: list[str] = []
    if missing:
        errors.append("missing-content")
    if duplicates:
        errors.append("duplicate-content")
    if not order_ok:
        errors.append("content-order")

    return {
        "code": "ICE_REFERENCE_RENDER_CONTENT",
        "status": "ERROR" if errors else "PASS",
        "message": "Rendered ICEReferencePackage content regression failed." if errors else "Rendered ICEReferencePackage contains every group and proof entry exactly once in view order.",
        "details": {"missing": missing, "duplicates": duplicates, "expectedOrder": expected_order, "actualOrder": order},
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
