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


def _exact(lines: list[PdfLine], value: Any) -> list[PdfLine]:
    wanted = _normalize(value)
    return [line for line in lines if _normalize(line.text) == wanted]


def _starts(lines: list[PdfLine], value: Any, *, page: int | None = None) -> list[PdfLine]:
    wanted = _normalize(value)
    if not wanted:
        return []
    return [
        line
        for line in lines
        if (page is None or line.page == page) and _normalize(line.text).startswith(wanted)
    ]


def evaluate_domain_package_geometry(
    lines: list[PdfLine],
    view: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    expected_leading = float(style.get("cardBodyLeadingPt", 11.3) or 11.3)
    leading_min = max(7.0, expected_leading - 1.8)
    leading_max = expected_leading + 2.2

    details: dict[str, Any] = {
        "cardHeadings": [],
        "levelHeadings": [],
        "recallAssociations": [],
        "descriptionLineSpacing": [],
        "columnStarts": [],
        "cardsPerPage": {},
    }
    errors: list[str] = []

    levels = view.get("levels") if isinstance(view.get("levels"), list) else []
    cards = [
        card
        for level in levels
        if isinstance(level, dict)
        for card in (level.get("cards") if isinstance(level.get("cards"), list) else [])
        if isinstance(card, dict)
    ]

    heading_lines: list[PdfLine] = []
    for card in cards:
        name = str(card.get("name") or "")
        matches = _exact(lines, name)
        details["cardHeadings"].append(
            {"name": name, "count": len(matches), "pages": [line.page for line in matches]}
        )
        if len(matches) != 1:
            errors.append(f"Card heading {name!r} rendered {len(matches)} times; expected exactly once.")
            continue
        heading = matches[0]
        heading_lines.append(heading)
        details["cardsPerPage"].setdefault(str(heading.page), 0)
        details["cardsPerPage"][str(heading.page)] += 1

        meta_prefix = f"LEVEL {int(card.get('level') or 0)}"
        nearby_meta = [
            line
            for line in _starts(lines, meta_prefix, page=heading.page)
            if 0 <= line.y_min - heading.y_min <= 30.0
            and abs(line.x_min - heading.x_min) <= 45.0
        ]
        wanted_recall = f"recall cost {int(card.get('recallCost') or 0)}"
        meta_match = next(
            (line for line in nearby_meta if wanted_recall in _normalize(line.text)),
            None,
        )
        details["recallAssociations"].append(
            {
                "name": name,
                "page": heading.page,
                "matched": meta_match.text if meta_match else None,
            }
        )
        if meta_match is None:
            errors.append(
                f"Could not associate {name!r} with nearby LEVEL/RECALL COST metadata on the rendered page."
            )

        description = str(card.get("description") or "").strip()
        description_candidates = [
            line
            for line in _starts(lines, _prefix(description), page=heading.page)
            if line.y_min > heading.y_min and line.y_min - heading.y_min <= 125.0
        ]
        first = min(
            description_candidates,
            key=lambda line: (abs(line.x_min - heading.x_min), line.y_min),
            default=None,
        )
        if description and first is None:
            errors.append(f"Could not locate the first rendered description line for {name!r}.")
        elif first is not None:
            wrapped = sorted(
                [
                    line
                    for line in lines
                    if line.page == first.page
                    and line.y_min >= first.y_min
                    and line.y_min - first.y_min <= 70.0
                    and abs(line.x_min - first.x_min) <= 30.0
                ],
                key=lambda line: line.y_min,
            )
            if len(wrapped) >= 3:
                deltas = [
                    wrapped[i + 1].y_min - wrapped[i].y_min
                    for i in range(len(wrapped) - 1)
                    if 7.0 <= wrapped[i + 1].y_min - wrapped[i].y_min <= 18.0
                ]
                # The first baseline transition can include paragraph-top glue in
                # LuaLaTeX. Require an interior transition rather than treating a
                # two-line paragraph as a reliable leading measurement.
                sample = deltas[1:] if len(deltas) >= 2 else []
                if sample:
                    delta = min(sample, key=lambda value: abs(value - expected_leading))
                    details["descriptionLineSpacing"].append(
                        {"name": name, "page": first.page, "points": round(delta, 3)}
                    )
                    if not leading_min <= delta <= leading_max:
                        errors.append(
                            f"Card description leading for {name!r} is {delta:.2f} pt; "
                            f"expected {leading_min:.1f}-{leading_max:.1f} pt."
                        )

    level_positions: list[tuple[int, float, int]] = []
    for level in levels:
        if not isinstance(level, dict):
            continue
        value = int(level.get("level") or 0)
        matches = _exact(lines, f"LEVEL {value}")
        details["levelHeadings"].append(
            {"level": value, "count": len(matches), "pages": [line.page for line in matches]}
        )
        if len(matches) != 1:
            errors.append(f"Level heading LEVEL {value} rendered {len(matches)} times; expected exactly once.")
        else:
            level_positions.append((matches[0].page, matches[0].y_min, value))

    expected_levels = [
        int(level.get("level") or 0)
        for level in levels
        if isinstance(level, dict)
    ]
    if [item[2] for item in sorted(level_positions)] != expected_levels:
        errors.append("Rendered Level headings are not in the same ascending order as the DomainPackage view.")

    if len(heading_lines) >= 2:
        x_values = sorted({round(line.x_min, 1) for line in heading_lines})
        details["columnStarts"] = x_values
        if not any(b - a >= 120.0 for a in x_values for b in x_values if b > a):
            errors.append("Rendered Domain Cards do not occupy two distinct publication columns.")

    if heading_lines:
        first_page = min(line.page for line in heading_lines)
        last_page = max(line.page for line in heading_lines)
        empty_card_pages = [
            page
            for page in range(first_page, last_page + 1)
            if str(page) not in details["cardsPerPage"]
        ]
        if empty_card_pages:
            errors.append(
                "Rendered DomainPackage contains intermediate page(s) with no card headings: "
                + ", ".join(str(page) for page in empty_card_pages)
            )

    return {
        "code": "DOMAIN_PACKAGE_RENDER_GEOMETRY",
        "status": "ERROR" if errors else "PASS",
        "message": (
            f"Rendered DomainPackage geometry/content regression found {len(errors)} blocking issue(s)."
            if errors
            else "Rendered DomainPackage card headings, level order, recall metadata, body leading, and two-column flow are consistent."
        ),
        "details": {**details, "errors": errors} if errors else details,
    }


def validate_domain_package_pdf_geometry(
    pdf_path: Path,
    view: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lines, diagnostic = _extract_pdf_lines(pdf_path)
    if lines is None:
        return {
            "code": "DOMAIN_PACKAGE_RENDER_GEOMETRY",
            "status": "WARNING",
            "message": "Rendered geometry/content validation was skipped because pdftotext is unavailable.",
            "details": diagnostic,
        }
    if diagnostic is not None:
        return {
            "code": "DOMAIN_PACKAGE_RENDER_GEOMETRY",
            "status": "ERROR",
            "message": "Rendered geometry/content validation could not read the generated PDF.",
            "details": diagnostic,
        }
    return evaluate_domain_package_geometry(lines, view, config)
