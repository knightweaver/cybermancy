from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_freeze_artifacts import (
    build_snapshot_change_summary,
    configure_assembly_markdown_consistency,
    refresh_publication_digest_provenance,
)


def _load_public_script(filename: str, module_name: str):
    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FreezeArtifactTests(unittest.TestCase):
    def test_snapshot_change_summary_replaces_stale_history_with_actual_delta(self) -> None:
        base = {
            "manifestVersion": "1.24",
            "repository": {"gitCommit": "old-commit"},
            "authorityDecisionFingerprint": "same-authority",
            "publicationInputs": {
                "authoredDocuments": [
                    {"id": "A047", "path": "docs/rules.md", "sha256": "old-sha"}
                ],
                "structuredFamilies": [
                    {
                        "id": "B001",
                        "generatorFamily": "adversaries",
                        "sourcePath": "src/packs/adversaries",
                        "contentDigestSha256": "same-digest",
                    }
                ],
            },
            "snapshotChangeSummary": {
                "previousManifestVersion": "1.17",
                "currentGitCommit": "stale-commit",
            },
        }
        current = {
            "manifestVersion": "1.25",
            "repository": {"gitCommit": "new-commit"},
            "authorityDecisionFingerprint": "same-authority",
            "publicationInputs": {
                "authoredDocuments": [
                    {"id": "A047", "path": "docs/rules.md", "sha256": "new-sha"}
                ],
                "structuredFamilies": [
                    {
                        "id": "B001",
                        "generatorFamily": "adversaries",
                        "sourcePath": "src/packs/adversaries",
                        "contentDigestSha256": "same-digest",
                    }
                ],
            },
        }

        summary = build_snapshot_change_summary(base, current)

        self.assertEqual(summary["previousManifestVersion"], "1.24")
        self.assertEqual(summary["previousGitCommit"], "old-commit")
        self.assertEqual(summary["currentGitCommit"], "new-commit")
        self.assertFalse(summary["authorityDecisionsChanged"])
        self.assertEqual(
            summary["authoredPublicationInputsChanged"],
            [
                {
                    "id": "A047",
                    "path": "docs/rules.md",
                    "fromSha256": "old-sha",
                    "toSha256": "new-sha",
                }
            ],
        )
        self.assertEqual(summary["structuredPublicationFamiliesChanged"], [])
        self.assertTrue(summary["publicationContentChanged"])

    def test_snapshot_change_summary_detects_structured_digest_change(self) -> None:
        base = {
            "manifestVersion": "1.24",
            "repository": {"gitCommit": "old"},
            "authorityDecisionFingerprint": "same",
            "publicationInputs": {
                "authoredDocuments": [],
                "structuredFamilies": [
                    {
                        "id": "B003",
                        "generatorFamily": "environments",
                        "sourcePath": "src/packs/environments",
                        "contentDigestSha256": "old-digest",
                    }
                ],
            },
        }
        current = {
            "manifestVersion": "1.25",
            "repository": {"gitCommit": "new"},
            "authorityDecisionFingerprint": "same",
            "publicationInputs": {
                "authoredDocuments": [],
                "structuredFamilies": [
                    {
                        "id": "B003",
                        "generatorFamily": "environments",
                        "sourcePath": "src/packs/environments",
                        "contentDigestSha256": "new-digest",
                    }
                ],
            },
        }

        summary = build_snapshot_change_summary(base, current)
        self.assertEqual(
            summary["structuredPublicationFamiliesChanged"],
            [
                {
                    "id": "B003",
                    "generatorFamily": "environments",
                    "sourcePath": "src/packs/environments",
                    "fromDigestSha256": "old-digest",
                    "toDigestSha256": "new-digest",
                }
            ],
        )
        self.assertTrue(summary["publicationContentChanged"])

    def test_digest_provenance_uses_current_version_without_stale_v3_text(self) -> None:
        manifest = {
            "supersedes": {"reason": "digest v3 stale text"},
            "publicationInputs": {
                "structuredFamilies": [
                    {
                        "generatorFamily": "weapons",
                        "contentDigestValidation": "v3 stale text",
                        "contentDigestAlgorithm": "digest-v4-description",
                    },
                    {
                        "generatorFamily": "adversaries",
                        "contentDigestValidation": "v3 stale text",
                        "contentDigestAlgorithm": "digest-v4-description",
                    },
                ]
            },
        }

        refresh_publication_digest_provenance(manifest, 4)

        reason = manifest["supersedes"]["reason"]
        self.assertIn("digest v4", reason)
        self.assertNotIn("v3", reason)
        for row in manifest["publicationInputs"]["structuredFamilies"]:
            validation = row["contentDigestValidation"]
            self.assertIn("at v4", validation)
            self.assertIn("contentDigestAlgorithm", validation)
            self.assertNotIn("v3", validation)

    def test_assembly_markdown_uses_configured_first_gm_chapter(self) -> None:
        namespace = {
            "ManifestError": RuntimeError,
            "build_markdown": lambda _manifest, _pub: (
                "The GM landing page is\n"
                "placed as GM-only front matter after the spoiler divider and before Chapter 24.\n"
            ),
        }
        configure_assembly_markdown_consistency(namespace)
        manifest = {
            "bookStructure": [
                {
                    "id": "part-v-gm-world",
                    "chapters": [{"id": "ch23-project-helios", "number": 23}],
                }
            ]
        }
        text = namespace["build_markdown"](manifest, {})
        self.assertIn("before Chapter 23.", text)
        self.assertNotIn("before Chapter 24.", text)

    def test_public_step3_wrapper_applies_markdown_consistency(self) -> None:
        builder = _load_public_script(
            "build-rulebook-assembly-manifest.py",
            "build_rulebook_assembly_manifest_freeze_test",
        )
        manifest = {
            "bookStructure": builder.BOOK_STRUCTURE,
            "authoredInputs": [],
            "structuredFamilies": [],
            "supersedes": {},
        }
        pub = {
            "manifestVersion": "1.25",
            "repository": {"gitCommit": "test"},
            "summary": {
                "includeRows": 0,
                "authoredPublicationInputs": 0,
                "structuredPublicationFamilies": 0,
                "structuredPublicationEntities": 0,
            },
        }
        text = builder.build_markdown(manifest, pub)
        self.assertIn("before Chapter 23.", text)
        self.assertNotIn("before Chapter 24.", text)


if __name__ == "__main__":
    unittest.main()
