from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulebook_inventory_strict as strict_inventory


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init")
    git(root, "config", "user.email", "inventory-test@example.com")
    git(root, "config", "user.name", "Inventory Test")
    return root


def commit_all(repo: Path, message: str = "fixture") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


class InventoryFilesystemCharacterizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = strict_inventory._legacy_namespace()
        cls.walk_repo = staticmethod(cls.legacy["walk_repo"])

    def test_existing_filesystem_walk_sees_untracked_and_ignored_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / ".gitignore").write_text("ignored-root.txt\n", encoding="utf-8")
            (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            commit_all(repo)
            (repo / "ignored-root.txt").write_text("ignored\n", encoding="utf-8")
            (repo / "untracked-root.txt").write_text("untracked\n", encoding="utf-8")

            names = {path.name for path in self.walk_repo(repo)}
            self.assertIn("ignored-root.txt", names)
            self.assertIn("untracked-root.txt", names)

    def test_existing_build_directory_exclusion_remains_in_force(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "build").mkdir()
            (root / "build" / "should-not-scan.txt").write_text("x\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "should-scan.txt").write_text("x\n", encoding="utf-8")
            rels = {path.relative_to(root).as_posix() for path in self.walk_repo(root)}
            self.assertIn("docs/should-scan.txt", rels)
            self.assertNotIn("build/should-not-scan.txt", rels)

    def test_non_git_filesystem_scan_retains_legacy_fallback_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "plain file.txt").write_text("diagnostic\n", encoding="utf-8")
            rels = [path.relative_to(root).as_posix() for path in self.walk_repo(root)]
            self.assertEqual(rels, ["plain file.txt"])


class StrictInventoryGitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        legacy = strict_inventory._legacy_namespace()
        cls.excluded = set(legacy["DEFAULT_EXCLUDED_DIRS"])

    def _snapshot(self, repo: Path, output: Path | None = None) -> tuple[str, list[str]]:
        return strict_inventory.strict_snapshot(
            repo,
            output or repo / "build/rulebook/inventory",
            self.excluded,
        )

    def test_strict_mode_requires_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(strict_inventory.StrictInventoryError):
                strict_inventory.strict_snapshot(root, root / "out", self.excluded)

    def test_clean_tracked_input_comes_from_git_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / "docs").mkdir()
            (repo / "docs" / "tracked.md").write_text("# Tracked\n", encoding="utf-8")
            expected_head = commit_all(repo)
            head, candidates = self._snapshot(repo)
            self.assertEqual(head, expected_head)
            self.assertIn("docs/tracked.md", candidates)

    def test_ignored_file_is_allowed_locally_but_cannot_be_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / ".gitignore").write_text("ignored local.txt\n", encoding="utf-8")
            (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            commit_all(repo)
            (repo / "ignored local.txt").write_text("ignored\n", encoding="utf-8")
            _head, candidates = self._snapshot(repo)
            self.assertIn("tracked.txt", candidates)
            self.assertNotIn("ignored local.txt", candidates)

    def test_untracked_nonignored_file_blocks_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            commit_all(repo)
            (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            with self.assertRaises(strict_inventory.StrictInventoryError):
                self._snapshot(repo)

    def test_modified_tracked_file_blocks_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            target = repo / "tracked.txt"
            target.write_text("before\n", encoding="utf-8")
            commit_all(repo)
            target.write_text("after\n", encoding="utf-8")
            with self.assertRaises(strict_inventory.StrictInventoryError):
                self._snapshot(repo)

    def test_missing_tracked_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            target = repo / "tracked.txt"
            target.write_text("tracked\n", encoding="utf-8")
            commit_all(repo)
            tracked = strict_inventory._git_ls_files(repo)
            target.unlink()
            with self.assertRaises(strict_inventory.StrictInventoryError):
                strict_inventory._validate_tracked_presence(repo, tracked)

    def test_filename_with_spaces_and_unicode_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / "docs").mkdir()
            relative = "docs/Rules with spaces — alpha.md"
            (repo / relative).write_text("# Alpha\n", encoding="utf-8")
            commit_all(repo)
            _head, candidates = self._snapshot(repo)
            self.assertIn(relative, candidates)

    def test_strict_candidates_retain_existing_build_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / "build").mkdir()
            (repo / "build" / "tracked-build.txt").write_text("build\n", encoding="utf-8")
            (repo / "docs").mkdir()
            (repo / "docs" / "tracked-doc.txt").write_text("doc\n", encoding="utf-8")
            commit_all(repo)
            _head, candidates = self._snapshot(repo)
            self.assertIn("docs/tracked-doc.txt", candidates)
            self.assertNotIn("build/tracked-build.txt", candidates)

    def test_custom_output_directory_is_never_a_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            output = repo / "inventory-output"
            output.mkdir()
            (output / "old.json").write_text("{}\n", encoding="utf-8")
            (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            commit_all(repo)
            _head, candidates = self._snapshot(repo, output)
            self.assertIn("tracked.txt", candidates)
            self.assertNotIn("inventory-output/old.json", candidates)

    def test_no_outputs_written_when_strict_startup_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            commit_all(repo)
            (repo / "dirty.txt").write_text("untracked\n", encoding="utf-8")
            output = repo / "strict-output"
            stderr = io.StringIO()
            argv = [
                str(strict_inventory.PUBLIC_SCRIPT),
                "--repo-root", str(repo),
                "--output-dir", str(output),
                "--strict",
            ]
            with patch.object(sys, "argv", argv), contextlib.redirect_stderr(stderr):
                code = strict_inventory.main()
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
            self.assertIn("clean working tree", stderr.getvalue())

    def test_staged_change_blocks_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            target = repo / "tracked.txt"
            target.write_text("before\n", encoding="utf-8")
            commit_all(repo)
            target.write_text("after\n", encoding="utf-8")
            git(repo, "add", "tracked.txt")
            with self.assertRaises(strict_inventory.StrictInventoryError):
                self._snapshot(repo)


if __name__ == "__main__":
    unittest.main()
