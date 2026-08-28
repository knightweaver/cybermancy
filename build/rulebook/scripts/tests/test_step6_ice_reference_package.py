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
from rulebook_layout.ice_reference_package import (
    integrate_chapter29_ast,
    runtime_config,
)


CONFIG_PATH = REPO_ROOT / "build/rulebook/layout/ice/ice-reference-package-v1.json"


class TestStep6IceReferencePackage(unittest.TestCase):
    def _config(self):
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_canonical_config_is_frozen_full_corpus_v1(self):
        config = self._config()
        lifecycle = config["lifecycle"]
        selection = config["selection"]
        policy = config["publicationPolicy"]

        self.assertEqual(lifecycle["version"], "v1.0")
        self.assertEqual(lifecycle["status"], "frozen")
        self.assertEqual(lifecycle["acceptance"]["semanticRegression"], "PASS")
        self.assertEqual(lifecycle["acceptance"]["renderedFullCorpus"], "PASS")
        self.assertEqual(lifecycle["acceptance"]["visualReview"], "ACCEPTED")
        self.assertEqual(lifecycle["acceptanceCorpus"], {"total": 13, "sentry": 6, "wall": 7})
        self.assertEqual(selection["mode"], "full-corpus")
        self.assertNotIn("semanticIds", selection)
        self.assertNotIn("prototype", config)
        self.assertNotIn("prototypePolicy", config)
        self.assertTrue(policy["requireFullCorpusSelection"])
        self.assertEqual(policy["expectedIceTotal"], 13)
        self.assertEqual(policy["expectedIceCounts"], {"sentry": 6, "wall": 7})

    def test_frozen_config_selects_every_step4_ice_id(self):
        config = runtime_config(self._config())
        all_ids = [f"entity:features:test-{index}" for index in range(13)]
        report = new_report()
        selected = _selected_ids(all_ids, config, report)

        self.assertEqual(selected, all_ids)
        self.assertEqual(len(selected), 13)
        self.assertEqual(report["status"], "PASS", report)

    def test_chapter29_ast_integration_replaces_exact_semantic_nodes(self):
        ast = {
            "pandoc-api-version": [1, 23, 1],
            "meta": {},
            "blocks": [
                {
                    "t": "Header",
                    "c": [
                        2,
                        ["section:ch29-ice-reference", ["rb-chapter"], []],
                        [{"t": "Str", "c": "ICE Reference"}],
                    ],
                },
                {
                    "t": "Div",
                    "c": [
                        ["family:features", [], []],
                        [{"t": "Para", "c": [{"t": "Str", "c": "normalized-feature-body"}]}],
                    ],
                },
            ],
        }
        counts = integrate_chapter29_ast(ast, "HEADER-LATEX", "BODY-LATEX")
        self.assertEqual(counts, {"chapterHeader": 1, "familyFeatures": 1})
        self.assertEqual(ast["blocks"][0], {"t": "RawBlock", "c": ["latex", "HEADER-LATEX"]})
        self.assertEqual(
            ast["blocks"][1]["c"][1],
            [{"t": "RawBlock", "c": ["latex", "BODY-LATEX"]}],
        )


if __name__ == "__main__":
    unittest.main()
