import argparse
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout import equipment_batch
from rulebook_layout_cli_compat import configure_layout_machine_output


class TestRulebookLayoutCliCompat(unittest.TestCase):
    def test_equipment_batch_children_request_verbose_json_output(self):
        configure_layout_machine_output({})
        args = argparse.Namespace(
            sidecar=None,
            manuscript=None,
            report_dir=None,
            tex_only=False,
        )
        item = {
            "family": "armors",
            "chapter": 18,
            "config": "armors-v1.json",
        }
        command = equipment_batch._child_command(
            "validate",
            item,
            args,
            script_path=Path("build-rulebook-layout.py"),
            output_base=None,
        )
        self.assertIn("--verbose", command)
        self.assertEqual(command.count("--verbose"), 1)


if __name__ == "__main__":
    unittest.main()
