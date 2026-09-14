from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package_batch import validate_domain_package_membership
from rulebook_layout.structured_count_authority import (
    count_authority_descriptor,
    reconcile_structured_count_authority,
)
from rulebook_production.contract import select_latest

STEP6_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
DOMAIN_CONFIG = RULEBOOK_DIR / "layout" / "domains" / "domain-package-v1.json"
PRODUCTION_CONTRACT = RULEBOOK_DIR / "production" / "production-renderer-v1.json"
SIDECAR = RULEBOOK_DIR / "source" / "metadata" / "structured-entities.json"
MANIFESTS = RULEBOOK_DIR / "manifests"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest(count: int = 74) -> dict:
    return {
        "publicationInputs": {
            "structuredFamilies": [
                {
                    "generatorFamily": "domains",
                    "entityCount": count,
                    "authority": "CANONICAL-CANDIDATE",
                    "disposition": "INCLUDE",
                    "decisionStatus": "DECIDED",
                    "audience": "player",
                }
            ]
        }
    }


def _sidecar(count: int = 74) -> dict:
    ids = [f"entity:domains:card-{index:03d}" for index in range(count)]
    third = count // 3
    groups = [ids[:third], ids[third : third * 2], ids[third * 2 :]]
    packages = []
    for index, cards in enumerate(groups):
        packages.append(
            {
                "domainKey": f"domain-{index}",
                "name": f"Domain {index}",
                "cardCount": len(cards),
                "cards": cards,
                "levels": [],
            }
        )
    return {
        "domainSemantics": {"domainCount": len(packages), "cardCount": count},
        "domainPackages": packages,
        "entities": [
            {
                "semanticId": semantic_id,
                "family": "domains",
                "name": semantic_id,
                "audience": "player",
                "publicationData": {"domainKey": "domain-0"},
            }
            for semantic_id in ids
        ],
    }


class DomainCountAuthorityTests(unittest.TestCase):
    def test_current_committed_74_card_corpus_succeeds(self) -> None:
        manifest = _load(
            select_latest(
                MANIFESTS,
                "cybermancy-rulebook-publication-manifest-v*.json",
            )
        )
        sidecar = _load(SIDECAR)
        report = reconcile_structured_count_authority(
            manifest, sidecar, families=("domains",)
        )
        self.assertEqual(report["status"], "PASS", report)
        domain = report["families"]["domains"]
        self.assertEqual(domain["expectedCount"], 74)
        self.assertEqual(domain["actualStep4Count"], 74)
        self.assertEqual(len(sidecar["domainPackages"]), 3)

    def test_reconciled_75_card_corpus_succeeds_without_frozen_count_edit(self) -> None:
        report = reconcile_structured_count_authority(
            _manifest(75), _sidecar(75), families=("domains",)
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["families"]["domains"]["actualStep4Count"], 75)

    def test_manifest_75_step4_74_fails_closed(self) -> None:
        report = reconcile_structured_count_authority(
            _manifest(75), _sidecar(74), families=("domains",)
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("expects 75" in message for message in report["errors"]))

    def test_step4_75_manifest_74_fails_closed(self) -> None:
        report = reconcile_structured_count_authority(
            _manifest(74), _sidecar(75), families=("domains",)
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("contains 75" in message for message in report["errors"]))

    def test_missing_domain_package_membership_fails(self) -> None:
        sidecar = _sidecar(6)
        removed = sidecar["domainPackages"][0]["cards"].pop()
        sidecar["domainPackages"][0]["cardCount"] -= 1
        expected = [row["semanticId"] for row in sidecar["entities"]]
        report = validate_domain_package_membership(sidecar, expected)
        self.assertEqual(report["status"], "FAIL", report)
        self.assertEqual(report["missing"], [removed])

    def test_duplicate_card_membership_fails(self) -> None:
        sidecar = _sidecar(6)
        duplicate = sidecar["domainPackages"][0]["cards"][0]
        displaced = sidecar["domainPackages"][1]["cards"][0]
        sidecar["domainPackages"][1]["cards"][0] = duplicate
        expected = [row["semanticId"] for row in sidecar["entities"]]
        report = validate_domain_package_membership(sidecar, expected)
        self.assertEqual(report["status"], "FAIL", report)
        self.assertIn(duplicate, report["duplicates"])
        self.assertIn(displaced, report["missing"])

    def test_duplicate_semantic_identity_fails(self) -> None:
        sidecar = _sidecar(3)
        sidecar["entities"][1]["semanticId"] = sidecar["entities"][0]["semanticId"]
        report = reconcile_structured_count_authority(
            _manifest(3), sidecar, families=("domains",)
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("duplicate semantic IDs" in message for message in report["errors"]))

    def test_missing_domains_manifest_family_fails(self) -> None:
        manifest = _manifest(3)
        manifest["publicationInputs"]["structuredFamilies"] = []
        report = reconcile_structured_count_authority(
            manifest, _sidecar(3), families=("domains",)
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("missing structured family 'domains'" in message for message in report["errors"]))

    def test_malformed_count_authority_descriptor_fails(self) -> None:
        report = reconcile_structured_count_authority(
            _manifest(3),
            _sidecar(3),
            families=("domains",),
            descriptors={"domains": {"canonicalExpected": "wrong"}},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("Malformed count-authority descriptor" in message for message in report["errors"]))

    def test_duplicate_manifest_family_fails(self) -> None:
        manifest = _manifest(3)
        manifest["publicationInputs"]["structuredFamilies"].append(
            copy.deepcopy(manifest["publicationInputs"]["structuredFamilies"][0])
        )
        report = reconcile_structured_count_authority(
            manifest, _sidecar(3), families=("domains",)
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("duplicate 'domains'" in message for message in report["errors"]))


class DomainCountAuthorityContractTests(unittest.TestCase):
    def test_domain_runtime_counts_are_descriptors_not_literals(self) -> None:
        step6 = _load(STEP6_CONTRACT)
        config = _load(DOMAIN_CONFIG)
        production = _load(PRODUCTION_CONTRACT)
        descriptor = count_authority_descriptor("domains")

        self.assertEqual(
            step6["regressionExpectations"]["domains"]["countAuthority"],
            descriptor,
        )
        historical = step6["regressionExpectations"]["domains"]["historicalAcceptance"]
        self.assertFalse(historical["operative"])
        self.assertEqual(historical["domainPackages"], 3)
        self.assertEqual(historical["cards"], 73)

        self.assertEqual(config["prototypePolicy"]["countAuthority"], descriptor)
        self.assertFalse(config["lifecycle"]["acceptance"]["historicalCorpus"]["operative"])
        self.assertEqual(production["mutableStructuredCountAuthorities"]["domains"], descriptor)
        self.assertNotIn("domains", production["structuredExpectations"])
        self.assertNotIn("domainCards", production["structuredExpectations"])


if __name__ == "__main__":
    unittest.main()
