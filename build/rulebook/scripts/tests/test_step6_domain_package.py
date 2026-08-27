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
from rulebook_layout.domain_package_geometry import PdfLine, evaluate_domain_package_geometry
from rulebook_layout.domain_package_refined import render_domain_package_tex
from rulebook_layout.render_assets import prepare_lualatex_render_assets

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised as a skip on minimal environments.
    Image = None


class TestStep6DomainPackage(unittest.TestCase):
    def _fixture(self, root: Path):
        source_root = root / "build/rulebook/source"
        for rel in (
            "assets/cards/alpha.png",
            "assets/cards/beta.png",
            "assets/cards/gamma.png",
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
            description=None,
        ):
            description = (
                description
                if description is not None
                else f"{name} rules text begins here and continues with enough detail for a second rendered line."
            )
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
                    "assets/cards/alpha.png",
                    source_id="a",
                ),
                card(
                    "entity:domains:b",
                    "Beta",
                    1,
                    "assets/cards/beta.png",
                    source_id="b",
                ),
                card(
                    "entity:domains:c",
                    "Gamma",
                    2,
                    "assets/cards/gamma.png",
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
            "partLabel": "CHARACTER OPTIONS",
            "title": "Domains and Domain Cards",
            "prototype": {"domainKey": "maker"},
            "composition": {
                "kind": "domain-package",
                "pageColumns": 2,
                "defaultCardType": "ability",
            },
            "style": {
                "cardBodyFontPt": 9.0,
                "cardBodyLeadingPt": 11.3,
                "levelMinStartSpaceIn": 2.65,
            },
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
            (source_root / "assets/cards/beta.png").unlink()
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

    def test_renderer_uses_two_column_level_grammar_and_step4_assets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, sidecar, config = self._fixture(root)
            output_dir = root / "build/rulebook/layout/domain-package-prototype"
            output_dir.mkdir(parents=True)
            view, report = compose_domain_package(sidecar, source_root, "maker", config)
            self.assertEqual(report["status"], "PASS")

            tex = render_domain_package_tex(view, config, source_root, output_dir)

            self.assertIn("MAKER", tex)
            self.assertIn("LEVEL 1", tex)
            self.assertIn("LEVEL 2", tex)
            self.assertIn("Alpha", tex)
            self.assertIn("Beta", tex)
            self.assertIn("Gamma", tex)
            self.assertIn("RECALL COST 1", tex)
            self.assertIn(r"\begin{multicols}{2}", tex)
            self.assertIn("alpha.png", tex)
            self.assertNotIn("src/packs", tex)
            self.assertNotIn("modules/cybermancy", tex)

    def test_rendered_geometry_contract_checks_columns_levels_and_recall(self):
        with tempfile.TemporaryDirectory() as td:
            source_root, sidecar, config = self._fixture(Path(td))
            view, report = compose_domain_package(sidecar, source_root, "maker", config)
            self.assertEqual(report["status"], "PASS")

            lines = [
                PdfLine(1, "LEVEL 1", 40, 100, 100, 115),
                PdfLine(1, "Alpha", 110, 150, 160, 165),
                PdfLine(1, "LEVEL 1 • RECALL COST 1", 110, 170, 230, 180),
                PdfLine(1, "Alpha rules text begins here and", 40, 205.0, 260, 215),
                PdfLine(1, "continues with enough detail for", 40, 216.3, 260, 226),
                PdfLine(1, "a second rendered line.", 40, 227.6, 210, 237),
                PdfLine(1, "Beta", 385, 150, 430, 165),
                PdfLine(1, "LEVEL 1 • RECALL COST 1", 385, 170, 505, 180),
                PdfLine(1, "Beta rules text begins here and", 315, 205.0, 535, 215),
                PdfLine(1, "continues with enough detail for", 315, 216.3, 535, 226),
                PdfLine(1, "a second rendered line.", 315, 227.6, 485, 237),
                PdfLine(1, "LEVEL 2", 40, 350, 100, 365),
                PdfLine(1, "Gamma", 110, 400, 165, 415),
                PdfLine(1, "LEVEL 2 • RECALL COST 1", 110, 420, 230, 430),
                PdfLine(1, "Gamma rules text begins here and", 40, 455.0, 270, 465),
                PdfLine(1, "continues with enough detail for", 40, 466.3, 260, 476),
                PdfLine(1, "a second rendered line.", 40, 477.6, 210, 487),
            ]
            geometry = evaluate_domain_package_geometry(lines, view, config)
            self.assertEqual(geometry["status"], "PASS", geometry)
            self.assertEqual(geometry["details"]["columnStarts"], [110, 385])
            self.assertEqual([row["level"] for row in geometry["details"]["levelHeadings"]], [1, 2])

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

    def test_cli_build_tex_only_writes_visual_prototype_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, sidecar, config = self._fixture(root)
            config_path = root / "config.json"
            sidecar_path = root / "structured-entities.json"
            report_path = root / "report.json"
            output_dir = root / "prototype"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(DOMAIN_PACKAGE_CLI),
                    "build",
                    "--tex-only",
                    "--config",
                    str(config_path),
                    "--sidecar",
                    str(sidecar_path),
                    "--source-root",
                    str(source_root),
                    "--output-dir",
                    str(output_dir),
                    "--report",
                    str(report_path),
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout, "build-rulebook-domain-package.py: PASS\n")
            self.assertTrue((output_dir / "maker-domain-package-view.json").is_file())
            self.assertTrue(
                (output_dir / "Cybermancy_Chapter14_Maker_DomainPackage_Step6.tex").is_file()
            )
            self.assertTrue(report_path.is_file())

    @unittest.skipIf(Image is None, "Pillow is not installed")
    def test_render_asset_preparation_converts_webp_without_mutating_step4_assets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "source"
            webp_path = source_root / "assets/cards/domain-card.webp"
            png_path = source_root / "assets/icons/domains/maker.png"
            webp_path.parent.mkdir(parents=True)
            png_path.parent.mkdir(parents=True)
            Image.new("RGB", (24, 24), (100, 120, 140)).save(webp_path, format="WEBP")
            Image.new("RGB", (24, 24), (20, 40, 60)).save(png_path, format="PNG")
            original_webp = webp_path.read_bytes()

            mapping, details = prepare_lualatex_render_assets(
                ["assets/cards/domain-card.webp", "assets/icons/domains/maker.png"],
                source_root,
                root / "render",
            )

            self.assertEqual(details["status"], "PASS", details)
            self.assertEqual(details["converted"], 1)
            self.assertEqual(details["direct"], 1)
            converted = Path(mapping["assets/cards/domain-card.webp"])
            self.assertEqual(converted.suffix.lower(), ".png")
            self.assertTrue(converted.is_file())
            self.assertEqual(webp_path.read_bytes(), original_webp)
            self.assertEqual(mapping["assets/icons/domains/maker.png"], str(png_path.resolve()))


if __name__ == "__main__":
    unittest.main()
