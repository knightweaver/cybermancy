import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package_geometry import PdfLine, evaluate_domain_package_geometry
from rulebook_layout.domain_package_refined import render_domain_package_tex


class TestStep6DomainPackageRegressionPolicy(unittest.TestCase):
    def _config(self):
        return {
            "chapter": 14,
            "partLabel": "CHARACTER OPTIONS",
            "composition": {"pageColumns": 3, "defaultCardType": "ability"},
            "style": {
                "minimumCardTextFontPt": 10.5,
                "cardBodyFontPt": 10.5,
                "cardBodyLeadingPt": 12.1,
                "cardMetaFontPt": 10.5,
                "cardMetaLeadingPt": 11.5,
                "pageBottomSafetyPt": 2.0,
                "columnTopAlignmentTolerancePt": 2.0,
            },
        }

    def test_special_typography_description_anchor_can_be_skipped_when_leading_is_sampled(self):
        view = {
            "levels": [
                {
                    "level": 7,
                    "cards": [
                        {
                            "name": "Matrix mind",
                            "level": 7,
                            "recallCost": 2,
                            "description": "“It’s full of stars… !” When 4 or more domain cards are equipped, gain a bonus.",
                        },
                        {
                            "name": "Other Card",
                            "level": 7,
                            "recallCost": 1,
                            "description": "Ordinary text wraps cleanly enough to measure.",
                        },
                    ],
                }
            ]
        }
        lines = [
            PdfLine(1, "LEVEL 7", 30, 50, 90, 68),
            PdfLine(1, "Matrix mind", 88, 100, 160, 113),
            PdfLine(1, "LEVEL 7", 88, 130, 140, 142),
            PdfLine(1, "RECALL COST 2", 88, 142, 175, 154),
            # Simulate pdftotext dropping punctuation/italic boundaries so this
            # one description cannot be anchored exactly.
            PdfLine(1, "full of stars !", 30, 165, 140, 176),
            PdfLine(1, "When 4 or more domain cards", 30, 177.1, 190, 188),
            PdfLine(1, "Other Card", 270, 100, 340, 113),
            PdfLine(1, "LEVEL 7", 270, 130, 322, 142),
            PdfLine(1, "RECALL COST 1", 270, 142, 357, 154),
            PdfLine(1, "Ordinary text wraps cleanly", 212, 165, 365, 176),
            PdfLine(1, "enough to measure.", 212, 177.1, 350, 188),
        ]

        report = evaluate_domain_package_geometry(lines, view, self._config())

        self.assertEqual(report["status"], "PASS", report)
        skipped = report["details"]["descriptionLineSpacingSkipped"]
        self.assertEqual(["Matrix mind"], [row["name"] for row in skipped])
        self.assertEqual(1, len(report["details"]["descriptionLineSpacing"]))

    def test_body_leading_probe_still_requires_at_least_one_measurable_sample(self):
        view = {
            "levels": [
                {
                    "level": 1,
                    "cards": [
                        {
                            "name": "Alpha",
                            "level": 1,
                            "recallCost": 1,
                            "description": "Description cannot be located in this extractor fixture.",
                        }
                    ],
                }
            ]
        }
        lines = [
            PdfLine(1, "LEVEL 1", 30, 50, 90, 68),
            PdfLine(1, "Alpha", 88, 100, 130, 113),
            PdfLine(1, "LEVEL 1", 88, 130, 140, 142),
            PdfLine(1, "RECALL COST 1", 88, 142, 175, 154),
        ]

        report = evaluate_domain_package_geometry(lines, view, self._config())

        self.assertEqual(report["status"], "ERROR")
        self.assertTrue(
            any("no measurable first-to-second-line" in error for error in report["details"]["errors"])
        )

    def test_standalone_renderer_adds_bottom_page_flow_headroom(self):
        view = {
            "chapter": 14,
            "domain": {
                "name": "Maker",
                "cardCount": 1,
                "artwork": {"image": "assets/icons/domains/maker.png"},
            },
            "levels": [
                {
                    "level": 1,
                    "cards": [
                        {
                            "name": "Alpha",
                            "description": "Alpha rules text wraps in normal publication rendering.",
                            "image": "assets/cards/alpha.png",
                            "level": 1,
                            "recallCost": 1,
                            "cardType": "ability",
                            "inVault": False,
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = render_domain_package_tex(view, self._config(), root / "source", root / "output")

        self.assertIn(r"\addtolength{\textheight}{-2.00pt}", tex)
        self.assertIn(r"\raggedbottom", tex)
        self.assertIn(r"\fontsize{10.50}{12.10}\selectfont", tex)


if __name__ == "__main__":
    unittest.main()
