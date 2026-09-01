import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounters import render_package, validate_sidecar


class TestEncounterLayout(unittest.TestCase):
    def _sidecar(self):
        return {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "encounterSemantics": {
                "schema": "cybermancy-step4-encounter-semantics-v1.0",
                "status": "PASS",
            },
            "entities": [
                {
                    "semanticId": "entity:adversaries:ADV1",
                    "family": "adversaries",
                    "name": "Proof Adversary",
                    "publicationData": {
                        "tier": 1,
                        "classification": "standard",
                        "difficulty": 13,
                        "damageThresholds": {"major": 5, "severe": 8},
                        "hitPoints": 5,
                        "stress": 2,
                        "descriptionMarkdown": "A compact proof adversary.",
                        "features": [
                            {"name": "Proof Feature", "rulesMarkdown": "**Passive.** Preserve structure.", "actions": []}
                        ],
                        "fastPlay": {
                            "prompts": [
                                {"label": "Opening", "text": "Establish pressure.", "featureRefs": ["Proof Feature"]},
                                {"label": "Default", "text": "Use the feature.", "featureRefs": []},
                            ],
                            "goal": "Keep the scene moving.",
                        },
                    },
                },
                {
                    "semanticId": "entity:environments:ENV1",
                    "family": "environments",
                    "name": "Sparse Environment",
                    "publicationData": {"tier": 1, "classification": None, "descriptionMarkdown": "", "impulses": "", "features": []},
                },
                {
                    "semanticId": "entity:adversaries-features:AAA",
                    "family": "adversaries-features",
                    "name": "Slow",
                    "publicationData": {"rulesMarkdown": "First Slow variant."},
                },
                {
                    "semanticId": "entity:adversaries-features:BBB",
                    "family": "adversaries-features",
                    "name": "Slow",
                    "publicationData": {"rulesMarkdown": "Second Slow variant."},
                },
            ],
        }

    def test_requires_encounter_semantics(self):
        self.assertEqual(validate_sidecar(self._sidecar()), [])
        bad = self._sidecar()
        bad.pop("encounterSemantics")
        self.assertTrue(validate_sidecar(bad))

    def test_adversary_v11_two_column_header_and_fast_play_render(self):
        sidecar = self._sidecar()
        tex, report = render_package(
            sidecar,
            {
                "family": "adversaries",
                "title": "Adversaries",
                "columns": 2,
                "selection": {"names": ["Proof Adversary"]},
            },
            Path("/does/not/exist"),
        )
        self.assertEqual(report["entryCount"], 1)
        self.assertIn("FAST PLAY", tex)
        self.assertIn("Proof Feature", tex)
        self.assertIn(r"\textbf{Passive.}", tex)
        self.assertIn(r"\begin{multicols}{2}\raggedcolumns", tex)
        self.assertIn(r"\setlength{\columnsep}{0.22in}", tex)
        self.assertIn(r"\begin{minipage}[t]{0.20\linewidth}", tex)
        self.assertIn(r"\begin{minipage}[t]{0.76\linewidth}", tex)
        self.assertNotIn(r"0.17\textwidth", tex)
        self.assertNotIn(r"0.80\textwidth", tex)
        self.assertIn("height=18mm", tex)
        self.assertIn(r"\Needspace{10\baselineskip}", tex)
        self.assertLess(tex.index("NO PUBLICATION ART"), tex.index(r"STANDARD \textbullet\ TIER 1"))
        self.assertIn(r"STANDARD \textbullet\ TIER 1}\\[1.5pt]", tex)
        self.assertNotIn(r"\clearpage", tex)

    def test_unselected_adversary_render_order_is_normalized_name(self):
        sidecar = self._sidecar()
        sidecar["entities"].extend(
            [
                {
                    "semanticId": "entity:adversaries:Z",
                    "family": "adversaries",
                    "name": "Zulu Adversary",
                    "publicationData": {"tier": 1, "classification": "standard"},
                },
                {
                    "semanticId": "entity:adversaries:B",
                    "family": "adversaries",
                    "name": "beta adversary",
                    "publicationData": {"tier": 2, "classification": "support"},
                },
                {
                    "semanticId": "entity:adversaries:A",
                    "family": "adversaries",
                    "name": "  Alpha Adversary  ",
                    "publicationData": {"tier": 3, "classification": "bruiser"},
                },
            ]
        )
        tex, report = render_package(
            sidecar,
            {
                "family": "adversaries",
                "title": "Adversaries",
                "columns": 2,
                "selection": {"mode": "full-corpus"},
            },
            Path("/does/not/exist"),
        )
        expected_names = [
            "  Alpha Adversary  ",
            "beta adversary",
            "Proof Adversary",
            "Zulu Adversary",
        ]
        expected_ids = [
            "entity:adversaries:A",
            "entity:adversaries:B",
            "entity:adversaries:ADV1",
            "entity:adversaries:Z",
        ]
        self.assertEqual(report["selectedNames"], expected_names)
        self.assertEqual(report["selectedSemanticIds"], expected_ids)
        self.assertEqual(len(report["selectedSemanticIds"]), len(set(report["selectedSemanticIds"])))
        positions = [tex.index(name.strip()) for name in expected_names]
        self.assertEqual(positions, sorted(positions))

    def test_environment_grammar_remains_one_column_and_unchanged(self):
        sidecar = self._sidecar()
        env_tex, env_report = render_package(
            sidecar,
            {"family": "environments", "title": "Environments", "columns": 1, "selection": {"names": ["Sparse Environment"]}},
            Path("/does/not/exist"),
        )
        self.assertEqual(env_report["entryCount"], 1)
        self.assertIn("No canonical description supplied.", env_tex)
        self.assertIn("No canonical impulses supplied.", env_tex)
        self.assertIn(r"\begin{minipage}[t]{0.17\textwidth}", env_tex)
        self.assertIn(r"\begin{minipage}[t]{0.80\textwidth}", env_tex)
        self.assertNotIn(r"\begin{multicols}{2}\raggedcolumns", env_tex)
        self.assertLess(env_tex.index("NO PUBLICATION ART"), env_tex.index(r"UNCLASSIFIED \textbullet\ TIER 1"))
        self.assertIn(r"UNCLASSIFIED \textbullet\ TIER 1}\\[2.5pt]", env_tex)

    def test_feature_semantic_id_selection_preserves_duplicate_variants(self):
        sidecar = self._sidecar()
        config = {
            "family": "adversaries-features",
            "title": "Feature Reference",
            "selection": {"semanticIds": ["entity:adversaries-features:BBB", "entity:adversaries-features:AAA"]},
        }
        tex, report = render_package(sidecar, config, Path("."))
        self.assertEqual(report["selectedSemanticIds"], config["selection"]["semanticIds"])
        self.assertEqual(report["selectedNames"], ["Slow", "Slow"])
        self.assertLess(tex.index("Second Slow variant"), tex.index("First Slow variant"))
        self.assertNotIn("entity:adversaries-features", tex)


if __name__ == "__main__":
    unittest.main()
