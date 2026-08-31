from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_production.freeze_state import verify_inventory_freeze_binding


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _fixture(root: Path) -> tuple[Path, dict]:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    (repo / "source.txt").write_text("source\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source")
    source_commit = _git(repo, "rev-parse", "HEAD")

    inventory_root = repo / "build/rulebook/inventory"
    inventory_root.mkdir(parents=True)
    inventory_json = inventory_root / "rulebook-inventory.json"
    inventory_csv = inventory_root / "rulebook-inventory.csv"
    inventory_report = inventory_root / "rulebook-inventory-report.md"
    _write_json(inventory_json, {"repository": {"git_commit": source_commit}})
    inventory_csv.write_text("path\n", encoding="utf-8")
    inventory_report.write_text("# Inventory\n", encoding="utf-8")

    publication = {
        "status": "FROZEN",
        "repository": {"gitCommit": source_commit},
        "validationSources": {
            "inventoryJson": {
                "file": inventory_json.name,
                "sha256": _sha256(inventory_json),
            },
            "inventoryCsv": {
                "file": inventory_csv.name,
                "sha256": _sha256(inventory_csv),
            },
            "inventoryReport": {
                "file": inventory_report.name,
                "sha256": _sha256(inventory_report),
            },
        },
    }
    _write_json(repo / "publication.json", publication)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "freeze")
    return repo, publication


class InventoryFreezeBindingTests(unittest.TestCase):
    def test_valid_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            result = verify_inventory_freeze_binding(repo, publication)
            self.assertEqual(result["status"], "PASS", result)
            self.assertTrue(result["sourceCommitMatches"])
            self.assertTrue(
                all(row["status"] == "PASS" for row in result["artifacts"].values())
            )

    def _assert_hash_mismatch(self, filename: str, role: str) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            path = repo / "build/rulebook/inventory" / filename
            path.write_bytes(path.read_bytes() + b"tamper")
            result = verify_inventory_freeze_binding(repo, publication)
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["artifacts"][role]["hashMatches"])

    def test_json_hash_mismatch(self) -> None:
        self._assert_hash_mismatch("rulebook-inventory.json", "inventoryJson")

    def test_csv_hash_mismatch(self) -> None:
        self._assert_hash_mismatch("rulebook-inventory.csv", "inventoryCsv")

    def test_report_hash_mismatch(self) -> None:
        self._assert_hash_mismatch("rulebook-inventory-report.md", "inventoryReport")

    def test_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            (repo / "build/rulebook/inventory/rulebook-inventory.csv").unlink()
            result = verify_inventory_freeze_binding(repo, publication)
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["artifacts"]["inventoryCsv"]["exists"])

    def test_untracked_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            relative = "build/rulebook/inventory/rulebook-inventory.csv"
            _git(repo, "rm", "--cached", relative)
            result = verify_inventory_freeze_binding(repo, publication)
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["artifacts"]["inventoryCsv"]["tracked"])

    def test_inventory_publication_source_commit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            changed = copy.deepcopy(publication)
            changed["repository"]["gitCommit"] = "different-source-commit"
            result = verify_inventory_freeze_binding(repo, changed)
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["sourceCommitMatches"])

    def test_current_head_can_be_later_than_frozen_source_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            (repo / "later-code.txt").write_text("later\n", encoding="utf-8")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "later code only")
            self.assertNotEqual(
                _git(repo, "rev-parse", "HEAD"), publication["repository"]["gitCommit"]
            )
            result = verify_inventory_freeze_binding(repo, publication)
            self.assertEqual(result["status"], "PASS", result)

    def test_traversal_or_absolute_filename_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, publication = _fixture(Path(temp))
            for filename in ("../escape.csv", "/tmp/escape.csv", r"C:\escape.csv"):
                with self.subTest(filename=filename):
                    changed = copy.deepcopy(publication)
                    changed["validationSources"]["inventoryCsv"]["file"] = filename
                    result = verify_inventory_freeze_binding(repo, changed)
                    self.assertEqual(result["status"], "FAIL")
                    self.assertIn("error", result["artifacts"]["inventoryCsv"])


if __name__ == "__main__":
    unittest.main()
