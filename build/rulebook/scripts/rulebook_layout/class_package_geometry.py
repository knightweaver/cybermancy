from __future__ import annotations

import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PdfLine:
    page: int
    text: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\u00ad", "")
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014"):
        text = text.replace(dash, "-")
    return " ".join(text.split()).casefold()


def _prefix(value: Any, words: int = 5) -> str:
    return " ".join(_normalize(value).split()[:words])


def _extract_pdf_lines(pdf_path: Path) -> tuple[list[PdfLine] | None, str | None]:
    exe = shutil.which("pdftotext")
    if not exe:
        return None, "pdftotext was not found on PATH."

    proc = subprocess.run(
        [exe, "-bbox-layout", str(pdf_path), "-"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return [], (proc.stderr or proc.stdout or "pdftotext failed.")[-6000:]

    try:
        root = ET.fromstring(proc.stdout)
    except ET.ParseError as exc:
        return [], f"Could not parse pdftotext bbox-layout output: {exc}"

    lines: list[PdfLine] = []
    pages = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "page"]
    for page_number, page in enumerate(pages, start=1):
        for line in page.iter():
            if line.tag.rsplit("}", 1)[-1] != "line":
                continue
            words = [
                node
                for node in line.iter()
                if node.tag.rsplit("}", 1)[-1] == "word" and (node.text or "").strip()
            ]
            text = " ".join((word.text or "").strip() for word in words).strip()
            if not text:
                continue
            try:
                lines.append(
                    PdfLine(
                        page=page_number,
                        text=text,
                        x_min=float(line.attrib["xMin"]),
                        y_min=float(line.attrib["yMin"]),
                        x_max=float(line.attrib["xMax"]),
                        y_max=float(line.attrib["yMax"]),
                    )
                )
            except (KeyError, ValueError):
                continue
    return lines, None


def _find_lines(lines: list[PdfLine], prefix: str, *, page: int | None = None) -> list[PdfLine]:
    wanted = _normalize(prefix)
    if not wanted:
        return []
    return [
        line
        for line in lines
        if (page is None or line.page == page) and _normalize(line.text).startswith(wanted)
    ]


def _find_line(lines: list[PdfLine], prefix: str, *, page: int | None = None) -> PdfLine | None:
    matches = _find_lines(lines, prefix, page=page)
    return matches[0] if matches else None


def _next_wrapped_line(lines: list[PdfLine], first: PdfLine) -> PdfLine | None:
    candidates = [
        line
        for line in lines
        if line.page == first.page
        and line.y_min > first.y_min
        and line.y_min - first.y_min <= 22.0
        and abs(line.x_min - first.x_min) <= 28.0
    ]
    return min(candidates, key=lambda line: line.y_min, default=None)


def _rendered_trait_text(traits: dict[str, Any]) -> str:
    return ", ".join(f"{str(name).title()} {value}" for name, value in traits.items())


def _starting_package_pairs(cls: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    class_items = cls.get("classItems") if isinstance(cls.get("classItems"), list) else []
    if class_items:
        pairs.append(("Class Items", str(class_items[0].get("name") or "")))

    inventory = cls.get("startingInventory") if isinstance(cls.get("startingInventory"), dict) else {}
    for key, label in (("take", "Take"), ("choiceA", "Choice A"), ("choiceB", "Choice B")):
        values = inventory.get(key) if isinstance(inventory.get(key), list) else []
        if values:
            pairs.append((label, str(values[0].get("name") or "")))

    guide = cls.get("characterGuide") if isinstance(cls.get("characterGuide"), dict) else {}
    for key, label in (
        ("suggestedPrimaryWeapon", "Suggested Weapon"),
        ("suggestedSecondaryWeapon", "Secondary Weapon"),
        ("suggestedArmor", "Suggested Armor"),
    ):
        value = guide.get(key)
        if isinstance(value, dict) and value.get("name"):
            pairs.append((label, str(value.get("name"))))
    traits = guide.get("suggestedTraits")
    if isinstance(traits, dict) and traits:
        pairs.append(("Suggested Traits", _rendered_trait_text(traits)))
    return pairs


def _line_position(line: PdfLine) -> tuple[int, float]:
    return line.page, line.y_min


def _starting_package_scope(lines: list[PdfLine]) -> list[PdfLine]:
    """Limit package matching to the rendered Starting Package section.

    Short labels such as ``Take`` can legitimately occur in feature prose on an
    earlier page. Starting Package may now share a page with the Subclass spread,
    so scope by both page and vertical position rather than excluding the entire
    first Subclass page.
    """
    header = next((line for line in lines if _normalize(line.text) == "starting package"), None)
    if header is None:
        return lines

    subclass_markers = [
        line
        for line in lines
        if _normalize(line.text) == "subclass" and _line_position(line) > _line_position(header)
    ]
    end = min(subclass_markers, key=_line_position, default=None)

    scoped: list[PdfLine] = []
    for line in lines:
        position = _line_position(line)
        if position < _line_position(header):
            continue
        if line.page == header.page and line.y_min < header.y_min:
            continue
        if end is not None and position >= _line_position(end):
            continue
        scoped.append(line)
    return scoped


def _find_best_package_pair(lines: list[PdfLine], label: str, value: str) -> tuple[PdfLine | None, PdfLine | None]:
    label_lines = _find_lines(lines, label)
    value_lines = _find_lines(lines, _prefix(value, words=3))
    if not label_lines or not value_lines:
        return (label_lines[0] if label_lines else None, value_lines[0] if value_lines else None)

    same_page = [
        (abs(label_line.y_min - value_line.y_min), label_line.page, label_line.y_min, label_line, value_line)
        for label_line in label_lines
        for value_line in value_lines
        if label_line.page == value_line.page
    ]
    if same_page:
        _, _, _, label_line, value_line = min(same_page, key=lambda item: item[:3])
        return label_line, value_line

    return label_lines[0], value_lines[0]


def _subclass_description_text(subclass: dict[str, Any]) -> str:
    description = str(subclass.get("description") or "").strip()
    return description or "No subclass lead text is currently supplied by Step 4."


def evaluate_class_package_geometry(lines: list[PdfLine], view: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {
        "descriptionLineSpacing": [],
        "startingPackageBaselines": [],
        "subclassParallelStarts": [],
    }
    errors: list[str] = []

    cls = view.get("class") if isinstance(view.get("class"), dict) else {}
    class_description = str(cls.get("description") or "")
    class_first = _find_line(lines, _prefix(class_description))
    if class_first is None:
        errors.append("Could not locate the first rendered Class-description line.")
    else:
        class_next = _next_wrapped_line(lines, class_first)
        if class_next is not None:
            delta = class_next.y_min - class_first.y_min
            details["descriptionLineSpacing"].append(
                {"owner": str(cls.get("name") or "Class"), "page": class_first.page, "points": round(delta, 3)}
            )
            if not 10.0 <= delta <= 13.8:
                errors.append(f"Class description first-line spacing is {delta:.2f} pt; expected 10.0-13.8 pt.")

    subclasses = view.get("subclasses") if isinstance(view.get("subclasses"), list) else []
    subclass_first_lines: list[tuple[dict[str, Any], PdfLine | None]] = []
    for subclass in subclasses:
        description = _subclass_description_text(subclass)
        first = _find_line(lines, _prefix(description))
        subclass_first_lines.append((subclass, first))
        if first is None:
            errors.append(f"Could not locate the first rendered Subclass-description line for {subclass.get('name')}.")
            continue
        next_line = _next_wrapped_line(lines, first)
        if next_line is None:
            continue
        delta = next_line.y_min - first.y_min
        details["descriptionLineSpacing"].append(
            {"owner": str(subclass.get("name") or "Subclass"), "page": first.page, "points": round(delta, 3)}
        )
        if not 10.0 <= delta <= 13.8:
            errors.append(
                f"Subclass description first-line spacing for {subclass.get('name')} is {delta:.2f} pt; expected 10.0-13.8 pt."
            )

    for offset in range(0, len(subclass_first_lines) - 1, 2):
        left_subclass, left = subclass_first_lines[offset]
        right_subclass, right = subclass_first_lines[offset + 1]
        if left is None or right is None:
            continue
        page_aligned = left.page == right.page
        horizontal_delta = abs(left.x_min - right.x_min) if page_aligned else None
        details["subclassParallelStarts"].append(
            {
                "left": str(left_subclass.get("name") or "Subclass"),
                "right": str(right_subclass.get("name") or "Subclass"),
                "leftPage": left.page,
                "rightPage": right.page,
                "xDeltaPoints": round(horizontal_delta, 3) if horizontal_delta is not None else None,
            }
        )
        if not page_aligned:
            errors.append(
                "Subclass pair did not begin in parallel columns: "
                f"{left_subclass.get('name')} begins on page {left.page}, while "
                f"{right_subclass.get('name')} begins on page {right.page}."
            )
        elif horizontal_delta is not None and horizontal_delta < 100.0:
            errors.append(
                "Subclass pair did not begin in distinct parallel columns: "
                f"{left_subclass.get('name')} / {right_subclass.get('name')} first-line x positions differ by "
                f"only {horizontal_delta:.2f} pt."
            )

    package_lines = _starting_package_scope(lines)
    for label, value in _starting_package_pairs(cls):
        label_line, value_line = _find_best_package_pair(package_lines, label, value)
        if label_line is None or value_line is None:
            errors.append(f"Could not locate rendered Starting Package pair: {label} / {value}.")
            continue
        if label_line.page != value_line.page:
            errors.append(
                f"Starting Package label/value pair {label} / {value} rendered on different pages."
            )
            continue
        delta = abs(label_line.y_min - value_line.y_min)
        details["startingPackageBaselines"].append(
            {"label": label, "value": value, "page": label_line.page, "deltaPoints": round(delta, 3)}
        )
        if delta > 1.5:
            errors.append(
                f"Starting Package label/value baselines for {label} differ by {delta:.2f} pt; expected at most 1.5 pt."
            )

    return {
        "code": "CLASS_PACKAGE_RENDER_GEOMETRY",
        "status": "ERROR" if errors else "PASS",
        "message": (
            f"Rendered ClassPackage geometry found {len(errors)} blocking alignment issue(s)."
            if errors
            else "Rendered ClassPackage description leading, parallel Subclass starts, and Starting Package baselines are aligned."
        ),
        "details": {**details, "errors": errors} if errors else details,
    }


def validate_class_package_pdf_geometry(pdf_path: Path, view: dict[str, Any]) -> dict[str, Any]:
    lines, diagnostic = _extract_pdf_lines(pdf_path)
    if lines is None:
        return {
            "code": "CLASS_PACKAGE_RENDER_GEOMETRY",
            "status": "WARNING",
            "message": "Rendered geometry validation was skipped because pdftotext is unavailable.",
            "details": diagnostic,
        }
    if diagnostic is not None:
        return {
            "code": "CLASS_PACKAGE_RENDER_GEOMETRY",
            "status": "ERROR",
            "message": "Rendered geometry validation could not read the generated PDF.",
            "details": diagnostic,
        }
    return evaluate_class_package_geometry(lines, view)
