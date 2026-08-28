import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.ice_reference import _selected_ids, new_report


CONFIG_PATH = REPO_ROOT / "build/rulebook/layout/ice/ice-reference-package-v1.json"


class TestStep6IceReferenceH3(unittest.TestCase):
    def _config(self):
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_canonical_config_is_h3_full_corpus(self):
        config = self._config()
        lifecycle = config["lifecycle"]
        prototype = config["prototype"]
        policy = config["prototypePolicy"]

        self.assertEqual(lifecycle["workstream"], "Step H3")
        self.assertEqual(lifecycle["alignmentRevision"], "H3.0")
        self.assertEqual(prototype["mode"], "full-corpus")
        self.assertNotIn("semanticIds", prototype)
        self.assertTrue(policy["requireFullCorpusSelection"])
        self.assertEqual(policy["expectedIceTotal"], 13)
        self.assertEqual(policy["expectedIceCounts"], {"sentry": 6, "wall": 7})

    def test_full_corpus_mode_selects_every_step4_ice_id(self):
        config = self._config()
        all_ids = [f"entity:features:test-{index}" for index in range(13)]
        report = new_report()
        selected = _selected_ids(all_ids, config, report)

        self.assertEqual(selected, all_ids)
        self.assertEqual(len(selected), 13)
        self.assertEqual(report["status"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
