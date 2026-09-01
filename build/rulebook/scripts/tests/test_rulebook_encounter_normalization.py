import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounters import (
    PRESENTATION_SCHEMA,
    normalize_encounter_entity,
    normalize_encounter_presentations,
    render_package,
)

SIDECAR = RULEBOOK_DIR / "source" / "metadata" / "structured-entities.json"
SOURCE_ROOT = RULEBOOK_DIR / "source"


def _entity(family: str, semantic_id: str, name: str, publication_data: dict) -> dict:
    return {
        "semanticId": semantic_id,
        "family": family,
        "name": name,
        "publicationData": publication_data,
    }


class EncounterPresentationNormalizationTests(unittest.TestCase):
    def test_sparse_and_rich_records_share_one_view_schema_without_fabrication(self):
        sparse = _entity(
            "adversaries",
            "entity:adversaries:sparse",
            "Sparse Legacy",
            {"tier": 1},
        )
        rich = _entity(
            "adversaries",
            "entity:adversaries:rich",
            "Current Rich",
            {
                "tier": 3,
                "classification": "solo",
                "difficulty": 16,
                "descriptionMarkdown": "Rich description.",
                "attack": {"name": "Pulse", "bonus": 4, "damageFormula": "2d8"},
                "motivesAndTactics": "Control the field.",
                "experiences": [{"name": "Hunter", "value": 3}],
                "fastPlay": {"goal": "Maintain pressure."},
                "actions": [{"name": "Counter", "actionType": "reaction", "rulesMarkdown": "React."}],
                "features": [{"name": "Shielded", "rulesMarkdown": "Hard to move.", "actions": []}],
            },
        )
        views = normalize_encounter_presentations([sparse, rich], "adversaries")
        self.assertEqual([view["schema"] for view in views], [PRESENTATION_SCHEMA, PRESENTATION_SCHEMA])
        self.assertEqual(views[0]["identity"], {"tier": 1})
        self.assertEqual(views[0]["sections"], {})
        self.assertEqual(views[1]["identity"]["classification"], "solo")
        self.assertEqual(views[1]["identity"]["statistics"]["difficulty"], 16)
        self.assertEqual(views[1]["sections"]["description"], "Rich description.")
        self.assertIn("features", views[1]["sections"])

    def test_environment_missing_art_and_optional_sections_are_not_invented(self):
        source = _entity(
            "environments",
            "entity:environments:sparse",
            "Sparse Zone",
            {"tier": 1},
        )
        view = normalize_encounter_entity(source)
        self.assertEqual(view["identity"], {"tier": 1})
        self.assertEqual(view["sections"], {})
        sidecar = {
            "encounterSemantics": {"schema": "cybermancy-step4-encounter-semantics-v1.0", "status": "PASS"},
            "entities": [source],
        }
        tex, report = render_package(
            sidecar,
            {"family": "environments", "selection": {"mode": "full-corpus"}},
            Path("/does/not/exist"),
        )
        self.assertEqual(report["renderedSemanticIds"], [source["semanticId"]])
        for token in (
            "UNCLASSIFIED",
            "No canonical description supplied.",
            "No canonical impulses supplied.",
            "NO PUBLICATION ART",
            "No embedded Features.",
        ):
            self.assertNotIn(token, tex)

    def test_normalization_is_deep_copy_and_never_mutates_step4_shape(self):
        source = _entity(
            "environments",
            "entity:environments:rich",
            "Rich Zone",
            {
                "classification": "social",
                "publicationArt": {"image": "assets/rich.png"},
                "actions": [{"name": "Shift", "rulesMarkdown": "Change the scene."}],
            },
        )
        original = copy.deepcopy(source)
        view = normalize_encounter_entity(source)
        view["identity"]["art"]["image"] = "changed.png"
        view["sections"]["actions"][0]["name"] = "Changed"
        self.assertEqual(source, original)

    @unittest.skipUnless(SIDECAR.is_file(), "Step 4 structured sidecar is not materialized in this checkout")
    def test_materialized_corpus_renders_each_adversary_and_environment_semantic_id_once(self):
        sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
        for family in ("adversaries", "environments"):
            source_ids = [
                str(entity.get("semanticId") or "")
                for entity in sidecar.get("entities") or []
                if isinstance(entity, dict) and entity.get("family") == family
            ]
            self.assertTrue(source_ids, family)
            self.assertEqual(len(source_ids), len(set(source_ids)), family)

            views = normalize_encounter_presentations(
                [
                    entity
                    for entity in sidecar.get("entities") or []
                    if isinstance(entity, dict) and entity.get("family") == family
                ],
                family,
            )
            self.assertEqual(len(views), len(source_ids), family)
            self.assertEqual({view["semanticId"] for view in views}, set(source_ids), family)
            self.assertTrue(all(view["schema"] == PRESENTATION_SCHEMA for view in views), family)

            config = {
                "family": family,
                "columns": 2 if family == "adversaries" else 1,
                "selection": {"mode": "full-corpus"},
            }
            tex, report = render_package(sidecar, config, SOURCE_ROOT)
            rendered = report["renderedSemanticIds"]
            self.assertEqual(report["entryCount"], len(source_ids), family)
            self.assertEqual(len(rendered), len(source_ids), family)
            self.assertEqual(len(rendered), len(set(rendered)), family)
            self.assertEqual(set(rendered), set(source_ids), family)
            self.assertEqual(report["presentationSchema"], PRESENTATION_SCHEMA, family)
            self.assertTrue(tex.strip(), family)


if __name__ == "__main__":
    unittest.main()
