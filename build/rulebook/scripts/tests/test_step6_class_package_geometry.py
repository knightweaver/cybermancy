import sys
import unittest
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.class_package_geometry import PdfLine, evaluate_class_package_geometry


class TestStep6ClassPackageGeometry(unittest.TestCase):
    def _view(self):
        return {
            "class": {
                "name": "Test Class",
                "description": "First class line wraps into another line for geometry validation.",
                "startingInventory": {
                    "take": [{"name": "Pendant Lens"}],
                },
                "characterGuide": {},
            },
            "subclasses": [
                {
                    "name": "Path A",
                    "description": "First subclass line wraps into another line for geometry validation.",
                }
            ],
        }

    def _lines(self):
        return [
            PdfLine(1, "First class line wraps into", 300.0, 100.0, 470.0, 110.0),
            PdfLine(1, "another line for geometry validation.", 300.0, 112.3, 500.0, 122.3),
            PdfLine(1, "Take", 30.0, 300.0, 60.0, 310.0),
            PdfLine(1, "Pendant Lens", 130.0, 300.7, 210.0, 310.7),
            PdfLine(2, "First subclass line wraps into", 40.0, 100.0, 220.0, 110.0),
            PdfLine(2, "another line for geometry validation.", 40.0, 112.1, 240.0, 122.1),
        ]

    def test_geometry_passes_with_expected_leading_and_baselines(self):
        result = evaluate_class_package_geometry(self._lines(), self._view())

        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["details"].get("errors", []))
        self.assertEqual(
            [12.3, 12.1],
            [row["points"] for row in result["details"]["descriptionLineSpacing"]],
        )
        self.assertEqual(
            0.7,
            result["details"]["startingPackageBaselines"][0]["deltaPoints"],
        )

    def test_geometry_rejects_excessive_description_leading(self):
        lines = self._lines()
        lines[1] = replace(lines[1], y_min=116.0, y_max=126.0)

        result = evaluate_class_package_geometry(lines, self._view())

        self.assertEqual("ERROR", result["status"])
        self.assertTrue(
            any(
                "Class description first-line spacing is 16.00 pt" in error
                for error in result["details"]["errors"]
            )
        )

    def test_geometry_rejects_starting_package_baseline_misalignment(self):
        lines = self._lines()
        lines[3] = replace(lines[3], y_min=303.0, y_max=313.0)

        result = evaluate_class_package_geometry(lines, self._view())

        self.assertEqual("ERROR", result["status"])
        self.assertTrue(
            any(
                "Starting Package label/value baselines for Take differ by 3.00 pt" in error
                for error in result["details"]["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
