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
    text = text.replace("\u00ad", "").replace("\u00a0", " ").replace("\u200b", "")
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014"):
        text = text.replace(dash, "-")
    for quote in ("\u2018", "\u2019", "\u2032"):
        text = text.replace(quote, "'")
    for quote in ("\u201c", "\u201d", "\u2033"):
        text = text.replace(quote, '"')
    text = text.replace("\u2026", "...")
    return " ".join(text.split()).casefold()


def _loose_normalize(value: Any) -> str:
    """Normalize extractor-sensitive punctuation around otherwise stable prose."""
    text = _normalize(value)
    return text.lstrip(" \t\r\n'\"`*_([{<.!?:;,-")


def _prefix(value: Any, words: int = 5, *, loose: bool = False) -> str:
    normalized = _loose_normalize(value) if loose else _normalize(value)
    return " ".join(normalized.split()[:words])


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


def _starts_loose(lines: list[PdfLine], value: Any, *, page: int | None = None) -> list[PdfLine]:
    wanted = _loose_normalize(value)
    if not wanted:
        return []
    return [
        line
        for line in lines
        if (page is None or line.page == page)
        and _loose_normalize(line.text).startswith(wanted)
    ]


def _partition_start_indexes(count: int, columns: int) -> list[int]:
    columns = max(1, columns)
    base, extra = divmod(count, columns)
    sizes = [base + (1 if index < extra else 0) for index in range(columns)]
    starts: list[int] = []
    offset = 0
    for size in sizes:
        if size:
            starts.append(offset)
        offset += size
    return starts


def _cluster_x(values: list[float], tolerance: float = 10.0) -> list[float]:
    clusters: list[list[float]] = []
    for value in sorted(values):
        if not clusters or abs(value - sum(clusters[-1]) / len(clusters[-1])) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [round(sum(cluster) / len(cluster), 1) for cluster in clusters]


def _nearby_card_meta(
    lines: list[PdfLine],
    heading: PdfLine,
    level: int,
    recall: int,
) -> tuple[PdfLine | None, PdfLine | None]:
    level_prefix = f"LEVEL {level}"
    recall_prefix = f"RECALL COST {recall}"
    level_lines = [
        line
        for line in _starts(lines, level_prefix, page=heading.page)
        if 0 <= line.y_min - heading.y_min <= 65.0
        and abs(line.x_min - heading.x_min) <= 70.0
    ]
    combined = next(
        (
            line
            for line in level_lines
            if f"recall cost {recall}" in _normalize(line.text)
        ),
        None,
    )
    if combined is not None:
        return combined, combined

    recall_lines = [
        line
        for line in _starts(lines, recall_prefix, page=heading.page)
        if 0 <= line.y_min - heading.y_min <= 80.0
        and abs(line.x_min - heading.x_min) <= 70.0
    ]
    return (level_lines[0] if level_lines else None, recall_lines[0] if recall_lines else None)


def _card_heading_matches(
    lines: list[PdfLine],
    name: str,
    level: int,
    recall: int,
) -> list[PdfLine]:
    exact = _exact(lines, name)
    candidates = exact
    if not candidates:
        word_count = len(_normalize(name).split())
        for words in (min(2, word_count), 1):
            if words <= 0:
                continue
            candidates = _starts(lines, _prefix(name, words))
            if candidates:
                break

    qualified: list[PdfLine] = []
    for candidate in candidates:
        level_line, recall_line = _nearby_card_meta(lines, candidate, level, recall)
        if level_line is not None and recall_line is not None:
            qualified.append(candidate)
    return qualified or candidates


def _description_first_line(
    lines: list[PdfLine],
    heading: PdfLine,
    description: str,
) -> PdfLine | None:
    if not description.strip():
        return None
    for words in (5, 4, 3, 2, 1):
        prefix = _prefix(description, words)
        if prefix:
            candidates = [
                line
                for line in _starts(lines, prefix, page=heading.page)
                if 0 < line.y_min - heading.y_min <= 180.0
                and abs(line.x_min - heading.x_min) <= 120.0
            ]
            if candidates:
                return min(
                    candidates,
                    key=lambda line: (abs(line.x_min - heading.x_min), line.y_min),
                )

        loose_prefix = _prefix(description, words, loose=True)
        if loose_prefix:
            candidates = [
                line
                for line in _starts_loose(lines, loose_prefix, page=heading.page)
                if 0 < line.y_min - heading.y_min <= 180.0
                and abs(line.x_min - heading.x_min) <= 120.0
            ]
            if candidates:
                return min(
                    candidates,
                    key=lambda line: (abs(line.x_min - heading.x_min), line.y_min),
                )
    return None


def evaluate_domain_package_geometry(
    lines: list[PdfLine],
    view: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    minimum_font = float(style.get("minimumCardTextFontPt", 10.5) or 10.5)
    body_font = max(minimum_font, float(style.get("cardBodyFontPt", minimum_font) or minimum_font))
    expected_leading = max(
        body_font + 1.6,
        float(style.get("cardBodyLeadingPt", body_font + 1.6) or (body_font + 1.6)),
    )
    leading_min = max(7.0, expected_leading - 1.5)
    leading_max = expected_leading + 1.8
    requested_columns = max(1, int(composition.get("pageColumns") or 3))
    top_tolerance = float(style.get("columnTopAlignmentTolerancePt", 2.0) or 2.0)

    details: dict[str, Any] = {
        "minimumCardTextFontPt": minimum_font,
        "cardBodyFontPt": body_font,
        "cardBodyLeadingPt": expected_leading,
        "cardHeadings": [],
        "levelHeadings": [],
        "recallAssociations": [],
        "descriptionLineSpacing": [],
        "descriptionLineSpacingSkipped": [],
        "columnStarts": [],
        "columnTopAlignment": [],
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
    heading_by_name: dict[str, PdfLine] = {}
    descriptions_expected = 0
    for card in cards:
        name = str(card.get("name") or "")
        level = int(card.get("level") or 0)
        recall = int(card.get("recallCost") or 0)
        matches = _card_heading_matches(lines, name, level, recall)
        details["cardHeadings"].append(
            {"name": name, "count": len(matches), "pages": [line.page for line in matches]}
        )
        if len(matches) != 1:
            errors.append(f"Card heading {name!r} rendered {len(matches)} times; expected exactly once.")
            continue
        heading = matches[0]
        heading_lines.append(heading)
        heading_by_name[name] = heading
        details["cardsPerPage"].setdefault(str(heading.page), 0)
        details["cardsPerPage"][str(heading.page)] += 1

        level_line, recall_line = _nearby_card_meta(lines, heading, level, recall)
        matched = None
        if level_line is not None and recall_line is not None:
            matched = (
                level_line.text
                if level_line is recall_line
                else f"{level_line.text} / {recall_line.text}"
            )
        details["recallAssociations"].append(
            {
                "name": name,
                "page": heading.page,
                "matched": matched,
            }
        )
        if matched is None:
            errors.append(
                f"Could not associate {name!r} with nearby LEVEL/RECALL COST metadata on the rendered page."
            )

        description = str(card.get("description") or "").strip()
        if description:
            descriptions_expected += 1
        first = _description_first_line(lines, heading, description)
        if description and first is None:
            details["descriptionLineSpacingSkipped"].append(
                {
                    "name": name,
                    "page": heading.page,
                    "reason": "first rendered description line could not be anchored reliably",
                }
            )
        elif first is not None:
            wrapped = sorted(
                [
                    line
                    for line in lines
                    if line.page == first.page
                    and line.y_min >= first.y_min
                    and line.y_min - first.y_min <= 90.0
                    and abs(line.x_min - first.x_min) <= 35.0
                ],
                key=lambda line: line.y_min,
            )
            deltas = [
                wrapped[i + 1].y_min - wrapped[i].y_min
                for i in range(len(wrapped) - 1)
                if 7.0 <= wrapped[i + 1].y_min - wrapped[i].y_min <= 20.0
            ]
            if deltas:
                delta = deltas[0]
                details["descriptionLineSpacing"].append(
                    {"name": name, "page": first.page, "points": round(delta, 3)}
                )
                if not leading_min <= delta <= leading_max:
                    errors.append(
                        f"Card description first-line spacing for {name!r} is {delta:.2f} pt; "
                        f"expected {leading_min:.1f}-{leading_max:.1f} pt."
                    )
            elif description:
                details["descriptionLineSpacingSkipped"].append(
                    {
                        "name": name,
                        "page": first.page,
                        "reason": "description did not contain two measurable rendered baselines",
                    }
                )

    if descriptions_expected and not details["descriptionLineSpacing"]:
        errors.append(
            "Rendered DomainPackage contains card descriptions but no measurable first-to-second-line body-leading sample."
        )

    level_positions: list[tuple[int, float, int]] = []
    max_cards_in_level = 0
    for level in levels:
        if not isinstance(level, dict):
            continue
        value = int(level.get("level") or 0)
        level_cards = [card for card in (level.get("cards") or []) if isinstance(card, dict)]
        max_cards_in_level = max(max_cards_in_level, len(level_cards))
        raw_matches = _exact(lines, f"LEVEL {value}")
        divider = min(raw_matches, key=lambda line: (line.x_min, line.page, line.y_min), default=None)
        details["levelHeadings"].append(
            {
                "level": value,
                "count": 1 if divider is not None else 0,
                "rawCount": len(raw_matches),
                "pages": [divider.page] if divider is not None else [],
            }
        )
        if divider is None:
            errors.append(f"Level heading LEVEL {value} rendered 0 times; expected exactly once.")
        else:
            level_positions.append((divider.page, divider.y_min, value))

        starts = _partition_start_indexes(len(level_cards), requested_columns)
        first_lines = [
            heading_by_name.get(str(level_cards[index].get("name") or ""))
            for index in starts
        ]
        first_lines = [line for line in first_lines if line is not None]
        if len(first_lines) >= 2:
            pages = {line.page for line in first_lines}
            y_values = [line.y_min for line in first_lines]
            max_delta = max(y_values) - min(y_values)
            details["columnTopAlignment"].append(
                {
                    "level": value,
                    "activeColumns": len(first_lines),
                    "pages": sorted(pages),
                    "yMinPoints": [round(y, 3) for y in y_values],
                    "maxDeltaPoints": round(max_delta, 3),
                }
            )
            if len(pages) != 1 or max_delta > top_tolerance:
                errors.append(
                    f"LEVEL {value} column tops are not aligned: active column headings span "
                    f"pages {sorted(pages)} with {max_delta:.2f} pt vertical delta; "
                    f"expected at most {top_tolerance:.2f} pt."
                )

    expected_levels = [
        int(level.get("level") or 0)
        for level in levels
        if isinstance(level, dict)
    ]
    if [item[2] for item in sorted(level_positions)] != expected_levels:
        errors.append("Rendered Level headings are not in the same ascending order as the DomainPackage view.")

    if heading_lines:
        x_values = _cluster_x([line.x_min for line in heading_lines])
        details["columnStarts"] = x_values
        active_expected = min(requested_columns, max_cards_in_level)
        if active_expected >= 2 and len(x_values) < active_expected:
            errors.append(
                f"Rendered Domain Cards occupy {len(x_values)} distinct column start(s); "
                f"expected {active_expected} from the configured {requested_columns}-column grammar."
            )

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
            else (
                "Rendered DomainPackage card headings, level order, recall metadata, sampled first-line body leading, "
                f"and {requested_columns}-column top alignment are consistent."
            )
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
