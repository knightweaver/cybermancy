import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _load_step3_builder():
    path = SCRIPT_DIR / "build-rulebook-assembly-manifest.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_assembly_manifest_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestStep3ClassPackageArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = _load_step3_builder()
        cls.part_three = next(
            part
            for part in cls.builder.BOOK_STRUCTURE
            if part.get("id") == "part-iii-characters"
        )

    def test_classes_and_subclasses_share_chapter_12(self):
        chapter = next(
            chapter
            for chapter in self.part_three["chapters"]
            if chapter.get("id") == "ch12-classes"
        )
        self.assertEqual(chapter["number"], 12)
        self.assertEqual(chapter["title"], "Classes and Subclasses")
        self.assertEqual(
            chapter["contentRefs"],
            ["family:classes", "family:subclasses"],
        )
        self.assertEqual(chapter["composition"]["kind"], "class-package")
        self.assertEqual(chapter["composition"]["primaryFamily"], "classes")
        self.assertEqual(chapter["composition"]["nestedFamily"], "subclasses")
        self.assertEqual(
            chapter["composition"]["relationshipResolutionStage"],
            "Step 4",
        )

    def test_no_independent_subclass_chapter_remains(self):
        chapter_ids = {chapter["id"] for chapter in self.part_three["chapters"]}
        self.assertNotIn("ch13-subclasses", chapter_ids)

        subclass_refs = [
            ref
            for part in self.builder.BOOK_STRUCTURE
            for chapter in part.get("chapters", [])
            for ref in chapter.get("contentRefs", [])
            if ref == "family:subclasses"
        ]
        self.assertEqual(subclass_refs, ["family:subclasses"])

    def test_subclass_family_primary_placement_is_class_package(self):
        self.assertEqual(
            self.builder.STRUCTURED_ARCHITECTURE["classes"]["placement"],
            "ch12-classes",
        )
        self.assertEqual(
            self.builder.STRUCTURED_ARCHITECTURE["subclasses"]["placement"],
            "ch12-classes",
        )

    def test_player_feature_reference_is_removed(self):
        chapter_ids = {chapter["id"] for chapter in self.part_three["chapters"]}
        self.assertNotIn("ch15-feature-reference", chapter_ids)
        domains = next(
            chapter for chapter in self.part_three["chapters"]
            if chapter.get("id") == "ch14-domains"
        )
        self.assertEqual(domains["number"], 14)

    def test_equipment_chapters_shift_down_one(self):
        part_four = next(
            part
            for part in self.builder.BOOK_STRUCTURE
            if part.get("id") == "part-iv-equipment"
        )
        numbers = {
            chapter["id"]: chapter["number"] for chapter in part_four["chapters"]
        }
        self.assertEqual(numbers["ch15-weapons"], 15)
        self.assertEqual(numbers["ch16-ammunition"], 16)
        self.assertEqual(numbers["ch17-armor"], 17)
        self.assertEqual(numbers["ch18-cybernetics"], 18)
        self.assertEqual(numbers["ch19-drones-devices"], 19)
        self.assertEqual(numbers["ch20-consumables"], 20)
        self.assertEqual(numbers["ch21-mods"], 21)
        self.assertEqual(numbers["ch22-loot"], 22)

    def test_gm_world_chapters_shift_to_23_through_28(self):
        part_five = next(
            part
            for part in self.builder.BOOK_STRUCTURE
            if part.get("id") == "part-v-gm-world"
        )
        numbers = {
            chapter["id"]: chapter["number"] for chapter in part_five["chapters"]
        }
        self.assertEqual(numbers["ch23-project-helios"], 23)
        self.assertEqual(numbers["ch24-council"], 24)
        self.assertEqual(numbers["ch25-cabal"], 25)
        self.assertEqual(numbers["ch26-cabal-projects"], 26)
        self.assertEqual(numbers["ch27-chessboard"], 27)
        self.assertEqual(numbers["ch28-gm-resonance"], 28)

    def test_ice_reference_is_gm_chapter_29(self):
        part_six = next(
            part
            for part in self.builder.BOOK_STRUCTURE
            if part.get("id") == "part-vi-gm-toolkit"
        )
        chapters = part_six["chapters"]
        self.assertEqual(
            [(chapter["id"], chapter["number"]) for chapter in chapters],
            [
                ("ch29-ice-reference", 29),
                ("ch30-adversaries", 30),
                ("ch31-environments", 31),
                ("ch32-adversary-features", 32),
            ],
        )
        ice = chapters[0]
        self.assertEqual(ice["contentRefs"], ["family:features"])
        self.assertEqual(ice["composition"]["kind"], "ice-reference")
        self.assertEqual(
            ice["composition"]["publicationSubset"],
            {"featureCategory": "ice", "iceTypes": ["sentry", "wall"]},
        )

    def test_feature_family_has_one_gm_primary_placement(self):
        self.assertEqual(
            self.builder.STRUCTURED_ARCHITECTURE["features"]["placement"],
            "ch29-ice-reference",
        )
        feature_refs = [
            (part.get("id"), ref)
            for part in self.builder.BOOK_STRUCTURE
            for chapter in part.get("chapters", [])
            for ref in chapter.get("contentRefs", [])
            if ref == "family:features"
        ]
        self.assertEqual(feature_refs, [("part-vi-gm-toolkit", "family:features")])


if __name__ == "__main__":
    unittest.main()
