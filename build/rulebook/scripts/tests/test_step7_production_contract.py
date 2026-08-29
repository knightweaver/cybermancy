import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = REPO_ROOT / "build/rulebook/production/production-renderer-v1.json"
METADATA_PATH = REPO_ROOT / "build/rulebook/production/publication-metadata-v1.json"


class ProductionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    def test_profiles_and_release_names_are_frozen(self):
        self.assertEqual(
            set(self.contract["profiles"]), {"complete-rulebook", "player-guide"}
        )
        self.assertEqual(
            self.contract["profiles"]["complete-rulebook"]["releaseFilename"],
            "Cybermancy_Core_Rulebook.pdf",
        )
        self.assertEqual(
            self.contract["profiles"]["player-guide"]["releaseFilename"],
            "Cybermancy_Player_Guide.pdf",
        )
        self.assertEqual(
            self.metadata["profiles"]["complete-rulebook"]["releaseFilename"],
            "Cybermancy_Core_Rulebook.pdf",
        )

    def test_step4_is_validated_but_not_rebuilt(self):
        readiness = self.contract["upstreamReadiness"]
        self.assertEqual(readiness["mode"], "validate-existing-step4-output")
        self.assertFalse(readiness["automaticStep4Rebuild"])
        self.assertTrue(readiness["failClosed"])
        self.assertIn(
            "build/rulebook/source/metadata/adversary-feature-publication-selection.json",
            readiness["requiredArtifacts"],
        )

    def test_navigation_scope_and_reserved_chapter(self):
        navigation = self.contract["navigation"]
        self.assertEqual(navigation["tocLevels"], ["part", "chapter", "appendix"])
        self.assertEqual(navigation["bookmarkLevels"], ["part", "chapter", "appendix"])
        self.assertFalse(navigation["routineLowerLevelHeadings"])
        self.assertFalse(navigation["reservedChapter13Allowed"])

    def test_deferred_appendices_are_not_generated(self):
        appendices = self.contract["appendices"]
        for appendix_id in (
            "appendix-a-rules-quick-reference",
            "appendix-c-attribution-publication-notice",
        ):
            self.assertEqual(appendices[appendix_id]["status"], "DEFERRED")
            self.assertFalse(appendices[appendix_id]["generate"])

    def test_transform_order_matches_accepted_step6_contract(self):
        step6_path = REPO_ROOT / self.contract["authorities"]["step6IntegrationContract"]["path"]
        step6 = json.loads(step6_path.read_text(encoding="utf-8"))
        expected = [(item["order"], item["stage"]) for item in step6["transformationOrder"]]
        actual = [(item["order"], item["stage"]) for item in self.contract["transformOrder"]]
        self.assertEqual(actual, expected)

    def test_frozen_contract_hashes_match_repository(self):
        bindings = [self.contract["authorities"]["step6IntegrationContract"]]
        bindings.extend(self.contract["frozenPackageBindings"])
        for binding in bindings:
            path = REPO_ROOT / binding["path"]
            with self.subTest(path=binding["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), binding["sha256"])


if __name__ == "__main__":
    unittest.main()
