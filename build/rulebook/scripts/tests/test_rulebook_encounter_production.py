import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-encounters.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_encounters_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestEncounterProductionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = _load_builder()

    def _sidecar(self):
        return {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "encounterSemantics": {
                "schema": "cybermancy-step4-encounter-semantics-v1.0",
                "status": "WARNING",
                "adversaryFeatureEquivalence": {
                    "publicationStatus": "APPLIED",
                    "publicationRepresentativeCount": 2,
                },
            },
            "entities": [
                {
                    "semanticId": "entity:adversaries:Z",
                    "family": "adversaries",
                    "name": "Zulu",
                    "publicationData": {"tier": 1, "classification": "standard"},
                },
                {
                    "semanticId": "entity:adversaries:B",
                    "family": "adversaries",
                    "name": "Beta",
                    "publicationData": {"tier": 2, "classification": "support"},
                },
                {
                    "semanticId": "entity:adversaries:A",
                    "family": "adversaries",
                    "name": "Alpha",
                    "publicationData": {"tier": 3, "classification": "bruiser"},
                },
                {
                    "semanticId": "entity:environments:Z",
                    "family": "environments",
                    "name": "Zulu Zone",
                    "publicationData": {"tier": 1, "classification": "standard"},
                },
                {
                    "semanticId": "entity:environments:B",
                    "family": "environments",
                    "name": "Beta Zone",
                    "publicationData": {"tier": 1, "classification": "support"},
                },
                {
                    "semanticId": "entity:environments:A",
                    "family": "environments",
                    "name": "Alpha Zone",
                    "publicationData": {"tier": 2, "classification": "bruiser"},
                },
                {
                    "semanticId": "entity:adversaries-features:S2",
                    "family": "adversaries-features",
                    "name": "Slow",
                    "publicationData": {
                        "rulesMarkdown": "Second.",
                        "publicationEquivalence": {
                            "isRepresentative": False,
                            "representativeSemanticId": "entity:adversaries-features:S1",
                        },
                    },
                },
                {
                    "semanticId": "entity:adversaries-features:F1",
                    "family": "adversaries-features",
                    "name": "Fast",
                    "publicationData": {"rulesMarkdown": "Fast."},
                },
                {
                    "semanticId": "entity:adversaries-features:S1",
                    "family": "adversaries-features",
                    "name": "Slow (Ooze)",
                    "publicationData": {
                        "rulesMarkdown": "First.",
                        "actions": [{"name": "Runtime Mirror", "rulesMarkdown": "First."}],
                        "publicationEquivalence": {
                            "isRepresentative": True,
                            "representativeSemanticId": "entity:adversaries-features:S1",
                        },
                        "referenceEntry": {
                            "name": "Slow",
                            "rulesMarkdown": "When you spotlight this adversary, resolve Slow.",
                            "actions": [],
                        },
                    },
                },
            ],
        }

    def _config(self, family, expected, ordering, *, version="v1.1"):
        return {
            "family": family,
            "lifecycle": {"version": version, "status": "frozen"},
            "selection": {"mode": "full-corpus"},
            "publicationPolicy": {
                "requireFullCorpusSelection": True,
                "expectedEntryCount": expected,
                "ordering": ordering,
            },
        }

    def test_package_versions_are_explicit_per_family(self):
        self.assertEqual(self.builder.EXPECTED_PACKAGE_VERSIONS["adversary"], "v1.1")
        self.assertEqual(self.builder.EXPECTED_PACKAGE_VERSIONS["environment"], "v1.0")
        self.assertEqual(self.builder.EXPECTED_PACKAGE_VERSIONS["feature-reference"], "v1.0")

    def test_package_orderings_are_explicit_per_family(self):
        self.assertEqual(
            self.builder.EXPECTED_ORDERINGS["adversary"],
            ["normalized-name", "semanticId"],
        )
        self.assertEqual(
            self.builder.EXPECTED_ORDERINGS["environment"],
            ["tier", "classification", "name", "semanticId"],
        )

    def test_adversary_full_corpus_order_is_normalized_name(self):
        ids, errors = self.builder._ordered_full_corpus(self._sidecar(), "adversaries")
        self.assertEqual(errors, [])
        self.assertEqual(
            ids,
            [
                "entity:adversaries:A",
                "entity:adversaries:B",
                "entity:adversaries:Z",
            ],
        )

    def test_adversary_duplicate_names_use_semantic_id_tie_breaker(self):
        sidecar = self._sidecar()
        sidecar["entities"].extend(
            [
                {
                    "semanticId": "entity:adversaries:A0",
                    "family": "adversaries",
                    "name": "  ALPHA  ",
                    "publicationData": {"tier": 4, "classification": "solo"},
                },
                {
                    "semanticId": "entity:adversaries:A2",
                    "family": "adversaries",
                    "name": "Alpha",
                    "publicationData": {"tier": 1, "classification": "minion"},
                },
            ]
        )
        ids, errors = self.builder._ordered_full_corpus(sidecar, "adversaries")
        self.assertEqual(errors, [])
        self.assertEqual(
            ids[:3],
            [
                "entity:adversaries:A",
                "entity:adversaries:A0",
                "entity:adversaries:A2",
            ],
        )

    def test_environment_full_corpus_order_remains_tier_classification_name(self):
        ids, errors = self.builder._ordered_full_corpus(self._sidecar(), "environments")
        self.assertEqual(errors, [])
        self.assertEqual(
            ids,
            [
                "entity:environments:Z",
                "entity:environments:B",
                "entity:environments:A",
            ],
        )

    def test_feature_full_corpus_uses_step4_publication_representatives(self):
        ids, errors = self.builder._ordered_full_corpus(self._sidecar(), "adversaries-features")
        self.assertEqual(errors, [])
        self.assertEqual(
            ids,
            [
                "entity:adversaries-features:F1",
                "entity:adversaries-features:S1",
            ],
        )

    def test_feature_reference_render_view_uses_reader_neutral_override(self):
        sidecar = self._sidecar()
        rendered = self.builder._prepare_feature_reference_sidecar(sidecar)
        source = next(entity for entity in sidecar["entities"] if entity.get("semanticId", "").endswith(":S1"))
        view = next(entity for entity in rendered["entities"] if entity.get("semanticId", "").endswith(":S1"))
        self.assertEqual(source["name"], "Slow (Ooze)")
        self.assertEqual(source["publicationData"]["rulesMarkdown"], "First.")
        self.assertEqual(view["name"], "Slow")
        self.assertEqual(view["publicationData"]["rulesMarkdown"], "When you spotlight this adversary, resolve Slow.")
        self.assertEqual(view["publicationData"]["actions"], [])

    def test_frozen_adversary_v11_contract_accepts_warning_step4_status(self):
        runtime, contract, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config("adversaries", 3, ["normalized-name", "semanticId"]),
            "adversary",
        )
        self.assertEqual(errors, [])
        self.assertEqual(contract["version"], "v1.1")
        self.assertEqual(contract["actualEntryCount"], 3)
        self.assertEqual(contract["expectedEntryCount"], 3)
        self.assertEqual(runtime["selection"]["mode"], "full-corpus")
        self.assertEqual(len(runtime["selection"]["semanticIds"]), 3)

    def test_adversary_contract_rejects_previous_tier_ordering(self):
        _, _, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config(
                "adversaries",
                3,
                ["tier", "classification", "name", "semanticId"],
            ),
            "adversary",
        )
        self.assertTrue(any("adversary ordering must be" in message for message in errors))

    def test_frozen_feature_reference_requires_applied_step4_equivalence(self):
        runtime, contract, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config(
                "adversaries-features",
                2,
                ["normalized-name", "semanticId"],
                version="v1.0",
            ),
            "feature-reference",
        )
        self.assertEqual(errors, [])
        self.assertEqual(contract["actualEntryCount"], 2)
        self.assertEqual(contract["step4FeaturePublicationStatus"], "APPLIED")
        self.assertEqual(len(runtime["selection"]["semanticIds"]), 2)

        sidecar = self._sidecar()
        sidecar["encounterSemantics"]["adversaryFeatureEquivalence"]["publicationStatus"] = "REVIEW_REQUIRED"
        _, _, errors = self.builder._productionize_config(
            sidecar,
            self._config(
                "adversaries-features",
                2,
                ["normalized-name", "semanticId"],
                version="v1.0",
            ),
            "feature-reference",
        )
        self.assertTrue(any("publicationStatus='APPLIED'" in message for message in errors))

    def test_adversary_v10_is_rejected_after_v11_freeze(self):
        _, _, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config("adversaries", 3, ["normalized-name", "semanticId"], version="v1.0"),
            "adversary",
        )
        self.assertTrue(any("adversary config must have lifecycle.version='v1.1'" in message for message in errors))

    def test_frozen_contract_fails_closed_on_count_drift(self):
        _, contract, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config("adversaries", 4, ["normalized-name", "semanticId"]),
            "adversary",
        )
        self.assertEqual(contract["actualEntryCount"], 3)
        self.assertTrue(any("frozen contract expects 4" in message for message in errors))

    def test_frozen_contract_blocks_failed_step4_semantics(self):
        sidecar = self._sidecar()
        sidecar["encounterSemantics"]["status"] = "FAIL"
        _, _, errors = self.builder._productionize_config(
            sidecar,
            self._config("adversaries", 3, ["normalized-name", "semanticId"]),
            "adversary",
        )
        self.assertTrue(any("encounterSemantics status is FAIL" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
