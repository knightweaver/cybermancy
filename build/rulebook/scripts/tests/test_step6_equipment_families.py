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

from rulebook_layout.equipment_catalog import build_catalog_rows, render_equipment_catalog_latex
from rulebook_layout.latex import render_equipment_chapter_document


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-layout.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_layout", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestAmmunitionFamilyConfig(unittest.TestCase):
    def setUp(self):
        self.config_path = HERE.parents[2] / "layout" / "equipment" / "ammo-v1.json"
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

    def ammo_entity(self, index: int) -> dict:
        name = f"Ammo {index:02d}"
        return {
            "semanticId": f"entity:ammo:A{index:02d}",
            "family": "ammo",
            "sourceId": f"A{index:02d}",
            "name": name,
            "publicationData": {
                "tier": None,
                "description": f"Rule text for {name}.",
                "burden": None,
                "range": None,
            },
        }

    def test_ammo_config_is_first_generic_single_catalog_family(self):
        self.assertEqual(self.config["layoutMode"], "single-catalog")
        self.assertEqual(self.config["family"], "ammo")
        self.assertEqual(self.config["chapter"], 16)
        self.assertEqual(self.config["expectedEntityCount"], 13)
        self.assertEqual(self.config["tierMode"], "absent")
        self.assertEqual(self.config["expectedColumnLabels"], ["Name", "Effect"])

    def test_tierless_catalog_renders_without_synthetic_group_band(self):
        rows = build_catalog_rows([self.ammo_entity(2), self.ammo_entity(1)], self.config)
        self.assertEqual([row.name for row in rows], ["Ammo 01", "Ammo 02"])
        latex = render_equipment_catalog_latex(rows, self.config)
        self.assertIn(r"\fontsize{7.8}{9.2}\selectfont", latex)
        self.assertIn("AMMUNITION — CONTINUED", latex)
        self.assertNotIn(r"\MakeUppercase{—}", latex)
        self.assertIn(r"\begin{longtable}", latex)

    def test_generic_chapter_wrapper_uses_configured_chapter_and_title(self):
        rows = build_catalog_rows([self.ammo_entity(1)], self.config)
        family_latex = render_equipment_catalog_latex(rows, self.config)
        chapter = render_equipment_chapter_document(family_latex, self.config)
        self.assertIn("CHAPTER 16 / EQUIPMENT", chapter)
        self.assertIn("AMMUNITION", chapter)


class TestGenericEquipmentValidation(unittest.TestCase):
    def test_validate_equipment_family_accepts_tierless_ammo_sidecar(self):
        builder = _load_builder()
        config_path = HERE.parents[2] / "layout" / "equipment" / "ammo-v1.json"
        entities = []
        for index in range(13):
            name = f"Ammo {index:02d}"
            entities.append({
                "semanticId": f"entity:ammo:A{index:02d}",
                "family": "ammo",
                "sourceId": f"A{index:02d}",
                "name": name,
                "publicationData": {
                    "tier": None,
                    "description": f"Rule text for {name}.",
                    "burden": None,
                    "range": None,
                },
            })
        sidecar = {"schema": builder.SIDECAR_SCHEMA_D, "entities": entities}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sidecar_path = root / "structured-entities.json"
            manuscript_path = root / "player-guide.md"
            sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
            manuscript_path.write_text("::: {#family:ammo}\nplaceholder\n:::\n", encoding="utf-8")
            report, config, _, rows = builder.validate_equipment_family(
                "ammo", config_path, sidecar_path, manuscript_path
            )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(config["chapter"], 16)
        self.assertEqual(len(rows), 13)
        checks = {check["code"]: check["status"] for check in report["checks"]}
        self.assertEqual(checks["EQUIPMENT_ENTITY_COUNT"], "PASS")
        self.assertEqual(checks["TIER_CONTRACT"], "PASS")
        self.assertEqual(checks["CATALOG_ORDER"], "PASS")


if __name__ == "__main__":
    unittest.main()
