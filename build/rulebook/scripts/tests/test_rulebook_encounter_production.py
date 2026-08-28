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
            },
            "entities": [
                {
                    "semanticId": "entity:adversaries:Z",
                    "family": "adversaries",
                    "name": "Zulu",
                    "publicationData": {"tier": 2, "classification": "standard"},
                },
                {
                    "semanticId": "entity:adversaries:B",
                    "family": "adversaries",
                    "name": "Beta",
                    "publicationData": {"tier": 1, "classification": "support"},
                },
                {
                    "semanticId": "entity:adversaries:A",
                    "family": "adversaries",
                    "name": "Alpha",
                    "publicationData": {"tier": 1, "classification": "bruiser"},
                },
                {
                    "semanticId": "entity:adversaries-features:S2",
                    "family": "adversaries-features",
                    "name": "Slow",
                    "publicationData": {"rulesMarkdown": "Second."},
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
                    "name": "Slow",
                    "publicationData": {"rulesMarkdown": "First."},
                },
            ],
        }

    def _config(self, family, expected, ordering):
        return {
            "family": family,
            "lifecycle": {"version": "v1.0", "status": "frozen"},
            "selection": {"mode": "full-corpus"},
            "publicationPolicy": {
                "requireFullCorpusSelection": True,
                "expectedEntryCount": expected,
                "ordering": ordering,
            },
        }

    def test_adversary_full_corpus_order_is_tier_classification_name(self):
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

    def test_feature_full_corpus_preserves_same_name_variants(self):
        ids, errors = self.builder._ordered_full_corpus(self._sidecar(), "adversaries-features")
        self.assertEqual(errors, [])
        self.assertEqual(
            ids,
            [
                "entity:adversaries-features:F1",
                "entity:adversaries-features:S1",
                "entity:adversaries-features:S2",
            ],
        )

    def test_frozen_contract_accepts_warning_step4_status(self):
        runtime, contract, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config("adversaries", 3, ["tier", "classification", "name", "semanticId"]),
            "adversary",
        )
        self.assertEqual(errors, [])
        self.assertEqual(contract["actualEntryCount"], 3)
        self.assertEqual(contract["expectedEntryCount"], 3)
        self.assertEqual(runtime["selection"]["mode"], "full-corpus")
        self.assertEqual(len(runtime["selection"]["semanticIds"]), 3)

    def test_frozen_contract_fails_closed_on_count_drift(self):
        _, contract, errors = self.builder._productionize_config(
            self._sidecar(),
            self._config("adversaries", 4, ["tier", "classification", "name", "semanticId"]),
            "adversary",
        )
        self.assertEqual(contract["actualEntryCount"], 3)
        self.assertTrue(any("frozen contract expects 4" in message for message in errors))

    def test_frozen_contract_blocks_failed_step4_semantics(self):
        sidecar = self._sidecar()
        sidecar["encounterSemantics"]["status"] = "FAIL"
        _, _, errors = self.builder._productionize_config(
            sidecar,
            self._config("adversaries", 3, ["tier", "classification", "name", "semanticId"]),
            "adversary",
        )
        self.assertTrue(any("encounterSemantics status is FAIL" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
