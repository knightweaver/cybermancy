import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_layout.equipment_catalog import (
    build_catalog_rows,
    render_equipment_catalog_latex,
    replace_family_div_with_latex,
)
from rulebook_normalize.publication import damage_formula, structured_publication_data


class TestStep4PublicationSidecarProjection(unittest.TestCase):
    def test_weapon_projection_uses_formula_only_and_normalized_semantics(self):
        doc = {
            "_id": "W1",
            "name": "Smartpistol",
            "system": {
                "tier": 1,
                "burden": "One Handed",
                "description": "<p>A <strong>smart</strong> sidearm.</p>",
                "attack": {
                    "range": "Far",
                    "roll": {"trait": "Finesse"},
                    "damage": {
                        "parts": [
                            {"value": {"dice": "d6", "bonus": 2}, "type": ["physical"]}
                        ]
                    },
                },
            },
        }
        metadata = {
            "weaponSemantics": {
                "trait": "Finesse",
                "weaponFeatures": [],
                "actions": ["Smartlink"],
                "criticalEffects": ["Pinpoint"],
            }
        }
        projected = structured_publication_data("weapons", doc, metadata)
        self.assertEqual(projected["attack"]["damageFormula"], "d6+2")
        self.assertNotIn("physical", projected["attack"]["damageFormula"])
        self.assertEqual(projected["description"], "A smart sidearm.")
        self.assertEqual(projected["actions"], ["Smartlink"])
        self.assertEqual(projected["criticalEffects"], ["Pinpoint"])

    def test_damage_formula_handles_multiple_parts_without_types(self):
        attack = {
            "damage": {
                "parts": [
                    {"value": {"dice": "d8", "bonus": 0}, "type": ["physical"]},
                    {"value": {"dice": "d4", "bonus": -1}, "type": ["magic"]},
                ]
            }
        }
        self.assertEqual(damage_formula(attack), "d8; d4-1")


class TestEquipmentCatalogPrimitive(unittest.TestCase):
    def setUp(self):
        config_path = HERE.parents[2] / "layout" / "equipment" / "weapons-v1.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

    def entity(
        self,
        name,
        trait,
        *,
        action=None,
        feature=None,
        critical=None,
        damage="d8",
        description="Desc",
        range_value="Close",
        burden="One Handed",
    ):
        return {
            "semanticId": f"entity:weapons:{name}",
            "family": "weapons",
            "sourceId": name,
            "name": name,
            "audience": "player",
            "sourcePath": f"src/{name}.json",
            "publicationData": {
                "tier": 1,
                "description": description,
                "burden": burden,
                "attack": {"trait": trait, "range": range_value, "damageFormula": damage},
                "weaponFeatures": [] if feature is None else [feature],
                "actions": [] if action is None else [action],
                "criticalEffects": [] if critical is None else [critical],
            },
        }

    def test_rows_sort_trait_then_name_case_insensitively(self):
        entities = [
            self.entity("Zulu", "Strength"),
            self.entity("beta", "Agility"),
            self.entity("Alpha", "agility"),
            self.entity("Middle", "Finesse"),
        ]
        rows = build_catalog_rows(entities, self.config, tier=1)
        self.assertEqual([row.name for row in rows], ["Alpha", "beta", "Middle", "Zulu"])
        self.assertEqual([row.group for row in rows], ["AGILITY", "AGILITY", "FINESSE", "STRENGTH"])

    def test_trait_range_and_burden_are_humanized_for_display(self):
        rows = build_catalog_rows([
            self.entity(
                "Example",
                "agility",
                range_value="veryClose",
                burden="oneHanded",
            )
        ], self.config, tier=1)
        row = rows[0]
        self.assertEqual(row.cells["publicationData.attack.trait"], "Agility")
        self.assertEqual(row.cells["publicationData.attack.range"], "Very close")
        self.assertEqual(row.cells["publicationData.burden"], "One handed")

    def test_cyber_spur_combines_weapon_feature_then_action(self):
        rows = build_catalog_rows([
            self.entity("Cyber Spur", "Strength", feature="retractable", action="Concealed", critical="Ambush Kill")
        ], self.config, tier=1)
        self.assertEqual(rows[0].cells["action"], "Retractable, Concealed")
        self.assertEqual(rows[0].cells["criticalEffect"], "Ambush Kill")

    def test_absent_action_and_critical_render_em_dash(self):
        rows = build_catalog_rows([
            self.entity("Light Semi-auto pistol", "Agility")
        ], self.config, tier=1)
        self.assertEqual(rows[0].cells["action"], "—")
        self.assertEqual(rows[0].cells["criticalEffect"], "—")

    def test_latex_table_has_approved_header_trait_band_description_padding_and_vertical_centering(self):
        rows = build_catalog_rows([
            self.entity("Alpha", "Agility", action="Quick Draw", critical="Pinning Strike")
        ], self.config, tier=1)
        latex = render_equipment_catalog_latex(rows, self.config)
        for label in ("Name", "Tier", "Trait", "Range", "Burden", "Damage", "Action", "Critical Effect", "Description"):
            self.assertIn(f"\\MakeUppercase{{{label}}}", latex)
        self.assertIn("AGILITY", latex)
        self.assertIn("CMTableHeader", latex)
        self.assertIn("CMGroupBand", latex)
        self.assertIn(r"\vspace*{2pt}\strut Desc\strut\par\vspace*{2pt}", latex)
        self.assertIn(r">{\RaggedRight\arraybackslash}m{0.970in}", latex)
        self.assertIn(r">{\Centering\arraybackslash}m{0.290in}", latex)
        self.assertNotIn(r">{\RaggedRight\arraybackslash}p{0.970in}", latex)

    def test_family_ast_replacement_is_semantic_not_textual(self):
        ast = {
            "pandoc-api-version": [1, 23],
            "meta": {},
            "blocks": [
                {
                    "t": "Div",
                    "c": [
                        ["family:weapons", ["rb-collection"], [["data-family", "weapons"]]],
                        [{"t": "Para", "c": [{"t": "Str", "c": "old"}]}],
                    ],
                },
                {
                    "t": "Div",
                    "c": [
                        ["family:ammo", ["rb-collection"], [["data-family", "ammo"]]],
                        [{"t": "Para", "c": [{"t": "Str", "c": "keep"}]}],
                    ],
                },
            ],
        }
        result = copy.deepcopy(ast)
        count = replace_family_div_with_latex(result, "weapons", "\\begin{longtable}...\\end{longtable}")
        self.assertEqual(count, 1)
        self.assertEqual(result["blocks"][0]["c"][1][0]["t"], "RawBlock")
        self.assertEqual(result["blocks"][1]["c"][1][0]["t"], "Para")


if __name__ == "__main__":
    unittest.main()
