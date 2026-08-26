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


def _find_line(lines: list[PdfLine], prefix: str, *, page: int | None = None) -> PdfLine | None:
    wanted = _normalize(prefix)
    if not wanted:
        return None
    for line in lines:
        if page is not None and line.page != page:
            continue
        if _normalize(line.text).startswith(wanted):
            return line
    return None


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


def evaluate_class_package_geometry(lines: list[PdfLine], view: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {"descriptionLineSpacing": [], "startingPackageBaselines": []}
    errors: list[str] = []

    cls = view.get("class") if isinstance(view.get("class"), dict) else {}
    class_description = str(cls.get("description") or "")
    class_first = _find_line(lines, _prefix(class_description), page=1)
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
    for subclass in subclasses:
        description = str(subclass.get("description") or "").strip()
        if not description:
            description = "No subclass lead text is currently supplied by Step 4."
        first = _find_line(lines, _prefix(description), page=2)
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

    for label, value in _starting_package_pairs(cls):
        label_line = _find_line(lines, label, page=1)
        value_line = _find_line(lines, _prefix(value, words=3), page=1)
        if label_line is None or value_line is None:
            errors.append(f"Could not locate rendered Starting Package pair: {label} / {value}.")
            continue
        delta = abs(label_line.y_min - value_line.y_min)
        details["startingPackageBaselines"].append(
            {"label": label, "value": value, "deltaPoints": round(delta, 3)}
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
            else "Rendered ClassPackage description leading and Starting Package baselines are aligned."
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
