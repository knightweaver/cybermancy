from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

from rulebook_layout.publication_shell import PARTS, PROFILE_PART_IDS
from rulebook_layout.unified_lualatex import _run_utf8, sha256_file


STAGE_NAME = "rendered-regression"
STAGE_ORDER = 170
LETTER_WIDTH_PT = 612.0
LETTER_HEIGHT_PT = 792.0
PAGE_SIZE_TOLERANCE_PT = 1.0
BOUND_TOLERANCE_PT = 0.5
EDGE_WARNING_PT = 2.0


def contract_stage(contract: dict[str, Any]) -> dict[str, Any] | None:
    rows = [
        row
        for row in contract.get("transformationOrder", [])
        if isinstance(row, dict) and row.get("stage") == STAGE_NAME
    ]
    return rows[0] if len(rows) == 1 else None


def stage160_pdf_hash(report: dict[str, Any]) -> str:
    for value in (
        report.get("outputPdfSha256"),
        (report.get("pdfOutput") or {}).get("sha256")
        if isinstance(report.get("pdfOutput"), dict)
        else None,
        (report.get("compilation") or {}).get("pdfSha256")
        if isinstance(report.get("compilation"), dict)
        else None,
    ):
        text = str(value or "").strip()
        if text:
            return text
    for check in report.get("checks") or []:
        if not isinstance(check, dict) or check.get("code") != "STAGE160_PDF_OUTPUT":
            continue
        details = check.get("details")
        if isinstance(details, dict):
            text = str(details.get("sha256") or "").strip()
            if text:
                return text
    return ""


def deferred_output_vboxes(report: dict[str, Any]) -> list[str]:
    compilation = report.get("compilation")
    if isinstance(compilation, dict):
        diagnostics = compilation.get("diagnostics")
        if isinstance(diagnostics, dict):
            values = diagnostics.get("outputRoutineVboxes")
            if isinstance(values, list):
                return sorted({str(value) for value in values if str(value).strip()})
    for check in report.get("checks") or []:
        if not isinstance(check, dict) or check.get("code") != "STAGE160_OUTPUT_ROUTINE_VBOXES":
            continue
        details = check.get("details")
        if isinstance(details, list):
            return sorted({str(value) for value in details if str(value).strip()})
    return []


def normalize_rendered_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip().casefold()


def parse_pdfinfo(text: str) -> dict[str, Any]:
    pages: int | None = None
    width: float | None = None
    height: float | None = None
    for line in (text or "").splitlines():
        if line.startswith("Pages:"):
            try:
                pages = int(line.split(":", 1)[1].strip())
            except ValueError:
                pages = None
        elif line.startswith("Page size:"):
            match = re.search(r"Page size:\s*([0-9.]+)\s*x\s*([0-9.]+)\s*pts", line)
            if match:
                width = float(match.group(1))
                height = float(match.group(2))
    return {"pages": pages, "pageWidthPt": width, "pageHeightPt": height}


def run_pdfinfo(
    pdf: Path,
    pdfinfo: str,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    command = [pdfinfo, str(pdf)]
    proc = runner(command, pdf.parent)
    parsed = parse_pdfinfo((proc.stdout or "") + "\n" + (proc.stderr or ""))
    return {
        "status": "PASS" if proc.returncode == 0 and parsed["pages"] else "FAIL",
        "command": command,
        "returnCode": proc.returncode,
        **parsed,
        "outputTail": "\n".join(((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines()[-60:]),
    }


def extract_layout_text(
    pdf: Path,
    pdftotext: str,
    output: Path,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [pdftotext, "-layout", "-enc", "UTF-8", str(pdf), str(output)]
    proc = runner(command, pdf.parent)
    text = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return {
        "status": "PASS" if proc.returncode == 0 and bool(pages) else "FAIL",
        "command": command,
        "returnCode": proc.returncode,
        "path": str(output),
        "pageCount": len(pages),
        "pages": pages,
        "stderr": (proc.stderr or "")[-8000:],
    }


def extract_bbox_layout(
    pdf: Path,
    pdftotext: str,
    output: Path,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [pdftotext, "-bbox-layout", "-enc", "UTF-8", str(pdf), str(output)]
    proc = runner(command, pdf.parent)
    pages: list[dict[str, Any]] = []
    parse_error: str | None = None
    if proc.returncode == 0 and output.is_file():
        try:
            root = ET.parse(output).getroot()
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] != "page":
                    continue
                width = float(element.attrib.get("width", "0") or 0)
                height = float(element.attrib.get("height", "0") or 0)
                words: list[dict[str, Any]] = []
                for child in element.iter():
                    if child.tag.rsplit("}", 1)[-1] != "word":
                        continue
                    try:
                        words.append(
                            {
                                "text": "".join(child.itertext()),
                                "xMin": float(child.attrib["xMin"]),
                                "yMin": float(child.attrib["yMin"]),
                                "xMax": float(child.attrib["xMax"]),
                                "yMax": float(child.attrib["yMax"]),
                            }
                        )
                    except (KeyError, ValueError):
                        continue
                pages.append(
                    {
                        "page": len(pages) + 1,
                        "widthPt": width,
                        "heightPt": height,
                        "words": words,
                    }
                )
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
    ok = proc.returncode == 0 and bool(pages) and parse_error is None
    return {
        "status": "PASS" if ok else "FAIL",
        "command": command,
        "returnCode": proc.returncode,
        "path": str(output),
        "pageCount": len(pages),
        "pages": pages,
        "parseError": parse_error,
        "stderr": (proc.stderr or "")[-8000:],
    }


def page_geometry_report(pages: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    for page in pages:
        width = float(page.get("widthPt") or 0)
        height = float(page.get("heightPt") or 0)
        if (
            abs(width - LETTER_WIDTH_PT) > PAGE_SIZE_TOLERANCE_PT
            or abs(height - LETTER_HEIGHT_PT) > PAGE_SIZE_TOLERANCE_PT
        ):
            mismatches.append(
                {
                    "page": page.get("page"),
                    "widthPt": width,
                    "heightPt": height,
                }
            )
    return {
        "status": "PASS" if pages and not mismatches else "FAIL",
        "expected": {"widthPt": LETTER_WIDTH_PT, "heightPt": LETTER_HEIGHT_PT},
        "tolerancePt": PAGE_SIZE_TOLERANCE_PT,
        "pageCount": len(pages),
        "mismatches": mismatches,
    }


def rendered_bounds_report(pages: list[dict[str, Any]]) -> dict[str, Any]:
    outside: list[dict[str, Any]] = []
    edge_words: list[dict[str, Any]] = []
    word_count = 0
    for page in pages:
        width = float(page.get("widthPt") or 0)
        height = float(page.get("heightPt") or 0)
        for word in page.get("words") or []:
            word_count += 1
            row = {
                "page": page.get("page"),
                "text": str(word.get("text") or ""),
                "xMin": float(word.get("xMin") or 0),
                "yMin": float(word.get("yMin") or 0),
                "xMax": float(word.get("xMax") or 0),
                "yMax": float(word.get("yMax") or 0),
            }
            if (
                row["xMin"] < -BOUND_TOLERANCE_PT
                or row["yMin"] < -BOUND_TOLERANCE_PT
                or row["xMax"] > width + BOUND_TOLERANCE_PT
                or row["yMax"] > height + BOUND_TOLERANCE_PT
            ):
                outside.append(row)
            elif (
                row["xMin"] < EDGE_WARNING_PT
                or row["yMin"] < EDGE_WARNING_PT
                or row["xMax"] > width - EDGE_WARNING_PT
                or row["yMax"] > height - EDGE_WARNING_PT
            ):
                edge_words.append(row)
    return {
        "status": "PASS" if not outside else "FAIL",
        "wordCount": word_count,
        "boundTolerancePt": BOUND_TOLERANCE_PT,
        "outsideCount": len(outside),
        "outside": outside[:200],
        "edgeWarningPt": EDGE_WARNING_PT,
        "edgeWordCount": len(edge_words),
        "edgeWords": edge_words[:200],
    }


def _chapter_map(contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in contract.get("chapterMap") or []:
        if not isinstance(row, dict):
            continue
        try:
            result[int(row.get("chapter"))] = row
        except (TypeError, ValueError):
            continue
    return result


def locate_rendered_structure(
    page_texts: list[str], contract: dict[str, Any], profile: str
) -> dict[str, Any]:
    normalized_pages = [normalize_rendered_text(page) for page in page_texts]
    chapter_map = _chapter_map(contract)
    profile_spec = contract.get("profiles", {}).get(profile, {})
    chapters = [int(value) for value in profile_spec.get("chapters") or []]

    # The production TOC deliberately repeats every Part title before main
    # matter. Use the final exact Part-title occurrence as the structural Part
    # opening, matching the production-shell rendered validation.
    expected_part_ids = PROFILE_PART_IDS.get(profile, ())
    part_by_id = {str(row["id"]): row for row in PARTS}
    part_rows: list[dict[str, Any]] = []
    missing_parts: list[str] = []
    for part_id in expected_part_ids:
        spec = part_by_id[part_id]
        title = normalize_rendered_text(spec["title"])
        roman = normalize_rendered_text(f"part {spec['roman']}")
        candidates = [
            index + 1
            for index, page in enumerate(normalized_pages)
            if title in page and roman in page
        ]
        if not candidates:
            candidates = [
                index + 1
                for index, page in enumerate(normalized_pages)
                if title in page
            ]
        if not candidates:
            missing_parts.append(part_id)
        part_rows.append(
            {
                "partId": part_id,
                "roman": spec["roman"],
                "title": spec["title"],
                "pages": candidates,
                "anchorPage": candidates[-1] if candidates else None,
            }
        )

    # Part I is the first main-matter structure. Ignore any chapter-title hits
    # before its rendered opening so generated TOC entries cannot masquerade as
    # chapter anchors. Later hits remain recorded in `pages`, while the earliest
    # main-matter occurrence is the structural anchor.
    main_matter_start = part_rows[0]["anchorPage"] if part_rows else None
    chapter_rows: list[dict[str, Any]] = []
    missing_chapters: list[int] = []
    for number in chapters:
        spec = chapter_map.get(number, {})
        title = normalize_rendered_text(str(spec.get("title") or ""))
        label = f"chapter {number}"
        candidates = [
            index + 1
            for index, page in enumerate(normalized_pages)
            if re.search(rf"\bchapter\s+{number}\b", page) and title in page
        ]
        if not candidates:
            candidates = [
                index + 1
                for index, page in enumerate(normalized_pages)
                if re.search(rf"\bchapter\s+{number}\b", page)
            ]
        body_candidates = [
            page
            for page in candidates
            if main_matter_start is None or page >= main_matter_start
        ]
        if not body_candidates:
            missing_chapters.append(number)
        chapter_rows.append(
            {
                "chapter": number,
                "chapterId": spec.get("chapterId"),
                "title": spec.get("title"),
                "pages": candidates,
                "anchorPage": body_candidates[0] if body_candidates else None,
                "label": label,
            }
        )

    chapter_anchor_pages = [row["anchorPage"] for row in chapter_rows if row["anchorPage"]]
    part_anchor_pages = [row["anchorPage"] for row in part_rows if row["anchorPage"]]
    chapter_order_ok = chapter_anchor_pages == sorted(chapter_anchor_pages)
    part_order_ok = part_anchor_pages == sorted(part_anchor_pages)

    divider = normalize_rendered_text(str(contract.get("gmDividerText") or ""))
    divider_pages = [
        index + 1 for index, page in enumerate(normalized_pages) if divider and divider in page
    ]
    expected_divider = int(profile_spec.get("gmDividerCount") or 0)
    divider_ok = len(divider_pages) == expected_divider

    chapter13_pages = [
        index + 1
        for index, page in enumerate(normalized_pages)
        if re.search(r"\bchapter\s+13\b", page)
    ]
    gm_chapter_pages: dict[int, list[int]] = {}
    if profile == "player-guide":
        for number in range(23, 33):
            matches = [
                index + 1
                for index, page in enumerate(normalized_pages)
                if re.search(rf"\bchapter\s+{number}\b", page)
            ]
            if matches:
                gm_chapter_pages[number] = matches

    residue_tokens = {
        "source-commit:": [],
        "profile: ``": [],
    }
    for token in residue_tokens:
        residue_tokens[token] = [
            index + 1
            for index, page in enumerate(normalized_pages)
            if normalize_rendered_text(token) in page
        ]

    gm_boundary_ok = divider_ok
    if profile == "complete-rulebook" and divider_pages:
        chapter22 = next((row["anchorPage"] for row in chapter_rows if row["chapter"] == 22), None)
        chapter23 = next((row["anchorPage"] for row in chapter_rows if row["chapter"] == 23), None)
        divider_page = divider_pages[0]
        gm_boundary_ok = bool(
            chapter22
            and chapter23
            and chapter22 <= divider_page <= chapter23
        )

    ok = (
        not missing_chapters
        and not missing_parts
        and chapter_order_ok
        and part_order_ok
        and divider_ok
        and gm_boundary_ok
        and not chapter13_pages
        and not gm_chapter_pages
        and not any(residue_tokens.values())
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "chapters": chapter_rows,
        "missingChapters": missing_chapters,
        "chapterOrder": chapter_anchor_pages,
        "chapterOrderValid": chapter_order_ok,
        "parts": part_rows,
        "missingParts": missing_parts,
        "partOrder": part_anchor_pages,
        "partOrderValid": part_order_ok,
        "gmDivider": {
            "expectedCount": expected_divider,
            "pages": divider_pages,
            "boundaryValid": gm_boundary_ok,
        },
        "chapter13Pages": chapter13_pages,
        "playerGuideGmChapterPages": gm_chapter_pages,
        "provenanceResiduePages": residue_tokens,
    }


def page_count_consistency(
    pdfinfo_report: dict[str, Any], layout_report: dict[str, Any], bbox_report: dict[str, Any]
) -> dict[str, Any]:
    counts = {
        "pdfinfo": pdfinfo_report.get("pages"),
        "layoutText": layout_report.get("pageCount"),
        "bbox": bbox_report.get("pageCount"),
    }
    numeric = [int(value) for value in counts.values() if isinstance(value, int) and value > 0]
    ok = len(numeric) == 3 and len(set(numeric)) == 1
    return {"status": "PASS" if ok else "FAIL", "counts": counts}


def render_anchor_previews(
    pdf: Path,
    pdftoppm: str | None,
    pages: list[int],
    output_dir: Path,
    dpi: int = 72,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    unique_pages = sorted({int(page) for page in pages if int(page) > 0})
    if not pdftoppm:
        return {
            "status": "SKIPPED",
            "pageCount": len(unique_pages),
            "pages": unique_pages,
            "message": "pdftoppm is unavailable; bbox/text rendered regression remains authoritative.",
        }
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for page in unique_pages:
        stem = output_dir / f"page-{page:03d}"
        command = [
            pdftoppm,
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            "-png",
            "-r",
            str(dpi),
            str(pdf),
            str(stem),
        ]
        proc = runner(command, pdf.parent)
        path = stem.with_suffix(".png")
        row = {
            "page": page,
            "path": str(path),
            "returnCode": proc.returncode,
            "bytes": path.stat().st_size if path.is_file() else 0,
        }
        rows.append(row)
        if proc.returncode != 0 or not path.is_file() or path.stat().st_size == 0:
            failures.append(row)
    return {
        "status": "PASS" if not failures else "FAIL",
        "dpi": dpi,
        "pageCount": len(unique_pages),
        "pages": unique_pages,
        "previews": rows,
        "failures": failures,
    }


def copy_validated_pdf(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_sha = sha256_file(source)
    output_sha = sha256_file(destination)
    valid = (
        destination.is_file()
        and destination.stat().st_size > 0
        and destination.read_bytes()[:5] == b"%PDF-"
        and source_sha == output_sha
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "source": str(source),
        "path": str(destination),
        "bytes": destination.stat().st_size if destination.is_file() else 0,
        "sourceSha256": source_sha,
        "sha256": output_sha if destination.is_file() else None,
        "exactCopy": source_sha == output_sha if destination.is_file() else False,
    }
