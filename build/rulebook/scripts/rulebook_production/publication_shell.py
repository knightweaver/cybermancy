from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any


FAMILY_CHAPTERS = {
    "classes": (12, "Classes"),
    "subclasses": (12, "Subclasses"),
    "domains": (14, "Domains and Domain Cards"),
    "weapons": (15, "Weapons"),
    "ammo": (16, "Ammunition"),
    "armors": (17, "Armor"),
    "cybernetics": (18, "Cybernetics"),
    "drones-devices": (19, "Drones and Devices"),
    "consumables": (20, "Consumables"),
    "mods": (21, "Mods"),
    "loot": (22, "Loot"),
    "features": (29, "ICE Reference"),
    "adversaries": (30, "Adversaries"),
    "environments": (31, "Environments"),
    "adversaries-features": (32, "Adversary Features"),
}
GM_FAMILIES = {"features", "adversaries", "environments", "adversaries-features"}
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


def _sort_key(value: str) -> tuple[str, str]:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return ("".join(char for char in normalized if char.isalnum() or char.isspace()), value)


def _is_published_feature(entity: dict[str, Any]) -> bool:
    data = entity.get("publicationData")
    if not isinstance(data, dict):
        return False
    equivalence = data.get("publicationEquivalence")
    # Ungrouped canonical features are standalone representatives. Grouped
    # features carry the explicit representative flag from the accepted Step 4
    # publication-equivalence pass.
    if not isinstance(equivalence, dict):
        return True
    return equivalence.get("isRepresentative") is True


def _published_name(entity: dict[str, Any]) -> str:
    data = entity.get("publicationData")
    if isinstance(data, dict):
        reference = data.get("referenceEntry")
        if isinstance(reference, dict):
            name = str(reference.get("name") or "").strip()
            if name:
                return name
    return str(entity.get("name") or "").strip()


def entity_index(
    sidecar: dict[str, Any], profile: str, expectations: dict[str, Any]
) -> dict[str, Any]:
    entities = sidecar.get("entities")
    if not isinstance(entities, list):
        raise ValueError("Step 4 structured sidecar has no entities list")

    ice_semantics = sidecar.get("iceSemantics")
    ice_ids = {
        str(value).strip()
        for value in (
            ice_semantics.get("semanticIds", [])
            if isinstance(ice_semantics, dict)
            else []
        )
        if str(value).strip()
    }

    rows: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        family = str(entity.get("family") or "")
        if family not in FAMILY_CHAPTERS:
            continue
        if profile == "player-guide" and family in GM_FAMILIES:
            continue
        # The Step 4 `features` family contains every system feature. Chapter
        # 29 publishes only the canonical ICE subset identified by the
        # accepted Step 4 ICE semantics, so Appendix B must use that same
        # selection rather than indexing unrelated class/system features.
        if family == "features" and str(entity.get("semanticId") or "") not in ice_ids:
            continue
        if family == "adversaries-features" and not _is_published_feature(entity):
            continue
        name = _published_name(entity)
        semantic_id = str(entity.get("semanticId") or "").strip()
        if not name or not semantic_id:
            raise ValueError(f"Indexable {family} entity lacks name or semanticId")
        chapter, family_label = FAMILY_CHAPTERS[family]
        rows.append(
            {
                "name": name,
                "semanticId": semantic_id,
                "family": family,
                "familyLabel": family_label,
                "chapter": chapter,
            }
        )
        family_counts[family] = family_counts.get(family, 0) + 1

    expected_by_family = {
        "classes": int(expectations["classes"]),
        "subclasses": int(expectations["subclasses"]),
        # `domains` is the count of organizational domain groupings. The Step 4
        # structured sidecar's `domains` family contains the individually
        # publishable domain-card entities only.
        "domains": int(expectations["domainCards"]),
        "weapons": int(expectations["weapons"]),
        "ammo": int(expectations["ammo"]),
        "armors": int(expectations["armors"]),
        "cybernetics": int(expectations["cybernetics"]),
        "drones-devices": int(expectations["dronesDevices"]),
        "consumables": int(expectations["consumables"]),
        "mods": int(expectations["mods"]),
        "loot": int(expectations["loot"]),
    }
    if profile == "complete-rulebook":
        expected_by_family.update(
            {
                "features": int(expectations["ice"]),
                "adversaries": int(expectations["adversaries"]),
                "environments": int(expectations["environments"]),
                "adversaries-features": int(expectations["adversaryFeaturesPublished"]),
            }
        )
    mismatches = {
        family: {"expected": expected, "actual": family_counts.get(family, 0)}
        for family, expected in expected_by_family.items()
        if family_counts.get(family, 0) != expected
    }
    unexpected = sorted(set(family_counts) - set(expected_by_family))
    if mismatches or unexpected:
        raise ValueError(
            f"Appendix B entity reconciliation failed: mismatches={mismatches}, unexpected={unexpected}"
        )

    rows.sort(key=lambda row: (*_sort_key(row["name"]), row["semanticId"]))
    return {
        "status": "PASS",
        "profile": profile,
        "entryCount": len(rows),
        "expectedEntryCount": sum(expected_by_family.values()),
        "familyCounts": family_counts,
        "rows": rows,
    }


def _index_tex(index: dict[str, Any]) -> str:
    pieces = [
        r"\CMProductionAppendix{B}{Entity Index}{appendix-b-entity-index}",
        r"\begin{multicols}{2}",
        r"\raggedcolumns",
        r"\setlength{\columnsep}{0.24in}",
    ]
    current = ""
    for row in index["rows"]:
        letter = row["name"][0].upper() if row["name"] else "#"
        if letter != current:
            current = letter
            pieces.append(rf"\CMEntityIndexLetter{{{_escape(letter)}}}")
        pieces.append(
            rf"\CMEntityIndexEntry{{{_escape(row['name'])}}}"
            rf"{{{_escape(row['familyLabel'])}}}"
            rf"{{{row['chapter']}}}"
        )
    pieces.extend([r"\end{multicols}", "% CM-PRODUCTION APPENDIX-B END"])
    return "\n".join(pieces) + "\n"


def _production_macros(title: str, subtitle: str, version: str, footer: str) -> str:
    return rf"""
% ---- Production Renderer Phase D publication shell ----
\newcommand{{\CMProductionRecto}}{{%
  \clearpage
  \ifodd\value{{page}}\else\null\thispagestyle{{empty}}\newpage\fi
}}
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
\newcommand{{\CMEntityIndexLetter}}[1]{{\par\Needspace{{4\baselineskip}}\vspace{{5pt}}{{\sffamily\fontsize{{12}}{{14}}\selectfont\bfseries\color{{CMTeal}}#1\par}}\vspace{{1pt}}}}
\newcommand{{\CMEntityIndexEntry}}[3]{{%
  \par\Needspace{{2\baselineskip}}\noindent
  \parbox[t]{{0.66\columnwidth}}{{\raggedright\sffamily\fontsize{{8.1}}{{9.4}}\selectfont\bfseries #1\\{{\fontsize{{6.8}}{{8.0}}\selectfont\color{{CMMuted}}#2}}}}\hfill
  \parbox[t]{{0.30\columnwidth}}{{\raggedleft\sffamily\fontsize{{7.1}}{{8.5}}\selectfont Chapter #3\\p.~\pageref{{cm-chapter-#3}}}}\par\vspace{{1.2pt}}
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
  \ifodd\value{{page}}\else\null\thispagestyle{{empty}}\newpage\fi
  \pagenumbering{{arabic}}
}}
% ---- Production Renderer Phase D publication shell end ----
"""


def _inject_package_navigation(document: str) -> tuple[str, list[int]]:
    applied: list[int] = []
    for chapter, (family, title, chapter_id) in PACKAGE_CHAPTERS.items():
        marker = f"% CM-STAGE150 FAMILY {family} BEGIN"
        start = document.find(marker)
        if start < 0:
            continue
        end = document.find("% CM-STAGE150 FAMILY ", start + len(marker))
        if end < 0:
            end = document.find(r"\end{document}", start)
        segment = document[start:end]
        navigation = rf"\CMProductionPackageChapter{{{chapter}}}{{{_escape(title)}}}{{{chapter_id}}}\n"
        clear_at = segment.find(r"\clearpage")
        if clear_at >= 0:
            insert_at = start + clear_at + len(r"\clearpage")
            document = document[:insert_at] + "\n" + navigation + document[insert_at:]
        else:
            insert_at = start + len(marker)
            document = document[:insert_at] + "\n" + navigation + document[insert_at:]
        applied.append(chapter)
    return document, applied


def apply_publication_shell(
    document: str,
    profile: str,
    production_contract: dict[str, Any],
    metadata: dict[str, Any],
    sidecar: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    shell = production_contract.get("publicationShell")
    appendices = production_contract.get("appendices")
    if not isinstance(shell, dict) or shell.get("status") != "ACCEPTED":
        raise ValueError("Production publication-shell decisions are not accepted")
    if not isinstance(appendices, dict):
        raise ValueError("Production appendix contract is missing")
    if appendices["appendix-a-rules-quick-reference"].get("generate"):
        raise ValueError("Appendix A must remain deferred")
    if appendices["appendix-c-attribution-publication-notice"].get("generate"):
        raise ValueError("Appendix C must remain deferred")
    if not appendices["appendix-b-entity-index"].get("generate"):
        raise ValueError("Appendix B must be generated")

    profile_metadata = metadata["profiles"][profile]
    title = str(shell["title"])
    subtitle = str(shell["profileSubtitles"][profile])
    version = str(shell["readerFacingVersion"])
    footer = f"CYBERMANCY // {subtitle.upper()} // {version.upper()}"
    index = entity_index(sidecar, profile, production_contract["structuredExpectations"])

    begin = r"\begin{document}"
    end = r"\end{document}"
    first_part = "% CM-INTEGRATED-SHELL PART "
    if document.count(begin) != 1 or document.count(end) != 1 or first_part not in document:
        raise ValueError("Stage 150 document lacks one shell or its first integrated Part marker")

    document = document.replace(begin, _production_macros(title, subtitle, version, footer) + "\n" + begin, 1)
    front_at = document.index(first_part)
    document = document[:front_at] + "\\CMProductionFrontMatter\n" + document[front_at:]
    document, package_chapters = _inject_package_navigation(document)
    appendix_tex = _index_tex(index)
    document = document.replace(end, appendix_tex + end, 1)

    expected_packages = [] if profile == "player-guide" else sorted(PACKAGE_CHAPTERS)
    if package_chapters != expected_packages:
        raise ValueError(
            f"Production package navigation mismatch: expected={expected_packages}, actual={package_chapters}"
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
        "rectoStarts": ["part", "appendix"],
        "packageChapterNavigation": package_chapters,
        "appendices": {"generated": ["appendix-b-entity-index"], "deferred": ["appendix-a-rules-quick-reference", "appendix-c-attribution-publication-notice"]},
        "entityIndex": {key: value for key, value in index.items() if key != "rows"},
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
    appendix_count = 1
    expected_levels = [0] * part_count + [1] * chapter_count + [0] * appendix_count
    # The order interleaves Parts and Chapters, so validate counts as well as the
    # absence of lower bookmark levels; rendered order is checked at Stage 170.
    expected_tokens = ["appendix-b-entity-index"]
    expected_tokens.extend(str(row["chapterId"]) for row in step6_contract["chapterMap"] if int(row["chapter"]) in step6_contract["profiles"][profile]["chapters"])
    token_misses = [token for token in expected_tokens if token not in toc_text and token not in out_text]
    ok = (
        len(levels) == len(expected_levels)
        and levels.count(0) == part_count + appendix_count
        and levels.count(1) == chapter_count
        and not any(level > 1 for level in levels)
        and not token_misses
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "bookmarkCount": len(levels),
        "expectedBookmarkCount": len(expected_levels),
        "levelCounts": {"0": levels.count(0), "1": levels.count(1)},
        "expectedLevelCounts": {"0": part_count + appendix_count, "1": chapter_count},
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
    appendix_pages = [i + 1 for i, page in enumerate(normalized) if "appendix b" in page and "entity index" in page]
    appendix_page = appendix_pages[-1] if appendix_pages else None
    part_pages: list[int] = []
    for roman, part_title in (("i", "the world of cybermancy"), ("ii", "cybermancy rules"), ("iii", "characters and character options"), ("iv", "equipment and technology"), ("v", "gm world guide"), ("vi", "gm encounter toolkit")):
        if len(part_pages) >= len(production_contract["profiles"][profile]["parts"]):
            break
        matches = [i + 1 for i, page in enumerate(normalized) if f"part {roman}" in page and part_title in page]
        if matches:
            part_pages.append(matches[-1])
    deferred_hits = {
        "appendixA": [i + 1 for i, page in enumerate(normalized) if "appendix a" in page and "rules quick reference" in page],
        "appendixC": [i + 1 for i, page in enumerate(normalized) if "appendix c" in page and "attribution and publication notice" in page],
    }
    recto = part_pages + ([appendix_page] if appendix_page else [])
    ok = (
        title_ok
        and bool(contents_pages)
        and appendix_page is not None
        and len(part_pages) == len(production_contract["profiles"][profile]["parts"])
        and all(page % 2 == 1 for page in recto)
        and not any(deferred_hits.values())
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "titlePage": {"page": 1, "valid": title_ok},
        "contentsPages": contents_pages,
        "partAnchorPages": part_pages,
        "appendixB": {"page": appendix_page, "pages": appendix_pages},
        "rectoStartPages": recto,
        "rectoStartsValid": bool(recto) and all(page % 2 == 1 for page in recto),
        "deferredAppendixHits": deferred_hits,
    }
