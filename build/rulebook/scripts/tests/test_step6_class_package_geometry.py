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
                },
                {
                    "name": "Path B",
                    "description": "Second subclass line wraps into another line for geometry validation.",
                },
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
            PdfLine(2, "Second subclass line wraps into", 340.0, 100.0, 520.0, 110.0),
            PdfLine(2, "another line for geometry validation.", 340.0, 112.1, 540.0, 122.1),
        ]

    def test_geometry_passes_with_expected_leading_baselines_and_parallel_subclasses(self):
        result = evaluate_class_package_geometry(self._lines(), self._view())

        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["details"].get("errors", []))
        self.assertEqual(
            [12.3, 12.1, 12.1],
            [row["points"] for row in result["details"]["descriptionLineSpacing"]],
        )
        self.assertEqual(
            0.7,
            result["details"]["startingPackageBaselines"][0]["deltaPoints"],
        )
        parallel = result["details"]["subclassParallelStarts"][0]
        self.assertEqual(2, parallel["leftPage"])
        self.assertEqual(2, parallel["rightPage"])
        self.assertEqual(300.0, parallel["xDeltaPoints"])

    def test_geometry_finds_package_and_parallel_subclasses_on_later_pages(self):
        lines = self._lines()
        lines[2] = replace(lines[2], page=2)
        lines[3] = replace(lines[3], page=2)
        for index in range(4, 8):
            lines[index] = replace(lines[index], page=3)

        result = evaluate_class_package_geometry(lines, self._view())

        self.assertEqual("PASS", result["status"])
        self.assertEqual(2, result["details"]["startingPackageBaselines"][0]["page"])
        self.assertEqual(3, result["details"]["descriptionLineSpacing"][1]["page"])
        self.assertEqual(3, result["details"]["descriptionLineSpacing"][2]["page"])
        self.assertEqual(3, result["details"]["subclassParallelStarts"][0]["leftPage"])
        self.assertEqual(3, result["details"]["subclassParallelStarts"][0]["rightPage"])

    def test_geometry_scopes_package_before_subclasses_when_they_share_a_page(self):
        lines = [
            PdfLine(1, "First class line wraps into", 300.0, 100.0, 470.0, 110.0),
            PdfLine(1, "another line for geometry validation.", 300.0, 112.3, 500.0, 122.3),
            PdfLine(1, "Take a Reaction when the drone moves.", 40.0, 240.0, 280.0, 250.0),
            PdfLine(2, "STARTING PACKAGE", 30.0, 80.0, 150.0, 90.0),
            PdfLine(2, "Take", 30.0, 120.0, 60.0, 130.0),
            PdfLine(2, "Pendant Lens", 130.0, 120.4, 210.0, 130.4),
            PdfLine(2, "SUBCLASS", 40.0, 240.0, 100.0, 250.0),
            PdfLine(2, "SUBCLASS", 340.0, 240.0, 400.0, 250.0),
            PdfLine(2, "First subclass line wraps into", 80.0, 300.0, 250.0, 310.0),
            PdfLine(2, "another line for geometry validation.", 80.0, 312.1, 270.0, 322.1),
            PdfLine(2, "Second subclass line wraps into", 380.0, 300.0, 550.0, 310.0),
            PdfLine(2, "another line for geometry validation.", 380.0, 312.1, 570.0, 322.1),
        ]

        result = evaluate_class_package_geometry(lines, self._view())

        self.assertEqual("PASS", result["status"])
        baseline = result["details"]["startingPackageBaselines"][0]
        self.assertEqual(2, baseline["page"])
        self.assertEqual(0.4, baseline["deltaPoints"])
        parallel = result["details"]["subclassParallelStarts"][0]
        self.assertEqual(2, parallel["leftPage"])
        self.assertEqual(2, parallel["rightPage"])
        self.assertEqual(300.0, parallel["xDeltaPoints"])

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

    def test_geometry_rejects_subclasses_that_start_on_different_pages(self):
        lines = self._lines()
        lines[6] = replace(lines[6], page=3)
        lines[7] = replace(lines[7], page=3)

        result = evaluate_class_package_geometry(lines, self._view())

        self.assertEqual("ERROR", result["status"])
        self.assertTrue(
            any(
                "Subclass pair did not begin in parallel columns" in error
                for error in result["details"]["errors"]
            )
        )

    def test_geometry_rejects_subclasses_that_start_at_same_horizontal_position(self):
        lines = self._lines()
        lines[6] = replace(lines[6], x_min=45.0, x_max=225.0)
        lines[7] = replace(lines[7], x_min=45.0, x_max=245.0)

        result = evaluate_class_package_geometry(lines, self._view())

        self.assertEqual("ERROR", result["status"])
        self.assertTrue(
            any(
                "did not begin in distinct parallel columns" in error
                for error in result["details"]["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
