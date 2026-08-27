import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
DOMAIN_PACKAGE_CLI = SCRIPT_DIR / "build-rulebook-domain-package.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package import compose_domain_package


class TestStep6DomainPackage(unittest.TestCase):
    def _fixture(self, root: Path):
        source_root = root / "build/rulebook/source"
        for rel in (
            "assets/cards/alpha.webp",
            "assets/cards/beta.webp",
            "assets/cards/gamma.webp",
            "assets/icons/domains/maker.png",
            "assets/icons/domains/maker.svg",
        ):
            path = source_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("asset:" + rel).encode("utf-8"))

        def card(
            semantic_id,
            name,
            level,
            image,
            *,
            source_id=None,
            domain_key="maker",
            family="domains",
            description="Useful rules text.",
        ):
            return {
                "semanticId": semantic_id,
                "family": family,
                "sourceId": source_id or semantic_id.rsplit(":", 1)[-1],
                "name": name,
                "audience": "player",
                "sourcePath": f"src/packs/system/domains/{name}.json",
                "publicationData": {
                    "description": description,
                    "domainKey": domain_key,
                    "level": level,
                    "recallCost": 1,
                    "cardType": "ability",
                    "inVault": False,
                    "image": image,
                },
            }

        sidecar = {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "domainSemantics": {
                "schema": "cybermancy-step4-domain-semantics-v1.0",
                "status": "PASS",
                "domainCount": 3,
                "cardCount": 73,
            },
            "entities": [
                card(
                    "entity:domains:a",
                    "Alpha",
                    1,
                    "assets/cards/alpha.webp",
                    source_id="a",
                ),
                card(
                    "entity:domains:b",
                    "Beta",
                    1,
                    "assets/cards/beta.webp",
                    source_id="b",
                ),
                card(
                    "entity:domains:c",
                    "Gamma",
                    2,
                    "assets/cards/gamma.webp",
                    source_id="c",
                ),
            ],
            "domainPackages": [
                {
                    "domainKey": "maker",
                    "name": "Maker",
                    "artwork": {
                        "image": "assets/icons/domains/maker.png",
                        "mask": "assets/icons/domains/maker.svg",
                    },
                    "cardCount": 3,
                    "cards": [
                        "entity:domains:a",
                        "entity:domains:b",
                        "entity:domains:c",
                    ],
                    "levels": [
                        {
                            "level": 1,
                            "cards": [
                                "entity:domains:a",
                                "entity:domains:b",
                            ],
                        },
                        {
                            "level": 2,
                            "cards": [
                                "entity:domains:c",
                            ],
                        },
                    ],
                }
            ],
        }

        config = {
            "schema": "cybermancy-step6-domain-package-config-v1.0",
            "chapter": 14,
            "title": "Domains and Domain Cards",
            "prototype": {"domainKey": "maker"},
            "prototypePolicy": {
                "consumeStep4Only": True,
                "requireStructuredSidecarSchema": "cybermancy-step4-structured-entities-v1.3",
                "requireDomainSemanticsSchema": "cybermancy-step4-domain-semantics-v1.0",
                "requireStagedImages": True,
                "requireCardDescription": True,
                "failOnRawSourceReferences": True,
            },
        }
        return source_root, sidecar, config

    def test_valid_maker_composition(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            view, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "PASS")
            self.assertIsNotNone(view)
            self.assertEqual(view["schema"], "cybermancy-step6-domain-package-view-v1.0")
            self.assertEqual(view["domain"]["name"], "Maker")
            self.assertEqual(view["domain"]["cardCount"], 3)
            self.assertEqual([row["level"] for row in view["levels"]], [1, 2])
            self.assertEqual(
                [card["name"] for row in view["levels"] for card in row["cards"]],
                ["Alpha", "Beta", "Gamma"],
            )
            raw = json.dumps(view)
            for token in ("Compendium.", "modules/", "worlds/", "docs/", "src/packs/", "!folders!"):
                self.assertNotIn(token, raw)

    def test_duplicate_semantic_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["entities"].append(copy.deepcopy(sidecar["entities"][0]))

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_ENTITY_IDENTITY", {item["code"] for item in report["errors"]})

    def test_wrong_family_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["entities"][0]["family"] = "features"

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_REFERENCE_FAMILY", {item["code"] for item in report["errors"]})

    def test_domain_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["entities"][0]["publicationData"]["domainKey"] = "bullet"

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_CARD_DOMAIN", {item["code"] for item in report["errors"]})

    def test_level_bucket_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["domainPackages"][0]["levels"][0]["cards"] = ["entity:domains:b"]
            sidecar["domainPackages"][0]["levels"][1]["cards"] = [
                "entity:domains:a",
                "entity:domains:c",
            ]

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_LEVEL_MISMATCH", {item["code"] for item in report["errors"]})

    def test_missing_staged_card_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            (source_root / "assets/cards/beta.webp").unlink()

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_ASSET", {item["code"] for item in report["errors"]})

    def test_card_order_contract_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["domainPackages"][0]["cards"][0:2] = [
                "entity:domains:b",
                "entity:domains:a",
            ]
            sidecar["domainPackages"][0]["levels"][0]["cards"] = [
                "entity:domains:b",
                "entity:domains:a",
            ]

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_CARD_ORDER", {item["code"] for item in report["errors"]})

    def test_source_leakage_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["entities"][0]["publicationData"]["description"] = "See Compendium.cybermancy.foo"

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_NO_SOURCE_LEAKAGE", {item["code"] for item in report["errors"]})

    def test_unsupported_domain_semantics_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            sidecar["domainSemantics"]["schema"] = "obsolete"

            _, report = compose_domain_package(sidecar, source_root, "maker", config)

            self.assertEqual(report["status"], "FAIL")
            self.assertIn("DOMAIN_PACKAGE_DOMAIN_SEMANTICS", {item["code"] for item in report["errors"]})

    def test_cli_defaults_to_terse_pass_and_verbose_can_follow_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, sidecar, config = self._fixture(root)
            config_path = root / "config.json"
            sidecar_path = root / "structured-entities.json"
            report_path = root / "report.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")

            base = [
                sys.executable,
                str(DOMAIN_PACKAGE_CLI),
                "validate",
                "--config",
                str(config_path),
                "--sidecar",
                str(sidecar_path),
                "--source-root",
                str(source_root),
                "--report",
                str(report_path),
            ]
            terse = subprocess.run(base, text=True, capture_output=True)
            self.assertEqual(terse.returncode, 0, terse.stdout + terse.stderr)
            self.assertEqual(terse.stdout, "build-rulebook-domain-package.py: PASS\n")
            self.assertTrue(report_path.is_file())

            verbose = subprocess.run(
                base[:3] + ["--verbose"] + base[3:],
                text=True,
                capture_output=True,
            )
            self.assertEqual(verbose.returncode, 0, verbose.stdout + verbose.stderr)
            self.assertIn('"status": "PASS"', verbose.stdout)
            self.assertIn('"domainKey": "maker"', verbose.stdout)


if __name__ == "__main__":
    unittest.main()
