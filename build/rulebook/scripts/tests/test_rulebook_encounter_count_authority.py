from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounter_authority import (
    count_authority_descriptor,
    reconcile_encounter_authority,
    sidecar_encounter_state,
)
from rulebook_layout.encounter_integration import (
    validate_encounter_routes,
    validate_package_selection,
)
from rulebook_production.contract import canonical_text_sha256
from rulebook_production.publication_shell import entity_index

STEP6_CONTRACT = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
PRODUCTION_CONTRACT = RULEBOOK_DIR / "production" / "production-renderer-v1.json"
ADVERSARY_CONFIG = RULEBOOK_DIR / "layout" / "encounters" / "adversary-package-v1.json"
ENVIRONMENT_CONFIG = RULEBOOK_DIR / "layout" / "encounters" / "environment-package-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest(adversaries: int = 106, environments: int = 8) -> dict:
    rows = []
    for family, count in (("adversaries", adversaries), ("environments", environments)):
        rows.append(
            {
                "generatorFamily": family,
                "entityCount": count,
                "authority": "CANONICAL-CANDIDATE",
                "disposition": "INCLUDE",
                "decisionStatus": "DECIDED",
                "audience": "gm",
            }
        )
    return {"publicationInputs": {"structuredFamilies": rows}}


def _entity(family: str, index: int, *, audience: str = "gm") -> dict:
    return {
        "semanticId": f"entity:{family}:{index:04d}",
        "family": family,
        "name": f"{family}-{index:04d}",
        "audience": audience,
        "publicationData": {
            "tier": 1 + (index % 4),
            "classification": "standard",
        },
    }


def _sidecar(adversaries: int = 106, environments: int = 8) -> dict:
    return {
        "encounterSemantics": {
            "entityCounts": {
                "adversaries": adversaries,
                "environments": environments,
            }
        },
        "entities": [
            *[_entity("adversaries", index) for index in range(adversaries)],
            *[_entity("environments", index) for index in range(environments)],
        ],
    }


def _index_expectations() -> dict:
    return {
        "classes": 1,
        "subclasses": 0,
        "domainCards": 0,
        "weapons": 0,
        "ammo": 0,
        "armors": 0,
        "cybernetics": 0,
        "dronesDevices": 0,
        "consumables": 0,
        "mods": 0,
        "loot": 0,
        "ice": 0,
        "adversaryFeaturesPublished": 0,
    }


class EncounterCountAuthorityGrowthTests(unittest.TestCase):
    def test_existing_106_adversary_8_environment_corpus_is_accepted(self) -> None:
        report = reconcile_encounter_authority(_manifest(), _sidecar())
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["families"]["adversaries"]["actualStep4Count"], 106)
        self.assertEqual(report["families"]["environments"]["actualStep4Count"], 8)

    def test_reconciled_107_adversary_corpus_is_accepted_without_contract_edit(self) -> None:
        report = reconcile_encounter_authority(_manifest(adversaries=107), _sidecar(adversaries=107))
        self.assertEqual(report["status"], "PASS", report)
        state = sidecar_encounter_state(_sidecar(adversaries=107))["adversaries"]
        self.assertEqual(validate_package_selection("adversaries", state, state["semanticIds"]), [])

    def test_reconciled_9_environment_corpus_is_accepted_without_contract_edit(self) -> None:
        report = reconcile_encounter_authority(_manifest(environments=9), _sidecar(environments=9))
        self.assertEqual(report["status"], "PASS", report)
        state = sidecar_encounter_state(_sidecar(environments=9))["environments"]
        self.assertEqual(validate_package_selection("environments", state, state["semanticIds"]), [])

    def test_manifest_107_sidecar_106_fails_closed(self) -> None:
        report = reconcile_encounter_authority(_manifest(adversaries=107), _sidecar(adversaries=106))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("expects 107" in message for message in report["errors"]))

    def test_step4_107_layout_106_fails_closed(self) -> None:
        state = sidecar_encounter_state(_sidecar(adversaries=107))["adversaries"]
        errors = validate_package_selection("adversaries", state, state["semanticIds"][:-1])
        self.assertTrue(errors)
        self.assertTrue(any("106" in message and "107" in message for message in errors))

    def test_duplicate_semantic_ids_fail(self) -> None:
        sidecar = _sidecar(adversaries=2, environments=1)
        sidecar["entities"][1]["semanticId"] = sidecar["entities"][0]["semanticId"]
        with self.assertRaisesRegex(ValueError, "duplicate semantic IDs"):
            sidecar_encounter_state(sidecar)

    def test_wrong_audience_and_wrong_chapter_fail(self) -> None:
        sidecar = _sidecar(adversaries=1, environments=1)
        sidecar["entities"][0]["audience"] = "player"
        with self.assertRaisesRegex(ValueError, "non-GM"):
            sidecar_encounter_state(sidecar)

        contract = _load(STEP6_CONTRACT)
        moved = json.loads(json.dumps(contract))
        target = next(row for row in moved["structuredTargets"] if row["families"] == ["adversaries"])
        target["chapter"] = 31
        self.assertTrue(validate_encounter_routes(moved))

    def test_player_guide_index_remains_free_of_encounters(self) -> None:
        sidecar = _sidecar(adversaries=107, environments=9)
        sidecar["entities"].append(
            {"family": "classes", "name": "Razzhacker", "semanticId": "entity:classes:r"}
        )
        result = entity_index(sidecar, "player-guide", _index_expectations())
        self.assertEqual(result["entryCount"], 1)
        self.assertEqual(result["familyCounts"], {"classes": 1})
        self.assertEqual(result["rows"][0]["family"], "classes")


class EncounterContractStabilityTests(unittest.TestCase):
    def test_mutable_count_contracts_reference_authority_not_literals(self) -> None:
        step6 = _load(STEP6_CONTRACT)
        production = _load(PRODUCTION_CONTRACT)
        adversary = _load(ADVERSARY_CONFIG)
        environment = _load(ENVIRONMENT_CONFIG)

        for family, config in (("adversaries", adversary), ("environments", environment)):
            descriptor = count_authority_descriptor(family)
            self.assertEqual(step6["regressionExpectations"][family]["countAuthority"], descriptor)
            self.assertEqual(config["publicationPolicy"]["countAuthority"], descriptor)
            self.assertEqual(production["mutableStructuredCountAuthorities"][family], descriptor)
            self.assertNotIn("entries", step6["regressionExpectations"][family])
            self.assertNotIn("expectedEntryCount", config["publicationPolicy"])
            self.assertNotIn(family, production["structuredExpectations"])

    def test_only_intended_frozen_bindings_changed_and_hashes_match(self) -> None:
        production = _load(PRODUCTION_CONTRACT)
        step6_binding = production["authorities"]["step6IntegrationContract"]
        package_bindings = {row["path"]: row["sha256"] for row in production["frozenPackageBindings"]}
        expected_paths = {
            "build/rulebook/layout/integration/step6-integration-v1.json": step6_binding["sha256"],
            "build/rulebook/layout/encounters/adversary-package-v1.json": package_bindings["build/rulebook/layout/encounters/adversary-package-v1.json"],
            "build/rulebook/layout/encounters/environment-package-v1.json": package_bindings["build/rulebook/layout/encounters/environment-package-v1.json"],
        }
        for relative, expected in expected_paths.items():
            actual = canonical_text_sha256((RULEBOOK_DIR.parent.parent / relative).read_bytes())
            self.assertEqual(actual, expected, relative)

        unchanged_bindings = {
            row["path"]: row["sha256"]
            for row in production["frozenPackageBindings"]
            if row["path"] not in {
                "build/rulebook/layout/encounters/adversary-package-v1.json",
                "build/rulebook/layout/encounters/environment-package-v1.json",
            }
        }
        self.assertEqual(
            unchanged_bindings["build/rulebook/layout/encounters/adversary-feature-reference-v1.json"],
            "1baa4a3aaa34581451f220f2ac6ce221c320b1f7ea0c361146c76a901931e4cc",
        )

    def test_layout_profiles_ordering_and_release_names_are_unchanged(self) -> None:
        step6 = _load(STEP6_CONTRACT)
        production = _load(PRODUCTION_CONTRACT)
        adversary = _load(ADVERSARY_CONFIG)
        environment = _load(ENVIRONMENT_CONFIG)

        self.assertEqual(step6["chapterMap"][-3]["chapter"], 30)
        self.assertEqual(step6["chapterMap"][-3]["audience"], "gm")
        self.assertEqual(step6["chapterMap"][-2]["chapter"], 31)
        self.assertEqual(step6["chapterMap"][-2]["audience"], "gm")
        self.assertEqual(adversary["publicationPolicy"]["ordering"], ["tier", "classification", "name", "semanticId"])
        self.assertEqual(environment["publicationPolicy"]["ordering"], ["tier", "classification", "name", "semanticId"])
        self.assertEqual(adversary["lifecycle"]["version"], "v1.1")
        self.assertEqual(environment["lifecycle"]["version"], "v1.0")
        self.assertEqual(production["profiles"]["complete-rulebook"]["releaseFilename"], "Cybermancy_Core_Rulebook.pdf")
        self.assertEqual(production["profiles"]["player-guide"]["releaseFilename"], "Cybermancy_Player_Guide.pdf")
        self.assertEqual(
            [row["order"] for row in production["transformOrder"]],
            list(range(10, 171, 10)),
        )

    def test_existing_corpus_entity_index_counts_are_stable(self) -> None:
        sidecar = _sidecar()
        result = entity_index(
            sidecar,
            "complete-rulebook",
            {
                "classes": 0,
                "subclasses": 0,
                "domainCards": 0,
                "weapons": 0,
                "ammo": 0,
                "armors": 0,
                "cybernetics": 0,
                "dronesDevices": 0,
                "consumables": 0,
                "mods": 0,
                "loot": 0,
                "ice": 0,
                "adversaryFeaturesPublished": 0,
            },
        )
        self.assertEqual(result["familyCounts"]["adversaries"], 106)
        self.assertEqual(result["familyCounts"]["environments"], 8)
        self.assertEqual(result["entryCount"], 114)


if __name__ == "__main__":
    unittest.main()
