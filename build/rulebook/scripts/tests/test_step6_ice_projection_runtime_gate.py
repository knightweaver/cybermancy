from __future__ import annotations

import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
INTEGRATION_SCRIPT = SCRIPT_DIR / "build-rulebook-step6-integrated.py"


class Step6IceProjectionRuntimeGateTests(unittest.TestCase):
    def test_stage130_ice_gate_does_not_reimpose_historical_cardinality(self) -> None:
        source = INTEGRATION_SCRIPT.read_text(encoding="utf-8")
        start = source.index("def _compose_ice(")
        end = source.index("\ndef _write_integrated_ast", start)
        compose_ice = source[start:end]

        self.assertIn('package_report.get("status") == "PASS"', compose_ice)
        self.assertIn("validated Step 4 ICE projection", compose_ice)
        self.assertNotIn("expectedIceTotal", compose_ice)
        self.assertNotIn("== 13", compose_ice)
        self.assertNotIn("13-entry", compose_ice)


if __name__ == "__main__":
    unittest.main()
