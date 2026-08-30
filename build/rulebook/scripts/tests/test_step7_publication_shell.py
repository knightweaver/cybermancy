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

from rulebook_production.publication_shell import (
    apply_publication_shell,
    bookmark_structure,
    entity_index,
    locate_rendered_publication_shell,
)


PRODUCTION_CONTRACT = RULEBOOK_DIR / "production" / "production-renderer-v1.json"
STEP6_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
METADATA = RULEBOOK_DIR / "production" / "publication-metadata-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _expectations(**updates: int) -> dict:
    values = {
        "ancestories": 0,
        "communities": 0,
        "classes": 0,
        "subclasses": 0,
        "domains": 0,
        "domainCards": 0,
        "weapons": 0,
        "ammo": 0,
        "armors": 0,
        "cybernetics": 0,
        "dronesDevices": 0,
        "consumables": 0,
        "mods": 0,
        "loot": 0,
        "ice": 0,
        "adversaries": 0,
        "environments": 0,
        "adversaryFeaturesPublished": 0,
    }
    values.update(updates)
    return values


class EntityIndexTests(unittest.TestCase):
    def test_authored_origin_counts_are_outside_the_structured_sidecar_index(self):
        sidecar = {
            "entities": [
                {"family": "classes", "name": "Razzhacker", "semanticId": "entity:classes:r"},
            ]
        }
        result = entity_index(
            sidecar,
            "player-guide",
            _expectations(ancestories=18, communities=9, classes=1),
        )
        self.assertEqual(result["entryCount"], 1)
        self.assertEqual(result["expectedEntryCount"], 1)

    def test_domain_group_count_is_not_added_to_domain_card_entities(self):
        sidecar = {
            "entities": [
                {
                    "family": "domains",
                    "name": "Arcane Barrage",
                    "semanticId": "entity:domains:arcane-barrage",
                },
            ]
        }
        result = entity_index(
            sidecar,
            "player-guide",
            _expectations(domains=3, domainCards=1),
        )
        self.assertEqual(result["entryCount"], 1)
        self.assertEqual(result["expectedEntryCount"], 1)

    def test_index_is_sorted_profile_scoped_and_reconciled(self):
        sidecar = {
            "entities": [
                {"family": "classes", "name": "Zed", "semanticId": "entity:classes:z"},
                {"family": "classes", "name": "Alpha", "semanticId": "entity:classes:a"},
                {"family": "adversaries", "name": "Hidden", "semanticId": "entity:adversaries:h"},
            ]
        }
        player = entity_index(sidecar, "player-guide", _expectations(classes=2))
        self.assertEqual([row["name"] for row in player["rows"]], ["Alpha", "Zed"])
        self.assertEqual(player["entryCount"], 2)

    def test_adversary_feature_index_includes_only_publication_representatives(self):
        sidecar = {
            "entities": [
                {
                    "family": "adversaries-features",
                    "name": "Keep",
                    "semanticId": "entity:adversaries-features:keep",
                    "publicationData": {
                        "publicationEquivalence": {"isRepresentative": True},
                        "referenceEntry": {"name": "Published Keep"},
                    },
                },
                {
                    "family": "adversaries-features",
                    "name": "Omit",
                    "semanticId": "entity:adversaries-features:omit",
                    "publicationData": {"publicationEquivalence": {"isRepresentative": False}},
                },
                {
                    "family": "adversaries-features",
                    "name": "Standalone",
                    "semanticId": "entity:adversaries-features:standalone",
                    "publicationData": {},
                },
            ]
        }
        result = entity_index(
            sidecar,
            "complete-rulebook",
            _expectations(adversaryFeaturesPublished=2),
        )
        self.assertEqual([row["name"] for row in result["rows"]], ["Published Keep", "Standalone"])

    def test_complete_rulebook_indexes_only_step4_canonical_ice_features(self):
        sidecar = {
            "iceSemantics": {
                "semanticIds": ["entity:features:ice"],
            },
            "entities": [
                {"family": "features", "name": "Sentry ICE", "semanticId": "entity:features:ice"},
                {"family": "features", "name": "Class Feature", "semanticId": "entity:features:class"},
            ],
        }
        result = entity_index(
            sidecar,
            "complete-rulebook",
            _expectations(ice=1),
        )
        self.assertEqual([row["name"] for row in result["rows"]], ["Sentry ICE"])


class PublicationShellGenerationTests(unittest.TestCase):
    def test_player_shell_adds_front_matter_navigation_and_only_appendix_b(self):
        contract = _load(PRODUCTION_CONTRACT)
        contract["structuredExpectations"] = _expectations(classes=1)
        document = """\\documentclass{article}
\\newcommand{\\CMIntegratedChapter}[4]{}
\\newcommand{\\CMIntegratedPart}[4]{}
\\begin{document}
\\frenchspacing
% CM-INTEGRATED-SHELL PART part-i-world
\\CMIntegratedPart{I}{World}{player}{part-i-world}
\\CMIntegratedChapter{1}{Welcome}{player}{ch01-welcome}
\\end{document}
"""
        sidecar = {"entities": [{"family": "classes", "name": "Razzhacker", "semanticId": "entity:classes:r"}]}
        rendered, report = apply_publication_shell(
            document,
            "player-guide",
            contract,
            _load(METADATA),
            sidecar,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertIn(r"\CMProductionFrontMatter", rendered)
        self.assertIn(r"\newcommand{\CMProductionPart}[5]", rendered)
        self.assertIn(r"\definecolor{CMProductionMuted}{HTML}{58747A}", rendered)
        self.assertIn(r"\hypersetup{bookmarksdepth=1}", rendered)
        self.assertIn(r"\color{CMProductionMuted}", rendered)
        self.assertNotIn(r"\color{CMMuted}#2", rendered)
        self.assertIn(
            r"\ifodd\value{page}\null\thispagestyle{empty}\newpage\fi",
            rendered,
        )
        self.assertIn(r"\CMProductionAppendix{B}{Entity Index}", rendered)
        self.assertNotIn("Appendix A", rendered)
        self.assertNotIn("Appendix C", rendered)
        self.assertIn("Razzhacker", rendered)


    def test_complete_rulebook_package_navigation_uses_real_line_endings(self):
        contract = _load(PRODUCTION_CONTRACT)
        contract["structuredExpectations"] = _expectations(
            ice=1,
            adversaries=1,
            environments=1,
            adversaryFeaturesPublished=1,
        )
        families = ("features", "adversaries", "environments", "adversaries-features")
        document = """\\documentclass{article}
\\newcommand{\\CMIntegratedChapter}[4]{}
\\newcommand{\\CMIntegratedPart}[4]{}
\\begin{document}
% CM-INTEGRATED-SHELL PART part-i-world
\\CMIntegratedPart{I}{World}{player}{part-i-world}
""" + "\n".join(
            f"% CM-STAGE150 FAMILY {family} BEGIN\n\\clearpage\n"
            for family in families
        ) + """
\\end{document}
"""
        sidecar = {
            "iceSemantics": {"semanticIds": ["entity:features:ice"]},
            "entities": [
                {"family": "features", "name": "ICE", "semanticId": "entity:features:ice"},
                {"family": "adversaries", "name": "Adversary", "semanticId": "entity:adversaries:a"},
                {"family": "environments", "name": "Environment", "semanticId": "entity:environments:e"},
                {
                    "family": "adversaries-features",
                    "name": "Feature",
                    "semanticId": "entity:adversaries-features:f",
                    "publicationData": {},
                },
            ],
        }
        rendered, report = apply_publication_shell(
            document, "complete-rulebook", contract, _load(METADATA), sidecar
        )
        self.assertEqual(report["packageChapterNavigation"], [29, 30, 31, 32])
        for chapter, title, chapter_id in (
            (29, "ICE Reference", "ch29-ice-reference"),
            (30, "Adversaries", "ch30-adversaries"),
            (31, "Environments", "ch31-environments"),
            (32, "Adversary Feature Reference", "ch32-adversary-features"),
        ):
            call = f"\\\\CMProductionPackageChapter{{{chapter}}}{{{title}}}{{{chapter_id}}}"
            self.assertIn(call + "\n", rendered)
            self.assertNotIn(call + r"\n", rendered)


class BookmarkStructureTests(unittest.TestCase):
    def test_only_part_chapter_appendix_levels_are_accepted(self):
        production = _load(PRODUCTION_CONTRACT)
        step6 = _load(STEP6_CONTRACT)
        part_count = len(production["profiles"]["player-guide"]["parts"])
        chapter_rows = [
            row
            for row in step6["chapterMap"]
            if row["chapter"] in step6["profiles"]["player-guide"]["chapters"]
        ]
        out = "\n".join(
            [r"\BOOKMARK [0][-]{part}{Part}{}"] * part_count
            + [r"\BOOKMARK [1][-]{chapter}{Chapter}{part}"] * len(chapter_rows)
            + [r"\BOOKMARK [0][-]{appendix-b-entity-index}{Appendix B}{}"]
        )
        toc = "\n".join(row["chapterId"] for row in chapter_rows) + "\nappendix-b-entity-index\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_path = root / "book.out"
            toc_path = root / "book.toc"
            out_path.write_text(out, encoding="utf-8")
            toc_path.write_text(toc, encoding="utf-8")
            report = bookmark_structure(out_path, toc_path, production, step6, "player-guide")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["lowerLevelBookmarks"], [])


class RenderedPublicationShellTests(unittest.TestCase):
    def test_title_contents_recto_starts_and_appendix_are_required(self):
        contract = _load(PRODUCTION_CONTRACT)
        pages = [
            "Cybermancy Core Rulebook Version 1.0",
            "Contents",
            "PART I The World of Cybermancy",
            "body",
            "PART II Cybermancy Rules",
            "body",
            "PART III Characters and Character Options",
            "body",
            "PART IV Equipment and Technology",
            "body",
            "PART V GM World Guide",
            "body",
            "PART VI GM Encounter Toolkit",
            "body",
            "APPENDIX B Entity Index",
        ]
        report = locate_rendered_publication_shell(pages, contract, "complete-rulebook")
        self.assertEqual(report["status"], "PASS", report)
        self.assertTrue(report["rectoStartsValid"])


if __name__ == "__main__":
    unittest.main()
