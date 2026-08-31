import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = REPO_ROOT / "build/rulebook/production/production-renderer-v1.json"
METADATA_PATH = REPO_ROOT / "build/rulebook/production/publication-metadata-v1.json"


def canonical_text_sha256(payload: bytes) -> str:
    text = payload.decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ProductionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    def test_profiles_and_release_names_are_frozen(self):
        self.assertEqual(self.contract["implementationStatus"], "PHASE_D_PUBLICATION_SHELL")
        self.assertEqual(set(self.contract["profiles"]), {"complete-rulebook", "player-guide"})
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

    def test_phase_d_publication_shell_decisions_are_accepted(self):
        shell = self.contract["publicationShell"]
        self.assertEqual(shell["status"], "ACCEPTED")
        self.assertEqual(shell["title"], "Cybermancy")
        self.assertEqual(shell["profileSubtitles"]["complete-rulebook"], "Core Rulebook")
        self.assertEqual(shell["readerFacingVersion"], "Version 1.0")
        self.assertFalse(shell["titlePageNumberVisible"])
        self.assertEqual(shell["frontMatterNumbering"], "lowercase-roman")
        self.assertEqual(shell["mainMatterNumbering"], "arabic-from-part-i")
        self.assertEqual(shell["rectoStarts"], ["part", "appendix"])
        self.assertEqual(self.metadata["status"], "ACCEPTED")

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

    def test_appendix_a_and_c_remain_deferred_and_appendix_b_is_removed(self):
        appendices = self.contract["appendices"]
        for appendix_id in (
            "appendix-a-rules-quick-reference",
            "appendix-c-attribution-publication-notice",
        ):
            self.assertEqual(appendices[appendix_id]["status"], "DEFERRED")
            self.assertFalse(appendices[appendix_id]["generate"])
        appendix_b = appendices["appendix-b-entity-index"]
        self.assertEqual(appendix_b["status"], "REMOVED")
        self.assertFalse(appendix_b["generate"])

    def test_no_active_appendix_is_generated(self):
        active = [
            appendix_id
            for appendix_id, state in self.contract["appendices"].items()
            if state.get("generate") is True
        ]
        self.assertEqual(active, [])

    def test_transform_order_matches_accepted_step6_contract(self):
        step6_path = REPO_ROOT / self.contract["authorities"]["step6IntegrationContract"]["path"]
        step6 = json.loads(step6_path.read_text(encoding="utf-8"))
        expected = [(item["order"], item["stage"]) for item in step6["transformationOrder"]]
        actual = [(item["order"], item["stage"]) for item in self.contract["transformOrder"]]
        self.assertEqual(actual, expected)

    def test_frozen_contract_hashes_match_repository(self):
        self.assertEqual(
            self.contract["frozenBindingHashAlgorithm"],
            "sha256-utf8-normalized-lf-v1",
        )
        bindings = [self.contract["authorities"]["step6IntegrationContract"]]
        bindings.extend(self.contract["frozenPackageBindings"])
        for binding in bindings:
            path = REPO_ROOT / binding["path"]
            with self.subTest(path=binding["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(canonical_text_sha256(path.read_bytes()), binding["sha256"])

    def test_frozen_contract_hashes_are_line_ending_independent(self):
        lf = b'{\n  "status": "accepted"\n}\n'
        crlf = lf.replace(b"\n", b"\r\n")
        cr = lf.replace(b"\n", b"\r")
        self.assertEqual(canonical_text_sha256(lf), canonical_text_sha256(crlf))
        self.assertEqual(canonical_text_sha256(lf), canonical_text_sha256(cr))


if __name__ == "__main__":
    unittest.main()
