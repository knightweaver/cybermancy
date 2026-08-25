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
    SCAFFOLD_STYLE,
    SCAFFOLD_TABLE_STYLE,
    generate_equipment_config,
    initialize_equipment,
    is_scaffold_config,
)


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-layout.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_layout_refresh", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _section():
    return {
        "schema": "cybermancy-step6-equipment-section-v1.0",
        "partLabel": "EQUIPMENT & TECHNOLOGY",
        "families": [
            {"chapter": 18, "family": "armors", "title": "Armor", "config": "armors-v1.json"},
        ],
    }


def _sidecar(tier):
    return {
        "schema": "cybermancy-step4-structured-entities-v1.2",
        "entities": [
            {
                "semanticId": "entity:armors:A",
                "family": "armors",
                "sourceId": "A",
                "name": "Test Armor",
                "sourcePath": "src/packs/items/armors/Test_A.json",
                "publicationData": {
                    "tier": tier,
                    "description": "Protective gear.",
                    "burden": None,
                    "range": None,
                },
                "publicationProvenance": {
                    "tier": {
                        "value": tier,
                        "source": "foundry-folder" if tier is not None else "absent",
                    }
                },
            }
        ],
    }


class TestEquipmentScaffoldMarker(unittest.TestCase):
    def test_new_config_is_marked_as_scaffold(self):
        config = generate_equipment_config({
            "family": "armors",
            "chapter": 18,
            "title": "Armor",
            "entityCount": 1,
            "sidecarSchema": "cybermancy-step4-structured-entities-v1.2",
            "publicationFields": [
                {"path": "publicationData.tier", "populatedCount": 1},
                {"path": "publicationData.description", "populatedCount": 1},
            ],
        })
        self.assertEqual(config["configStatus"], "scaffold")
        self.assertEqual(config["generatedBy"]["basisSidecarSchema"], "cybermancy-step4-structured-entities-v1.2")
        self.assertEqual(config["layoutMode"], "tiered-catalog")
        self.assertTrue(is_scaffold_config(config))

    def test_legacy_v1_initializer_shape_is_recognized(self):
        legacy = {
            "schema": "cybermancy-step6-equipment-catalog-config-v1.1",
            "layoutMode": "single-catalog",
            "family": "armors",
            "chapter": 18,
            "partLabel": "EQUIPMENT & TECHNOLOGY",
            "title": "Armor",
            "deck": "",
            "outputStem": "Cybermancy_Chapter18_Armor_Step6",
            "expectedEntityCount": 1,
            "expectedColumnLabels": ["Name", "Description"],
            "tierMode": "absent",
            "sort": ["name"],
            "requiredPublicationFields": ["publicationData.description"],
            "display": {"missing": "—", "groupUppercase": True},
            "columns": [
                {"key": "name", "label": "Name", "widthIn": 1.5, "align": "left", "verticalPaddingPt": 2, "bold": True},
                {"key": "publicationData.description", "label": "Description", "widthIn": 5.881, "align": "left", "verticalPaddingPt": 2},
            ],
            "tableStyle": dict(SCAFFOLD_TABLE_STYLE),
            "pagination": {"continuationLabel": "Armor", "continuationTemplate": "{label} — CONTINUED"},
            "style": dict(SCAFFOLD_STYLE),
        }
        self.assertTrue(is_scaffold_config(legacy))

    def test_tuned_ammo_style_is_not_mistaken_for_scaffold(self):
        accepted = {
            "schema": "cybermancy-step6-equipment-catalog-config-v1.1",
            "layoutMode": "single-catalog",
            "family": "ammo",
            "chapter": 17,
            "partLabel": "EQUIPMENT & TECHNOLOGY",
            "title": "Ammunition",
            "deck": "",
            "expectedColumnLabels": ["Name", "Effect"],
            "columns": [
                {"key": "name", "label": "Name", "widthIn": 1.65},
                {"key": "publicationData.description", "label": "Effect", "widthIn": 5.75},
            ],
            "tableStyle": {"tabcolsepPt": 2.5, "arrayStretch": 1.08, "fontSizePt": 7.8, "leadingPt": 9.2},
            "style": dict(SCAFFOLD_STYLE),
        }
        self.assertFalse(is_scaffold_config(accepted))


class TestEquipmentScaffoldRefresh(unittest.TestCase):
    def test_refresh_migrates_legacy_scaffold_and_adds_new_tier_column(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "equipment"
            report_dir = root / "reports"
            config_dir.mkdir()
            section = config_dir / "equipment-section-v1.json"
            section.write_text(json.dumps(_section()), encoding="utf-8")
            manuscript = root / "player-guide.md"
            manuscript.write_text("::: {#family:armors}\nplaceholder\n:::\n", encoding="utf-8")
            sidecar = root / "structured-entities.json"
            sidecar.write_text(json.dumps(_sidecar(None)), encoding="utf-8")

            first_rc, first = initialize_equipment(
                family="armors",
                all_families=False,
                config_dir=config_dir,
                sidecar=sidecar,
                manuscript=manuscript,
                section_registry=section,
                report_dir=report_dir,
            )
            config_path = config_dir / "armors-v1.json"
            original = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(original["tierMode"], "absent")
            self.assertEqual(original["layoutMode"], "single-catalog")

            # Emulate a config created by the already-released init-equipment
            # v1.0, before explicit scaffold markers and tiered catalogs existed.
            original.pop("configStatus", None)
            original.pop("generatedBy", None)
            original.pop("tierLabel", None)
            original["pagination"] = {
                "continuationLabel": "Armor",
                "continuationTemplate": "{label} — CONTINUED",
            }
            config_path.write_text(json.dumps(original, indent=2), encoding="utf-8")
            sidecar.write_text(json.dumps(_sidecar(2)), encoding="utf-8")

            refresh_rc, refresh = initialize_equipment(
                family="armors",
                all_families=False,
                config_dir=config_dir,
                sidecar=sidecar,
                manuscript=manuscript,
                section_registry=section,
                report_dir=report_dir,
                refresh_scaffolds=True,
            )
            updated = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(first_rc, 0)
        self.assertEqual(first["families"][0]["status"], "CREATED")
        self.assertEqual(refresh_rc, 0)
        self.assertEqual(refresh["families"][0]["status"], "REFRESHED")
        self.assertTrue(refresh["families"][0]["legacyScaffoldMigrated"])
        self.assertEqual(updated["tierMode"], "present")
        self.assertEqual(updated["layoutMode"], "tiered-catalog")
        self.assertEqual(updated["expectedColumnLabels"], ["Name", "Tier", "Description"])
        self.assertEqual(updated["configStatus"], "scaffold")

    def test_step6_generic_validator_accepts_v12_sidecar(self):
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "equipment"
            report_dir = root / "reports"
            config_dir.mkdir()
            section = config_dir / "equipment-section-v1.json"
            section.write_text(json.dumps(_section()), encoding="utf-8")
            manuscript = root / "player-guide.md"
            manuscript.write_text("::: {#family:armors}\nplaceholder\n:::\n", encoding="utf-8")
            sidecar = root / "structured-entities.json"
            sidecar.write_text(json.dumps(_sidecar(2)), encoding="utf-8")
            rc, _ = initialize_equipment(
                family="armors",
                all_families=False,
                config_dir=config_dir,
                sidecar=sidecar,
                manuscript=manuscript,
                section_registry=section,
                report_dir=report_dir,
            )
            report, config, _, rows = builder.validate_equipment_family(
                "armors", config_dir / "armors-v1.json", sidecar, manuscript
            )

        self.assertEqual(rc, 0)
        self.assertIsNotNone(config)
        self.assertEqual(config["layoutMode"], "tiered-catalog")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(rows), 1)
        schemas = [check for check in report["checks"] if check["code"] == "SIDECAR_SCHEMA"]
        self.assertEqual(schemas[0]["status"], "PASS")

    def test_cli_accepts_refresh_scaffolds(self):
        builder = _load_builder()
        args = builder.parser().parse_args(["init-equipment", "--all", "--refresh-scaffolds"])
        self.assertTrue(args.all)
        self.assertTrue(args.refresh_scaffolds)


if __name__ == "__main__":
    unittest.main()
