from __future__ import annotations

import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
REPO_ROOT = RULEBOOK_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_production import PROFILES
from rulebook_production.baseline import (
    EXPECTED_CHAPTER_TOPOLOGY,
    EXPECTED_PRODUCTION_STAGE_ORDER,
    EXPECTED_PROFILES,
    EXPECTED_RELEASE_FILENAMES,
    run_baseline_check,
)
from rulebook_production.contract import version_key


class MaintenanceBaselineCharacterizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_baseline_check(REPO_ROOT)

    def test_repository_code_freeze_baseline_passes_without_step4_rendering(self) -> None:
        self.assertEqual(self.report["status"], "PASS", self.report)

    def test_profile_names_and_release_filenames_are_frozen(self) -> None:
        self.assertEqual(tuple(PROFILES), EXPECTED_PROFILES)
        self.assertEqual(set(self.report["profiles"]), set(EXPECTED_PROFILES))
        for profile, filename in EXPECTED_RELEASE_FILENAMES.items():
            self.assertEqual(self.report["profiles"][profile]["contract"], filename)
            self.assertEqual(self.report["profiles"][profile]["metadata"], filename)

    def test_production_stage_tail_is_frozen(self) -> None:
        self.assertEqual(
            tuple(self.report["productionStages"]), EXPECTED_PRODUCTION_STAGE_ORDER
        )

    def test_chapter_topology_is_frozen(self) -> None:
        for profile, chapters in EXPECTED_CHAPTER_TOPOLOGY.items():
            self.assertEqual(tuple(self.report["chapterTopology"][profile]), chapters)

    def test_selected_freezes_are_current_and_compatible(self) -> None:
        selected = self.report["selectedManifests"]
        selected_keys = {
            role: version_key(Path(path)) for role, path in selected.items()
        }
        self.assertEqual(len(set(selected_keys.values())), 1)
        checks = {row["code"]: row for row in self.report["checks"]}
        self.assertEqual(checks["FREEZE_ARTIFACT_SELECTION"]["status"], "PASS")
        self.assertEqual(checks["FREEZE_ARTIFACT_COMPATIBILITY"]["status"], "PASS")
        self.assertEqual(checks["INVENTORY_FREEZE_BINDING"]["status"], "PASS")
        self.assertEqual(checks["FROZEN_STEP6_BINDINGS"]["status"], "PASS")
        self.assertEqual(checks["READ_ONLY_WORKTREE"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
