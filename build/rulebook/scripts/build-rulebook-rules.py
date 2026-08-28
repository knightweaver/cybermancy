#!/usr/bin/env python3
"""Cybermancy Step 6 Part II Rules Layout prototype builder.

Reuses the accepted Long-Form Prose v1.0 Pandoc + LuaLaTeX engine while
changing only Part II routing and the approved rules-specific proof grammar.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent
LAYOUT_DIR = RULEBOOK_DIR / "layout" / "rules"
PROSE_BUILDER = SCRIPT_DIR / "build-rulebook-prose.py"

DEFAULT_CONFIG = LAYOUT_DIR / "rules-layout-v1.json"
DEFAULT_FILTER = LAYOUT_DIR / "pandoc" / "rules.lua"
DEFAULT_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "player-guide.md"
DEFAULT_CROSS_PROFILE = RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md"
DEFAULT_ASSET_ROOT = RULEBOOK_DIR / "source" / "assets"
DEFAULT_OUTPUT = LAYOUT_DIR / "output" / "Cybermancy_Part_II_Rules_Design_Proof_v1.pdf"
DEFAULT_REPORT = LAYOUT_DIR / "reports" / "rules-design-proof-v1.json"
DEFAULT_WORK = LAYOUT_DIR / "work" / "pandoc-lualatex-v1"

PART_ID = "section:part-ii-rules"
ALL_PART_II_CHAPTERS = {4, 5, 6, 7, 8, 9}
DESIGN_PROOF_CHAPTERS = {4, 6, 8, 9}


def _load_prose_builder():
    spec = importlib.util.spec_from_file_location("cybermancy_step6_prose_base", PROSE_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load accepted prose builder: {PROSE_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_prose_builder()
BASE.TARGET_PARTS = {
    PART_ID: (
        "II",
        "Cybermancy Rules",
        "The procedures, pressure systems, and operational rules that make the sprawl move.",
    )
}
BASE.TARGET_CHAPTERS = set(DESIGN_PROOF_CHAPTERS)
_BASE_PREAMBLE = BASE.document_preamble
_BASE_REPORT_SHELL = BASE.report_shell


def rules_document_preamble() -> str:
    text = _BASE_PREAMBLE()
    text = text.replace("STEP 6 // LONG-FORM PROSE // V1.0", "STEP 6 // CYBERMANCY RULES // PROTOTYPE")
    text = text.replace("\\newcommand{\\CMRunningMarker}{PLAYER WORLD}", "\\newcommand{\\CMRunningMarker}{CYBERMANCY RULES}")
    text = text.replace("\\renewcommand{\\CMRunningMarker}{PLAYER WORLD}", "\\renewcommand{\\CMRunningMarker}{CYBERMANCY RULES}")
    # The accepted prose preamble uses CMRunningAccent as a command that stores
    # a color name, but its fancyhdr definitions pass the command name to xcolor
    # literally. Expand the command when the rules lane inherits the preamble.
    # This remains lane-local and does not mutate the frozen prose implementation.
    text = text.replace(r"\color{CMRunningAccent}", r"\color{\CMRunningAccent}")
    extension = r'''
% ---- Part II Rules Layout prototype extensions ----
% Mechanical blockquotes must remain flowable. A list + Needspace wrapper caused
% a nearly blank page when a short callout fell between full-width rules tables.
% Use paragraph indentation only: neutral visual treatment, no semantic subtype,
% and no artificial page/column reservation.
\newenvironment{CMRulesQuote}{%
  \par\vspace{3pt}%
  \begingroup
  \leftskip=0.12in%
  \rightskip=0.02in%
  \parindent=0pt%
  \parskip=2pt%
  \color{CMBody}\fontsize{9.6}{13.0}\selectfont
}{%
  \par\endgroup\vspace{2pt}\par
}
\newenvironment{CMRulesTable}{\begin{CMProseTable}}{\end{CMProseTable}}
\setlist[enumerate,1]{%
  label=\textcolor{CMTeal}{\sffamily\bfseries\arabic*.},%
  leftmargin=1.45em,itemsep=2.8pt,topsep=3.5pt
}
'''
    marker = "\\begin{document}"
    if marker not in text:
        raise RuntimeError("Accepted prose preamble no longer exposes the rules extension point.")
    return text.replace(marker, extension + "\n" + marker, 1)


BASE.document_preamble = rules_document_preamble


def _rules_validate_inputs(paths, report):
    for code, path in (("CONFIG_PRESENT", paths.config), ("SOURCE_PRESENT", paths.source), ("LUA_FILTER_PRESENT", paths.lua_filter)):
        BASE.add_check(report, code, "PASS" if path.is_file() else "ERROR",
                       f"{code.split('_')[0]} {'present' if path.is_file() else 'missing'}", str(path))
    pandoc_path = BASE.resolve_tool("pandoc")
    lualatex_path = BASE.resolve_tool("lualatex")
    BASE.add_check(report, "TOOL_PANDOC", "PASS" if pandoc_path else "ERROR",
                   "pandoc available" if pandoc_path else "pandoc not found", pandoc_path)
    BASE.add_check(report, "TOOL_LUALATEX", "PASS" if lualatex_path else "ERROR",
                   "lualatex available" if lualatex_path else "lualatex not found", lualatex_path)
    if report["status"] != "PASS":
        return None
    config = BASE.load_json(paths.config)
    valid = (config.get("schema") == "cybermancy-rulebook-rules-layout-v1"
             and config.get("version") == "1.0-prototype"
             and config.get("status") == "PROTOTYPE")
    BASE.add_check(report, "LAYOUT_VERSION", "PASS" if valid else "ERROR",
                   "Rules Layout v1 prototype loaded" if valid else "Expected Rules Layout v1 prototype contract")
    BASE.add_check(report, "INHERITED_PROSE_CONTRACT", "PASS",
                   "Rules lane inherits Long-Form Prose v1.0 production grammar and toolchain")
    return config if valid else None


BASE.validate_inputs = _rules_validate_inputs


def _rules_validate_structure(parts: list[dict[str, Any]], report: dict[str, Any]) -> None:
    found_parts = {p["semanticId"] for p in parts}
    found_chapters = {c["number"] for p in parts for c in p["chapters"]}
    missing_parts = sorted({PART_ID} - found_parts)
    missing_chapters = sorted(DESIGN_PROOF_CHAPTERS - found_chapters)
    BASE.add_check(
        report, "DESIGN_PROOF_ROUTING", "ERROR" if (missing_parts or missing_chapters) else "PASS",
        "Part II design-proof routing is incomplete" if (missing_parts or missing_chapters)
        else "Part II design-proof chapters 4, 6, 8, and 9 resolved",
        {"missingParts": missing_parts, "missingChapters": missing_chapters, "found": sorted(found_chapters)},
    )


BASE.validate_structure = _rules_validate_structure


def _part_ii_map(text: str) -> dict[int, dict[str, Any]]:
    for part in BASE.parse_source(text):
        if part.get("semanticId") == PART_ID:
            return {int(ch["number"]): ch for ch in part.get("chapters", [])}
    return {}


def _validate_profiles(source: Path, cross_profile: Path, report: dict[str, Any]) -> None:
    if not source.is_file():
        return
    primary = _part_ii_map(source.read_text(encoding="utf-8"))
    missing = sorted(ALL_PART_II_CHAPTERS - set(primary))
    BASE.add_check(report, "PART_II_PRIMARY_CORPUS", "ERROR" if missing else "PASS",
                   "Primary player-guide Part II corpus is complete" if not missing else "Primary player-guide Part II corpus is incomplete",
                   {"found": sorted(primary), "missing": missing})
    if not cross_profile.is_file():
        BASE.add_check(report, "CROSS_PROFILE_PART_II", "INFO",
                       "Complete-rulebook profile unavailable; cross-profile comparison skipped", str(cross_profile))
        return
    complete = _part_ii_map(cross_profile.read_text(encoding="utf-8"))
    mismatches = []
    for number in sorted(ALL_PART_II_CHAPTERS):
        left, right = primary.get(number), complete.get(number)
        if left is None or right is None:
            mismatches.append({"chapter": number, "issue": "missing-profile-chapter"})
        elif (left.get("title"), left.get("audience"), left.get("markdown")) != (right.get("title"), right.get("audience"), right.get("markdown")):
            mismatches.append({"chapter": number, "issue": "normalized-content-differs"})
    BASE.add_check(report, "CROSS_PROFILE_PART_II", "ERROR" if mismatches else "PASS",
                   "Part II differs between assembled publication profiles" if mismatches
                   else "Part II normalized content matches between player-guide and complete-rulebook",
                   mismatches if mismatches else {"chapters": sorted(ALL_PART_II_CHAPTERS)})


def _report_shell(paths) -> dict[str, Any]:
    report = _BASE_REPORT_SHELL(paths)
    report["schema"] = "cybermancy-step6-rules-layout-validation-v1.0-prototype"
    report["implementation"] = "rules-layout-prototype-on-accepted-prose-engine"
    report["implementationPatch"] = "phase-b-design-proof-glyph-and-quote-flow"
    return report


BASE.report_shell = _report_shell


def _paths(args: argparse.Namespace):
    return BASE.Paths(
        repo_root=Path(args.repo_root).resolve(), config=Path(args.config).resolve(),
        lua_filter=Path(args.lua_filter).resolve(), source=Path(args.source).resolve(),
        asset_root=Path(args.asset_root).resolve(), output=Path(args.output).resolve(),
        report=Path(args.report).resolve(), work=Path(args.work).resolve(),
    )


def run_build(args: argparse.Namespace) -> dict[str, Any]:
    paths = _paths(args)
    report = BASE.build(paths)
    _validate_profiles(paths.source, Path(args.cross_profile).resolve(), report)
    report.setdefault("implementationDetails", {}).update({
        "lane": "Part II Cybermancy Rules",
        "designProofChapters": sorted(DESIGN_PROOF_CHAPTERS),
        "requiredPartIIChapters": sorted(ALL_PART_II_CHAPTERS),
        "primaryProfile": str(paths.source),
        "crossProfile": str(Path(args.cross_profile).resolve()),
        "semanticPolicy": "no wording-, filename-, or chapter-specific semantic inference",
        "deferredSemantics": ["rulesCallout.kind", "imageRole=chapter-lead", "stateTrack.label+states"],
    })
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def validate_only(args: argparse.Namespace) -> dict[str, Any]:
    paths = _paths(args)
    report = _report_shell(paths)
    _rules_validate_inputs(paths, report)
    if paths.source.is_file():
        parts = BASE.select_target_parts(BASE.parse_source(paths.source.read_text(encoding="utf-8")))
        _rules_validate_structure(parts, report)
    _validate_profiles(paths.source, Path(args.cross_profile).resolve(), report)
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", nargs="?", choices=("validate", "build"), default="build")
    p.add_argument("--repo-root", default=str(REPO_ROOT))
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--lua-filter", default=str(DEFAULT_FILTER))
    p.add_argument("--source", default=str(DEFAULT_SOURCE))
    p.add_argument("--cross-profile", default=str(DEFAULT_CROSS_PROFILE))
    p.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--work", default=str(DEFAULT_WORK))
    return p


def main() -> int:
    args = parser().parse_args()
    report = validate_only(args) if args.command == "validate" else run_build(args)
    print(json.dumps({"status": report.get("status"), "report": args.report, "output": args.output}, ensure_ascii=False))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
