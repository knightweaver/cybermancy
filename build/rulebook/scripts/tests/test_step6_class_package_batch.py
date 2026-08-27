import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.class_package_batch import (
    class_package_output_stem,
    discover_class_package_targets,
    slugify_class_name,
)


class TestStep6ClassPackageBatch(unittest.TestCase):
    def test_discovers_all_classes_sorted_by_name(self):
        sidecar = {
            "entities": [
                {"semanticId": "entity:features:1", "family": "features", "name": "Ignore Me"},
                {"semanticId": "entity:classes:3", "family": "classes", "name": "Street Samurai"},
                {"semanticId": "entity:classes:1", "family": "classes", "name": "Cybermancer"},
                {"semanticId": "entity:classes:2", "family": "classes", "name": "Razz Hacker"},
            ]
        }

        targets = discover_class_package_targets(sidecar)

        self.assertEqual(["Cybermancer", "Razz Hacker", "Street Samurai"], [row["name"] for row in targets])
        self.assertEqual(
            ["cybermancer", "razz-hacker", "street-samurai"],
            [row["slug"] for row in targets],
        )
        self.assertEqual(
            "Cybermancy_Chapter12_Street_Samurai_ClassPackage_Step6",
            targets[2]["outputStem"],
        )

    def test_output_names_are_deterministic(self):
        self.assertEqual("razz-hacker", slugify_class_name("Razz Hacker"))
        self.assertEqual(
            "Cybermancy_Chapter12_Razz_Hacker_ClassPackage_Step6",
            class_package_output_stem("Razz Hacker"),
        )

    def test_rejects_missing_class_identity(self):
        with self.assertRaisesRegex(ValueError, "missing semanticId"):
            discover_class_package_targets({"entities": [{"family": "classes", "name": "Broken"}]})

    def test_rejects_sidecar_without_classes(self):
        with self.assertRaisesRegex(ValueError, "contains no Class entities"):
            discover_class_package_targets({"entities": [{"family": "features", "semanticId": "x", "name": "F"}]})


if __name__ == "__main__":
    unittest.main()
