import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package_geometry import PdfLine, evaluate_domain_package_geometry


class TestStep6DomainPackageGeometryWrapping(unittest.TestCase):
    def test_wrapped_titles_and_stacked_metadata_are_recognized(self):
        view = {
            "levels": [
                {
                    "level": 1,
                    "cards": [
                        {
                            "name": "Patience Young Padawan",
                            "level": 1,
                            "recallCost": 1,
                            "description": "Wait for the opening before you commit to the action.",
                        },
                        {
                            "name": "All quiet here, how are you?",
                            "level": 1,
                            "recallCost": 2,
                            "description": "Talk like you belong and keep the channel calm.",
                        },
                        {
                            "name": "Cyberware Malfunction",
                            "level": 1,
                            "recallCost": 0,
                            "description": "Disable a nearby implant with a targeted disruption.",
                        },
                    ],
                }
            ]
        }
        config = {
            "composition": {"pageColumns": 3},
            "style": {
                "minimumCardTextFontPt": 10.5,
                "cardBodyFontPt": 10.5,
                "cardBodyLeadingPt": 12.1,
                "columnTopAlignmentTolerancePt": 2.0,
            },
        }
        lines = [
            PdfLine(1, "LEVEL 1", 30, 50, 92, 68),
            PdfLine(1, "Patience Young", 88, 100, 180, 113),
            PdfLine(1, "Padawan", 88, 113, 145, 126),
            PdfLine(1, "LEVEL 1", 88, 130, 140, 142),
            PdfLine(1, "RECALL COST 1", 88, 142, 175, 154),
            PdfLine(1, "Wait for the opening before", 30, 165.0, 190, 176),
            PdfLine(1, "you commit to the action.", 30, 177.1, 180, 188),
            PdfLine(1, "All quiet here, how", 270, 100, 390, 113),
            PdfLine(1, "are you?", 270, 113, 325, 126),
            PdfLine(1, "LEVEL 1", 270, 130, 322, 142),
            PdfLine(1, "RECALL COST 2", 270, 142, 357, 154),
            PdfLine(1, "Talk like you belong and", 212, 165.0, 365, 176),
            PdfLine(1, "keep the channel calm.", 212, 177.1, 350, 188),
            PdfLine(1, "Cyberware", 452, 100, 520, 113),
            PdfLine(1, "Malfunction", 452, 113, 525, 126),
            PdfLine(1, "LEVEL 1", 452, 130, 504, 142),
            PdfLine(1, "RECALL COST 0", 452, 142, 539, 154),
            PdfLine(1, "Disable a nearby implant with", 394, 165.0, 560, 176),
            PdfLine(1, "a targeted disruption.", 394, 177.1, 535, 188),
        ]

        report = evaluate_domain_package_geometry(lines, view, config)

        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual([88.0, 270.0, 452.0], report["details"]["columnStarts"])
        self.assertEqual(10.5, report["details"]["minimumCardTextFontPt"])
        self.assertEqual(12.1, report["details"]["cardBodyLeadingPt"])
        self.assertEqual(
            ["Patience Young Padawan", "All quiet here, how are you?", "Cyberware Malfunction"],
            [row["name"] for row in report["details"]["cardHeadings"]],
        )
        self.assertTrue(all(row["count"] == 1 for row in report["details"]["cardHeadings"]))
        self.assertEqual(4, report["details"]["levelHeadings"][0]["rawCount"])
        self.assertEqual(1, report["details"]["levelHeadings"][0]["count"])


if __name__ == "__main__":
    unittest.main()
