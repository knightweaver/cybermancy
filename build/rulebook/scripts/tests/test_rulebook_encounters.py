import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounters import (
    PRESENTATION_SCHEMA,
    _actions,
    normalize_encounter_entity,
    render_package,
    validate_sidecar,
)


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
                        "attack": {
                            "name": "Arc Blade",
                            "bonus": 2,
                            "range": "Melee",
                            "damageFormula": "1d8+2",
                            "damageTypes": ["physical"],
                        },
                        "motivesAndTactics": "Press the weakest target.",
                        "experiences": [{"name": "Streetwise", "value": 2}],
                        "actions": [
                            {
                                "name": "Interrupt Cascade",
                                "actionType": "reaction",
                                "rulesMarkdown": "Action body remains unchanged.",
                            }
                        ],
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
                    "semanticId": "entity:adversaries:LEGACY",
                    "family": "adversaries",
                    "name": "Sparse Adversary",
                    "publicationData": {"tier": 1},
                },
                {
                    "semanticId": "entity:environments:ENV1",
                    "family": "environments",
                    "name": "Rich Environment",
                    "publicationData": {
                        "tier": 2,
                        "classification": "exploration",
                        "difficulty": 14,
                        "descriptionMarkdown": "A complete environment description.",
                        "impulses": "Escalate the pressure.",
                        "potentialAdversaries": ["Proof Adversary"],
                        "actions": [
                            {
                                "name": "Sudden Collapse",
                                "actionType": "reaction",
                                "rulesMarkdown": "The environment changes shape.",
                            }
                        ],
                        "features": [{"name": "Unstable", "rulesMarkdown": "Movement is dangerous.", "actions": []}],
                        "fastPlay": {
                            "prompts": [{"label": "Opening", "text": "Show the hazard.", "featureRefs": ["Unstable"]}],
                            "goal": "Force movement.",
                        },
                    },
                },
                {
                    "semanticId": "entity:environments:LEGACY",
                    "family": "environments",
                    "name": "Sparse Environment",
                    "publicationData": {"tier": 1},
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

    def _adversary_config(self, names):
        return {
            "family": "adversaries",
            "title": "Adversaries",
            "columns": 2,
            "selection": {"names": names},
            "presentationPolicy": {
                "sectionOrder": [
                    "identity",
                    "description",
                    "attack",
                    "motivesAndTactics",
                    "experiences",
                    "fastPlay",
                    "actions",
                    "features",
                ]
            },
        }

    def _environment_config(self, names):
        return {
            "family": "environments",
            "title": "Environments",
            "columns": 1,
            "selection": {"names": names},
            "presentationPolicy": {
                "sectionOrder": [
                    "identity",
                    "description",
                    "impulses",
                    "potentialAdversaries",
                    "fastPlay",
                    "actions",
                    "features",
                ]
            },
        }

    def test_requires_encounter_semantics(self):
        self.assertEqual(validate_sidecar(self._sidecar()), [])
        bad = self._sidecar()
        bad.pop("encounterSemantics")
        self.assertTrue(validate_sidecar(bad))

    def test_rich_adversary_uses_normalized_section_order_and_preserves_content(self):
        tex, report = render_package(
            self._sidecar(),
            self._adversary_config(["Proof Adversary"]),
            Path("/does/not/exist"),
        )
        self.assertEqual(report["entryCount"], 1)
        self.assertEqual(report["presentationSchema"], PRESENTATION_SCHEMA)
        self.assertEqual(report["renderedSemanticIds"], ["entity:adversaries:ADV1"])
        self.assertIn(r"\begin{multicols}{2}\raggedcolumns", tex)
        self.assertIn(r"\begin{minipage}[t]{\linewidth}", tex)
        self.assertNotIn("NO PUBLICATION ART", tex)
        self.assertNotIn("ART NOT STAGED", tex)
        self.assertIn("A compact proof adversary.", tex)
        self.assertIn("Arc Blade / +2 / Melee / 1d8+2 physical", tex)
        self.assertIn("Press the weakest target.", tex)
        self.assertIn("Streetwise +2", tex)
        self.assertIn("FAST PLAY", tex)
        self.assertIn("Interrupt Cascade", tex)
        self.assertIn("Proof Feature", tex)
        self.assertIn(r"\textbf{Passive.}", tex)
        self.assertIn(
            r"\fontsize{9.5}{10.5}\selectfont\bfseries\color{CMTealDark} REACTION",
            tex,
        )
        positions = [
            tex.index("A compact proof adversary."),
            tex.index("Attack:"),
            tex.index("Motives \\& Tactics:"),
            tex.index("Experiences:"),
            tex.index("FAST PLAY"),
            tex.index("ACTIONS"),
            tex.index("FEATURES"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_sparse_adversary_collapses_absent_optional_sections_without_invention(self):
        tex, report = render_package(
            self._sidecar(),
            self._adversary_config(["Sparse Adversary"]),
            Path("/does/not/exist"),
        )
        self.assertEqual(report["renderedSemanticIds"], ["entity:adversaries:LEGACY"])
        self.assertIn("Sparse Adversary", tex)
        self.assertIn("TIER 1", tex)
        for invented in (
            "UNCLASSIFIED",
            "No canonical description supplied.",
            "NO PUBLICATION ART",
            "Attack:",
            "Motives \\& Tactics:",
            "Experiences:",
            "FAST PLAY",
            "ACTIONS",
            "FEATURES",
            "No embedded Features.",
        ):
            self.assertNotIn(invented, tex)

    def test_normalized_view_preserves_present_values_and_does_not_mutate_source(self):
        sidecar = self._sidecar()
        entity = next(row for row in sidecar["entities"] if row["name"] == "Proof Adversary")
        original = copy.deepcopy(entity)
        view = normalize_encounter_entity(entity)
        self.assertEqual(view["schema"], PRESENTATION_SCHEMA)
        self.assertEqual(view["semanticId"], entity["semanticId"])
        self.assertEqual(view["identity"]["classification"], "standard")
        self.assertEqual(view["identity"]["statistics"]["difficulty"], 13)
        self.assertEqual(view["sections"]["description"], "A compact proof adversary.")
        self.assertEqual(view["sections"]["attack"]["name"], "Arc Blade")
        view["sections"]["attack"]["name"] = "Changed only in presentation view"
        self.assertEqual(entity, original)

    def test_sparse_environment_and_rich_environment_share_family_grammar(self):
        rich_tex, rich_report = render_package(
            self._sidecar(),
            self._environment_config(["Rich Environment"]),
            Path("/does/not/exist"),
        )
        sparse_tex, sparse_report = render_package(
            self._sidecar(),
            self._environment_config(["Sparse Environment"]),
            Path("/does/not/exist"),
        )
        self.assertEqual(rich_report["presentationSchema"], PRESENTATION_SCHEMA)
        self.assertEqual(sparse_report["presentationSchema"], PRESENTATION_SCHEMA)
        self.assertIn("A complete environment description.", rich_tex)
        self.assertIn("Impulses:", rich_tex)
        self.assertIn("Potential Adversaries:", rich_tex)
        self.assertIn("FAST PLAY", rich_tex)
        self.assertIn("ACTIONS", rich_tex)
        self.assertIn("FEATURES", rich_tex)
        self.assertIn(
            r"\fontsize{9.5}{10.5}\selectfont\bfseries\color{CMTealDark} REACTION",
            rich_tex,
        )
        self.assertIn("Sparse Environment", sparse_tex)
        self.assertIn("TIER 1", sparse_tex)
        for invented in (
            "UNCLASSIFIED",
            "No canonical description supplied.",
            "No canonical impulses supplied.",
            "NO PUBLICATION ART",
            "Impulses:",
            "Potential Adversaries:",
            "FAST PLAY",
            "ACTIONS",
            "FEATURES",
            "No embedded Features.",
        ):
            self.assertNotIn(invented, sparse_tex)

    def test_action_type_uses_shared_blue_role_and_preserves_long_label_content(self):
        tex = _actions(
            [
                {
                    "name": "Interrupt Cascade",
                    "actionType": "triggered reaction with extended label",
                    "rulesMarkdown": "Action body remains unchanged.",
                }
            ]
        )
        self.assertIn("Interrupt Cascade", tex)
        self.assertIn("Action body remains unchanged.", tex)
        self.assertIn(
            r"\fontsize{9.5}{10.5}\selectfont\bfseries\color{CMTealDark} TRIGGERED REACTION WITH EXTENDED LABEL",
            tex,
        )
        self.assertNotIn(r"\scriptsize\bfseries\color{CMViolet}", tex)

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
            "Sparse Adversary",
            "Zulu Adversary",
        ]
        expected_ids = [
            "entity:adversaries:A",
            "entity:adversaries:B",
            "entity:adversaries:ADV1",
            "entity:adversaries:LEGACY",
            "entity:adversaries:Z",
        ]
        self.assertEqual(report["selectedNames"], expected_names)
        self.assertEqual(report["selectedSemanticIds"], expected_ids)
        self.assertEqual(report["renderedSemanticIds"], expected_ids)
        self.assertEqual(len(report["selectedSemanticIds"]), len(set(report["selectedSemanticIds"])))
        positions = [tex.index(name.strip()) for name in expected_names]
        self.assertEqual(positions, sorted(positions))

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
        self.assertEqual(report["renderedSemanticIds"], config["selection"]["semanticIds"])
        self.assertIsNone(report["presentationSchema"])
        self.assertLess(tex.index("Second Slow variant"), tex.index("First Slow variant"))
        self.assertNotIn("entity:adversaries-features", tex)


if __name__ == "__main__":
    unittest.main()
