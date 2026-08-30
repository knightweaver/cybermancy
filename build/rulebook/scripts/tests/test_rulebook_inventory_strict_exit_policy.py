from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulebook_inventory_strict as strict_inventory


class StrictInventoryExitPolicyTests(unittest.TestCase):
    def test_unresolved_dependencies_remain_review_findings_not_process_failure(self) -> None:
        inventory = {
            "mkdocs_config_warnings": [],
            "counts": {"unresolved_dependency_files": 6},
        }
        self.assertEqual(strict_inventory._strict_exit_code(inventory), 0)

    def test_mkdocs_configuration_warning_remains_fatal(self) -> None:
        inventory = {
            "mkdocs_config_warnings": ["could not read mkdocs.player.yml"],
            "counts": {"unresolved_dependency_files": 0},
        }
        self.assertEqual(strict_inventory._strict_exit_code(inventory), 1)


if __name__ == "__main__":
    unittest.main()
