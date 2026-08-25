import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_init import (
    generate_equipment_config,
    initialize_equipment,
)


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-layout.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_layout_init", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _section(entries):
    return {
        "schema": "cybermancy-step6-equipment-section-v1.0",
        "partLabel": "EQUIPMENT & TECHNOLOGY",
        "families": [
            {
                "chapter": chapter,
                "family": family,
                "title": title,
                "config": f"{family}-v1.json",
            }
            for chapter, family, title in entries
        ],
    }


def _entity(family, source_id, name, tier=None, description="Rule text."):
    return {
        "semanticId": f"entity:{family}:{source_id}",
        "family": family,
        "sourceId": source_id,
        "name": name,
        "sourcePath": f"src/packs/items/{family}/{source_id}.json",
        "publicationData": {
            "tier": tier,
            "description": description,
            "burden": None,
            "range": None,
        },
    }


def _existing_config(family, chapter, title):
    return {
        "schema": "cybermancy-step6-equipment-catalog-config-v1.1",
        "layoutMode": "single-catalog",
        "family": family,
        "chapter": chapter,
        "partLabel": "EQUIPMENT & TECHNOLOGY",
        "title": title,
        "expectedEntityCount": 1,
        "expectedColumnLabels": ["Name", "Description"],
        "tierMode": "absent",
        "sort": ["name"],
        "requiredPublicationFields": ["publicationData.description"],
        "columns": [
            {"key": "name", "label": "Name", "widthIn": 1.5},
            {"key": "publicationData.description", "label": "Description", "widthIn": 5.7},
        ],
    }


class TestEquipmentInitConfigGeneration(unittest.TestCase):
    def test_generated_config_uses_only_populated_safe_fields(self):
        bootstrap = {
            "family": "armors",
            "chapter": 18,
            "title": "Armor",
            "entityCount": 2,
            "publicationFields": [
                {"path": "publicationData.tier", "populatedCount": 2},
                {"path": "publicationData.description", "populatedCount": 2},
                {"path": "publicationData.range", "populatedCount": 0},
                {"path": "publicationData.burden", "populatedCount": 0},
                {"path": "publicationData.someFutureField", "populatedCount": 2},
            ],
        }
        config = generate_equipment_config(bootstrap)
        self.assertEqual(config["family"], "armors")
        self.assertEqual(config["chapter"], 18)
        self.assertEqual(config["tierMode"], "present")
        self.assertEqual(config["expectedColumnLabels"], ["Name", "Tier", "Description"])
        self.assertEqual(
            [column["key"] for column in config["columns"]],
            ["name", "publicationData.tier", "publicationData.description"],
        )
        self.assertNotIn("publicationData.someFutureField", [column["key"] for column in config["columns"]])
        self.assertIn("publicationData.tier", config["requiredPublicationFields"])
        self.assertIn("publicationData.description", config["requiredPublicationFields"])

    def test_generated_config_stays_inside_width_budget(self):
        bootstrap = {
            "family": "armors",
            "chapter": 18,
            "title": "Armor",
            "entityCount": 2,
            "publicationFields": [
                {"path": "publicationData.tier", "populatedCount": 2},
                {"path": "publicationData.range", "populatedCount": 2},
                {"path": "publicationData.burden", "populatedCount": 2},
                {"path": "publicationData.description", "populatedCount": 2},
            ],
        }
        config = generate_equipment_config(bootstrap)
        tabcolsep = config["tableStyle"]["tabcolsepPt"]
        occupied = sum(column["widthIn"] for column in config["columns"])
        occupied += (len(config["columns"]) - 1) * (2 * tabcolsep / 72.27)
        self.assertLessEqual(occupied, 7.58)


class TestEquipmentInitWorkflow(unittest.TestCase):
    def test_single_family_init_creates_config_that_generic_validator_accepts(self):
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "equipment"
            report_dir = root / "reports"
            config_dir.mkdir()
            section_registry = config_dir / "equipment-section-v1.json"
            section_registry.write_text(
                json.dumps(_section([(18, "armors", "Armor")])),
                encoding="utf-8",
            )
            sidecar = root / "structured-entities.json"
            sidecar.write_text(
                json.dumps({
                    "schema": builder.SIDECAR_SCHEMA_D,
                    "entities": [
                        _entity("armors", "a1", "Aegis Coat", tier=1),
                        _entity("armors", "a2", "Bulwark Mesh", tier=2),
                    ],
                }),
                encoding="utf-8",
            )
            manuscript = root / "player-guide.md"
            manuscript.write_text("::: {#family:armors}\nplaceholder\n:::\n", encoding="utf-8")

            rc, payload = initialize_equipment(
                family="armors",
                all_families=False,
                config_dir=config_dir,
                sidecar=sidecar,
                manuscript=manuscript,
                section_registry=section_registry,
                report_dir=report_dir,
            )
            config_path = config_dir / "armors-v1.json"
            report, config, _, rows = builder.validate_equipment_family(
                "armors", config_path, sidecar, manuscript
            )

        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["families"][0]["status"], "CREATED")
        self.assertIsNotNone(config)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(rows), 2)

    def test_all_initializes_missing_configs_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "equipment"
            report_dir = root / "reports"
            config_dir.mkdir()
            entries = [
                (16, "weapons", "Weapons"),
                (17, "ammo", "Ammunition"),
                (18, "armors", "Armor"),
                (19, "cybernetics", "Cybernetics"),
            ]
            section_registry = config_dir / "equipment-section-v1.json"
            section_registry.write_text(json.dumps(_section(entries)), encoding="utf-8")
            for chapter, family, title in entries[:2]:
                (config_dir / f"{family}-v1.json").write_text(
                    json.dumps(_existing_config(family, chapter, title)),
                    encoding="utf-8",
                )
            weapons_before = (config_dir / "weapons-v1.json").read_text(encoding="utf-8")
            ammo_before = (config_dir / "ammo-v1.json").read_text(encoding="utf-8")

            entities = [
                _entity("weapons", "w1", "Weapon", description="Weapon text."),
                _entity("ammo", "m1", "Ammo", description="Ammo text."),
                _entity("armors", "a1", "Armor", tier=1),
                _entity("cybernetics", "c1", "Cybernetic", tier=None),
            ]
            sidecar = root / "structured-entities.json"
            sidecar.write_text(
                json.dumps({"schema": "cybermancy-step4-structured-entities-v1.1", "entities": entities}),
                encoding="utf-8",
            )
            manuscript = root / "player-guide.md"
            manuscript.write_text(
                "\n".join(f"::: {{#family:{family}}}\nplaceholder\n:::" for _, family, _ in entries),
                encoding="utf-8",
            )

            rc, payload = initialize_equipment(
                family=None,
                all_families=True,
                config_dir=config_dir,
                sidecar=sidecar,
                manuscript=manuscript,
                section_registry=section_registry,
                report_dir=report_dir,
            )
            statuses = {item["family"]: item["status"] for item in payload["families"]}

            self.assertEqual((config_dir / "weapons-v1.json").read_text(encoding="utf-8"), weapons_before)
            self.assertEqual((config_dir / "ammo-v1.json").read_text(encoding="utf-8"), ammo_before)
            self.assertTrue((config_dir / "armors-v1.json").is_file())
            self.assertTrue((config_dir / "cybernetics-v1.json").is_file())
            self.assertTrue((report_dir / "equipment-init-all.json").is_file())

        self.assertEqual(rc, 0)
        self.assertEqual(statuses["weapons"], "EXISTS")
        self.assertEqual(statuses["ammo"], "EXISTS")
        self.assertEqual(statuses["armors"], "CREATED")
        self.assertEqual(statuses["cybernetics"], "CREATED")


class TestEquipmentInitParser(unittest.TestCase):
    def test_init_accepts_family_and_all(self):
        builder = _load_builder()
        family_args = builder.parser().parse_args(["init-equipment", "--family", "armor"])
        all_args = builder.parser().parse_args(["init-equipment", "--all"])
        self.assertEqual(family_args.family, "armor")
        self.assertTrue(all_args.all)

    def test_init_requires_exactly_one_selector(self):
        builder = _load_builder()
        with self.assertRaises(SystemExit):
            builder.parser().parse_args(["init-equipment"])
        with self.assertRaises(SystemExit):
            builder.parser().parse_args(["init-equipment", "--family", "armors", "--all"])


if __name__ == "__main__":
    unittest.main()
