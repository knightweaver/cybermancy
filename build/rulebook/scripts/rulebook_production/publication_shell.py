from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any


PACKAGE_CHAPTERS = {
    29: ("features", "ICE Reference", "ch29-ice-reference"),
    30: ("adversaries", "Adversaries", "ch30-adversaries"),
    31: ("environments", "Environments", "ch31-environments"),
    32: ("adversaries-features", "Adversary Feature Reference", "ch32-adversary-features"),
}


def _escape(value: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(value or ""))


def _appendix_state(appendices: dict[str, Any]) -> dict[str, list[str]]:
    generated: list[str] = []
    deferred: list[str] = []
    removed: list[str] = []
    for appendix_id, value in appendices.items():
        if not isinstance(value, dict):
            continue
        if value.get("generate") is True:
            generated.append(str(appendix_id))
        status = str(value.get("status") or "").upper()
        if status == "DEFERRED":
            deferred.append(str(appendix_id))
        elif status == "REMOVED":
            removed.append(str(appendix_id))
    return {
        "generated": sorted(generated),
        "deferred": sorted(deferred),
        "removed": sorted(removed),
    }


def _ordinary_chapter_breaks(shell: dict[str, Any]) -> list[int]:
    raw = shell.get("ordinaryChapterBreaks")
    if not isinstance(raw, list):
        raise ValueError("Production publication-shell ordinaryChapterBreaks policy is missing")
    try:
        chapters = [int(value) for value in raw]
    except (TypeError, ValueError) as exc:
        raise ValueError("Production ordinaryChapterBreaks must contain chapter numbers") from exc
    if chapters != sorted(set(chapters)):
        raise ValueError("Production ordinaryChapterBreaks must be unique and ascending")
    unknown = [chapter for chapter in chapters if chapter not in PACKAGE_CHAPTERS]
    if unknown:
        raise ValueError(f"Production ordinaryChapterBreaks contains non-package chapters: {unknown}")
    return chapters


def _production_macros(title: str, subtitle: str, version: str, footer: str) -> str:
    return rf"""
% ---- Production Renderer Phase D publication shell ----
\hypersetup{{bookmarksdepth=1}}
\newcommand{{\CMProductionRecto}}{{%
  \clearpage
  \ifodd\value{{page}}\else\null\thispagestyle{{empty}}\newpage\fi
}}
\newcommand{{\CMProductionChapterBreak}}{{\clearpage}}
\newcommand{{\CMProductionTOCLine}}[4]{{%
  \addtocontents{{toc}}{{\protect\contentsline{{#1}}{{#2}}{{\thepage}}{{#3}}}}%
  \pdfbookmark[#4]{{#2}}{{#3}}%
}}
\newcommand{{\CMProductionPart}}[5]{{%
  \CMProductionRecto
  \CMProductionTOCLine{{part}}{{Part #1: #2}}{{cm-part-#5}}{{0}}%
  \begingroup
  \thispagestyle{{empty}}
  \pagecolor{{CMInk}}\color{{white}}
  \vspace*{{0.78in}}
  {{\sffamily\fontsize{{11}}{{13}}\selectfont\color{{#4}}\bfseries PART #1\par}}
  \vspace{{0.15in}}
  {{\sffamily\fontsize{{28}}{{31}}\selectfont\bfseries #2\par}}
  \vspace{{0.12in}}
  {{\color{{#4}}\rule{{1.25in}}{{2pt}}\par}}
  \vfill
  \begin{{minipage}}{{0.78\textwidth}}\sffamily\fontsize{{11}}{{15}}\selectfont\color{{white!82}}#3\end{{minipage}}
  \vspace*{{0.50in}}
  \clearpage
  \pagecolor{{CMPaper}}\color{{CMBody}}
  \endgroup
}}
\let\CMPhaseCIntegratedChapter\CMIntegratedChapter
\renewcommand{{\CMIntegratedChapter}}[4]{{%
  \CMPhaseCIntegratedChapter{{#1}}{{#2}}{{#3}}{{#4}}%
  \CMProductionTOCLine{{section}}{{Chapter #1: #2}}{{cm-chapter-#4}}{{1}}%
  \label{{cm-chapter-#1}}%
}}
\renewcommand{{\CMIntegratedPart}}[4]{{%
  \ifstrequal{{#4}}{{part-iv-equipment}}{{\CMUseEquipmentGeometry}}{{%
    \ifstrequal{{#4}}{{part-vi-gm-toolkit}}{{\CMUsePackageGeometry}}{{\CMUseProseGeometry}}%
  }}%
  \ifstrequal{{#3}}{{gm}}{{\def\CMThisPartDeck{{GM MATERIAL}}\def\CMThisPartAccent{{CMViolet}}}}{{\def\CMThisPartDeck{{PLAYER MATERIAL}}\def\CMThisPartAccent{{CMCyan}}}}%
  \CMProductionPart{{#1}}{{#2}}{{\CMThisPartDeck}}{{\CMThisPartAccent}}{{#4}}%
}}
\newcommand{{\CMProductionPackageChapter}}[3]{{%
  \CMProductionTOCLine{{section}}{{Chapter #1: #2}}{{cm-chapter-#3}}{{1}}%
  \label{{cm-chapter-#1}}%
}}
\newcommand{{\CMProductionAppendix}}[3]{{%
  \CMUseProseGeometry
  \CMProductionRecto
  \CMProductionTOCLine{{part}}{{Appendix #1: #2}}{{cm-appendix-#3}}{{0}}%
  \thispagestyle{{empty}}
  \noindent\colorbox{{CMInk}}{{\parbox{{\dimexpr\textwidth-2\fboxsep\relax}}{{%
    \vspace{{0.10in}}\sffamily\fontsize{{8.3}}{{10}}\selectfont\color{{CMCyan}}\bfseries APPENDIX #1\par
    \vspace{{0.045in}}\sffamily\fontsize{{20}}{{22}}\selectfont\color{{white}}\bfseries #2\par\vspace{{0.09in}}
  }}}}
  \vspace{{0.15in}}
}}
\renewcommand{{\contentsname}}{{Contents}}
\fancyfoot[L]{{\sffamily\fontsize{{7.0}}{{8.5}}\selectfont\color{{CMTeal}}{_escape(footer)}}}
\newcommand{{\CMProductionFrontMatter}}{{%
  \pagenumbering{{roman}}
  \begin{{titlepage}}
  \thispagestyle{{empty}}
  \pagecolor{{CMInk}}\color{{white}}
  \vspace*{{1.15in}}
  {{\sffamily\fontsize{{12}}{{14}}\selectfont\bfseries\color{{CMCyan}} VERSION 1.0\par}}
  \vspace{{0.22in}}
  {{\sffamily\fontsize{{38}}{{42}}\selectfont\bfseries {_escape(title)}\par}}
  \vspace{{0.14in}}
  {{\sffamily\fontsize{{22}}{{26}}\selectfont\bfseries\color{{white!88}} {_escape(subtitle)}\par}}
  \vspace{{0.16in}}{{\color{{CMCyan}}\rule{{1.65in}}{{2pt}}\par}}
  \vfill
  {{\sffamily\fontsize{{10}}{{12}}\selectfont\color{{white!72}} {_escape(version)}\par}}
  \end{{titlepage}}
  \pagecolor{{CMPaper}}\color{{CMBody}}
  \pagestyle{{fancy}}
  \tableofcontents
  \clearpage
  % Align physical and logical parity before resetting Arabic numbering. At
  % this point an odd Roman counter means the next physical content page would
  % be even, so emit a blank verso page first.
  \ifodd\value{{page}}\null\thispagestyle{{empty}}\newpage\fi
  \pagenumbering{{arabic}}
}}
% ---- Production Renderer Phase D publication shell end ----
"""


def _inject_package_navigation(
    document: str,
    ordinary_break_chapters: list[int],
) -> tuple[str, list[int], list[int]]:
    applied: list[int] = []
    breaks_applied: list[int] = []
    ordinary_breaks = set(ordinary_break_chapters)
    for chapter, (family, title, chapter_id) in PACKAGE_CHAPTERS.items():
        marker = f"% CM-STAGE150 FAMILY {family} BEGIN"
        start = document.find(marker)
        if start < 0:
            continue
        end = document.find("% CM-STAGE150 FAMILY ", start + len(marker))
        if end < 0:
            end = document.find(r"\end{document}", start)
        segment = document[start:end]
        navigation = (
            rf"\CMProductionPackageChapter{{{chapter}}}{{{_escape(title)}}}{{{chapter_id}}}"
            + "\n"
        )
        clear_at = segment.find(r"\clearpage")
        if chapter in ordinary_breaks:
            # The shell owns this boundary. Replace one incidental package-local
            # leading/page-opening clearpage when present, then emit exactly one
            # ordinary break at the semantic package boundary. Placement no longer
            # depends on where the package happened to put its first clearpage.
            if clear_at >= 0:
                clear_abs = start + clear_at
                document = document[:clear_abs] + document[clear_abs + len(r"\clearpage") :]
            insert_at = start + len(marker)
            boundary = "\n" + r"\CMProductionChapterBreak" + "\n" + navigation
            document = document[:insert_at] + boundary + document[insert_at:]
            breaks_applied.append(chapter)
        elif clear_at >= 0:
            insert_at = start + clear_at + len(r"\clearpage")
            document = document[:insert_at] + "\n" + navigation + document[insert_at:]
        else:
            insert_at = start + len(marker)
            document = document[:insert_at] + "\n" + navigation + document[insert_at:]
        applied.append(chapter)
    return document, applied, breaks_applied


def apply_publication_shell(
    document: str,
    profile: str,
    production_contract: dict[str, Any],
    metadata: dict[str, Any],
    sidecar: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    shell = production_contract.get("publicationShell")
    appendices = production_contract.get("appendices")
    if not isinstance(shell, dict) or shell.get("status") != "ACCEPTED":
        raise ValueError("Production publication-shell decisions are not accepted")
    if not isinstance(appendices, dict):
        raise ValueError("Production appendix contract is missing")

    ordinary_chapter_breaks = _ordinary_chapter_breaks(shell)
    appendix_state = _appendix_state(appendices)
    appendix_b = appendices.get("appendix-b-entity-index")
    if not isinstance(appendix_b, dict):
        raise ValueError("Appendix B audit state is missing")
    if appendix_b.get("status") != "REMOVED" or appendix_b.get("generate") is not False:
        raise ValueError("Appendix B must remain REMOVED and disabled")
    if appendix_state["generated"]:
        raise ValueError(
            "No production appendix generator is active; contract requested generation for "
            + ", ".join(appendix_state["generated"])
        )

    # Kept as an optional compatibility argument because the Stage 150 caller
    # still passes the Step 4 sidecar. It is intentionally not consumed by the
    # publication shell now that the generated entity index is removed.
    _ = sidecar

    profile_metadata = metadata["profiles"][profile]
    title = str(shell["title"])
    subtitle = str(shell["profileSubtitles"][profile])
    version = str(shell["readerFacingVersion"])
    footer = f"CYBERMANCY // {subtitle.upper()} // {version.upper()}"

    begin = r"\begin{document}"
    end = r"\end{document}"
    first_part = "% CM-INTEGRATED-SHELL PART "
    if document.count(begin) != 1 or document.count(end) != 1 or first_part not in document:
        raise ValueError("Stage 150 document lacks one shell or its first integrated Part marker")

    document = document.replace(begin, _production_macros(title, subtitle, version, footer) + "\n" + begin, 1)
    front_at = document.index(first_part)
    document = document[:front_at] + "\\CMProductionFrontMatter\n" + document[front_at:]
    document, package_chapters, package_breaks = _inject_package_navigation(
        document,
        ordinary_chapter_breaks,
    )

    expected_packages = [] if profile == "player-guide" else sorted(PACKAGE_CHAPTERS)
    expected_breaks = [] if profile == "player-guide" else ordinary_chapter_breaks
    if package_chapters != expected_packages:
        raise ValueError(
            f"Production package navigation mismatch: expected={expected_packages}, actual={package_chapters}"
        )
    if package_breaks != expected_breaks:
        raise ValueError(
            f"Production package chapter-break mismatch: expected={expected_breaks}, actual={package_breaks}"
        )
    report = {
        "schema": "cybermancy-production-publication-shell-v1",
        "status": "PASS",
        "profile": profile,
        "title": title,
        "subtitle": subtitle,
        "readerFacingVersion": version,
        "titlePageNumberVisible": False,
        "frontMatterNumbering": "lowercase-roman",
        "mainMatterNumbering": "arabic-from-part-i",
        "rectoStarts": ["part"],
        "ordinaryChapterBreaks": ordinary_chapter_breaks,
        "packageChapterBreaksApplied": package_breaks,
        "packageChapterNavigation": package_chapters,
        "appendices": appendix_state,
        "documentSha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "readerFacingName": profile_metadata["readerFacingName"],
    }
    return document, report


_BOOKMARK_RE = re.compile(r"\\BOOKMARK\s*\[(?P<level>-?\d+)\].*")


def bookmark_structure(
    out_path: Path,
    toc_path: Path,
    production_contract: dict[str, Any],
    step6_contract: dict[str, Any],
    profile: str,
) -> dict[str, Any]:
    out_text = out_path.read_text(encoding="utf-8", errors="replace") if out_path.is_file() else ""
    toc_text = toc_path.read_text(encoding="utf-8", errors="replace") if toc_path.is_file() else ""
    levels = [int(match.group("level")) for match in _BOOKMARK_RE.finditer(out_text)]
    part_count = len(production_contract["profiles"][profile]["parts"])
    chapter_count = len(step6_contract["profiles"][profile]["chapters"])
    appendix_state = _appendix_state(production_contract.get("appendices") or {})
    expected_appendix_tokens = appendix_state["generated"]
    appendix_count = len(expected_appendix_tokens)
    expected_levels = [0] * part_count + [1] * chapter_count + [0] * appendix_count
    expected_tokens = list(expected_appendix_tokens)
    expected_tokens.extend(
        str(row["chapterId"])
        for row in step6_contract["chapterMap"]
        if int(row["chapter"]) in step6_contract["profiles"][profile]["chapters"]
    )
    token_misses = [token for token in expected_tokens if token not in toc_text and token not in out_text]
    removed_hits = [
        token
        for token in appendix_state["removed"]
        if token in toc_text or token in out_text
    ]
    ok = (
        len(levels) == len(expected_levels)
        and levels.count(0) == part_count + appendix_count
        and levels.count(1) == chapter_count
        and not any(level > 1 for level in levels)
        and not token_misses
        and not removed_hits
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "bookmarkCount": len(levels),
        "expectedBookmarkCount": len(expected_levels),
        "levelCounts": {"0": levels.count(0), "1": levels.count(1)},
        "expectedLevelCounts": {"0": part_count + appendix_count, "1": chapter_count},
        "generatedAppendixDestinations": expected_appendix_tokens,
        "removedAppendixDestinations": appendix_state["removed"],
        "unexpectedRemovedAppendixDestinations": removed_hits,
        "lowerLevelBookmarks": [level for level in levels if level > 1],
        "missingSemanticDestinations": token_misses,
        "outPath": str(out_path),
        "tocPath": str(toc_path),
    }


def locate_rendered_publication_shell(
    page_texts: list[str], production_contract: dict[str, Any], profile: str
) -> dict[str, Any]:
    normalized = [re.sub(r"\s+", " ", unicodedata.normalize("NFKC", page)).strip().casefold() for page in page_texts]
    shell = production_contract["publicationShell"]
    title = str(shell["title"]).casefold()
    subtitle = str(shell["profileSubtitles"][profile]).casefold()
    version = str(shell["readerFacingVersion"]).casefold()
    title_ok = bool(normalized) and all(token in normalized[0] for token in (title, subtitle, version))
    contents_pages = [i + 1 for i, page in enumerate(normalized) if "contents" in page]
    part_pages: list[int] = []
    for roman, part_title in (
        ("i", "the world of cybermancy"),
        ("ii", "cybermancy rules"),
        ("iii", "characters and character options"),
        ("iv", "equipment and technology"),
        ("v", "gm world guide"),
        ("vi", "gm encounter toolkit"),
    ):
        if len(part_pages) >= len(production_contract["profiles"][profile]["parts"]):
            break
        matches = [i + 1 for i, page in enumerate(normalized) if f"part {roman}" in page and part_title in page]
        if matches:
            part_pages.append(matches[-1])

    appendix_hits = {
        "appendixA": [
            i + 1
            for i, page in enumerate(normalized)
            if "appendix a" in page and "rules quick reference" in page
        ],
        "appendixB": [
            i + 1
            for i, page in enumerate(normalized)
            if "appendix b" in page and "entity index" in page
        ],
        "appendixC": [
            i + 1
            for i, page in enumerate(normalized)
            if "appendix c" in page and "attribution and publication notice" in page
        ],
    }
    appendix_state = _appendix_state(production_contract.get("appendices") or {})
    removed_hits = {
        "appendixB": appendix_hits["appendixB"]
        if "appendix-b-entity-index" in appendix_state["removed"]
        else []
    }
    deferred_hits = {
        "appendixA": appendix_hits["appendixA"],
        "appendixC": appendix_hits["appendixC"],
    }
    recto = part_pages
    ok = (
        title_ok
        and bool(contents_pages)
        and len(part_pages) == len(production_contract["profiles"][profile]["parts"])
        and all(page % 2 == 1 for page in recto)
        and not any(deferred_hits.values())
        and not any(removed_hits.values())
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "titlePage": {"page": 1, "valid": title_ok},
        "contentsPages": contents_pages,
        "partAnchorPages": part_pages,
        "appendices": {
            "generated": appendix_state["generated"],
            "deferred": appendix_state["deferred"],
            "removed": appendix_state["removed"],
        },
        "appendixB": {"status": "REMOVED", "pages": appendix_hits["appendixB"]},
        "rectoStartPages": recto,
        "rectoStartsValid": bool(recto) and all(page % 2 == 1 for page in recto),
        "deferredAppendixHits": deferred_hits,
        "removedAppendixHits": removed_hits,
    }
