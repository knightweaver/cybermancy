from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
RULEBOOK_DIR = HERE.parents[2]
SCRIPT_DIR = RULEBOOK_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.structured_count_authority import (
    CHARACTER_OPTION_COUNT_FAMILIES,
    EQUIPMENT_COUNT_FAMILIES,
    count_authority_descriptor,
    reconcile_structured_count_authority,
)


PHASE2_FAMILIES = (*CHARACTER_OPTION_COUNT_FAMILIES, *EQUIPMENT_COUNT_FAMILIES)
CURRENT_COUNTS = {
    "classes": 5,
    "subclasses": 10,
    "weapons": 47,
    "ammo": 13,
    "armors": 36,
    "cybernetics": 103,
    "drones-devices": 19,
    "consumables": 59,
    "mods": 20,
    "loot": 60,
}


def _manifest(counts: dict[str, int] | None = None) -> dict:
    values = counts or CURRENT_COUNTS
    return {
        "publicationInputs": {
            "structuredFamilies": [
                {
                    "generatorFamily": family,
                    "entityCount": values[family],
                    "authority": "CANONICAL-CANDIDATE",
                    "disposition": "INCLUDE",
                    "decisionStatus": "DECIDED",
                    "audience": "player",
                }
                for family in PHASE2_FAMILIES
            ]
        }
    }


def _sidecar(counts: dict[str, int] | None = None) -> dict:
    values = counts or CURRENT_COUNTS
    entities = []
    for family in PHASE2_FAMILIES:
        for index in range(values[family]):
            entities.append(
                {
                    "family": family,
                    "semanticId": f"entity:{family}:{index:03d}",
                    "sourceId": f"{family}-{index:03d}",
                    "name": f"{family} {index:03d}",
                    "audience": "player",
                }
            )
    return {
        "schema": "cybermancy-step4-structured-entities-v1.3",
        "entities": entities,
    }


def _descriptors() -> dict[str, dict[str, str]]:
    return {family: count_authority_descriptor(family) for family in PHASE2_FAMILIES}


class Phase2StructuredCountAuthorityTests(unittest.TestCase):
    def test_phase2_descriptors_use_row_backed_step4_authority(self) -> None:
        for family in PHASE2_FAMILIES:
            with self.subTest(family=family):
                descriptor = count_authority_descriptor(family)
                self.assertEqual(
                    descriptor["canonicalExpected"],
                    "selected-publication-manifest:publicationInputs.structuredFamilies"
                    f"[generatorFamily={family}].entityCount",
                )
                self.assertEqual(
                    descriptor["normalizedActual"],
                    f"step4-structured-sidecar:entities[family={family}]",
                )
                self.assertEqual(descriptor["reconciliation"], "exact-before-render")

    def test_current_phase2_corpus_reconciles(self) -> None:
        report = reconcile_structured_count_authority(
            _manifest(),
            _sidecar(),
            families=PHASE2_FAMILIES,
            descriptors=_descriptors(),
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(
            {family: report["families"][family]["actualStep4Count"] for family in PHASE2_FAMILIES},
            CURRENT_COUNTS,
        )

    def test_future_increment_succeeds_without_renderer_count_edit(self) -> None:
        counts = dict(CURRENT_COUNTS)
        counts["loot"] += 1
        report = reconcile_structured_count_authority(
            _manifest(counts),
            _sidecar(counts),
            families=PHASE2_FAMILIES,
            descriptors=_descriptors(),
        )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["families"]["loot"]["expectedCount"], 61)
        self.assertEqual(report["families"]["loot"]["actualStep4Count"], 61)

    def test_manifest_increment_without_step4_increment_fails(self) -> None:
        counts = dict(CURRENT_COUNTS)
        counts["weapons"] += 1
        report = reconcile_structured_count_authority(
            _manifest(counts),
            _sidecar(),
            families=PHASE2_FAMILIES,
            descriptors=_descriptors(),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["families"]["weapons"]["status"], "FAIL")

    def test_step4_increment_without_manifest_increment_fails(self) -> None:
        counts = dict(CURRENT_COUNTS)
        counts["classes"] += 1
        report = reconcile_structured_count_authority(
            _manifest(),
            _sidecar(counts),
            families=PHASE2_FAMILIES,
            descriptors=_descriptors(),
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["families"]["classes"]["status"], "FAIL")

    def test_duplicate_semantic_identity_fails(self) -> None:
        sidecar = _sidecar()
        rows = [row for row in sidecar["entities"] if row["family"] == "ammo"]
        rows[1]["semanticId"] = rows[0]["semanticId"]
        report = reconcile_structured_count_authority(
            _manifest(),
            sidecar,
            families=("ammo",),
            descriptors={"ammo": count_authority_descriptor("ammo")},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("duplicate semantic IDs", " ".join(report["errors"]))

    def test_missing_semantic_identity_fails(self) -> None:
        sidecar = _sidecar()
        next(row for row in sidecar["entities"] if row["family"] == "mods")["semanticId"] = ""
        report = reconcile_structured_count_authority(
            _manifest(),
            sidecar,
            families=("mods",),
            descriptors={"mods": count_authority_descriptor("mods")},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("missing semanticId", " ".join(report["errors"]))

    def test_missing_manifest_family_fails(self) -> None:
        manifest = _manifest()
        manifest["publicationInputs"]["structuredFamilies"] = [
            row
            for row in manifest["publicationInputs"]["structuredFamilies"]
            if row["generatorFamily"] != "subclasses"
        ]
        report = reconcile_structured_count_authority(
            manifest,
            _sidecar(),
            families=("subclasses",),
            descriptors={"subclasses": count_authority_descriptor("subclasses")},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("missing structured family", " ".join(report["errors"]))

    def test_duplicate_manifest_family_fails(self) -> None:
        manifest = _manifest()
        row = next(
            row
            for row in manifest["publicationInputs"]["structuredFamilies"]
            if row["generatorFamily"] == "cybernetics"
        )
        manifest["publicationInputs"]["structuredFamilies"].append(copy.deepcopy(row))
        report = reconcile_structured_count_authority(
            manifest,
            _sidecar(),
            families=("cybernetics",),
            descriptors={"cybernetics": count_authority_descriptor("cybernetics")},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("duplicate", " ".join(report["errors"]))

    def test_malformed_descriptor_fails(self) -> None:
        descriptor = count_authority_descriptor("loot")
        descriptor["reconciliation"] = "best-effort"
        report = reconcile_structured_count_authority(
            _manifest(),
            _sidecar(),
            families=("loot",),
            descriptors={"loot": descriptor},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("Malformed count-authority descriptor", " ".join(report["errors"]))

    def test_audience_mismatch_fails(self) -> None:
        sidecar = _sidecar()
        next(row for row in sidecar["entities"] if row["family"] == "armors")["audience"] = "gm"
        report = reconcile_structured_count_authority(
            _manifest(),
            sidecar,
            families=("armors",),
            descriptors={"armors": count_authority_descriptor("armors")},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("outside allowed audiences", " ".join(report["errors"]))

    def test_contracts_retain_only_nonoperative_phase2_historical_counts(self) -> None:
        step6 = json.loads(
            (RULEBOOK_DIR / "layout/integration/step6-integration-v1.json").read_text(encoding="utf-8")
        )
        production = json.loads(
            (RULEBOOK_DIR / "production/production-renderer-v1.json").read_text(encoding="utf-8")
        )

        class_contract = step6["regressionExpectations"]["classes"]
        self.assertFalse(class_contract["historicalAcceptance"]["operative"])
        self.assertEqual(
            class_contract["countAuthorities"],
            {family: count_authority_descriptor(family) for family in CHARACTER_OPTION_COUNT_FAMILIES},
        )

        equipment_contract = step6["regressionExpectations"]["equipment"]
        self.assertFalse(equipment_contract["historicalAcceptance"]["operative"])
        self.assertEqual(
            equipment_contract["countAuthorities"],
            {family: count_authority_descriptor(family) for family in EQUIPMENT_COUNT_FAMILIES},
        )

        for family in PHASE2_FAMILIES:
            self.assertEqual(
                production["mutableStructuredCountAuthorities"][family],
                count_authority_descriptor(family),
            )
        for key in (
            "classes",
            "subclasses",
            "weapons",
            "ammo",
            "armors",
            "cybernetics",
            "dronesDevices",
            "consumables",
            "mods",
            "loot",
        ):
            self.assertNotIn(key, production["structuredExpectations"])

        for _chapter, family, config_name in (
            (15, "weapons", "weapons-v1.json"),
            (16, "ammo", "ammo-v1.json"),
            (17, "armors", "armors-v1.json"),
            (18, "cybernetics", "cybernetics-v1.json"),
            (19, "drones-devices", "drones-devices-v1.json"),
            (20, "consumables", "consumables-v1.json"),
            (21, "mods", "mods-v1.json"),
            (22, "loot", "loot-v1.json"),
        ):
            config = json.loads(
                (RULEBOOK_DIR / "layout/equipment" / config_name).read_text(encoding="utf-8")
            )
            self.assertEqual(config["family"], family)
            self.assertFalse(config["historicalAcceptance"]["operative"])
            self.assertNotIn("expectedEntityCount", config)
            self.assertNotIn("expectedTierCounts", config)


if __name__ == "__main__":
    unittest.main()
