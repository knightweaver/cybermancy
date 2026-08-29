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
from rulebook_step4_feature_equivalence import (
    FEATURE_EQUIVALENCE_SCHEMA,
    _postprocess_feature_equivalence,
    build_feature_equivalence_audit,
)


class TestFeatureEquivalenceAudit(unittest.TestCase):
    def _entities(self):
        return [
            {
                "semanticId": "entity:adversaries-features:EXACT1",
                "family": "adversaries-features",
                "name": "Slow",
                "sourcePath": "slow-a.json",
                "publicationData": {"rulesMarkdown": "When hit, mark 1 Stress.", "actions": []},
            },
            {
                "semanticId": "entity:adversaries-features:EXACT2",
                "family": "adversaries-features",
                "name": "Slow",
                "sourcePath": "slow-b.json",
                "publicationData": {"rulesMarkdown": "When hit, mark 1 Stress.", "actions": []},
            },
            {
                "semanticId": "entity:adversaries-features:TRIV1",
                "family": "adversaries-features",
                "name": "Detain",
                "sourcePath": "detain-a.json",
                "publicationData": {
                    "rulesMarkdown": "Make an attack. On a success, Restrain the target.",
                    "actions": [],
                },
            },
            {
                "semanticId": "entity:adversaries-features:TRIV2",
                "family": "adversaries-features",
                "name": "detain!",
                "sourcePath": "detain-b.json",
                "publicationData": {
                    "rulesMarkdown": "make an attack on a success restrain the target",
                    "actions": [
                        {
                            "sourceId": "ACTION123",
                            "name": "Attack",
                            "type": "effect",
                            "actionType": "action",
                            "rulesMarkdown": "Make an attack. On a success, Restrain the target.",
                        }
                    ],
                },
            },
            {
                "semanticId": "entity:adversaries-features:CAND1",
                "family": "adversaries-features",
                "name": "Strike",
                "sourcePath": "strike-a.json",
                "publicationData": {"rulesMarkdown": "Mark a Stress to attack two targets.", "actions": []},
            },
            {
                "semanticId": "entity:adversaries-features:CAND2",
                "family": "adversaries-features",
                "name": "Strike",
                "sourcePath": "strike-b.json",
                "publicationData": {"rulesMarkdown": "Mark 1 Stress to attack two targets.", "actions": []},
            },
            {
                "semanticId": "entity:adversaries-features:DISTINCT",
                "family": "adversaries-features",
                "name": "Strike",
                "sourcePath": "strike-c.json",
                "publicationData": {"rulesMarkdown": "Teleport anywhere within Far range.", "actions": []},
            },
        ]

    def test_audit_separates_exact_trivial_and_fuzzy_review(self):
        entities = self._entities()
        audit = build_feature_equivalence_audit(entities)
        summary = audit["summary"]
        self.assertEqual(audit["schema"], FEATURE_EQUIVALENCE_SCHEMA)
        self.assertEqual(summary["sourceFeatureCount"], 7)
        self.assertEqual(summary["exactEquivalentGroupCount"], 1)
        self.assertEqual(summary["trivialEquivalentGroupCount"], 1)
        self.assertEqual(summary["autoRedundantEntityCount"], 2)
        self.assertEqual(summary["provisionalRepresentativeCount"], 5)
        self.assertEqual(summary["reviewCandidatePairCount"], 1)
        self.assertEqual(summary["reviewStatus"], "REVIEW_REQUIRED")

        levels = {group["equivalenceLevel"] for group in audit["autoEquivalentGroups"]}
        self.assertEqual(levels, {"exact", "trivial"})
        candidate = audit["reviewCandidatePairs"][0]
        candidate_ids = {
            candidate["left"]["representativeSemanticId"],
            candidate["right"]["representativeSemanticId"],
        }
        self.assertEqual(
            candidate_ids,
            {
                "entity:adversaries-features:CAND1",
                "entity:adversaries-features:CAND2",
            },
        )

        # The audit is advisory only. It must not modify publication selection state.
        for entity in entities:
            self.assertNotIn("publicationRepresentative", entity.get("publicationData", {}))
            self.assertNotIn("standalonePublication", entity.get("publicationData", {}))

    def test_step4_postprocessor_writes_review_artifacts_without_warning_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outroot = root / "build" / "rulebook"
            metadata = outroot / "source" / "metadata"
            metadata.mkdir(parents=True)
            sidecar = {
                "schema": "cybermancy-step4-structured-entities-v1.3",
                "encounterSemantics": {
                    "schema": "cybermancy-step4-encounter-semantics-v1.0",
                    "status": "PASS",
                },
                "entities": self._entities(),
            }
            (metadata / "structured-entities.json").write_text(json.dumps(sidecar), encoding="utf-8")
            report = new_report()

            _postprocess_feature_equivalence(
                root,
                outroot,
                {},
                report,
                add_check=add_check,
            )

            audit_path = metadata / "adversary-feature-equivalence-audit.json"
            review_path = metadata / "adversary-feature-equivalence-review.md"
            self.assertTrue(audit_path.is_file())
            self.assertTrue(review_path.is_file())

            rebuilt = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            equivalence = rebuilt["encounterSemantics"]["adversaryFeatureEquivalence"]
            self.assertEqual(equivalence["status"], "REVIEW_REQUIRED")
            self.assertEqual(equivalence["sourceFeatureCount"], 7)
            self.assertEqual(equivalence["provisionalRepresentativeCount"], 5)

            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["ADVERSARY_FEATURE_EQUIVALENCE_AUDIT"]["status"], "PASS")
            self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
