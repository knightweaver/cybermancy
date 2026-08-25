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

from rulebook_layout.equipment_catalog import (
    build_catalog_rows,
    partition_catalog_rows_by_tier,
    render_equipment_catalog_latex,
)
from rulebook_layout.equipment_init import generate_equipment_config


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-layout.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_layout_tiered", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _entity(source_id: str, name: str, tier):
    return {
        "semanticId": f"entity:cybernetics:{source_id}",
        "family": "cybernetics",
        "sourceId": source_id,
        "name": name,
        "publicationData": {
            "tier": tier,
            "description": f"Rule text for {name}.",
            "range": None,
            "burden": None,
        },
    }


def _bootstrap(tier_populated: int, entity_count: int = 4):
    return {
        "family": "cybernetics",
        "chapter": 19,
        "title": "Cybernetics",
        "entityCount": entity_count,
        "sidecarSchema": "cybermancy-step4-structured-entities-v1.2",
        "publicationFields": [
            {"path": "publicationData.tier", "populatedCount": tier_populated},
            {"path": "publicationData.description", "populatedCount": entity_count},
            {"path": "publicationData.range", "populatedCount": 0},
            {"path": "publicationData.burden", "populatedCount": 0},
        ],
    }


class TestTieredConfigSelection(unittest.TestCase):
    def test_complete_tier_coverage_selects_tiered_catalog(self):
        config = generate_equipment_config(_bootstrap(4))
        self.assertEqual(config["tierMode"], "present")
        self.assertEqual(config["layoutMode"], "tiered-catalog")
        self.assertEqual(config["tierLabel"], "TIER {tier}")
        self.assertEqual(config["sort"], ["publicationData.tier", "name"])

    def test_partial_tier_coverage_stays_single_catalog(self):
        config = generate_equipment_config(_bootstrap(2))
        self.assertEqual(config["tierMode"], "optional")
        self.assertEqual(config["layoutMode"], "single-catalog")

    def test_tierless_family_stays_single_catalog(self):
        config = generate_equipment_config(_bootstrap(0))
        self.assertEqual(config["tierMode"], "absent")
        self.assertEqual(config["layoutMode"], "single-catalog")


class TestTieredCatalogRendering(unittest.TestCase):
    def setUp(self):
        self.config = generate_equipment_config(_bootstrap(4))
        self.entities = [
            _entity("C2B", "Beta Two", 2),
            _entity("C1B", "Beta One", 1),
            _entity("C2A", "Alpha Two", 2),
            _entity("C1A", "Alpha One", 1),
        ]

    def test_rows_partition_by_tier_and_remain_name_sorted_within_tier(self):
        rows = build_catalog_rows(self.entities, self.config)
        tiers = partition_catalog_rows_by_tier(rows)
        self.assertEqual(list(tiers), [1, 2])
        self.assertEqual([row.name for row in tiers[1]], ["Alpha One", "Beta One"])
        self.assertEqual([row.name for row in tiers[2]], ["Alpha Two", "Beta Two"])

    def test_renderer_produces_one_longtable_per_tier(self):
        rows = build_catalog_rows(self.entities, self.config)
        latex = render_equipment_catalog_latex(rows, self.config)
        self.assertEqual(latex.count(r"\begin{longtable}"), 2)
        self.assertEqual(latex.count(r"\end{longtable}"), 2)
        self.assertEqual(latex.count(r"\Needspace{1.25in}"), 2)
        self.assertEqual(latex.count(r"\par\addvspace{10pt}"), 1)
        self.assertIn("TIER 1", latex)
        self.assertIn("TIER 2", latex)
        self.assertLess(latex.index("TIER 1"), latex.index("TIER 2"))
        self.assertIn("TIER 1 — CONTINUED", latex)
        self.assertIn("TIER 2 — CONTINUED", latex)

        tier1_section, tier2_section = latex.split("TIER 2", 1)
        self.assertIn("Alpha One", tier1_section)
        self.assertIn("Beta One", tier1_section)
        self.assertNotIn("Alpha Two", tier1_section)
        self.assertIn("Alpha Two", tier2_section)
        self.assertIn("Beta Two", tier2_section)

    def test_invalid_tier_is_rejected_before_rendering(self):
        rows = build_catalog_rows([_entity("BAD", "Bad Tier", "bogus")], self.config)
        self.assertEqual(rows, [])
        with self.assertRaises(ValueError):
            render_equipment_catalog_latex(rows, self.config)

    def test_generic_validator_fails_closed_on_malformed_tier(self):
        builder = _load_builder()
        config = generate_equipment_config(_bootstrap(1, entity_count=1))
        bad_entity = _entity("BAD", "Bad Tier", "bogus")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path = root / "cybernetics-v1.json"
            sidecar_path = root / "structured-entities.json"
            manuscript_path = root / "player-guide.md"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            sidecar_path.write_text(
                json.dumps({"schema": builder.SIDECAR_SCHEMA_E, "entities": [bad_entity]}),
                encoding="utf-8",
            )
            manuscript_path.write_text("::: {#family:cybernetics}\nplaceholder\n:::\n", encoding="utf-8")
            report, _, _, rows = builder.validate_equipment_family(
                "cybernetics", config_path, sidecar_path, manuscript_path
            )

        self.assertEqual(rows, [])
        self.assertEqual(report["status"], "FAIL")
        checks = {check["code"]: check["status"] for check in report["checks"]}
        self.assertEqual(checks["CATALOG_ROW_COUNT"], "ERROR")


if __name__ == "__main__":
    unittest.main()
