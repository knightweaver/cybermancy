from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.publication_shell import PARTS, PROFILE_PART_IDS
from rulebook_layout.rendered_regression import (
    STAGE_ORDER,
    contract_stage,
    deferred_output_vboxes,
    extract_bbox_layout,
    locate_rendered_structure,
    normalize_rendered_text,
    page_count_consistency,
    page_geometry_report,
    parse_pdfinfo,
    rendered_bounds_report,
    stage160_pdf_hash,
)

CONTRACT_PATH = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _completed(command: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


class Stage170ContractTests(unittest.TestCase):
    def test_contract_places_rendered_regression_at_170(self) -> None:
        stage = contract_stage(_load_contract())
        self.assertIsNotNone(stage)
        self.assertEqual(stage["stage"], "rendered-regression")
        self.assertEqual(int(stage["order"]), STAGE_ORDER)


class Stage170PdfInfoTests(unittest.TestCase):
    def test_parses_pages_and_letter_size(self) -> None:
        parsed = parse_pdfinfo("Pages:          79\nPage size:      612 x 792 pts (letter)\n")
        self.assertEqual(parsed["pages"], 79)
        self.assertEqual(parsed["pageWidthPt"], 612.0)
        self.assertEqual(parsed["pageHeightPt"], 792.0)


class Stage170BboxTests(unittest.TestCase):
    def test_bbox_extraction_and_bounds(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><doc>
<page width="612.000000" height="792.000000">
<flow><block><line><word xMin="36" yMin="40" xMax="80" yMax="52">Cybermancy</word></line></block></flow>
</page>
</doc></body></html>"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "book.pdf"
            pdf.write_bytes(b"%PDF-1.7\n")
            output = root / "bbox.html"

            def runner(command: list[str], cwd: Path):
                Path(command[-1]).write_text(xml, encoding="utf-8")
                return _completed(command, 0)

            report = extract_bbox_layout(pdf, "pdftotext", output, runner=runner)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["pageCount"], 1)
        geometry = page_geometry_report(report["pages"])
        bounds = rendered_bounds_report(report["pages"])
        self.assertEqual(geometry["status"], "PASS", geometry)
        self.assertEqual(bounds["status"], "PASS", bounds)
        self.assertEqual(bounds["wordCount"], 1)

    def test_out_of_page_word_is_blocking(self) -> None:
        pages = [
            {
                "page": 1,
                "widthPt": 612.0,
                "heightPt": 792.0,
                "words": [
                    {"text": "overflow", "xMin": 600.0, "yMin": 40.0, "xMax": 620.0, "yMax": 52.0}
                ],
            }
        ]
        report = rendered_bounds_report(pages)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["outsideCount"], 1)


class Stage170StructureTests(unittest.TestCase):
    def _pages_for_profile(self, profile: str) -> list[str]:
        contract = _load_contract()
        chapter_map = {int(row["chapter"]): row for row in contract["chapterMap"]}
        part_by_id = {row["id"]: row for row in PARTS}
        pages: list[str] = []
        for part_id in PROFILE_PART_IDS[profile]:
            part = part_by_id[part_id]
            pages.append(f"PART {part['roman']}\n{part['title']}\n")
        for number in contract["profiles"][profile]["chapters"]:
            row = chapter_map[number]
            pages.append(f"CHAPTER {number}\n{row['title']}\n")
        if profile == "complete-rulebook":
            chapter22_index = next(i for i, text in enumerate(pages) if "CHAPTER 22" in text)
            chapter23_index = next(i for i, text in enumerate(pages) if "CHAPTER 23" in text)
            pages.insert(chapter23_index, contract["gmDividerText"])
        return pages

    def test_player_structure_is_complete_and_excludes_gm(self) -> None:
        contract = _load_contract()
        report = locate_rendered_structure(self._pages_for_profile("player-guide"), contract, "player-guide")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["chapter13Pages"], [])
        self.assertEqual(report["playerGuideGmChapterPages"], {})
        self.assertEqual(report["gmDivider"]["pages"], [])

    def test_complete_structure_preserves_gm_divider_between_22_and_23(self) -> None:
        contract = _load_contract()
        report = locate_rendered_structure(self._pages_for_profile("complete-rulebook"), contract, "complete-rulebook")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(len(report["gmDivider"]["pages"]), 1)
        self.assertTrue(report["gmDivider"]["boundaryValid"])

    def test_provenance_residue_fails_rendered_structure(self) -> None:
        contract = _load_contract()
        pages = self._pages_for_profile("player-guide")
        pages[0] += "source-commit: 0123456789012345678901234567890123456789"
        report = locate_rendered_structure(pages, contract, "player-guide")
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["provenanceResiduePages"]["source-commit:"])


class Stage170HandoffTests(unittest.TestCase):
    def test_stage160_pdf_hash_and_deferred_vboxes(self) -> None:
        report = {
            "status": "PASS",
            "outputPdfSha256": "abc123",
            "compilation": {
                "diagnostics": {
                    "outputRoutineVboxes": [
                        "Overfull \\vbox (1.0pt too high) while \\output is active"
                    ]
                }
            },
        }
        self.assertEqual(stage160_pdf_hash(report), "abc123")
        self.assertEqual(len(deferred_output_vboxes(report)), 1)

    def test_page_count_sources_must_agree(self) -> None:
        passed = page_count_consistency(
            {"pages": 10}, {"pageCount": 10}, {"pageCount": 10}
        )
        failed = page_count_consistency(
            {"pages": 10}, {"pageCount": 9}, {"pageCount": 10}
        )
        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(failed["status"], "FAIL")


class Stage170TextNormalizationTests(unittest.TestCase):
    def test_normalization_collapses_layout_whitespace_and_unicode_dashes(self) -> None:
        self.assertEqual(
            normalize_rendered_text("GM MATERIAL —  SPOILERS\nBEYOND THIS POINT"),
            "gm material - spoilers beyond this point",
        )


if __name__ == "__main__":
    unittest.main()
