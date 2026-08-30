from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounter_authority import sidecar_encounter_state
from rulebook_layout.encounter_integration import _prepare_runtime_configs

CONFIG_ROOT = RULEBOOK_DIR / "layout" / "encounters"


def _entity(family: str, index: int) -> dict:
    return {
        "semanticId": f"entity:{family}:{index:04d}",
        "family": family,
        "name": f"{family}-{index:04d}",
        "audience": "gm",
        "publicationData": {"tier": 1, "classification": "standard"},
    }


def _sidecar(adversaries: int, environments: int) -> dict:
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


class EncounterRuntimeCountInjectionTests(unittest.TestCase):
    def test_growth_counts_are_runtime_only_and_preserve_frozen_grammars(self) -> None:
        state = sidecar_encounter_state(_sidecar(107, 9))
        source_configs = {
            name: json.loads((CONFIG_ROOT / name).read_text(encoding="utf-8"))
            for name in (
                "adversary-package-v1.json",
                "environment-package-v1.json",
                "adversary-feature-reference-v1.json",
            )
        }
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = _prepare_runtime_configs(
                CONFIG_ROOT,
                Path(temporary),
                state,
            )
            runtime_configs = {
                name: json.loads((runtime_root / name).read_text(encoding="utf-8"))
                for name in source_configs
            }

        self.assertEqual(
            runtime_configs["adversary-package-v1.json"]["publicationPolicy"]["expectedEntryCount"],
            107,
        )
        self.assertEqual(
            runtime_configs["environment-package-v1.json"]["publicationPolicy"]["expectedEntryCount"],
            9,
        )
        self.assertEqual(
            runtime_configs["adversary-feature-reference-v1.json"]["publicationPolicy"]["expectedEntryCount"],
            344,
        )

        for name in ("adversary-package-v1.json", "environment-package-v1.json"):
            expected = copy.deepcopy(source_configs[name])
            actual = copy.deepcopy(runtime_configs[name])
            self.assertNotIn("expectedEntryCount", expected["publicationPolicy"])
            actual["publicationPolicy"].pop("expectedEntryCount")
            self.assertEqual(actual, expected)

        self.assertEqual(
            runtime_configs["adversary-feature-reference-v1.json"],
            source_configs["adversary-feature-reference-v1.json"],
        )


if __name__ == "__main__":
    unittest.main()
