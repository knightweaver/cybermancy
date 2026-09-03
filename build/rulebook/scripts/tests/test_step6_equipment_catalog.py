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

    def test_armor_projection_includes_thresholds_score_and_complete_features(self):
        doc = {
            "_id": "A1",
            "name": "Test Carapace",
            "system": {
                "tier": 2,
                "baseScore": 4,
                "baseThresholds": {"major": 9, "severe": 20},
                "armorFeatures": [
                    {"value": "heavy", "effectIds": ["E1"], "actionIds": []},
                    {"value": "hopeful", "effectIds": [], "actionIds": ["A1"]},
                ],
                "actions": {
                    "A1": {
                        "_id": "A1",
                        "name": "Hope",
                        "description": "When you would spend a Hope, you can mark an Armor Slot instead.",
                    }
                },
            },
            "effects": [
                {"_id": "E1", "name": "Heavy", "description": "<p>-1 to <strong>Evasion</strong></p>"}
            ],
        }

        projected = structured_publication_data("armors", doc, {})

        self.assertEqual(projected["baseScore"], 4)
        self.assertEqual(projected["baseThresholds"], {"major": 9, "severe": 20})
        self.assertEqual(
            projected["armorFeatures"],
            [
                {"name": "Heavy", "description": "-1 to Evasion"},
                {
                    "name": "Hopeful",
                    "description": "When you would spend a Hope, you can mark an Armor Slot instead.",
                },
            ],
        )

    def test_armor_projection_retains_unlinked_rule_bearing_effect_once(self):
        doc = {
            "_id": "A2",
            "name": "Bare Bones",
            "system": {
                "tier": 1,
                "baseScore": 3,
                "baseThresholds": {"major": 9, "severe": 19},
                "armorFeatures": [],
                "actions": {},
            },
            "effects": [
                {
                    "_id": "E2",
                    "name": "Bare Bones",
                    "description": "<p>When you choose not to equip armor, use these base values.</p>",
                }
            ],
        }

        projected = structured_publication_data("armors", doc, {})

        self.assertEqual(
            projected["armorFeatures"],
            [{"name": "Bare Bones", "description": "When you choose not to equip armor, use these base values."}],
        )

    def test_armor_projection_uses_empty_feature_array_for_featureless_armor(self):
        doc = {
            "_id": "A3",
            "name": "Plain Armor",
            "system": {
                "tier": 1,
                "baseScore": 3,
                "baseThresholds": {"major": 6, "severe": 13},
                "armorFeatures": [],
                "actions": {},
            },
            "effects": [],
        }

        projected = structured_publication_data("armors", doc, {})

        self.assertEqual(projected["armorFeatures"], [])


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

    def test_armor_catalog_uses_tier_for_tables_not_columns(self):
        config_path = HERE.parents[2] / "layout" / "equipment" / "armors-v1.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        entities = [
            {
                "semanticId": "entity:armors:A1",
                "family": "armors",
                "sourceId": "A1",
                "name": "Aegis Coat",
                "publicationData": {
                    "tier": 1,
                    "baseScore": 3,
                    "baseThresholds": {"major": 7, "severe": 15},
                    "armorFeatures": [
                        {
                            "name": "Reinforced",
                            "description": "Increase both thresholds by +2.",
                        },
                        {
                            "name": "Flexible",
                            "description": "You have +1 Evasion.",
                        },
                    ],
                    "description": "This description must not be published in the table.",
                },
            },
            {
                "semanticId": "entity:armors:A2",
                "family": "armors",
                "sourceId": "A2",
                "name": "Bulwark Mesh",
                "publicationData": {
                    "tier": 2,
                    "baseScore": 4,
                    "baseThresholds": {"major": 9, "severe": 20},
                    "armorFeatures": [],
                    "description": "A second description that must not be published.",
                },
            },
        ]

        rows = build_catalog_rows(entities, config)
        self.assertEqual([row.tier for row in rows], [1, 2])
        self.assertEqual(rows[0].cells["thresholds"], "7 / 15")
        self.assertEqual(rows[0].cells["publicationData.baseScore"], "3")
        self.assertEqual(
            rows[0].cells["publicationData.armorFeatures"],
            "Reinforced: Increase both thresholds by +2.; Flexible: You have +1 Evasion.",
        )
        self.assertEqual(rows[1].cells["publicationData.armorFeatures"], "—")

        latex = render_equipment_catalog_latex(rows, config)
        for label in ("Name", "Thresholds", "Base Score", "Features"):
            self.assertIn(f"\\MakeUppercase{{{label}}}", latex)
        self.assertNotIn(r"\MakeUppercase{Tier}", latex)
        self.assertNotIn(r"\MakeUppercase{Description}", latex)
        self.assertIn("TIER 1", latex)
        self.assertIn("TIER 2", latex)
        self.assertIn("7 / 15", latex)
        self.assertIn("Reinforced: Increase both thresholds by +2.; Flexible: You have +1 Evasion.", latex)
        self.assertNotIn("This description must not be published", latex)

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

    def test_longtable_repeats_header_and_protects_trait_band_on_page_breaks(self):
        rows = build_catalog_rows([
            self.entity("Alpha", "Agility", action="Quick Draw", critical="Pinning Strike")
        ], self.config, tier=1)
        latex = render_equipment_catalog_latex(rows, self.config)
        self.assertIn(r"\setlength{\LTpre}{0pt}", latex)
        self.assertIn(r"\setlength{\LTpost}{0pt}", latex)
        self.assertIn("TIER 1 — CONTINUED", latex)
        self.assertIn(r"\endfirsthead", latex)
        self.assertIn(r"\endhead", latex)
        self.assertGreaterEqual(latex.count("CMTableHeader"), 2)
        self.assertIn(r"\MakeUppercase{AGILITY}}} \\*", latex)

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
