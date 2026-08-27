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

    def test_rules_markdown_preserves_list_structure(self):
        doc = {
            "system": {
                "description": "<p>Outcomes:</p><ul><li>One</li><li>Two</li></ul>",
                "actions": {},
            }
        }
        data = ice_publication_data(doc, "sentry")
        self.assertIn("- One", data["rulesMarkdown"])
        self.assertIn("- Two", data["rulesMarkdown"])

    def test_action_only_ice_is_publication_complete(self):
        doc = {
            "system": {
                "description": "",
                "actions": {
                    "zap": {
                        "_id": "zap",
                        "name": "Zap",
                        "type": "damage",
                        "description": "The wall sends feedback down the line.",
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
        self.assertEqual(data["actions"][0]["damage"]["parts"][0]["applyTo"], "stress")
        self.assertEqual(
            data["actions"][0]["damage"]["parts"][0]["value"]["customFormula"],
            "1",
        )

    def test_blank_ice_without_actions_is_not_publication_complete(self):
        data = ice_publication_data(
            {"system": {"description": "", "actions": {}, "resource": {"value": 10}}},
            "wall",
        )
        self.assertFalse(has_reader_rules(data))


if __name__ == "__main__":
    unittest.main()
