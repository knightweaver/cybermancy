from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.integrated_latex import (
    EQUIPMENT_FAMILIES,
    _profile_shell_counts,
    build_integrated_preamble,
    custom_dependency_audit,
    flatten_family_containers,
    stage_generation_assets,
)
from rulebook_layout.publication_shell import _chapter_shell, _divider_shell, _part_shell, PART_BY_ID

CONTRACT_PATH = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
PROSE_CONFIG_PATH = RULEBOOK_DIR / "layout" / "prose" / "prose-layout-v1.json"
ORIGIN_CONFIG_PATH = RULEBOOK_DIR / "layout" / "character-origins" / "character-origins-layout-v1.json"
CLASS_CONFIG_PATH = RULEBOOK_DIR / "layout" / "classes" / "class-package-v1.json"
DOMAIN_CONFIG_PATH = RULEBOOK_DIR / "layout" / "domains" / "domain-package-v1.json"
ICE_CONFIG_PATH = RULEBOOK_DIR / "layout" / "ice" / "ice-reference-package-v1.json"
EQUIPMENT_DIR = RULEBOOK_DIR / "layout" / "equipment"
EQUIPMENT_REGISTRY = EQUIPMENT_DIR / "equipment-section-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw(text: str) -> dict:
    return {"t": "RawBlock", "c": ["latex", text]}


def _family(name: str, body: str) -> dict:
    return {
        "t": "Div",
        "c": [[f"family:{name}", [], []], [_raw(body)]],
    }


def _configs() -> dict:
    registry = _load(EQUIPMENT_REGISTRY)
    equipment = {
        row["family"]: _load(EQUIPMENT_DIR / row["config"])
        for row in registry["families"]
    }
    return {
        "prose": _load(PROSE_CONFIG_PATH),
        "origins": _load(ORIGIN_CONFIG_PATH),
        "class": _load(CLASS_CONFIG_PATH),
        "domain": _load(DOMAIN_CONFIG_PATH),
        "equipment": equipment,
        "ice": _load(ICE_CONFIG_PATH),
    }


def _minimal_prose_preamble() -> str:
    return r"""\documentclass[10pt,letterpaper]{article}
\usepackage[letterpaper,top=0.72in,bottom=0.70in,inner=0.78in,outer=0.78in]{geometry}
\usepackage{fontspec}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{multicol}
\usepackage{fancyhdr}
\usepackage{microtype}
\usepackage{needspace}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{ragged2e}
\usepackage{enumitem}
\usepackage{calc}
\usepackage{etoolbox}
\usepackage[hidelinks]{hyperref}
\definecolor{CMPaper}{HTML}{F9F9F7}
\definecolor{CMInk}{HTML}{111B28}
\definecolor{CMBody}{HTML}{202833}
\definecolor{CMCyan}{HTML}{3CCBC7}
\definecolor{CMTeal}{HTML}{1B7078}
\definecolor{CMIndigo}{HTML}{5968D9}
\definecolor{CMViolet}{HTML}{6C55A6}
\newcommand{\CMRunningAccent}{CMCyan}
\newcommand{\CMPartPage}[4]{#1#2#3#4}
\newcommand{\CMChapterBanner}[3]{#1#2#3}
\newcommand{\CMHThree}[1]{#1}
\newcommand{\CMHFour}[1]{#1}
\newcommand{\CMHFive}[1]{#1}
\newcommand{\CMSectionRule}{}
\newenvironment{CMQuote}{}{}
\newcommand{\CMStandardImage}[1]{#1}
\newcommand{\CMMarkImage}[1]{#1}
\newcommand{\CMSymbolicImage}[1]{#1}
\newcommand{\CMPortraitImage}[1]{#1}
\newcommand{\CMWideImage}[1]{#1}
\newcommand{\CMAssetPlaceholder}[1]{#1}
\newcommand{\CMWideAssetPlaceholder}[1]{#1}
\newenvironment{CMProseTable}{}{}
\begin{document}
\frenchspacing
"""


class Stage150FamilyFlatteningTests(unittest.TestCase):
    def test_flattens_structured_family_and_wraps_package_header_with_family(self) -> None:
        ast = {
            "pandoc-api-version": [1, 23, 1],
            "meta": {},
            "blocks": [
                _family("classes", r"\CMClassBody"),
                _family("subclasses", "% nested marker"),
                _raw("% package chapter 29 header\n\\CMDisplay ICE\n"),
                _family("features", r"\CMDisplay ICEBODY"),
            ],
        }
        flattened, report = flatten_family_containers(ast, _configs())
        self.assertEqual(report["remainingFamilyDivs"], [])
        self.assertIn("classes", report["flattenedFamilies"])
        self.assertIn("features", report["packageHeaderPairs"])
        raw = "\n".join(
            node["c"][1]
            for node in flattened["blocks"]
            if isinstance(node, dict) and node.get("t") == "RawBlock"
        )
        self.assertIn("CM-STAGE150 FAMILY classes BEGIN", raw)
        self.assertIn("% package chapter 29 header", raw)
        self.assertIn("CM-STAGE150 FAMILY features BEGIN", raw)
        self.assertNotEqual(flattened, ast)
        self.assertTrue(any(node.get("t") == "Div" for node in ast["blocks"]))


class Stage150PreambleTests(unittest.TestCase):
    def test_integrated_preamble_adds_one_document_dependency_surface(self) -> None:
        preamble = build_integrated_preamble(
            _minimal_prose_preamble(),
            "complete-rulebook",
            _load(PROSE_CONFIG_PATH),
            _load(ORIGIN_CONFIG_PATH),
        )
        self.assertEqual(preamble.count(r"\documentclass"), 1)
        self.assertNotIn(r"\begin{document}", preamble)
        self.assertIn(r"\usepackage[table]{xcolor}", preamble)
        self.assertIn(r"\usepackage{paracol}", preamble)
        self.assertIn(r"\usepackage{wrapfig}", preamble)
        self.assertIn(r"\usepackage{tcolorbox}", preamble)
        self.assertIn(r"\newcommand{\CMIntegratedPart}", preamble)
        self.assertIn(r"\newcommand{\CMIntegratedChapter}", preamble)
        self.assertIn(r"\newcommand{\CMIntegratedGMDivider}", preamble)
        self.assertIn(r"\newenvironment{CMRulesQuote}", preamble)
        self.assertIn(r"\newcommand{\CMOriginIdentity}", preamble)
        self.assertIn("COMPLETE RULEBOOK", preamble)

    def test_dependency_audit_accepts_defined_lane_macros_and_rejects_unknown_macro(self) -> None:
        preamble = build_integrated_preamble(
            _minimal_prose_preamble(),
            "player-guide",
            _load(PROSE_CONFIG_PATH),
            _load(ORIGIN_CONFIG_PATH),
        )
        body = "\n".join(
            [
                r"\CMIntegratedPart{I}{World}{player}{part-i-world}",
                r"\CMIntegratedChapter{4}{Rules}{player}{ch04-frame-rules}",
                r"\begin{CMRulesQuote}Rules\end{CMRulesQuote}",
                r"\CMOriginIdentity{a}{b}{c}",
                r"\CMClassSans",
            ]
        )
        good = custom_dependency_audit(preamble, body)
        self.assertEqual(good["status"], "PASS", good)
        bad = custom_dependency_audit(preamble, body + "\n" + r"\CMUndefinedStageMacro")
        self.assertEqual(bad["status"], "FAIL")
        self.assertIn("CMUndefinedStageMacro", bad["missingCommands"])


class Stage150AssetTests(unittest.TestCase):
    def test_stages_relative_graphics_to_single_compile_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            rulebook = repo / "build" / "rulebook"
            integration_work = rulebook / "layout" / "integration" / "work"
            source_dir = integration_work / "stage130" / "prose-player" / "assets"
            source_dir.mkdir(parents=True)
            source = source_dir / "proof-image.png"
            source.write_bytes(b"not-a-real-png-but-deterministic")
            output = root / "out"
            ast = {
                "meta": {},
                "blocks": [
                    _raw(r"\CMStandardImage{\detokenize{assets/proof-image.png}}")
                ],
            }
            report = stage_generation_assets(
                ast,
                repo,
                rulebook,
                integration_work,
                output / "assets",
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["assetCount"], 1)
            staged = report["assets"][0]["staged"]
            self.assertTrue((output / staged).is_file())
            rendered = ast["blocks"][0]["c"][1]
            self.assertIn(r"\detokenize{assets/", rendered)
            self.assertNotIn("proof-image.png}", rendered)


class Stage150ShellCountTests(unittest.TestCase):
    def test_profile_shell_counts_match_contract(self) -> None:
        contract = _load(CONTRACT_PATH)
        chapter_map = {int(row["chapter"]): row for row in contract["chapterMap"]}
        player_parts = "\n".join(
            _part_shell(PART_BY_ID[part_id])
            for part_id in ("part-i-world", "part-ii-rules", "part-iii-characters", "part-iv-equipment")
        )
        player_chapters = "\n".join(
            _chapter_shell(number, chapter_map[number], number in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11))
            for number in contract["profiles"]["player-guide"]["chapters"]
        )
        result = _profile_shell_counts(
            player_parts + "\n" + player_chapters,
            contract,
            "player-guide",
        )
        self.assertEqual(result["status"], "PASS", result)

        complete_chapters = [
            number
            for number in contract["profiles"]["complete-rulebook"]["chapters"]
            if number not in (29, 30, 31, 32)
        ]
        complete_body = "\n".join(
            [
                *[_part_shell(PART_BY_ID[row["id"]]) for row in (
                    {"id": "part-i-world"}, {"id": "part-ii-rules"}, {"id": "part-iii-characters"},
                    {"id": "part-iv-equipment"}, {"id": "part-v-gm-world"}, {"id": "part-vi-gm-toolkit"},
                )],
                *[_chapter_shell(number, chapter_map[number], number in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 23, 24, 25, 26, 27, 28)) for number in complete_chapters],
                _divider_shell(contract["gmDividerText"]),
            ]
        )
        result = _profile_shell_counts(complete_body, contract, "complete-rulebook")
        self.assertEqual(result["status"], "PASS", result)


class Stage150EquipmentContractTests(unittest.TestCase):
    def test_all_accepted_equipment_configs_resolve(self) -> None:
        configs = _configs()["equipment"]
        self.assertEqual(set(configs), EQUIPMENT_FAMILIES)
        self.assertEqual(
            sorted(int(config["chapter"]) for config in configs.values()),
            list(range(15, 23)),
        )


if __name__ == "__main__":
    unittest.main()
