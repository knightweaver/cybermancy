import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_cli import expose_implementation, run_implementation


_IMPL = '''
import argparse
from pathlib import Path
PUBLIC_FILE_NAME = Path(__file__).name

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail", action="store_true")
    args = parser.parse_args()
    print("routine progress one")
    print("routine progress two")
    if args.fail:
        print("ERROR: synthetic failure")
        return 3
    return 0
'''


class TestRulebookCli(unittest.TestCase):
    def _paths(self, root: Path):
        public = root / "fake.py"
        impl = root / "fake.py.impl"
        public.write_text("# public wrapper placeholder\n", encoding="utf-8")
        impl.write_text(_IMPL, encoding="utf-8")
        return public, impl

    def test_default_success_is_one_pass_line(self):
        with tempfile.TemporaryDirectory() as td:
            public, impl = self._paths(Path(td))
            output = io.StringIO()
            with patch.object(sys, "argv", [str(public)]), contextlib.redirect_stdout(output):
                code = run_implementation(public, impl)
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "fake.py: PASS\n")

    def test_default_failure_reports_error_without_full_progress_log(self):
        with tempfile.TemporaryDirectory() as td:
            public, impl = self._paths(Path(td))
            output = io.StringIO()
            with patch.object(sys, "argv", [str(public), "--fail"]), contextlib.redirect_stdout(output):
                code = run_implementation(public, impl)
        text = output.getvalue()
        self.assertEqual(code, 3)
        self.assertIn("fake.py: FAIL", text)
        self.assertIn("ERROR: synthetic failure", text)

    def test_verbose_restores_legacy_output(self):
        with tempfile.TemporaryDirectory() as td:
            public, impl = self._paths(Path(td))
            output = io.StringIO()
            with patch.object(sys, "argv", [str(public), "--verbose"]), contextlib.redirect_stdout(output):
                code = run_implementation(public, impl)
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("routine progress one", text)
        self.assertIn("routine progress two", text)
        self.assertNotIn("fake.py: PASS", text)

    def test_import_exposure_preserves_public_file_contract(self):
        with tempfile.TemporaryDirectory() as td:
            public, impl = self._paths(Path(td))
            target = {}
            expose_implementation(target, public, impl, "fake")
        self.assertEqual(target["PUBLIC_FILE_NAME"], "fake.py")
        self.assertTrue(callable(target["main"]))


if __name__ == "__main__":
    unittest.main()
