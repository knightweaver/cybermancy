import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_layout.equipment_catalog import build_catalog_rows, render_equipment_catalog_latex
from rulebook_layout.latex import render_weapons_chapter_document, render_weapons_family_latex
from rulebook_layout.mechanics_reference import collect_weapon_references, render_mechanics_reference_latex
from rulebook_normalize.publication import SCHEMA_VERSION, structured_publication_data


class TestStep4WeaponReferenceDefinitions(unittest.TestCase):
    def test_sidecar_schema_and_action_definitions_support_step6d(self):
        self.assertEqual(SCHEMA_VERSION, "cybermancy-step4-structured-entities-v1.1")
        doc = {
            "_id": "W1",
            "name": "Cyber Spur",
            "system": {
                "tier": 1,
                "burden": "oneHanded",
                "description": "A hidden blade.",
                "attack": {
                    "range": "melee",
                    "roll": {"trait": "strength"},
                    "damage": {"parts": [{"value": {"dice": "d8", "bonus": 0}, "type": ["physical"]}]},
                },
                "weaponFeatures": [{"value": "retractable", "effectIds": [], "actionIds": []}],
                "actions": {
                    "Concealed": {
                        "name": "Concealed",
                        "description": "<p><strong>Concealed:</strong></p><p>Can be hidden; gain advantage on your first attack each scene.</p>",
                    },
                    "Ambush Kill": {
                        "name": "Critical Effect:  Ambush Kill",
                        "description": "<p><strong>Critical Effect - Ambush Kill:</strong></p><p>If striking from surprise, escalate Fear consequences for target.</p>",
                    },
                },
            },
        }
        metadata = {
            "weaponSemantics": {
                "trait": "strength",
                "weaponFeatures": ["retractable"],
                "actions": ["Concealed"],
                "criticalEffects": ["Ambush Kill"],
            }
        }
        data = structured_publication_data("weapons", doc, metadata)
        self.assertEqual(data["weaponFeatures"], ["retractable"])
        self.assertEqual(data["actions"], ["Concealed"])
        self.assertEqual(data["criticalEffects"], ["Ambush Kill"])
        self.assertEqual(data["actionDefinitions"][0]["name"], "Concealed")
        self.assertEqual(data["actionDefinitions"][0]["description"], "Can be hidden; gain advantage on your first attack each scene.")
        self.assertEqual(data["criticalEffectDefinitions"][0]["name"], "Ambush Kill")
        self.assertEqual(data["criticalEffectDefinitions"][0]["description"], "If striking from surprise, escalate Fear consequences for target.")
        self.assertEqual(data["weaponFeatureDefinitions"][0]["name"], "Retractable")
        self.assertEqual(data["weaponFeatureDefinitions"][0]["definitionStatus"], "resolved")
        self.assertTrue(data["weaponFeatureDefinitions"][0]["description"])
        self.assertEqual(data["weaponFeatureDefinitions"][0]["definitionSourcePath"], "daggerheart-mods/en.json")
        self.assertTrue(data["weaponFeatureDefinitions"][0]["definitionSourceSha256"])


class TestWeaponMechanicReferences(unittest.TestCase):
    def entity(self, sid, *, name=None, action_name="Smartlink", action_description="Same rule.", critical_name="Pinpoint", critical_description="Critical rule."):
        return {
            "semanticId": f"entity:weapons:{sid}",
            "family": "weapons",
            "sourceId": sid,
            "name": name or sid,
            "publicationData": {
                "weaponFeatures": [],
                "actions": [action_name] if action_name else [],
                "criticalEffects": [critical_name] if critical_name else [],
                "weaponFeatureDefinitions": [],
                "actionDefinitions": ([{"name": action_name, "kind": "action", "description": action_description, "definitionStatus": "resolved"}] if action_name else []),
                "criticalEffectDefinitions": ([{"name": critical_name, "kind": "critical-effect", "description": critical_description, "definitionStatus": "resolved"}] if critical_name else []),
            },
        }

    def test_identical_definitions_dedupe(self):
        refs = collect_weapon_references([self.entity("A"), self.entity("B")])
        self.assertEqual(len(refs["actions"]), 1)
        self.assertEqual(len(refs["criticalEffects"]), 1)
        self.assertEqual(refs["actions"][0].name, "Smartlink")
        self.assertEqual(refs["actions"][0].source_entities, ("entity:weapons:A", "entity:weapons:B"))
        self.assertEqual(refs["collisions"], [])
        self.assertEqual(refs["missingDefinitions"], [])
        self.assertEqual(refs["orphanDefinitions"], [])

    def test_same_name_with_different_rules_is_a_collision(self):
        refs = collect_weapon_references([
            self.entity("A", name="Smartpistol", action_description="Tier one rule."),
            self.entity("B", name="Smartpistol Mk II", action_description="Tier two rule."),
        ])
        self.assertEqual(len(refs["collisions"]), 1)
        collision = refs["collisions"][0]
        self.assertEqual(collision["name"], "Smartlink")
        details = [variant["sourceEntityDetails"] for variant in collision["variants"]]
        flattened = [item for group in details for item in group]
        self.assertIn({"semanticId": "entity:weapons:A", "name": "Smartpistol"}, flattened)
        self.assertIn({"semanticId": "entity:weapons:B", "name": "Smartpistol Mk II"}, flattened)
        self.assertEqual(refs["actions"], [])

    def test_displayed_mechanic_without_text_is_missing(self):
        refs = collect_weapon_references([self.entity("A", action_description="")])
        self.assertEqual(len(refs["missingDefinitions"]), 1)
        self.assertEqual(refs["missingDefinitions"][0]["name"], "Smartlink")


class TestCompleteChapter16Composition(unittest.TestCase):
    def setUp(self):
        config_path = HERE.parents[2] / "layout" / "equipment" / "weapons-v1.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

    def entity(self, name, tier, trait):
        return {
            "semanticId": f"entity:weapons:{tier}:{name}",
            "family": "weapons",
            "sourceId": f"{tier}:{name}",
            "name": name,
            "publicationData": {
                "tier": tier,
                "description": "Description",
                "burden": "oneHanded",
                "attack": {"trait": trait, "range": "veryClose", "damageFormula": "d8"},
                "weaponFeatures": [],
                "actions": [f"Action {tier}"],
                "criticalEffects": [f"Critical {tier}"],
                "weaponFeatureDefinitions": [],
                "actionDefinitions": [{"name": f"Action {tier}", "kind": "action", "description": f"Action rule {tier}.", "definitionStatus": "resolved"}],
                "criticalEffectDefinitions": [{"name": f"Critical {tier}", "kind": "critical-effect", "description": f"Critical rule {tier}.", "definitionStatus": "resolved"}],
            },
        }

    def test_config_locks_all_four_weapon_tiers(self):
        self.assertEqual(self.config["expectedEntityCount"], 47)
        self.assertEqual(self.config["expectedTierCounts"], {"1": 14, "2": 11, "3": 11, "4": 11})

    def test_family_and_chapter_render_four_tiers_plus_two_references(self):
        entities = [self.entity(f"Weapon {tier}", tier, "agility") for tier in range(1, 5)]
        tier_tables = {
            tier: render_equipment_catalog_latex(build_catalog_rows(entities, self.config, tier=tier), self.config)
            for tier in range(1, 5)
        }
        refs = collect_weapon_references(entities)
        actions = render_mechanics_reference_latex(refs["actions"], self.config)
        critical = render_mechanics_reference_latex(refs["criticalEffects"], self.config)
        family = render_weapons_family_latex(tier_tables, actions, critical, self.config)
        chapter = render_weapons_chapter_document(family, self.config)
        for tier in range(1, 5):
            self.assertIn(f"TIER {tier}", family)
        self.assertIn("WEAPON ACTIONS", family)
        self.assertIn("CRITICAL EFFECTS", family)
        self.assertGreaterEqual(family.count(r"\newpage"), 5)
        self.assertIn("CHAPTER 16 / EQUIPMENT", chapter)
        self.assertIn("WEAPONS", chapter)
        self.assertIn(r"\begin{document}", chapter)
        self.assertIn(r"\end{document}", chapter)


if __name__ == "__main__":
    unittest.main()
