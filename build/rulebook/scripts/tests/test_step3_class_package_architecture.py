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

    def test_later_accepted_chapter_numbers_do_not_shift(self):
        part_three_by_id = {
            chapter["id"]: chapter for chapter in self.part_three["chapters"]
        }
        self.assertEqual(part_three_by_id["ch14-domains"]["number"], 14)
        self.assertEqual(part_three_by_id["ch15-feature-reference"]["number"], 15)

        part_four = next(
            part
            for part in self.builder.BOOK_STRUCTURE
            if part.get("id") == "part-iv-equipment"
        )
        numbers = {
            chapter["id"]: chapter["number"] for chapter in part_four["chapters"]
        }
        self.assertEqual(numbers["ch16-weapons"], 16)
        self.assertEqual(numbers["ch23-loot"], 23)


if __name__ == "__main__":
    unittest.main()
