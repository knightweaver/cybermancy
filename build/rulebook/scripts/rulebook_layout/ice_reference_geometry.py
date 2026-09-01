from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


REQUIRED_SHELL_TOKENS = (
    "CYBERMANCY // ICE REFERENCE",
    "GM MATERIAL",
)
FORBIDDEN_READER_TOKENS = (
    "resource: simple",
    "target: any",
    "hitpoints",
    "simple; value",
)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def evaluate_ice_reference_text(text: str, view: dict[str, Any]) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    required: list[str] = []
    for group in view.get("groups", []):
        if not isinstance(group, dict):
            continue
        title = str(group.get("title") or "").strip()
        entries = [
            str(entry.get("name") or "").strip()
            for entry in group.get("entries", [])
            if isinstance(entry, dict) and str(entry.get("name") or "").strip()
        ]
        if not title:
            continue
        groups.append({"title": title, "entries": entries})
        required.append(title)
        required.extend(entries)

    missing = [token for token in required if text.find(token) < 0]

    # The standalone proof uses multi-column group bodies. pdftotext -layout can
    # interleave entry text from those columns when line wrapping changes, so
    # flattened entry order is not a stable rendering invariant. Group headings,
    # however, remain sequential publication boundaries and are stable selectors.
    group_positions: list[tuple[int, str]] = []
    for group in groups:
        title = str(group["title"])
        pos = text.find(title)
        if pos >= 0:
            group_positions.append((pos, title))
    expected_group_order = [str(group["title"]) for group in groups if str(group["title"]) not in missing]
    actual_group_order = [title for _, title in sorted(group_positions)]
    group_order_ok = actual_group_order == expected_group_order

    position_by_group = {title: pos for pos, title in group_positions}
    misplaced_entries: list[dict[str, str]] = []
    for index, group in enumerate(groups):
        title = str(group["title"])
        start = position_by_group.get(title)
        if start is None:
            continue
        next_starts = [
            position_by_group[str(later["title"])]
            for later in groups[index + 1 :]
            if str(later["title"]) in position_by_group
        ]
        end = min(next_starts) if next_starts else len(text)
        for entry in group["entries"]:
            if entry in missing:
                continue
            if text.find(entry, start, end) < 0:
                misplaced_entries.append({"entry": entry, "expectedGroup": title})

    normalized_upper = _normalized(text).upper()
    missing_shell = [token for token in REQUIRED_SHELL_TOKENS if token not in normalized_upper]
    normalized_casefold = _normalized(text).casefold()
    forbidden_rendered = [token for token in FORBIDDEN_READER_TOKENS if token.casefold() in normalized_casefold]

    errors: list[str] = []
    if missing:
        errors.append("missing-content")
    if not group_order_ok:
        errors.append("group-order")
    if misplaced_entries:
        errors.append("entry-group")
    if missing_shell:
        errors.append("missing-rulebook-shell")
    if forbidden_rendered:
        errors.append("reader-metadata-leakage")

    return {
        "code": "ICE_REFERENCE_RENDER_CONTENT",
        "status": "ERROR" if errors else "PASS",
        "message": (
            "Rendered ICEReferencePackage content/style regression failed."
            if errors
            else "Rendered ICEReferencePackage contains every entry within its canonical group, the groups in order, the Cybermancy GM shell, and no prohibited runtime metadata."
        ),
        "details": {
            "missing": missing,
            "expectedGroupOrder": expected_group_order,
            "actualGroupOrder": actual_group_order,
            "misplacedEntries": misplaced_entries,
            "missingShell": missing_shell,
            "forbiddenRendered": forbidden_rendered,
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
