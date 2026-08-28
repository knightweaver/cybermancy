import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_step4_ice_semantics import (
    EXPECTED_ICE_COUNTS,
    EXPECTED_ICE_TOTAL,
    classify_ice_document,
    has_reader_rules,
    ice_publication_data,
    normalize_actions,
    normalize_resource,
    resolve_ice_folders,
)


class TestStep4IceSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feature_root = REPO_ROOT / "src" / "packs" / "system" / "features"
        cls.folder_types, cls.folder_errors = resolve_ice_folders(cls.feature_root)

    def test_canonical_ice_folder_taxonomy_resolves(self):
        self.assertEqual(self.folder_errors, [])
        self.assertEqual(set(self.folder_types.values()), {"sentry", "wall"})

    def test_canonical_ice_membership_is_6_7_13(self):
        counts = {"sentry": 0, "wall": 0}
        for path in sorted(self.feature_root.glob("*.json")):
            import json

            doc = json.loads(path.read_text(encoding="utf-8"))
            key = doc.get("_key")
            if isinstance(key, str) and "!folders!" in key:
                continue
            ice_type = classify_ice_document(doc, self.folder_types)
            if ice_type:
                counts[ice_type] += 1
        self.assertEqual(counts, EXPECTED_ICE_COUNTS)
        self.assertEqual(sum(counts.values()), EXPECTED_ICE_TOTAL)

    def test_duplicate_foundry_action_alias_prefers_richer_semantics(self):
        system = {
            "actions": {
                "Alias": {
                    "_id": "same",
                    "name": "Example",
                    "type": "effect",
                    "description": "short",
                },
                "same": {
                    "_id": "same",
                    "name": "Example",
                    "type": "effect",
                    "description": "<p>Longer reader-facing rules text.</p>",
                    "cost": [{"key": "fear", "value": 1}],
                },
            }
        }
        actions = normalize_actions(system)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["sourceId"], "same")
        self.assertEqual(actions[0]["rulesMarkdown"], "Longer reader-facing rules text.")
        self.assertEqual(actions[0]["cost"][0]["key"], "fear")
        self.assertNotIn("systemPath", actions[0])
        self.assertNotIn("chatDisplay", actions[0])

    def test_paragraph_wrapped_nested_lists_are_publication_markdown(self):
        doc = {
            "system": {
                "description": (
                    "<p>Outcomes:</p><ul>"
                    "<li><p>One</p></li>"
                    "<li><p>Failure</p><ul>"
                    "<li><p>Advance alert</p></li>"
                    "<li><p>Apply penalty</p></li>"
                    "</ul></li></ul>"
                ),
                "actions": {},
            }
        }
        markdown = ice_publication_data(doc, "sentry")["rulesMarkdown"]
        self.assertIn("- One", markdown)
        self.assertIn("- Failure", markdown)
        self.assertIn("  - Advance alert", markdown)
        self.assertIn("  - Apply penalty", markdown)
        self.assertNotIn("-\n\nOne", markdown)
        self.assertNotIn("  -\n\nAdvance alert", markdown)

    def test_generic_any_target_is_not_reader_semantics(self):
        actions = normalize_actions(
            {
                "actions": {
                    "a": {
                        "_id": "a",
                        "name": "Example",
                        "type": "effect",
                        "actionType": "action",
                        "description": "Do something.",
                        "target": {"type": "any", "amount": None},
                    }
                }
            }
        )
        self.assertEqual(len(actions), 1)
        self.assertNotIn("target", actions[0])

    def test_action_only_ice_is_publication_complete_and_damage_has_reader_labels(self):
        doc = {
            "system": {
                "description": "",
                "actions": {
                    "zap": {
                        "_id": "zap",
                        "name": "Zap",
                        "type": "damage",
                        "description": "The wall sends feedback down the line.",
                        "target": {"type": "any", "amount": None},
                        "damage": {
                            "parts": [
                                {
                                    "value": {
                                        "custom": {"enabled": True, "formula": "1"},
                                        "multiplier": "prof",
                                        "flatMultiplier": 1,
                                        "dice": "d6",
                                    },
                                    "applyTo": "stress",
                                    "type": [],
                                }
                            ],
                            "includeBase": False,
                        },
                    }
                },
            }
        }
        data = ice_publication_data(doc, "wall")
        self.assertTrue(has_reader_rules(data))
        action = data["actions"][0]
        self.assertNotIn("target", action)
        part = action["damage"]["parts"][0]
        self.assertEqual(part["applyTo"], "stress")
        self.assertEqual(part["readerTarget"], "Stress")
        self.assertEqual(part["value"]["customFormula"], "1")

    def test_hit_points_and_damage_types_have_reader_labels(self):
        actions = normalize_actions(
            {
                "actions": {
                    "damage": {
                        "_id": "damage",
                        "name": "Damage",
                        "type": "damage",
                        "damage": {
                            "parts": [
                                {
                                    "value": {"custom": {"enabled": True, "formula": "1"}},
                                    "applyTo": "hitPoints",
                                    "type": ["physical"],
                                }
                            ]
                        },
                    }
                }
            }
        )
        part = actions[0]["damage"]["parts"][0]
        self.assertEqual(part["readerTarget"], "HP")
        self.assertEqual(part["readerTypes"], ["Physical"])

    def test_unlabeled_resource_is_preserved_but_not_reader_facing(self):
        resource = normalize_resource({"resource": {"type": "simple", "value": 14, "max": ""}})
        self.assertEqual(resource["type"], "simple")
        self.assertEqual(resource["value"], 14)
        self.assertIs(resource["readerFacing"], False)

    def test_blank_ice_without_actions_is_not_publication_complete(self):
        data = ice_publication_data(
            {"system": {"description": "", "actions": {}, "resource": {"value": 10}}},
            "wall",
        )
        self.assertFalse(has_reader_rules(data))


if __name__ == "__main__":
    unittest.main()
