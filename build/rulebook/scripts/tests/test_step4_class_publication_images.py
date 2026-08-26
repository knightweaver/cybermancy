import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_normalize.assets import resolve_publication_source_asset
from rulebook_normalize.validate import add_check, new_report
from rulebook_step4_class_publication_images import (
    PUBLICATION_IMAGE_SCHEMA,
    _postprocess_publication_images,
)


class TestClassPublicationImages(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        image_reference: str,
        create_asset: bool = True,
        *,
        audience: str = "player",
        asset_root: str = "docs/player-facing",
    ):
        repo = root / "repo"
        outroot = root / "build" / "rulebook"
        metadata = outroot / "source" / "metadata"
        metadata.mkdir(parents=True)

        source_rel = "src/packs/system/classes/Test_Class_c1.json"
        source = repo / source_rel
        source.parent.mkdir(parents=True)
        source.write_text(
            json.dumps(
                {
                    "name": "Test Class",
                    "type": "class",
                    "_id": "c1",
                    "img": image_reference,
                    "system": {},
                }
            ),
            encoding="utf-8",
        )

        if create_asset:
            asset = repo / asset_root / "assets" / "icons" / "classes" / "test-class.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"class-publication-art")

        (metadata / "structured-entities.json").write_text(
            json.dumps(
                {
                    "schema": "cybermancy-step4-structured-entities-v1.3",
                    "entities": [
                        {
                            "semanticId": "entity:classes:c1",
                            "family": "classes",
                            "sourceId": "c1",
                            "name": "Test Class",
                            "audience": audience,
                            "sourcePath": source_rel,
                            "publicationData": {"description": "Test."},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (metadata / "assets.json").write_text("[]\n", encoding="utf-8")

        config = {
            "assets": {
                "foundryRuntimeMappings": [
                    {"prefix": "modules/cybermancy/", "repoPrefix": ""},
                    {"prefix": "worlds/cybermancer/", "repoPrefix": ""},
                ]
            }
        }
        return repo, outroot, metadata, config

    def test_player_docs_image_is_promoted_to_staged_step4_publication_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, outroot, metadata, config = self._fixture(
                root,
                "modules/cybermancy/assets/icons/classes/test-class.png",
            )
            report = new_report()

            _postprocess_publication_images(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            entity = sidecar["entities"][0]
            self.assertEqual(
                entity["publicationData"]["image"],
                "assets/icons/classes/test-class.png",
            )
            self.assertNotIn(
                "modules/cybermancy/",
                json.dumps(entity["publicationData"]),
            )
            self.assertNotIn(
                "docs/player-facing/",
                json.dumps(entity["publicationData"]),
            )
            self.assertEqual(
                sidecar["publicationImageSemantics"]["schema"],
                PUBLICATION_IMAGE_SCHEMA,
            )
            self.assertEqual(sidecar["publicationImageSemantics"]["status"], "PASS")

            staged = outroot / "source" / "assets" / "icons" / "classes" / "test-class.png"
            self.assertTrue(staged.is_file())
            self.assertEqual(staged.read_bytes(), b"class-publication-art")

            asset_rows = json.loads((metadata / "assets.json").read_text(encoding="utf-8"))
            promoted = [row for row in asset_rows if row.get("kind") == "structured-publication-image"]
            self.assertEqual(len(promoted), 1)
            self.assertEqual(promoted[0]["reference"], "assets/icons/classes/test-class.png")
            self.assertEqual(
                promoted[0]["sourceRepoPath"],
                "docs/player-facing/assets/icons/classes/test-class.png",
            )
            self.assertEqual(
                promoted[0]["sourceReference"],
                "modules/cybermancy/assets/icons/classes/test-class.png",
            )

            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["CLASS_PUBLICATION_IMAGES"]["status"], "PASS")

    def test_missing_audience_asset_fails_closed_and_does_not_publish_raw_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, outroot, metadata, config = self._fixture(
                root,
                "modules/cybermancy/assets/icons/classes/missing.png",
                create_asset=False,
            )
            report = new_report()

            _postprocess_publication_images(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            entity = sidecar["entities"][0]
            self.assertNotIn("image", entity["publicationData"])
            self.assertEqual(sidecar["publicationImageSemantics"]["status"], "FAIL")

            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["CLASS_PUBLICATION_IMAGES"]["status"], "ERROR")
            issues = checks["CLASS_PUBLICATION_IMAGES"]["details"]
            self.assertIn("CLASS_PUBLICATION_IMAGE_MISSING", {issue["code"] for issue in issues})
            missing = next(issue for issue in issues if issue["code"] == "CLASS_PUBLICATION_IMAGE_MISSING")
            self.assertIn(
                "docs/player-facing/assets/icons/classes/missing.png",
                missing["resolution"]["candidates"],
            )

    def test_remote_class_art_is_rejected_because_step4_cannot_stage_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, outroot, metadata, config = self._fixture(
                root,
                "https://example.com/class.png",
                create_asset=False,
            )
            report = new_report()

            _postprocess_publication_images(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            self.assertNotIn("image", sidecar["entities"][0]["publicationData"])
            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["CLASS_PUBLICATION_IMAGES"]["status"], "ERROR")

    def test_generic_resolver_honors_gm_docs_root(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            asset = repo / "docs/gm-facing/assets/icons/adversaries/test.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"gm-art")

            resolved = resolve_publication_source_asset(
                repo,
                "assets/icons/adversaries/test.png",
                "gm",
            )

            self.assertEqual(resolved["status"], "resolved")
            self.assertEqual(
                resolved["sourceRepoPath"],
                "docs/gm-facing/assets/icons/adversaries/test.png",
            )

    def test_audience_docs_source_overrides_conflicting_legacy_root_copy(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            direct = repo / "assets/icons/classes/test-class.png"
            docs = repo / "docs/player-facing/assets/icons/classes/test-class.png"
            direct.parent.mkdir(parents=True)
            docs.parent.mkdir(parents=True)
            direct.write_bytes(b"old-copy")
            docs.write_bytes(b"publication-copy")

            resolved = resolve_publication_source_asset(
                repo,
                "assets/icons/classes/test-class.png",
                "player",
            )

            self.assertEqual(resolved["status"], "resolved")
            self.assertEqual(
                resolved["sourceRepoPath"],
                "docs/player-facing/assets/icons/classes/test-class.png",
            )
            self.assertEqual(resolved["authorityPriority"], 0)

    def test_legacy_root_copy_remains_fallback_when_docs_asset_is_absent(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            direct = repo / "assets/icons/classes/test-class.png"
            direct.parent.mkdir(parents=True)
            direct.write_bytes(b"legacy-only")

            resolved = resolve_publication_source_asset(
                repo,
                "assets/icons/classes/test-class.png",
                "player",
            )

            self.assertEqual(resolved["status"], "resolved")
            self.assertEqual(
                resolved["sourceRepoPath"],
                "assets/icons/classes/test-class.png",
            )
            self.assertEqual(resolved["authorityPriority"], 2)

    def test_shared_cross_audience_conflict_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            player = repo / "docs/player-facing/assets/icons/shared/test.png"
            gm = repo / "docs/gm-facing/assets/icons/shared/test.png"
            player.parent.mkdir(parents=True)
            gm.parent.mkdir(parents=True)
            player.write_bytes(b"player-copy")
            gm.write_bytes(b"gm-copy")

            resolved = resolve_publication_source_asset(
                repo,
                "assets/icons/shared/test.png",
                "shared",
            )

            self.assertEqual(resolved["status"], "ambiguous")
            self.assertEqual(len(resolved["existing"]), 2)
            self.assertEqual(resolved["authorityPriority"], 1)


if __name__ == "__main__":
    unittest.main()
