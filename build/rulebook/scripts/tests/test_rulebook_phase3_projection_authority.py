import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.projection_authority import (
    projection_authority_descriptor,
    reconcile_adversary_feature_projection_authority,
    reconcile_ice_projection_authority,
    reconcile_structured_projection_authority,
)
from rulebook_layout.structured_count_authority import (
    count_authority_descriptor,
    reconcile_structured_count_authority,
)


class TestPhase3ProjectionAuthority(unittest.TestCase):
    def _publication(self):
        return {
            "publicationInputs": {
                "structuredFamilies": [
                    {
                        "generatorFamily": "features",
                        "authority": "CANONICAL-CANDIDATE",
                        "disposition": "INCLUDE",
                        "decisionStatus": "DECIDED",
                        "audience": "player",
                        "entityCount": 3,
                    },
                    {
                        "generatorFamily": "adversaries-features",
                        "authority": "CANONICAL-CANDIDATE",
                        "disposition": "INCLUDE",
                        "decisionStatus": "DECIDED",
                        "audience": "gm",
                        "entityCount": 3,
                    },
                ]
            }
        }

    def _sidecar(self):
        return {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "iceSemantics": {
                "schema": "cybermancy-step4-ice-semantics-v1.0",
                "status": "PASS",
                "featureCategory": "ice",
                "iceCount": 2,
                "sentryCount": 1,
                "wallCount": 1,
                "semanticIds": ["entity:features:I1", "entity:features:I2"],
            },
            "encounterSemantics": {
                "status": "PASS",
                "adversaryFeatureEquivalence": {
                    "publicationStatus": "APPLIED",
                    "canonicalSourceFeatureCount": 3,
                    "publicationRepresentativeCount": 2,
                    "excludedRedundantCount": 1,
                    "approvedGroupCount": 1,
                },
            },
            "entities": [
                {
                    "semanticId": "entity:features:I1",
                    "family": "features",
                    "audience": "gm",
                    "name": "Sentry One",
                    "publicationData": {
                        "featureCategory": "ice",
                        "iceType": "sentry",
                        "standalonePublication": True,
                    },
                },
                {
                    "semanticId": "entity:features:I2",
                    "family": "features",
                    "audience": "gm",
                    "name": "Wall One",
                    "publicationData": {
                        "featureCategory": "ice",
                        "iceType": "wall",
                        "standalonePublication": True,
                    },
                },
                {
                    "semanticId": "entity:features:P1",
                    "family": "features",
                    "audience": "player",
                    "name": "Class Feature",
                    "publicationData": {},
                },
                {
                    "semanticId": "entity:adversaries-features:A1",
                    "family": "adversaries-features",
                    "audience": "gm",
                    "name": "Grouped Representative",
                    "publicationData": {
                        "publicationEquivalence": {
                            "isRepresentative": True,
                            "representativeSemanticId": "entity:adversaries-features:A1",
                        }
                    },
                },
                {
                    "semanticId": "entity:adversaries-features:A2",
                    "family": "adversaries-features",
                    "audience": "gm",
                    "name": "Grouped Redundant",
                    "publicationData": {
                        "publicationEquivalence": {
                            "isRepresentative": False,
                            "representativeSemanticId": "entity:adversaries-features:A1",
                        }
                    },
                },
                {
                    "semanticId": "entity:adversaries-features:B1",
                    "family": "adversaries-features",
                    "audience": "gm",
                    "name": "Ungrouped Representative",
                    "publicationData": {},
                },
            ],
        }

    def _selection(self):
        return {
            "schema": "cybermancy-step4-adversary-feature-publication-selection-v1.0",
            "status": "APPLIED",
            "canonicalSourceFeatureCount": 3,
            "publicationRepresentativeCount": 2,
            "excludedRedundantCount": 1,
            "approvedGroupCount": 1,
            "representativeSemanticIds": [
                "entity:adversaries-features:A1",
                "entity:adversaries-features:B1",
            ],
            "excludedSemanticIds": ["entity:adversaries-features:A2"],
            "groups": [{"groupId": "group-a"}],
        }

    def test_phase3_source_and_projection_descriptors_are_stable(self):
        self.assertEqual(
            count_authority_descriptor("features")["normalizedActual"],
            "step4-structured-sidecar:entities[family=features]",
        )
        self.assertEqual(
            count_authority_descriptor("adversaries-features")["normalizedActual"],
            "step4-structured-sidecar:entities[family=adversaries-features]",
        )
        self.assertEqual(
            projection_authority_descriptor("ice")["normalizedSelection"],
            "step4-structured-sidecar:iceSemantics.semanticIds",
        )
        self.assertEqual(
            projection_authority_descriptor("adversaryFeatures")["normalizedSelection"],
            "step4-adversary-feature-publication-selection:representativeSemanticIds",
        )

    def test_phase3_source_families_reconcile_to_manifest_authority(self):
        report = reconcile_structured_count_authority(
            self._publication(),
            self._sidecar(),
            families=("features", "adversaries-features"),
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["families"]["features"]["actualStep4Count"], 3)
        self.assertEqual(report["families"]["adversaries-features"]["actualStep4Count"], 3)

    def test_phase3_projections_reconcile_without_fixed_projection_counts(self):
        report = reconcile_structured_projection_authority(
            self._publication(),
            self._sidecar(),
            self._selection(),
            descriptors={
                "ice": projection_authority_descriptor("ice"),
                "adversaryFeatures": projection_authority_descriptor("adversaryFeatures"),
            },
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["projections"]["ice"]["sourceCount"], 3)
        self.assertEqual(report["projections"]["ice"]["projectedCount"], 2)
        self.assertEqual(report["projections"]["adversaryFeatures"]["sourceCount"], 3)
        self.assertEqual(report["projections"]["adversaryFeatures"]["projectedCount"], 2)

    def test_future_ice_growth_succeeds_when_manifest_and_step4_source_advance_together(self):
        publication = self._publication()
        publication["publicationInputs"]["structuredFamilies"][0]["entityCount"] = 4
        sidecar = self._sidecar()
        sidecar["entities"].append(
            {
                "semanticId": "entity:features:I3",
                "family": "features",
                "audience": "gm",
                "name": "Sentry Two",
                "publicationData": {
                    "featureCategory": "ice",
                    "iceType": "sentry",
                    "standalonePublication": True,
                },
            }
        )
        sidecar["iceSemantics"].update(
            {
                "iceCount": 3,
                "sentryCount": 2,
                "wallCount": 1,
                "semanticIds": [
                    "entity:features:I1",
                    "entity:features:I2",
                    "entity:features:I3",
                ],
            }
        )
        report = reconcile_ice_projection_authority(publication, sidecar)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["sourceCount"], 4)
        self.assertEqual(report["projectedCount"], 3)
        self.assertEqual(report["groupCounts"], {"sentry": 2, "wall": 1})

    def test_manifest_only_source_growth_fails_closed(self):
        publication = self._publication()
        publication["publicationInputs"]["structuredFamilies"][0]["entityCount"] = 4
        report = reconcile_ice_projection_authority(publication, self._sidecar())
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["errors"])

    def test_ice_projection_rejects_unknown_or_misclassified_selected_ids(self):
        sidecar = self._sidecar()
        sidecar["iceSemantics"]["semanticIds"] = [
            "entity:features:I1",
            "entity:features:P1",
        ]
        report = reconcile_ice_projection_authority(self._publication(), sidecar)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("do not exactly match" in error for error in report["errors"]))

    def test_ice_projection_rejects_declared_type_count_drift(self):
        sidecar = self._sidecar()
        sidecar["iceSemantics"]["sentryCount"] = 2
        sidecar["iceSemantics"]["wallCount"] = 0
        report = reconcile_ice_projection_authority(self._publication(), sidecar)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("type counts" in error for error in report["errors"]))

    def test_future_adversary_feature_growth_defaults_to_new_representative(self):
        publication = self._publication()
        publication["publicationInputs"]["structuredFamilies"][1]["entityCount"] = 4
        sidecar = self._sidecar()
        sidecar["entities"].append(
            {
                "semanticId": "entity:adversaries-features:C1",
                "family": "adversaries-features",
                "audience": "gm",
                "name": "New Feature",
                "publicationData": {},
            }
        )
        sidecar["encounterSemantics"]["adversaryFeatureEquivalence"].update(
            {
                "canonicalSourceFeatureCount": 4,
                "publicationRepresentativeCount": 3,
                "excludedRedundantCount": 1,
            }
        )
        selection = self._selection()
        selection.update(
            {
                "canonicalSourceFeatureCount": 4,
                "publicationRepresentativeCount": 3,
                "representativeSemanticIds": [
                    "entity:adversaries-features:A1",
                    "entity:adversaries-features:B1",
                    "entity:adversaries-features:C1",
                ],
            }
        )
        report = reconcile_adversary_feature_projection_authority(
            publication, sidecar, selection
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["sourceCount"], 4)
        self.assertEqual(report["projectedCount"], 3)

    def test_adversary_feature_selection_must_match_applied_sidecar_metadata(self):
        selection = self._selection()
        selection["representativeSemanticIds"] = ["entity:adversaries-features:B1"]
        selection["publicationRepresentativeCount"] = 1
        report = reconcile_adversary_feature_projection_authority(
            self._publication(), self._sidecar(), selection
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("representatives do not match" in error for error in report["errors"]))

    def test_malformed_projection_descriptor_fails_closed(self):
        report = reconcile_ice_projection_authority(
            self._publication(),
            self._sidecar(),
            descriptor={"reconciliation": "approximate"},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Malformed projection-authority" in error for error in report["errors"]))

    def test_production_configs_contain_no_operative_phase3_fixed_counts(self):
        ice = json.loads(
            (REPO_ROOT / "build/rulebook/layout/ice/ice-reference-package-v1.json").read_text(
                encoding="utf-8"
            )
        )
        feature = json.loads(
            (
                REPO_ROOT
                / "build/rulebook/layout/encounters/adversary-feature-reference-v1.json"
            ).read_text(encoding="utf-8")
        )
        renderer = json.loads(
            (REPO_ROOT / "build/rulebook/production/production-renderer-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("expectedIceTotal", ice["publicationPolicy"])
        self.assertNotIn("expectedIceCounts", ice["publicationPolicy"])
        self.assertIs(ice["lifecycle"]["acceptanceCorpus"]["operative"], False)
        self.assertNotIn("expectedEntryCount", feature["publicationPolicy"])
        self.assertNotIn("canonicalSourceEntryCount", feature["publicationPolicy"])
        self.assertIs(feature["lifecycle"]["historicalAcceptance"]["operative"], False)
        self.assertEqual(
            renderer["structuredExpectations"],
            {"ancestories": 18, "communities": 9, "characterOriginArtwork": 27},
        )
        self.assertIs(renderer["historicalProjectionAcceptance"]["ice"]["operative"], False)
        self.assertIs(
            renderer["historicalProjectionAcceptance"]["adversaryFeatures"]["operative"],
            False,
        )


if __name__ == "__main__":
    unittest.main()
