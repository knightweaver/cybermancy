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
    locate_rendered_publication_shell,
)

PRODUCTION_CONTRACT = RULEBOOK_DIR / "production" / "production-renderer-v1.json"
STEP6_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
METADATA = RULEBOOK_DIR / "production" / "publication-metadata-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PublicationShellGenerationTests(unittest.TestCase):
    def test_player_shell_adds_front_matter_without_removed_appendix_b(self):
        contract = _load(PRODUCTION_CONTRACT)
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
        rendered, report = apply_publication_shell(
            document, "player-guide", contract, _load(METADATA)
        )
        self.assertEqual(report["status"], "PASS")
        self.assertIn(r"\CMProductionFrontMatter", rendered)
        self.assertIn(r"\newcommand{\CMProductionPart}[5]", rendered)
        self.assertIn(r"\hypersetup{bookmarksdepth=1}", rendered)
        self.assertIn(
            r"\ifodd\value{page}\null\thispagestyle{empty}\newpage\fi",
            rendered,
        )
        self.assertNotIn(r"\CMProductionAppendix{B}{Entity Index}", rendered)
        self.assertNotIn("appendix-b-entity-index", rendered)
        self.assertNotIn(r"\CMEntityIndexLetter", rendered)
        self.assertNotIn(r"\CMEntityIndexEntry", rendered)
        self.assertEqual(report["appendices"]["generated"], [])
        self.assertIn("appendix-a-rules-quick-reference", report["appendices"]["deferred"])
        self.assertIn("appendix-b-entity-index", report["appendices"]["removed"])
        self.assertIn("appendix-c-attribution-publication-notice", report["appendices"]["deferred"])

    def test_complete_rulebook_package_navigation_order_is_unchanged(self):
        contract = _load(PRODUCTION_CONTRACT)
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
        rendered, report = apply_publication_shell(
            document, "complete-rulebook", contract, _load(METADATA)
        )
        self.assertEqual(report["packageChapterNavigation"], [29, 30, 31, 32])
        for chapter, title, chapter_id in (
            (29, "ICE Reference", "ch29-ice-reference"),
            (30, "Adversaries", "ch30-adversaries"),
            (31, "Environments", "ch31-environments"),
            (32, "Adversary Feature Reference", "ch32-adversary-features"),
        ):
            call = rf"\CMProductionPackageChapter{{{chapter}}}{{{title}}}{{{chapter_id}}}"
            self.assertIn(call + "\n", rendered)
            self.assertNotIn(call + r"\n", rendered)
        self.assertNotIn("appendix-b-entity-index", rendered)

    def test_profile_chapter_order_remains_frozen(self):
        step6 = _load(STEP6_CONTRACT)
        self.assertEqual(
            step6["profiles"]["player-guide"]["chapters"],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22],
        )
        self.assertEqual(
            step6["profiles"]["complete-rulebook"]["chapters"],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32],
        )


class BookmarkStructureTests(unittest.TestCase):
    def _evidence(self, include_removed_appendix: bool = False) -> tuple[dict, dict, str, str]:
        production = _load(PRODUCTION_CONTRACT)
        step6 = _load(STEP6_CONTRACT)
        part_count = len(production["profiles"]["player-guide"]["parts"])
        chapter_rows = [
            row
            for row in step6["chapterMap"]
            if row["chapter"] in step6["profiles"]["player-guide"]["chapters"]
        ]
        lines = [r"\BOOKMARK [0][-]{part}{Part}{}"] * part_count
        lines += [r"\BOOKMARK [1][-]{chapter}{Chapter}{part}"] * len(chapter_rows)
        toc = "\n".join(row["chapterId"] for row in chapter_rows)
        if include_removed_appendix:
            lines.append(r"\BOOKMARK [0][-]{appendix-b-entity-index}{Appendix B}{}")
            toc += "\nappendix-b-entity-index"
        return production, step6, "\n".join(lines), toc + "\n"

    def test_expected_bookmark_count_reconciles_without_appendix_b(self):
        production, step6, out, toc = self._evidence()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_path = root / "book.out"
            toc_path = root / "book.toc"
            out_path.write_text(out, encoding="utf-8")
            toc_path.write_text(toc, encoding="utf-8")
            report = bookmark_structure(out_path, toc_path, production, step6, "player-guide")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["bookmarkCount"], report["expectedBookmarkCount"])
        self.assertEqual(report["generatedAppendixDestinations"], [])
        self.assertEqual(report["unexpectedRemovedAppendixDestinations"], [])
        self.assertEqual(report["lowerLevelBookmarks"], [])

    def test_removed_appendix_b_bookmark_or_toc_destination_is_rejected(self):
        production, step6, out, toc = self._evidence(include_removed_appendix=True)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_path = root / "book.out"
            toc_path = root / "book.toc"
            out_path.write_text(out, encoding="utf-8")
            toc_path.write_text(toc, encoding="utf-8")
            report = bookmark_structure(out_path, toc_path, production, step6, "player-guide")
        self.assertEqual(report["status"], "FAIL", report)
        self.assertIn("appendix-b-entity-index", report["unexpectedRemovedAppendixDestinations"])


class RenderedPublicationShellTests(unittest.TestCase):
    def _complete_pages(self) -> list[str]:
        return [
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
        ]

    def test_title_contents_recto_parts_and_clean_termination_are_required(self):
        contract = _load(PRODUCTION_CONTRACT)
        report = locate_rendered_publication_shell(
            self._complete_pages(), contract, "complete-rulebook"
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertTrue(report["rectoStartsValid"])
        self.assertEqual(report["appendixB"], {"status": "REMOVED", "pages": []})
        self.assertEqual(report["removedAppendixHits"]["appendixB"], [])
        self.assertEqual(report["deferredAppendixHits"]["appendixA"], [])

    def test_rendered_appendix_b_page_is_rejected(self):
        contract = _load(PRODUCTION_CONTRACT)
        pages = self._complete_pages() + ["APPENDIX B Entity Index"]
        report = locate_rendered_publication_shell(pages, contract, "complete-rulebook")
        self.assertEqual(report["status"], "FAIL", report)
        self.assertEqual(report["appendixB"]["pages"], [15])


if __name__ == "__main__":
    unittest.main()
