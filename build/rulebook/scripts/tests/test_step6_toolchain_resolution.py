from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout import toolchain


class Step6ToolchainResolutionTests(unittest.TestCase):
    def tearDown(self) -> None:
        toolchain.clear_tool_cache()

    def test_explicit_cybermancy_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "pandoc.exe"
            exe.write_text("fixture", encoding="utf-8")
            with patch.dict(os.environ, {"CYBERMANCY_PANDOC_PATH": str(exe)}, clear=False):
                with patch("rulebook_layout.toolchain.shutil.which", return_value=None):
                    resolved = toolchain.resolve_tool("pandoc")
        self.assertEqual(resolved, str(exe.resolve()))

    def test_windows_local_programs_pandoc_is_found_without_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            local = Path(td)
            exe = local / "Programs" / "Pandoc" / "pandoc.exe"
            exe.parent.mkdir(parents=True)
            exe.write_text("fixture", encoding="utf-8")
            env = {"LOCALAPPDATA": str(local)}
            with patch.dict(os.environ, env, clear=False):
                with patch("rulebook_layout.toolchain._is_windows", return_value=True):
                    with patch("rulebook_layout.toolchain.shutil.which", return_value=None):
                        with patch("rulebook_layout.toolchain._windows_app_path", return_value=None):
                            resolved = toolchain.resolve_tool("pandoc")
        self.assertEqual(resolved, str(exe.resolve()))

    def test_windows_winget_link_is_found_without_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            local = Path(td)
            exe = local / "Microsoft" / "WinGet" / "Links" / "pandoc.exe"
            exe.parent.mkdir(parents=True)
            exe.write_text("fixture", encoding="utf-8")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local)}, clear=False):
                with patch("rulebook_layout.toolchain._is_windows", return_value=True):
                    with patch("rulebook_layout.toolchain.shutil.which", return_value=None):
                        with patch("rulebook_layout.toolchain._windows_app_path", return_value=None):
                            resolved = toolchain.resolve_tool("pandoc")
        self.assertEqual(resolved, str(exe.resolve()))


if __name__ == "__main__":
    unittest.main()
