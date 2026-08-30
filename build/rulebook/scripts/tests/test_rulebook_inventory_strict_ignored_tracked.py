from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulebook_inventory_strict as strict_inventory


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init")
    git(root, "config", "user.email", "inventory-test@example.com")
    git(root, "config", "user.name", "Inventory Test")
    return root


class StrictInventoryTrackedIgnoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        legacy = strict_inventory._legacy_namespace()
        cls.excluded = set(legacy["DEFAULT_EXCLUDED_DIRS"])

    def test_tracked_file_later_ignored_is_not_a_strict_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo")
            (repo / "packs").mkdir()
            (repo / "packs" / "tracked.log").write_text("tracked\n", encoding="utf-8")
            git(repo, "add", "packs/tracked.log")
            git(repo, "commit", "-m", "track legacy pack output")

            (repo / ".gitignore").write_text("/packs/\n", encoding="utf-8")
            git(repo, "add", ".gitignore")
            git(repo, "commit", "-m", "ignore legacy pack output")

            ignored = strict_inventory._git_ignored_tracked_files(repo)
            self.assertIn("packs/tracked.log", ignored)

            _head, candidates = strict_inventory.strict_snapshot(
                repo,
                repo / "build/rulebook/inventory",
                self.excluded,
            )
            self.assertNotIn("packs/tracked.log", candidates)


if __name__ == "__main__":
    unittest.main()
