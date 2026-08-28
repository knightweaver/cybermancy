#!/usr/bin/env python3
"""Cybermancy Step 6 Character Origins builder v0.1.2.

Implements the approved Outcome B prose-derived entry grammar for Chapters 10-11.
Consumes only Step 4 assembled publication profiles and staged assets, while
reusing the accepted Long-Form Prose v1.0 Pandoc/LuaLaTeX runtime.

Patch 0.1.1 aligns entry parsing with the Step 4 Pandoc-safety contract: Step 4
rewrites body `---` thematic breaks to `***` after assembly. Character Origins
accepts either spelling at its input boundary and emits `***` in temporary
annotated Markdown.

Patch 0.1.2 makes rendered-PDF semantic validation presence-based. pdftotext
reading order is not stable for the inherited two-column/minipage layout, so
canonical entry order remains validated from the normalized corpus while the
rendered-PDF check verifies that every entry heading and Feature name survived
into extractable PDF text.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_VERSION = "0.1.2"
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
DEFAULT_REPO_ROOT = RULEBOOK_DIR.parent.parent
LAYOUT_DIR = RULEBOOK_DIR / "layout" / "character-origins"
DEFAULT_CONFIG = LAYOUT_DIR / "character-origins-layout-v1.json"
DEFAULT_FILTER = LAYOUT_DIR / "pandoc" / "character-origins.lua"
DEFAULT_PROSE_CONFIG = RULEBOOK_DIR / "layout" / "prose" / "prose-layout-v1.json"
DEFAULT_PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"
DEFAULT_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md"
DEFAULT_PLAYER_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "player-guide.md"
DEFAULT_ASSET_ROOT = RULEBOOK_DIR / "source" / "assets"
DEFAULT_OUTPUT = LAYOUT_DIR / "output" / "Cybermancy_Chapters10_11_CharacterOrigins_Step6.pdf"
DEFAULT_REPORT = LAYOUT_DIR / "reports" / "character-origins-regression-v1.json"
DEFAULT_WORK = LAYOUT_DIR / "work" / "pandoc-lualatex-v1"
TARGET_CHAPTERS = (10, 11)

# Step 4's pandoc_safe_assembled_markdown() deliberately converts body `---`
# thematic breaks to `***`, preserving only the manuscript YAML delimiters.
# Accept both forms here so this renderer is compatible with the normalized
# assembled corpus and with direct normalized-fragment regression fixtures.
ENTRY_SEPARATOR_RE = re.compile(r"(?m)^\s*(?:\*\*\*|---)\s*$")
H4_RE = re.compile(r"(?m)^####\s+(?P<title>.+?)\s*$")
IMAGE_LINE_RE = re.compile(
    r'(?m)^\s*(?P<markdown>!\[[^\]\n]*\]\((?P<src>[^)\s]+)(?:\s+"[^"]*")?\)(?:\{[^\n}]*\})?)\s*$'
)
ANCESTRY_MARKER_RE = re.compile(r"(?m)^\s*\*\*Features\*\*\s*$")
ANCESTRY_FEATURE_RE = re.compile(r"(?m)^\s*\*\*(?P<name>.+?):\*\*\s*(?P<lead>.*)$")
COMMUNITY_MARKER_RE = re.compile(r"(?m)^\s*\*\*Community Feature\s+[—-]\s+(?P<name>.+?)\*\*\s*$")
RAW_MKDOCS_RE = re.compile(r"(?im)^\s*</?div(?:\s+[^>]*)?>\s*$")
HEADING_ATTR_RE = re.compile(r"\s+\{[^{}]*\}\s*$")


@dataclass
class Paths:
    repo_root: Path
    config: Path
    lua_filter: Path
    prose_config: Path
    prose_builder: Path
    source: Path
    player_source: Path
    asset_root: Path
    output: Path
    report: Path
    work: Path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_prose_builder(path: Path) -> Any:
    if not path.is_file():
        raise RuntimeError(f"Accepted Long-Form Prose builder is missing: {path}")
    spec = importlib.util.spec_from_file_location("cybermancy_step6_prose_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Long-Form Prose builder: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def add_check(
    report: dict[str, Any],
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["errors"].append(item)
        report["status"] = "FAIL"
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def report_shell(paths: Paths, command: str) -> dict[str, Any]:
    return {
        "schema": "cybermancy-step6-character-origins-validation-v1.0",
        "status": "PASS",
        "command": command,
        "builderVersion": SCRIPT_VERSION,
        "implementationPatch": "0.1.2-pdf-text-presence-validation",
        "layoutContract": str(paths.config),
        "inherits": str(paths.prose_config),
        "checks": [],
        "warnings": [],
        "errors": [],
        "paths": {
            "completeRulebook": str(paths.source),
            "playerGuide": str(paths.player_source),
            "assetRoot": str(paths.asset_root),
            "output": str(paths.output),
            "work": str(paths.work),
        },
    }


def resolve_paths(args: argparse.Namespace) -> Paths:
    return Paths(
        repo_root=Path(args.repo_root).resolve(),
        config=Path(args.config).resolve(),
        lua_filter=Path(args.lua_filter).resolve(),
        prose_config=Path(args.prose_config).resolve(),
        prose_builder=Path(args.prose_builder).resolve(),
        source=Path(args.source).resolve(),
        player_source=Path(args.player_source).resolve(),
        asset_root=Path(args.asset_root).resolve(),
        output=Path(args.output).resolve(),
        report=Path(args.report).resolve(),
        work=Path(args.work).resolve(),
    )


def extract_target_chapters(prose: Any, source_text: str) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for part in prose.parse_source(source_text):
        for chapter in part.get("chapters", []):
            number = int(chapter.get("number", -1))
            if number not in TARGET_CHAPTERS:
                continue
            if number in found:
                raise ValueError(f"Chapter {number} appears more than once")
            found[number] = chapter
    return found


def normalize_title(title: str) -> str:
    value = HEADING_ATTR_RE.sub("", title).strip()
    for left, right in (("**", "**"), ("__", "__"), ("*", "*"), ("_", "_"), ("`", "`")):
        if value.startswith(left) and value.endswith(right) and len(value) > len(left) + len(right):
            return value[len(left):-len(right)].strip()
    return value


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def parse_ancestry_features(text: str) -> tuple[str, list[dict[str, str]]]:
    marker = ANCESTRY_MARKER_RE.search(text)
    if not marker:
        raise ValueError("missing **Features** marker")
    flavor = text[:marker.start()].strip()
    feature_text = text[marker.end():].strip()
    matches = list(ANCESTRY_FEATURE_RE.finditer(feature_text))
    if not matches or feature_text[:matches[0].start()].strip():
        raise ValueError("invalid Ancestory Feature structure")
    features: list[dict[str, str]] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(feature_text)
        continuation = feature_text[match.end():end].strip()
        desc = "\n".join(
            x for x in (match.group("lead").strip(), continuation) if x
        ).strip()
        if not desc:
            raise ValueError(f"Feature {match.group('name').strip()!r} has no rules text")
        features.append({"name": match.group("name").strip(), "description": desc})
    return flavor, features


def parse_community_feature(text: str) -> tuple[str, list[dict[str, str]]]:
    marker = COMMUNITY_MARKER_RE.search(text)
    if not marker:
        raise ValueError("missing **Community Feature — <name>** marker")
    flavor = text[:marker.start()].strip()
    desc = text[marker.end():].strip()
    if not desc:
        raise ValueError(
            f"Community Feature {marker.group('name').strip()!r} has no rules text"
        )
    return flavor, [{"name": marker.group("name").strip(), "description": desc}]


def parse_entry_chunk(chunk: str, chapter_number: int, entry_kind: str) -> dict[str, Any]:
    images = list(IMAGE_LINE_RE.finditer(chunk))
    headings = list(H4_RE.finditer(chunk))
    if len(images) != 1 or len(headings) != 1:
        raise ValueError(
            f"expected one artwork and one H4; found images={len(images)} H4={len(headings)}"
        )
    image, heading = images[0], headings[0]
    if (
        heading.start() < image.end()
        or chunk[:image.start()].strip()
        or chunk[image.end():heading.start()].strip()
    ):
        raise ValueError("entry artwork/H4 adjacency structure is unsupported")

    title = normalize_title(heading.group("title"))
    body = chunk[heading.end():].strip()
    if not body:
        raise ValueError(f"entry {title!r} has no prose")

    if entry_kind == "ancestory":
        flavor, features = parse_ancestry_features(body)
        label = "Features"
    elif entry_kind == "community":
        flavor, features = parse_community_feature(body)
        label = "Community Feature"
    else:
        raise ValueError(f"unknown entry kind: {entry_kind}")

    paragraphs = split_paragraphs(flavor)
    if not paragraphs:
        raise ValueError(f"entry {title!r} has no flavor paragraph")

    return {
        "chapter": chapter_number,
        "kind": entry_kind,
        "title": title,
        "imageMarkdown": image.group("markdown").strip(),
        "imageSource": image.group("src").strip(),
        "flavorParagraphs": paragraphs,
        "featureLabel": label,
        "features": features,
    }


def parse_chapter_entries(
    markdown: str,
    chapter_number: int,
    entry_kind: str,
) -> tuple[str, list[dict[str, Any]]]:
    pieces = ENTRY_SEPARATOR_RE.split(markdown)
    if len(pieces) < 2 or not pieces[0].strip():
        styles = sorted(
            set(
                match.group(0).strip()
                for match in re.finditer(r"(?m)^\s*(?:\*\*\*|---)\s*$", markdown)
            )
        )
        raise ValueError(
            f"Chapter {chapter_number} lacks expected preamble/entry separators"
            + (f"; detected separator styles: {styles}" if styles else "")
        )

    entries: list[dict[str, Any]] = []
    for index, chunk in enumerate(pieces[1:], 1):
        if not chunk.strip():
            continue
        try:
            entries.append(parse_entry_chunk(chunk, chapter_number, entry_kind))
        except ValueError as exc:
            raise ValueError(f"Chapter {chapter_number} entry block {index}: {exc}") from exc
    return pieces[0].strip(), entries


def annotated_entry(entry: dict[str, Any]) -> str:
    flavor = entry["flavorParagraphs"]
    out = [
        "::: {.cm-origin-identity}",
        entry["imageMarkdown"],
        "",
        f"#### {entry['title']}",
        "",
        flavor[0],
        ":::",
        "",
    ]
    for paragraph in flavor[1:]:
        out.extend([paragraph, ""])
    out.extend(
        [
            "::: {.cm-origin-feature-label}",
            entry["featureLabel"],
            ":::",
            "",
        ]
    )
    for feature in entry["features"]:
        out.extend(
            [
                "::: {.cm-origin-feature}",
                f"**{feature['name']}**",
                "",
                feature["description"],
                ":::",
                "",
            ]
        )
    return "\n".join(out).strip()


def annotate_chapter(
    markdown: str,
    chapter_number: int,
    entry_kind: str,
) -> tuple[str, list[dict[str, Any]]]:
    preamble, entries = parse_chapter_entries(markdown, chapter_number, entry_kind)
    chunks = [preamble]
    for entry in entries:
        # Keep temporary fragments Pandoc-safe for the same reason Step 4 does.
        chunks.extend(["***", annotated_entry(entry)])
    return "\n\n".join(chunks).strip() + "\n", entries


def validate_static(
    paths: Paths,
    report: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    for code, path in [
        ("CONFIG_PRESENT", paths.config),
        ("PROSE_CONFIG_PRESENT", paths.prose_config),
        ("PROSE_BUILDER_PRESENT", paths.prose_builder),
        ("COMPLETE_SOURCE_PRESENT", paths.source),
        ("PLAYER_SOURCE_PRESENT", paths.player_source),
    ]:
        add_check(
            report,
            code,
            "PASS" if path.is_file() else "ERROR",
            f"{path.name} {'present' if path.is_file() else 'missing'}",
            str(path),
        )
    if report["status"] != "PASS":
        return None, None

    try:
        config = load_json(paths.config)
        prose_config = load_json(paths.prose_config)
    except Exception as exc:
        add_check(report, "CONFIG_PARSE", "ERROR", str(exc))
        return None, None

    if (
        config.get("schema") != "cybermancy-rulebook-character-origins-layout-v1"
        or config.get("version") != "1.0"
    ):
        add_check(report, "LAYOUT_VERSION", "ERROR", "Expected Character Origins v1.0 draft")
    else:
        add_check(
            report,
            "LAYOUT_VERSION",
            "PASS",
            f"Character Origins v1.0 loaded ({config.get('status')})",
        )

    if (
        prose_config.get("schema") != "cybermancy-rulebook-prose-layout-v1"
        or prose_config.get("version") != "1.0"
        or str((config.get("inherits") or {}).get("version")) != "1.0"
    ):
        add_check(
            report,
            "PROSE_INHERITANCE",
            "ERROR",
            "Long-Form Prose v1.0 inheritance is not valid",
        )
    else:
        add_check(
            report,
            "PROSE_INHERITANCE",
            "PASS",
            "Long-Form Prose v1.0 is the inherited publication shell",
        )
    return config, prose_config


def inspect_corpus(
    paths: Paths,
    prose: Any,
    report: dict[str, Any],
    config: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    complete = extract_target_chapters(
        prose, paths.source.read_text(encoding="utf-8")
    )
    player = extract_target_chapters(
        prose, paths.player_source.read_text(encoding="utf-8")
    )

    missing_complete = [n for n in TARGET_CHAPTERS if n not in complete]
    missing_player = [n for n in TARGET_CHAPTERS if n not in player]
    if missing_complete or missing_player:
        add_check(
            report,
            "CHAPTER_ROUTING",
            "ERROR",
            "Chapters 10-11 missing from Step 4 profiles",
            {"completeMissing": missing_complete, "playerMissing": missing_player},
        )
        return complete
    add_check(
        report,
        "CHAPTER_ROUTING",
        "PASS",
        "Chapters 10-11 found in both Step 4 profiles",
    )

    mismatch = [
        {
            "chapter": n,
            "completeSha256": sha256_text(complete[n]["markdown"]),
            "playerSha256": sha256_text(player[n]["markdown"]),
        }
        for n in TARGET_CHAPTERS
        if complete[n]["markdown"] != player[n]["markdown"]
    ]
    add_check(
        report,
        "PROFILE_EQUIVALENCE",
        "ERROR" if mismatch else "PASS",
        "Profile Chapter 10-11 fragments differ"
        if mismatch
        else "Complete Rulebook and Player Guide Chapter 10-11 fragments are identical",
        mismatch or None,
    )

    inspection: dict[str, Any] = {}
    for number in TARGET_CHAPTERS:
        chapter = complete[number]
        expected = config["expectedCorpus"][str(number)]

        if chapter.get("title") != expected["title"]:
            add_check(
                report,
                f"CH{number}_TITLE",
                "ERROR",
                "Chapter title differs",
                {"expected": expected["title"], "actual": chapter.get("title")},
            )

        raw = RAW_MKDOCS_RE.findall(chapter["markdown"])
        add_check(
            report,
            f"CH{number}_RAW_HTML",
            "ERROR" if raw else "PASS",
            f"Chapter {number} contains raw MkDocs wrappers"
            if raw
            else f"Chapter {number} has no raw MkDocs wrappers",
            raw[:20] or None,
        )

        defects = prose.find_adjacent_image_headings(chapter["markdown"])
        add_check(
            report,
            f"CH{number}_IMAGE_HEADING_BOUNDARY",
            "ERROR" if defects else "PASS",
            f"Chapter {number} contains image/heading boundary defects"
            if defects
            else f"Chapter {number} image/heading boundaries are valid",
            defects or None,
        )

        separator_styles = sorted(
            set(m.group(0).strip() for m in ENTRY_SEPARATOR_RE.finditer(chapter["markdown"]))
        )
        add_check(
            report,
            f"CH{number}_ENTRY_SEPARATOR_STYLE",
            "PASS" if separator_styles else "ERROR",
            f"Chapter {number} entry separators recognized: {', '.join(separator_styles)}"
            if separator_styles
            else f"Chapter {number} has no recognized normalized entry separators",
            separator_styles or None,
        )

        try:
            _, entries = parse_chapter_entries(
                chapter["markdown"], number, expected["entryKind"]
            )
        except Exception as exc:
            add_check(report, f"CH{number}_ENTRY_PARSE", "ERROR", str(exc))
            continue

        names = [e["title"] for e in entries]
        expected_names = list(expected["entries"])
        add_check(
            report,
            f"CH{number}_ENTRY_IDENTITY",
            "PASS" if names == expected_names else "ERROR",
            f"Chapter {number} exact entry identity/order "
            + ("matches" if names == expected_names else "differs"),
            {"expected": expected_names, "actual": names}
            if names != expected_names
            else len(names),
        )

        expected_features = int(expected["featuresPerEntry"])
        feature_errors = [
            {
                "entry": e["title"],
                "expected": expected_features,
                "actual": len(e["features"]),
            }
            for e in entries
            if len(e["features"]) != expected_features
        ]
        add_check(
            report,
            f"CH{number}_FEATURE_COUNTS",
            "ERROR" if feature_errors else "PASS",
            f"Chapter {number} Feature cardinality differs"
            if feature_errors
            else f"Every Chapter {number} entry has {expected_features} Feature(s)",
            feature_errors or None,
        )

        inspection[str(number)] = {
            "title": chapter.get("title"),
            "semanticId": chapter.get("semanticId"),
            "entryKind": expected["entryKind"],
            "entryCount": len(entries),
            "separatorStyles": separator_styles,
            "entries": [
                {
                    "name": e["title"],
                    "image": e["imageSource"],
                    "flavorParagraphs": len(e["flavorParagraphs"]),
                    "features": [f["name"] for f in e["features"]],
                }
                for e in entries
            ],
        }

    report["inspection"] = inspection
    return complete


def validate_toolchain(paths: Paths, prose: Any, report: dict[str, Any]) -> None:
    add_check(
        report,
        "LUA_FILTER_PRESENT",
        "PASS" if paths.lua_filter.is_file() else "ERROR",
        f"Lua filter {'present' if paths.lua_filter.is_file() else 'missing'}",
        str(paths.lua_filter),
    )
    for tool in ("pandoc", "lualatex"):
        resolved = prose.resolve_tool(tool)
        add_check(
            report,
            f"TOOL_{tool.upper()}",
            "PASS" if resolved else "ERROR",
            f"{tool} available"
            if resolved
            else f"{tool} not found through accepted Prose resolution",
            {"path": resolved, "version": prose.executable_version(tool)}
            if resolved
            else None,
        )


def character_origin_preamble(
    config: dict[str, Any],
    prose_config: dict[str, Any],
    prose: Any,
) -> str:
    identity = config["entryGrammar"]["identityRow"]
    feature = config["entryGrammar"]["featureGroup"]
    typo = prose_config["typography"]
    delta = rf'''
% Character Origins Outcome B delta; Long-Form Prose v1.0 remains authoritative.
\newcommand{{\CMOriginEntryRule}}{{\par\vspace{{5pt}}\noindent{{\color{{CMCyan!38}}\rule{{\columnwidth}}{{0.45pt}}}}\vspace{{5pt}}\par}}
\newcommand{{\CMOriginIdentityImage}}[1]{{\includegraphics[width=\linewidth,height={float(identity['imageMaxHeightInches']):.3f}in,keepaspectratio]{{#1}}}}
\newcommand{{\CMOriginIdentityMissing}}[1]{{\fcolorbox{{CMCyan!45}}{{white}}{{\parbox[c][1.02in][c]{{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}}{{\centering\sffamily\fontsize{{7.3}}{{8.6}}\selectfont\color{{CMTeal}}\textbf{{STAGED ART}}\\\color{{CMInk}}#1}}}}}}
\newcommand{{\CMOriginIdentity}}[3]{{\par\Needspace{{11\baselineskip}}\vspace{{2pt}}\noindent\begin{{minipage}}{{\columnwidth}}\begin{{minipage}}[t]{{{float(identity['imageColumnFraction']):.3f}\linewidth}}\vspace{{0pt}}#1\end{{minipage}}\hfill\begin{{minipage}}[t]{{{float(identity['textColumnFraction']):.3f}\linewidth}}\vspace{{0pt}}{{\sffamily\fontsize{{{float(identity['titleSizePt']):.2f}}}{{{float(identity['titleLeadingPt']):.2f}}}\selectfont\bfseries\color{{CMInk}}#2\par}}\vspace{{3pt}}{{\fontsize{{{float(typo['bodySizePt']):.2f}}}{{{float(typo['bodyLeadingPt']):.2f}}}\selectfont\RaggedRight #3\par}}\end{{minipage}}\end{{minipage}}\par\vspace{{4pt}}}}
\newcommand{{\CMOriginFeatureLabel}}[1]{{\par\Needspace{{4\baselineskip}}\vspace{{4pt}}{{\sffamily\fontsize{{8.4}}{{10.0}}\selectfont\bfseries\color{{CMTeal}}\MakeUppercase{{#1}}\par}}\vspace{{1.5pt}}}}
\newcommand{{\CMOriginFeature}}[2]{{\par\Needspace{{3\baselineskip}}{{\sffamily\fontsize{{{float(feature['featureNameSizePt']):.2f}}}{{{float(feature['featureNameLeadingPt']):.2f}}}\selectfont\bfseries\color{{CMInk}}#1\par}}\vspace{{0.6pt}}#2\par\vspace{{3.2pt}}}}
'''
    base = prose.document_preamble().replace(
        "STEP 6 // LONG-FORM PROSE // V1.0",
        "STEP 6 // CHARACTER ORIGINS // V1.0",
    ).replace("PLAYER WORLD", "PLAYER OPTIONS")
    if "\\begin{document}" not in base:
        raise RuntimeError("Accepted Prose preamble has no document-start marker")
    return base.replace("\\begin{document}", delta + "\n\\begin{document}", 1)


def validate_pdf_text(paths: Paths, prose: Any, report: dict[str, Any]) -> None:
    tool = prose.resolve_tool("pdftotext")
    if not tool:
        add_check(
            report,
            "PDF_TEXT_SEMANTICS",
            "INFO",
            "pdftotext unavailable; rendered semantic text check skipped",
        )
        return

    p = prose.run([tool, str(paths.output), "-"])
    if p.returncode != 0:
        add_check(
            report,
            "PDF_TEXT_SEMANTICS",
            "WARNING",
            "pdftotext extraction failed",
            (p.stderr or "")[-2000:],
        )
        return

    # pdf text extraction order is not a reliable proxy for visual/source order
    # in a two-column document containing minipages. Canonical order is already
    # asserted by CH10/CH11_ENTRY_IDENTITY before rendering. Here we only verify
    # that the expected semantic labels survived into extractable PDF text.
    text = re.sub(r"\s+", " ", p.stdout or "").strip()
    missing: list[str] = []
    checked_entries = 0
    checked_features = 0
    for chapter_number in map(str, TARGET_CHAPTERS):
        entries = report.get("inspection", {}).get(chapter_number, {}).get("entries", [])
        for entry in entries:
            checked_entries += 1
            if entry["name"] not in text:
                missing.append(entry["name"])
            for feature_name in entry.get("features", []):
                checked_features += 1
                if feature_name not in text:
                    missing.append(f"{entry['name']} :: {feature_name}")

    add_check(
        report,
        "PDF_TEXT_SEMANTICS",
        "ERROR" if missing else "PASS",
        "Rendered PDF is missing expected entry/Feature text"
        if missing
        else (
            f"All {checked_entries} entry headings and {checked_features} Feature names "
            "are present in extracted PDF text"
        ),
        missing or {
            "entryOrderValidatedBy": "normalized corpus + deterministic annotation/Pandoc block order",
            "pdfTextValidation": "presence only; pdftotext stream order is not stable for multicolumn/minipage layouts",
        },
    )


def write_report(paths: Paths, report: dict[str, Any]) -> None:
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def inspect_or_validate(
    paths: Paths,
    command: str,
) -> tuple[
    dict[str, Any],
    Any | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[int, dict[str, Any]],
]:
    report = report_shell(paths, command)
    config, prose_config = validate_static(paths, report)
    if config is None or prose_config is None or report["status"] != "PASS":
        write_report(paths, report)
        return report, None, config, prose_config, {}

    try:
        prose = load_prose_builder(paths.prose_builder)
    except Exception as exc:
        add_check(report, "PROSE_BUILDER_LOAD", "ERROR", str(exc))
        write_report(paths, report)
        return report, None, config, prose_config, {}

    add_check(
        report,
        "PROSE_BUILDER_LOAD",
        "PASS",
        "Accepted Long-Form Prose builder loaded as reusable runtime",
    )
    chapters = inspect_corpus(paths, prose, report, config)
    if command in {"validate", "build"}:
        validate_toolchain(paths, prose, report)
    write_report(paths, report)
    return report, prose, config, prose_config, chapters


def build(paths: Paths) -> dict[str, Any]:
    report, prose, config, prose_config, chapters = inspect_or_validate(paths, "build")
    if (
        prose is None
        or config is None
        or prose_config is None
        or report["status"] != "PASS"
    ):
        return report

    if paths.output.exists():
        paths.output.unlink()
    if paths.work.exists():
        shutil.rmtree(paths.work)
    paths.work.mkdir(parents=True, exist_ok=True)
    fragments = paths.work / "fragments"
    asset_cache = paths.work / "assets"
    fragments.mkdir(parents=True, exist_ok=True)
    asset_cache.mkdir(parents=True, exist_ok=True)

    missing_assets: list[dict[str, Any]] = []
    resolved_assets = 0
    pandoc_warnings: list[str] = []
    document = [character_origin_preamble(config, prose_config, prose)]

    for number in TARGET_CHAPTERS:
        chapter = chapters[number]
        kind = config["expectedCorpus"][str(number)]["entryKind"]
        annotated, _ = annotate_chapter(chapter["markdown"], number, kind)
        staged, resolved = prose.stage_markdown_assets(
            annotated,
            number,
            paths.asset_root,
            asset_cache,
            missing_assets,
        )
        resolved_assets += resolved

        md_path = fragments / f"chapter-{number:02d}.annotated.md"
        body_path = fragments / f"chapter-{number:02d}.body.tex"
        md_path.write_text(staged, encoding="utf-8")
        _, stderr = prose.run_pandoc_body(
            md_path,
            body_path,
            paths.lua_filter,
            paths.work,
        )
        pandoc_warnings.extend(
            line.strip() for line in stderr.splitlines() if line.strip()
        )
        document.extend(
            [
                prose.chapter_banner_tex(chapter),
                body_path.read_text(encoding="utf-8"),
                "\\end{multicols}\n",
            ]
        )

    document.append(prose.document_end())
    tex_path = paths.work / "Cybermancy_Chapters10_11_CharacterOrigins_Step6.tex"
    tex_path.write_text("\n".join(document), encoding="utf-8")
    add_check(
        report,
        "LATEX_GENERATED",
        "PASS",
        "Annotated Character Origins Markdown assembled to TeX",
        str(tex_path),
    )
    add_check(
        report,
        "PANDOC_WARNINGS",
        "WARNING" if pandoc_warnings else "PASS",
        f"Pandoc emitted {len(pandoc_warnings)} diagnostic line(s)"
        if pandoc_warnings
        else "Pandoc emitted no warnings",
        pandoc_warnings[:80] or None,
    )

    unique_missing = sorted({item["source"] for item in missing_assets})
    add_check(
        report,
        "ASSETS",
        "ERROR" if unique_missing else "PASS",
        f"{len(unique_missing)} Character Origins assets are missing from Step 4 staging"
        if unique_missing
        else f"All {resolved_assets} Character Origins artwork references resolved",
        unique_missing or None,
    )

    if report["status"] == "PASS":
        try:
            compile_log, latex_warnings = prose.compile_lualatex(
                tex_path, paths.output, paths.work
            )
        except Exception as exc:
            add_check(report, "PDF_COMPILED", "ERROR", str(exc))
        else:
            add_check(
                report,
                "PDF_COMPILED",
                "PASS",
                "LuaLaTeX produced Character Origins regression PDF",
                str(paths.output),
            )
            overfull = sorted(
                set(re.findall(r"(?m)^Overfull \\[hv]box.*$", compile_log))
            )
            add_check(
                report,
                "OVERFULL_BOXES",
                "ERROR" if overfull else "PASS",
                f"LuaLaTeX emitted {len(overfull)} overfull box warning(s)"
                if overfull
                else "No overfull hbox/vbox warnings detected",
                overfull[:100] or None,
            )
            other = [
                line for line in latex_warnings if not line.startswith("Overfull ")
            ]
            add_check(
                report,
                "LATEX_WARNINGS",
                "WARNING" if other else "PASS",
                f"LuaLaTeX emitted {len(other)} other material warning(s)"
                if other
                else "No additional material LaTeX warnings detected",
                other[:100] or None,
            )

    if paths.output.is_file():
        pages = prose.pdf_page_count(paths.output)
        add_check(
            report,
            "PAGE_COUNT",
            "PASS" if pages else "WARNING",
            f"PDF page count: {pages if pages else 'unknown'}",
            pages,
        )
        validate_pdf_text(paths, prose, report)
        report["outputSha256"] = sha256_file(paths.output)

    report["implementationDetails"] = {
        "renderer": "Step 4 normalized Markdown -> prose-derived Character Option Entry annotations -> Pandoc AST -> Character Origins Lua -> inherited Prose v1.0 LuaLaTeX shell",
        "targetChapters": list(TARGET_CHAPTERS),
        "expectedEntries": 27,
        "identityRow": config["entryGrammar"]["identityRow"],
        "resolvedAssetReferences": resolved_assets,
        "missingAssetCount": len(unique_missing),
        "temporaryAnnotationsAreCanonical": False,
        "step4ThematicBreakCompatibility": "accepts *** and ---; temporary fragments emit ***",
        "pdfTextSemanticPolicy": "presence-only; canonical order is validated from normalized corpus because pdftotext order is unstable for multicolumn/minipage layouts",
        "diagnosticArtifacts": {
            "generatedTex": str(tex_path),
            "annotatedMarkdownDirectory": str(fragments),
            "passLogsDirectory": str(paths.work / "logs"),
        },
    }
    write_report(paths, report)
    return report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Inspect, validate, or build Chapters 10-11 Character Origins Outcome B"
    )
    p.add_argument(
        "command",
        nargs="?",
        choices=["inspect", "validate", "build"],
        default="inspect",
    )
    p.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--lua-filter", default=str(DEFAULT_FILTER))
    p.add_argument("--prose-config", default=str(DEFAULT_PROSE_CONFIG))
    p.add_argument("--prose-builder", default=str(DEFAULT_PROSE_BUILDER))
    p.add_argument("--source", default=str(DEFAULT_SOURCE))
    p.add_argument("--player-source", default=str(DEFAULT_PLAYER_SOURCE))
    p.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--work", default=str(DEFAULT_WORK))
    return p


def main() -> int:
    args = parser().parse_args()
    paths = resolve_paths(args)
    report = (
        build(paths)
        if args.command == "build"
        else inspect_or_validate(paths, args.command)[0]
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(paths.report),
                "output": str(paths.output) if paths.output.is_file() else None,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
