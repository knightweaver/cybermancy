import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_normalize.validate import add_check, new_report
from rulebook_step4_class_publication_images import (
    PUBLICATION_IMAGE_SCHEMA,
    _postprocess_publication_images,
)


class TestClassPublicationImages(unittest.TestCase):
    def _fixture(self, root: Path, image_reference: str, create_asset: bool = True):
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
            asset = repo / "assets" / "icons" / "classes" / "test-class.png"
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
                            "audience": "player",
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

    def test_foundry_image_is_promoted_to_staged_step4_publication_path(self):
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
                promoted[0]["sourceReference"],
                "modules/cybermancy/assets/icons/classes/test-class.png",
            )

            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["CLASS_PUBLICATION_IMAGES"]["status"], "PASS")

    def test_missing_mapped_asset_fails_closed_and_does_not_publish_raw_path(self):
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
            self.assertIn(
                "CLASS_PUBLICATION_IMAGE_MISSING",
                {issue["code"] for issue in checks["CLASS_PUBLICATION_IMAGES"]["details"]},
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


if __name__ == "__main__":
    unittest.main()
