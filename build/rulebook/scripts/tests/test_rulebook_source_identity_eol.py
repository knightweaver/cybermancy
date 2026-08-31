from __future__ import annotations

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

import rulebook_inventory_strict as strict_inventory
from rulebook_git_source_identity import (
    configure_step4_authored_source_identity,
    configure_strict_inventory_git_identity,
    git_blob_bytes,
)
from rulebook_normalize import pipeline
from rulebook_normalize.snapshot import (
    STRUCTURED_DIGEST_ALGORITHM,
    structured_family_snapshot,
)
from rulebook_normalize.validate import new_report


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


def init_repo(root: Path, *, autocrlf: str = "false") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init")
    git(root, "config", "user.email", "source-identity-test@example.com")
    git(root, "config", "user.name", "Source Identity Test")
    git(root, "config", "core.autocrlf", autocrlf)
    return root


def commit_all(repo: Path, message: str = "fixture") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


class StrictInventoryEolIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        legacy = strict_inventory._legacy_namespace()
        cls.excluded = set(legacy["DEFAULT_EXCLUDED_DIRS"])

    def test_strict_inventory_uses_exact_git_blob_bytes_with_autocrlf_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = init_repo(Path(td) / "repo", autocrlf="true")
            target = repo / "docs" / "tracked.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"# Tracked\n\nAlpha\nBeta\nGamma\n")
            commit_all(repo)

            raw_blob = git_blob_bytes(repo, "docs/tracked.md")
            expected_hash = hashlib.sha256(raw_blob).hexdigest()
            expected_size = len(raw_blob)

            head, candidates = strict_inventory.strict_snapshot(
                repo,
                repo / "build/rulebook/inventory",
                self.excluded,
            )
            original_builder = strict_inventory._build_from_committed_index
            try:
                configure_strict_inventory_git_identity(strict_inventory.__dict__)
                inventory = strict_inventory._build_from_committed_index(
                    repo,
                    head,
                    candidates,
                )
            finally:
                strict_inventory._build_from_committed_index = original_builder

            record = next(
                item
                for item in inventory["items"]
                if item["path"] == "docs/tracked.md"
            )
            self.assertEqual(record["size_bytes"], expected_size)
            self.assertEqual(record["sha256"], expected_hash)


class Step4AuthoredSourceIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_preflight = pipeline.repository_preflight
        configure_step4_authored_source_identity(pipeline.__dict__)

    @classmethod
    def tearDownClass(cls) -> None:
        pipeline.repository_preflight = cls.original_preflight

    def _fixture(self, root: Path):
        repo = init_repo(root, autocrlf="false")
        authored = repo / "rules.md"
        authored.write_bytes(b"# Rules\nFrozen.\n")

        family = repo / "src" / "packs" / "system" / "things"
        family.mkdir(parents=True)
        (family / "one.json").write_text(
            json.dumps({"_id": "A", "name": "One"}),
            encoding="utf-8",
        )
        frozen_commit = commit_all(repo)
        frozen_hash = hashlib.sha256(git_blob_bytes(repo, "rules.md")).hexdigest()
        snapshot = structured_family_snapshot(repo, "src/packs/system/things")

        publication = {
            "repository": {"gitCommit": frozen_commit},
            "publicationInputs": {
                "authoredDocuments": [
                    {
                        "path": "rules.md",
                        "disposition": "INCLUDE",
                        "decisionStatus": "DECIDED",
                        "sha256": frozen_hash,
                    }
                ],
                "structuredFamilies": [
                    {
                        "generatorFamily": "things",
                        "sourcePath": "src/packs/system/things",
                        "entityCount": 1,
                        "disposition": "INCLUDE",
                        "decisionStatus": "DECIDED",
                        "contentDigestAlgorithm": STRUCTURED_DIGEST_ALGORITHM,
                        "contentDigestSha256": snapshot.digest_sha256,
                    }
                ],
            },
        }
        assembly = {
            "authority": {"sourceCommit": frozen_commit},
            "authoredInputs": [
                {"assemblyInputId": "auth.rules", "path": "rules.md"}
            ],
            "structuredFamilies": [
                {
                    "familyId": "things",
                    "sourcePath": "src/packs/system/things",
                    "entityCount": 1,
                }
            ],
        }
        config = {
            "baseline": {"commit": frozen_commit, "expectedLogicalEntities": 1},
            "families": {"things": {"expected": 1}},
            "manifestAdapter": {
                "publication": {
                    "baselineCommitPointer": "/repository/gitCommit",
                    "authoredIncludeRecordsPointer": "/publicationInputs/authoredDocuments",
                    "structuredFamilyRecordsPointer": "/publicationInputs/structuredFamilies",
                },
                "assembly": {
                    "sectionsPointer": "/bookStructure",
                    "profilesPointer": "/buildProfiles",
                },
            },
            "semantics": {"gmDivider": "GM MATERIAL — SPOILERS BEYOND THIS POINT"},
            "structured": {"familyDigestAlgorithm": STRUCTURED_DIGEST_ALGORITHM},
        }
        return repo, authored, publication, assembly, config

    def _checks(self, report: dict) -> dict[str, dict]:
        return {item["code"]: item for item in report["checks"]}

    def test_eol_only_worktree_representation_matches_frozen_git_blob(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo, authored, publication, assembly, config = self._fixture(Path(td) / "repo")
            git(repo, "config", "core.autocrlf", "true")
            authored.unlink()
            git(repo, "checkout", "--", "rules.md")
            self.assertIn(b"\r\n", authored.read_bytes())
            self.assertEqual(git(repo, "status", "--porcelain").stdout.strip(), "")

            report = new_report()
            pipeline.repository_preflight(repo, publication, assembly, config, report)
            checks = self._checks(report)

            self.assertEqual(report["status"], "PASS", report)
            self.assertNotEqual(checks.get("AUTHORED_SOURCE_HASHES", {}).get("status"), "ERROR")
            self.assertEqual(checks["SOURCE_CORPUS_INTEGRITY"]["status"], "PASS")

    def test_committed_authored_change_after_freeze_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo, authored, publication, assembly, config = self._fixture(Path(td) / "repo")
            authored.write_bytes(b"# Rules\nChanged after freeze.\n")
            commit_all(repo, "change canonical prose")

            report = new_report()
            pipeline.repository_preflight(repo, publication, assembly, config, report)
            checks = self._checks(report)

            self.assertEqual(checks["AUTHORED_SOURCE_HASHES"]["status"], "ERROR")
            self.assertEqual(checks["SOURCE_CORPUS_INTEGRITY"]["status"], "ERROR")
            self.assertEqual(report["status"], "FAIL")

    def test_uncommitted_authored_change_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo, authored, publication, assembly, config = self._fixture(Path(td) / "repo")
            authored.write_bytes(b"# Rules\nDirty worktree.\n")

            report = new_report()
            pipeline.repository_preflight(repo, publication, assembly, config, report)
            checks = self._checks(report)

            self.assertEqual(checks["AUTHORED_SOURCE_GIT_STATE"]["status"], "ERROR")
            self.assertEqual(checks["SOURCE_CORPUS_INTEGRITY"]["status"], "ERROR")
            self.assertEqual(report["status"], "FAIL")

    def test_staged_authored_change_fails_even_if_worktree_matches_head(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo, authored, publication, assembly, config = self._fixture(Path(td) / "repo")
            authored.write_bytes(b"# Rules\nStaged change.\n")
            git(repo, "add", "rules.md")
            git(repo, "restore", "--worktree", "--source=HEAD", "--", "rules.md")

            report = new_report()
            pipeline.repository_preflight(repo, publication, assembly, config, report)
            checks = self._checks(report)

            self.assertEqual(checks["AUTHORED_SOURCE_GIT_STATE"]["status"], "ERROR")
            self.assertEqual(checks["SOURCE_CORPUS_INTEGRITY"]["status"], "ERROR")
            self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
