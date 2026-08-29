import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_normalize.validate import add_check, new_report
from rulebook_step4_feature_publication_equivalence import (
    DECISIONS_REPO_PATH,
    DECISIONS_SCHEMA,
    PUBLICATION_SELECTION_SCHEMA,
    _postprocess_feature_publication_equivalence,
    apply_feature_publication_equivalence,
)


class TestFeaturePublicationEquivalence(unittest.TestCase):
    def _sidecar(self):
        entities = []
        for source_id, name, rules in (
            ("A1", "Momentum", "When the Captain attacks, gain a Fear."),
            ("A2", "Momentum", "When the Demon attacks, gain a Fear."),
            ("B1", "Death Quake", "Same exact rules."),
            ("B2", "Death Quake", "Same exact rules."),
            ("C1", "Group Attack", "Spend Fear; deal 4 damage each."),
        ):
            entities.append(
                {
                    "semanticId": f"entity:adversaries-features:{source_id}",
                    "sourceId": source_id,
                    "family": "adversaries-features",
                    "name": name,
                    "publicationData": {
                        "rulesMarkdown": rules,
                        "actions": [],
                    },
                }
            )
        return {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "encounterSemantics": {
                "schema": "cybermancy-step4-encounter-semantics-v1.0",
                "status": "PASS",
                "adversaryFeatureEquivalence": {
                    "status": "REVIEW_REQUIRED",
                },
            },
            "entities": entities,
        }

    def _decisions(self):
        return {
            "schema": DECISIONS_SCHEMA,
            "status": "approved",
            "sourceFeatureCount": 5,
            "expectedPublicationRepresentativeCount": 3,
            "groups": [
                {
                    "groupId": "momentum-group",
                    "basis": "feature-library-family-parameters",
                    "familyId": "momentum",
                    "representativeSourceId": "A1",
                    "memberSourceIds": ["A1", "A2"],
                    "publicationEntry": {
                        "name": "Momentum",
                        "rulesMarkdown": "When this adversary attacks, gain a Fear.",
                        "actions": [],
                    },
                },
                {
                    "groupId": "death-quake-group",
                    "basis": "exact-publication-semantics",
                    "familyId": "death-quake",
                    "representativeSourceId": "B1",
                    "memberSourceIds": ["B1", "B2"],
                },
            ],
        }

    def test_frozen_decision_file_contract_is_419_to_344(self):
        decisions = json.loads((SCRIPT_DIR / "data" / "adversary-feature-equivalence-decisions-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(decisions["schema"], DECISIONS_SCHEMA)
        self.assertEqual(decisions["status"], "approved")
        self.assertEqual(decisions["sourceFeatureCount"], 419)
        self.assertEqual(decisions["expectedPublicationRepresentativeCount"], 344)
        self.assertEqual(len(decisions["groups"]), 29)

        seen = set()
        redundant = 0
        for group in decisions["groups"]:
            members = group["memberSourceIds"]
            self.assertGreaterEqual(len(members), 2)
            self.assertIn(group["representativeSourceId"], members)
            self.assertFalse(seen.intersection(members))
            seen.update(members)
            redundant += len(members) - 1
        self.assertEqual(redundant, 75)
        self.assertEqual(decisions["sourceFeatureCount"] - redundant, 344)

    def test_applies_reviewed_groups_without_deleting_canonical_entities(self):
        sidecar = self._sidecar()
        selection, errors = apply_feature_publication_equivalence(sidecar, self._decisions())
        self.assertEqual(errors, [])
        self.assertEqual(selection["schema"], PUBLICATION_SELECTION_SCHEMA)
        self.assertEqual(selection["canonicalSourceFeatureCount"], 5)
        self.assertEqual(selection["publicationRepresentativeCount"], 3)
        self.assertEqual(selection["excludedRedundantCount"], 2)
        self.assertEqual(len(sidecar["entities"]), 5)

        by_source = {entity["sourceId"]: entity for entity in sidecar["entities"]}
        self.assertTrue(by_source["A1"]["publicationData"]["publicationEquivalence"]["isRepresentative"])
        self.assertFalse(by_source["A2"]["publicationData"]["publicationEquivalence"]["isRepresentative"])
        self.assertEqual(
            by_source["A1"]["publicationData"]["referenceEntry"]["rulesMarkdown"],
            "When this adversary attacks, gain a Fear.",
        )
        self.assertTrue(by_source["B1"]["publicationData"]["publicationEquivalence"]["isRepresentative"])
        self.assertFalse(by_source["B2"]["publicationData"]["publicationEquivalence"]["isRepresentative"])
        self.assertNotIn("referenceEntry", by_source["B1"]["publicationData"])
        self.assertNotIn("publicationEquivalence", by_source["C1"]["publicationData"])

    def test_overlapping_groups_fail_closed(self):
        decisions = self._decisions()
        decisions["groups"].append(
            {
                "groupId": "bad-overlap",
                "basis": "exact-publication-semantics",
                "familyId": "momentum",
                "representativeSourceId": "A2",
                "memberSourceIds": ["A2", "C1"],
            }
        )
        _, errors = apply_feature_publication_equivalence(self._sidecar(), decisions)
        self.assertIn(
            "ADVERSARY_FEATURE_EQUIVALENCE_GROUP_OVERLAP",
            {error["code"] for error in errors},
        )

    def test_step4_postprocessor_marks_applied_and_writes_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outroot = root / "build" / "rulebook"
            metadata = outroot / "source" / "metadata"
            metadata.mkdir(parents=True)
            (metadata / "structured-entities.json").write_text(
                json.dumps(self._sidecar()),
                encoding="utf-8",
            )
            decisions_path = root / DECISIONS_REPO_PATH
            decisions_path.parent.mkdir(parents=True, exist_ok=True)
            decisions_path.write_text(json.dumps(self._decisions()), encoding="utf-8")
            report = new_report()

            _postprocess_feature_publication_equivalence(
                root,
                outroot,
                {},
                report,
                add_check=add_check,
            )

            rebuilt = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            status = rebuilt["encounterSemantics"]["adversaryFeatureEquivalence"]
            self.assertEqual(status["publicationStatus"], "APPLIED")
            self.assertEqual(status["canonicalSourceFeatureCount"], 5)
            self.assertEqual(status["publicationRepresentativeCount"], 3)
            selection = json.loads(
                (metadata / "adversary-feature-publication-selection.json").read_text(encoding="utf-8")
            )
            self.assertEqual(selection["publicationRepresentativeCount"], 3)
            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["ADVERSARY_FEATURE_PUBLICATION_EQUIVALENCE"]["status"], "PASS")
            self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
