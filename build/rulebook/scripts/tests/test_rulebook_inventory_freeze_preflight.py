from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounter_authority import (
    MUTABLE_ENCOUNTER_FAMILIES,
    count_authority_descriptor,
)
from rulebook_production import preflight


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InventoryFreezePreflightTests(unittest.TestCase):
    def test_inventory_binding_is_blocking_preflight_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            metadata = repo / "build/rulebook/source/metadata"
            metadata.mkdir(parents=True)
            _write_json(metadata / "validation.json", {"status": "PASS"})
            _write_json(
                metadata / "adversary-feature-publication-selection.json",
                {
                    "status": "APPLIED",
                    "canonicalSourceFeatureCount": 419,
                    "publicationRepresentativeCount": 344,
                },
            )
            _write_json(metadata / "structured-entities.json", {"sourceCommit": "source"})
            source = repo / "source.txt"
            source.write_text("x", encoding="utf-8")
            (metadata / "source-hashes.json").write_text(
                json.dumps([{"path": "source.txt", "sha256": _sha256(source)}]),
                encoding="utf-8",
            )

            manifests = {
                role: repo / f"{role}-v1.25.json"
                for role in (
                    "publicationManifest",
                    "assemblyManifest",
                    "normalizationConfig",
                )
            }
            publication = {"repository": {"gitCommit": "source"}}
            _write_json(manifests["publicationManifest"], publication)
            _write_json(manifests["assemblyManifest"], {})
            _write_json(manifests["normalizationConfig"], {})
            contract = {
                "mutableStructuredCountAuthorities": {
                    family: count_authority_descriptor(family)
                    for family in MUTABLE_ENCOUNTER_FAMILIES
                },
                "authorities": {"step6IntegrationContract": {}},
                "frozenPackageBindings": [],
                "upstreamReadiness": {
                    "requiredArtifacts": [
                        "build/rulebook/source/metadata/validation.json"
                    ]
                },
                "requiredTools": [],
            }

            with (
                patch.object(preflight, "load_production_contract", return_value=contract),
                patch.object(preflight, "verify_frozen_bindings", return_value=[]),
                patch.object(preflight, "select_freeze_artifacts", return_value=manifests),
                patch.object(preflight, "git_tracked", return_value=True),
                patch.object(
                    preflight,
                    "verify_inventory_freeze_binding",
                    return_value={"status": "FAIL", "errors": ["mismatch"]},
                ),
                patch.object(
                    preflight,
                    "reconcile_encounter_authority",
                    return_value={"status": "PASS"},
                ),
            ):
                report = preflight.run_preflight(
                    repo,
                    repo / "report.json",
                    check_tools=False,
                    run_step4_validator=False,
                )

            checks = {row["code"]: row for row in report["checks"]}
            self.assertEqual(checks["INVENTORY_FREEZE_BINDING"]["status"], "FAIL")
            self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
