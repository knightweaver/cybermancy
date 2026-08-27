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
from rulebook_step4_domain_semantics import (
    DOMAIN_SEMANTICS_SCHEMA,
    _postprocess_domain_semantics,
)


class TestDomainSemantics(unittest.TestCase):
    def _fixture(self, root: Path, *, domain: str = "maker", level: int = 3):
        repo = root / "repo"
        outroot = root / "build" / "rulebook"
        metadata = outroot / "source" / "metadata"
        metadata.mkdir(parents=True)

        source_dir = repo / "src" / "packs" / "system" / "domains"
        source_dir.mkdir(parents=True)
        source_rel = "src/packs/system/domains/Test_Card_card1.json"
        (repo / source_rel).write_text(
            json.dumps(
                {
                    "name": "Test Card",
                    "type": "domainCard",
                    "_id": "card1",
                    "folder": "level3",
                    "img": "modules/cybermancy/assets/icons/domains/maker/test-card.webp",
                    "system": {
                        "description": "Test rules.",
                        "domain": domain,
                        "level": level,
                        "recallCost": 1,
                        "type": "ability",
                        "inVault": False,
                    },
                }
            ),
            encoding="utf-8",
        )

        (source_dir / "Maker_folder.json").write_text(
            json.dumps(
                {
                    "type": "Item",
                    "folder": None,
                    "name": "Maker",
                    "_id": "makerFolder",
                    "_key": "!folders!makerFolder",
                }
            ),
            encoding="utf-8",
        )
        (source_dir / "3_folder.json").write_text(
            json.dumps(
                {
                    "type": "Item",
                    "folder": "makerFolder",
                    "name": "3",
                    "_id": "level3",
                    "_key": "!folders!level3",
                }
            ),
            encoding="utf-8",
        )

        card_art = repo / "assets" / "icons" / "domains" / "maker" / "test-card.webp"
        card_art.parent.mkdir(parents=True)
        card_art.write_bytes(b"card-art")

        for key in ("bullet", "circuit", "maker"):
            for suffix, payload in (("png", b"domain-png"), ("svg", b"<svg/>")):
                path = repo / "assets" / "icons" / "domains" / f"{key}.{suffix}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload + key.encode("utf-8"))

        (metadata / "structured-entities.json").write_text(
            json.dumps(
                {
                    "schema": "cybermancy-step4-structured-entities-v1.3",
                    "entities": [
                        {
                            "semanticId": "entity:domains:card1",
                            "family": "domains",
                            "sourceId": "card1",
                            "name": "Test Card",
                            "audience": "player",
                            "sourcePath": source_rel,
                            "publicationData": {"description": "Test rules."},
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

    def test_domain_card_semantics_and_domain_package_are_materialized(self):
        with tempfile.TemporaryDirectory() as td:
            repo, outroot, metadata, config = self._fixture(Path(td))
            report = new_report()

            _postprocess_domain_semantics(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            entity = sidecar["entities"][0]
            pdata = entity["publicationData"]
            self.assertEqual(pdata["domainKey"], "maker")
            self.assertEqual(pdata["level"], 3)
            self.assertEqual(pdata["recallCost"], 1)
            self.assertEqual(pdata["cardType"], "ability")
            self.assertFalse(pdata["inVault"])
            self.assertEqual(
                pdata["image"],
                "assets/icons/domains/maker/test-card.webp",
            )

            self.assertEqual(sidecar["domainSemantics"]["schema"], DOMAIN_SEMANTICS_SCHEMA)
            self.assertEqual(sidecar["domainSemantics"]["status"], "PASS")
            self.assertEqual(sidecar["domainSemantics"]["cardCount"], 1)

            packages = sidecar["domainPackages"]
            self.assertEqual(len(packages), 1)
            package = packages[0]
            self.assertEqual(package["domainKey"], "maker")
            self.assertEqual(package["name"], "Maker")
            self.assertEqual(package["cards"], ["entity:domains:card1"])
            self.assertEqual(
                package["levels"],
                [{"level": 3, "cards": ["entity:domains:card1"]}],
            )
            self.assertEqual(package["artwork"]["image"], "assets/icons/domains/maker.png")
            self.assertEqual(package["artwork"]["mask"], "assets/icons/domains/maker.svg")

            self.assertTrue(
                (outroot / "source" / "assets" / "icons" / "domains" / "maker.png").is_file()
            )
            self.assertTrue(
                (outroot / "source" / "assets" / "icons" / "domains" / "maker.svg").is_file()
            )
            self.assertTrue(
                (
                    outroot
                    / "source"
                    / "assets"
                    / "icons"
                    / "domains"
                    / "maker"
                    / "test-card.webp"
                ).is_file()
            )

            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["DOMAIN_PUBLICATION_SEMANTICS"]["status"], "PASS")
            self.assertEqual(checks["DOMAIN_FOLDER_CROSSCHECK"]["status"], "PASS")

    def test_folder_mismatch_is_warning_but_intrinsic_semantics_remain_authoritative(self):
        with tempfile.TemporaryDirectory() as td:
            repo, outroot, metadata, config = self._fixture(Path(td))
            level_folder = repo / "src" / "packs" / "system" / "domains" / "3_folder.json"
            data = json.loads(level_folder.read_text(encoding="utf-8"))
            data["name"] = "4"
            level_folder.write_text(json.dumps(data), encoding="utf-8")

            report = new_report()
            _postprocess_domain_semantics(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["entities"][0]["publicationData"]["level"], 3)
            self.assertEqual(report["status"], "PASS")
            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["DOMAIN_FOLDER_CROSSCHECK"]["status"], "WARNING")
            issue_codes = {item["code"] for item in checks["DOMAIN_FOLDER_CROSSCHECK"]["details"]}
            self.assertIn("DOMAIN_FOLDER_LEVEL_MISMATCH", issue_codes)

    def test_unknown_intrinsic_domain_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo, outroot, metadata, config = self._fixture(Path(td), domain="unknown")
            report = new_report()

            _postprocess_domain_semantics(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["domainSemantics"]["status"], "FAIL")
            self.assertEqual(report["status"], "FAIL")
            checks = {item["code"]: item for item in report["checks"]}
            issues = checks["DOMAIN_PUBLICATION_SEMANTICS"]["details"]
            self.assertIn("DOMAIN_KEY_INVALID", {item["code"] for item in issues})


if __name__ == "__main__":
    unittest.main()
