import argparse
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_bootstrap import (
    inspect_equipment_bootstrap,
    publication_field_inventory,
)


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-layout.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_layout_bootstrap", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _section() -> dict:
    return {
        "schema": "cybermancy-step6-equipment-section-v1.0",
        "partLabel": "EQUIPMENT & TECHNOLOGY",
        "families": [
            {"chapter": 18, "family": "armors", "title": "Armor", "config": "armors-v1.json"}
        ],
    }


def _armor_entities() -> list[dict]:
    return [
        {
            "semanticId": "entity:armors:A1",
            "family": "armors",
            "sourceId": "A1",
            "name": "Aegis Coat",
            "sourcePath": "src/packs/items/armors/aegis.json",
            "publicationData": {
                "tier": 1,
                "description": "Armor rule text.",
                "burden": None,
                "range": None,
                "baseScore": 3,
                "baseThresholds": {"major": 7, "severe": 15},
                "armorFeatures": [
                    {"name": "Reinforced", "description": "Increase both thresholds by +2."}
                ],
            },
        },
        {
            "semanticId": "entity:armors:A2",
            "family": "armors",
            "sourceId": "A2",
            "name": "Bulwark Mesh",
            "sourcePath": "src/packs/items/armors/bulwark.json",
            "publicationData": {
                "tier": 2,
                "description": "Second armor rule.",
                "burden": "twoHanded",
                "range": None,
                "baseScore": 4,
                "baseThresholds": {"major": 9, "severe": 20},
                "armorFeatures": [],
            },
        },
    ]


class TestPublicationFieldInventory(unittest.TestCase):
    def test_inventory_reports_population_and_samples(self):
        fields = {item["path"]: item for item in publication_field_inventory(_armor_entities())}
        self.assertEqual(fields["publicationData.tier"]["populatedCount"], 2)
        self.assertEqual(fields["publicationData.tier"]["coveragePct"], 100.0)
        self.assertEqual(fields["publicationData.burden"]["populatedCount"], 1)
        self.assertEqual(fields["publicationData.burden"]["missingCount"], 1)
        self.assertEqual(fields["publicationData.range"]["populatedCount"], 0)
        self.assertIn("Armor rule text.", fields["publicationData.description"]["sampleValues"])
        self.assertEqual(fields["publicationData.baseScore"]["populatedCount"], 2)
        self.assertEqual(fields["publicationData.baseThresholds.major"]["populatedCount"], 2)
        self.assertEqual(fields["publicationData.baseThresholds.severe"]["populatedCount"], 2)
        self.assertEqual(fields["publicationData.armorFeatures"]["availableCount"], 2)
        self.assertEqual(fields["publicationData.armorFeatures"]["populatedCount"], 1)
        self.assertIn('"name": "Reinforced"', fields["publicationData.armorFeatures"]["sampleValues"][0])


class TestBootstrapInspection(unittest.TestCase):
    def test_missing_config_is_informational_not_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / "armors-v1.json"
            sidecar = root / "structured-entities.json"
            manuscript = root / "player-guide.md"
            registry = root / "equipment-section-v1.json"
            sidecar.write_text(
                json.dumps({"schema": "cybermancy-step4-structured-entities-v1.3", "entities": _armor_entities()}),
                encoding="utf-8",
            )
            manuscript.write_text("::: {#family:armors}\nplaceholder\n:::\n", encoding="utf-8")
            registry.write_text(json.dumps(_section()), encoding="utf-8")
            payload = inspect_equipment_bootstrap("armors", config, sidecar, manuscript, registry)

        self.assertEqual(payload["report"]["status"], "PASS")
        self.assertIsNone(payload["config"])
        self.assertEqual(payload["bootstrap"]["configStatus"], "NOT_IMPLEMENTED")
        self.assertEqual(payload["bootstrap"]["chapter"], 18)
        self.assertEqual(payload["bootstrap"]["title"], "Armor")
        self.assertEqual(payload["bootstrap"]["entityCount"], 2)
        self.assertEqual(payload["bootstrap"]["sidecarSchema"], "cybermancy-step4-structured-entities-v1.3")
        checks = {item["code"]: item["status"] for item in payload["report"]["checks"]}
        self.assertEqual(checks["CONFIG_STATUS"], "INFO")
        self.assertEqual(checks["EQUIPMENT_SECTION_CONTRACT"], "PASS")
        self.assertEqual(checks["EQUIPMENT_ENTITY_IDENTITY"], "PASS")
        self.assertEqual(checks["MANUSCRIPT_FAMILY_ALIGNMENT"], "PASS")
        self.assertEqual(checks["PUBLICATION_FIELD_INVENTORY"], "PASS")

    def test_command_inspect_equipment_routes_to_bootstrap_when_config_missing(self):
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / "armors-v1.json"
            sidecar = root / "structured-entities.json"
            manuscript = root / "player-guide.md"
            registry = root / "equipment-section-v1.json"
            sidecar.write_text(
                json.dumps({"schema": builder.SIDECAR_SCHEMA_D, "entities": _armor_entities()}),
                encoding="utf-8",
            )
            manuscript.write_text("::: {#family:armors}\nplaceholder\n:::\n", encoding="utf-8")
            registry.write_text(json.dumps(_section()), encoding="utf-8")
            builder.DEFAULT_SECTION_REGISTRY = registry
            args = argparse.Namespace(
                all=False,
                family="armor",
                config=str(config),
                sidecar=str(sidecar),
                manuscript=str(manuscript),
                report_dir=None,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = builder.command_inspect_equipment(args)
            payload = json.loads(output.getvalue())

        self.assertEqual(rc, 0)
        self.assertEqual(payload["report"]["status"], "PASS")
        self.assertEqual(payload["bootstrap"]["family"], "armors")
        self.assertEqual(payload["bootstrap"]["configStatus"], "NOT_IMPLEMENTED")

    def test_validate_equipment_still_requires_family_config(self):
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / "armors-v1.json"
            sidecar = root / "structured-entities.json"
            manuscript = root / "player-guide.md"
            sidecar.write_text(
                json.dumps({"schema": builder.SIDECAR_SCHEMA_D, "entities": _armor_entities()}),
                encoding="utf-8",
            )
            manuscript.write_text("::: {#family:armors}\nplaceholder\n:::\n", encoding="utf-8")
            report, _, _, _ = builder.validate_equipment_family("armors", config, sidecar, manuscript)

        self.assertEqual(report["status"], "FAIL")
        checks = {item["code"]: item["status"] for item in report["checks"]}
        self.assertEqual(checks["CONFIG_PRESENT"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
