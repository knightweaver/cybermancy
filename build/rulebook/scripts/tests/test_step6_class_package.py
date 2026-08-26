import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.class_package import compose_class_package, render_class_package_tex


class TestStep6ClassPackage(unittest.TestCase):
    def _fixture(self, root: Path):
        source_root = root / "build/rulebook/source"
        for rel in (
            "assets/icons/classes/test-class.png",
            "assets/icons/subclasses/path-a.png",
            "assets/icons/subclasses/path-b.png",
        ):
            path = source_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("image:" + rel).encode("utf-8"))

        def feature(sid, name, description):
            return {
                "semanticId": sid,
                "family": "features",
                "sourceId": sid.split(":")[-1],
                "name": name,
                "audience": "player",
                "sourcePath": f"src/features/{name}.json",
                "publicationData": {"description": description},
            }

        sidecar = {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "publicationImageSemantics": {
                "schema": "cybermancy-step4-class-publication-images-v1.1",
                "status": "PASS",
                "entityCount": 3,
                "publicationImageCount": 3,
            },
            "entities": [
                {
                    "semanticId": "entity:classes:c1",
                    "family": "classes",
                    "sourceId": "c1",
                    "name": "Test Class",
                    "audience": "player",
                    "sourcePath": "src/classes/Test_Class.json",
                    "publicationData": {
                        "description": "A class built to test package composition.",
                        "image": "assets/icons/classes/test-class.png",
                        "hitPoints": 6,
                        "evasion": 11,
                        "domains": ["arcana", "circuit"],
                        "features": [
                            {"type": "hope", "semanticId": "entity:features:f1"},
                            {"type": "class", "semanticId": "entity:features:f2"},
                        ],
                        "subclasses": ["entity:subclasses:s1", "entity:subclasses:s2"],
                        "startingInventory": {
                            "take": ["entity:weapons:w1"],
                            "choiceA": ["entity:armors:a1"],
                        },
                        "characterGuide": {
                            "suggestedTraits": {"instinct": 2, "finesse": 1},
                            "suggestedPrimaryWeapon": "entity:weapons:w1",
                            "suggestedSecondaryWeapon": None,
                            "suggestedArmor": "entity:armors:a1",
                        },
                    },
                },
                {
                    "semanticId": "entity:subclasses:s1",
                    "family": "subclasses",
                    "sourceId": "s1",
                    "name": "Path A",
                    "audience": "player",
                    "sourcePath": "src/subclasses/Path_A.json",
                    "publicationData": {
                        "description": "The first path.",
                        "image": "assets/icons/subclasses/path-a.png",
                        "linkedClass": "entity:classes:c1",
                        "spellcastingTrait": "instinct",
                        "progression": {
                            "foundation": ["entity:features:f3"],
                            "specialization": ["entity:features:f4", "entity:features:f5"],
                            "mastery": ["entity:features:f6"],
                        },
                    },
                },
                {
                    "semanticId": "entity:subclasses:s2",
                    "family": "subclasses",
                    "sourceId": "s2",
                    "name": "Path B",
                    "audience": "player",
                    "sourcePath": "src/subclasses/Path_B.json",
                    "publicationData": {
                        "description": "",
                        "image": "assets/icons/subclasses/path-b.png",
                        "linkedClass": "entity:classes:c1",
                        "progression": {
                            "foundation": ["entity:features:f7", "entity:features:f8"],
                            "specialization": ["entity:features:f9"],
                            "mastery": ["entity:features:f10", "entity:features:f11"],
                        },
                    },
                },
                feature("entity:features:f1", "Hope Signal", "Spend Hope to amplify the signal."),
                feature("entity:features:f2", "Class Engine", "The defining class feature."),
                feature("entity:features:f3", "A Foundation", "Foundation feature A."),
                feature("entity:features:f4", "A Specialization One", "Specialization feature A1."),
                feature("entity:features:f5", "A Specialization Two", "Specialization feature A2."),
                feature("entity:features:f6", "A Mastery", "Mastery feature A."),
                feature("entity:features:f7", "B Foundation One", "Foundation feature B1."),
                feature("entity:features:f8", "B Foundation Two", "Foundation feature B2."),
                feature("entity:features:f9", "B Specialization", "Specialization feature B."),
                feature("entity:features:f10", "B Mastery One", "Mastery feature B1."),
                feature("entity:features:f11", "B Mastery Two", "Mastery feature B2."),
                {
                    "semanticId": "entity:weapons:w1",
                    "family": "weapons",
                    "sourceId": "w1",
                    "name": "Test Weapon",
                    "audience": "player",
                    "sourcePath": "src/weapons/Test_Weapon.json",
                    "publicationData": {},
                },
                {
                    "semanticId": "entity:armors:a1",
                    "family": "armors",
                    "sourceId": "a1",
                    "name": "Test Armor",
                    "audience": "player",
                    "sourcePath": "src/armors/Test_Armor.json",
                    "publicationData": {},
                },
            ],
        }
        config = {
            "chapter": 12,
            "title": "Classes and Subclasses",
            "partLabel": "CHARACTER OPTIONS",
            "composition": {
                "subclassProgressionOrder": ["foundation", "specialization", "mastery"]
            },
            "prototypePolicy": {
                "requireStructuredSidecarSchema": "cybermancy-step4-structured-entities-v1.3",
                "requirePublicationImageSemanticsPass": True,
            },
            "style": {},
        }
        return source_root, sidecar, config

    def test_composes_class_subclasses_features_inventory_and_guide(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            view, report = compose_class_package(sidecar, source_root, "entity:classes:c1", config)

            self.assertEqual(report["status"], "PASS")
            self.assertEqual(view["class"]["name"], "Test Class")
            self.assertEqual(view["class"]["image"], "assets/icons/classes/test-class.png")
            self.assertEqual(view["class"]["features"]["hope"][0]["name"], "Hope Signal")
            self.assertEqual(view["class"]["features"]["class"][0]["description"], "The defining class feature.")
            self.assertEqual(view["class"]["startingInventory"]["take"][0]["name"], "Test Weapon")
            self.assertEqual(view["class"]["characterGuide"]["suggestedArmor"]["name"], "Test Armor")
            self.assertEqual([row["name"] for row in view["subclasses"]], ["Path A", "Path B"])
            self.assertEqual(len(view["subclasses"][0]["progression"]["specialization"]), 2)
            self.assertEqual(len(view["subclasses"][1]["progression"]["foundation"]), 2)
            self.assertEqual(len(view["subclasses"][1]["progression"]["mastery"]), 2)

            raw = json.dumps(view)
            self.assertNotIn("Compendium.", raw)
            self.assertNotIn("modules/cybermancy/", raw)

    def test_blank_subclass_description_is_warning_not_failure(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            _, report = compose_class_package(sidecar, source_root, "entity:classes:c1", config)

            self.assertEqual(report["status"], "PASS")
            warnings = {item["code"] for item in report["warnings"]}
            self.assertIn("CLASS_PACKAGE_SUBCLASS_DESCRIPTION", warnings)

    def test_linked_class_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            broken = copy.deepcopy(sidecar)
            subclass = next(row for row in broken["entities"] if row.get("semanticId") == "entity:subclasses:s1")
            subclass["publicationData"]["linkedClass"] = "entity:classes:other"

            _, report = compose_class_package(broken, source_root, "entity:classes:c1", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("CLASS_PACKAGE_SUBCLASS_PARENT", {item["code"] for item in report["errors"]})

    def test_missing_feature_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            broken = copy.deepcopy(sidecar)
            cls = next(row for row in broken["entities"] if row.get("semanticId") == "entity:classes:c1")
            cls["publicationData"]["features"][0]["semanticId"] = "entity:features:missing"

            _, report = compose_class_package(broken, source_root, "entity:classes:c1", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("CLASS_PACKAGE_REFERENCE", {item["code"] for item in report["errors"]})

    def test_missing_staged_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            (source_root / "assets/icons/subclasses/path-a.png").unlink()

            _, report = compose_class_package(sidecar, source_root, "entity:classes:c1", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("CLASS_PACKAGE_IMAGE", {item["code"] for item in report["errors"]})

    def test_renderer_uses_composed_content_and_step4_staged_images(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, sidecar, config = self._fixture(root)
            output_dir = root / "build/rulebook/layout/class-package-prototype"
            output_dir.mkdir(parents=True)
            view, report = compose_class_package(sidecar, source_root, "entity:classes:c1", config)
            self.assertEqual(report["status"], "PASS")

            tex = render_class_package_tex(view, config, source_root, output_dir)

            self.assertIn("TEST CLASS", tex)
            self.assertIn("PATH A", tex)
            self.assertIn("PATH B", tex)
            self.assertIn("FOUNDATION", tex)
            self.assertIn("SPECIALIZATION", tex)
            self.assertIn("MASTERY", tex)
            self.assertIn("Hope Signal", tex)
            self.assertIn("test-class.png", tex)
            self.assertNotIn("docs/player-facing", tex)
            self.assertNotIn("modules/cybermancy", tex)


if __name__ == "__main__":
    unittest.main()
