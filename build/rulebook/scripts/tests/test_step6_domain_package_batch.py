import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
BATCH_CLI = SCRIPT_DIR / "build-rulebook-all-domain-packages.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package_batch import (
    discover_domain_package_targets,
    slugify_domain_name,
)


class TestStep6DomainPackageBatch(unittest.TestCase):
    def test_discovers_all_domain_packages_sorted_without_hard_coding(self):
        sidecar = {
            "domainSemantics": {"domainCount": 3, "cardCount": 6},
            "domainPackages": [
                {"domainKey": "maker", "name": "Maker", "cardCount": 3, "cards": ["m1", "m2", "m3"]},
                {"domainKey": "circuit", "name": "Circuit", "cardCount": 2, "cards": ["c1", "c2"]},
                {"domainKey": "bullet", "name": "Bullet", "cardCount": 1, "cards": ["b1"]},
            ],
        }

        targets = discover_domain_package_targets(sidecar)

        self.assertEqual(["Bullet", "Circuit", "Maker"], [row["name"] for row in targets])
        self.assertEqual(["bullet", "circuit", "maker"], [row["domainKey"] for row in targets])
        self.assertEqual([1, 2, 3], [row["cardCount"] for row in targets])
        self.assertEqual(
            "Cybermancy_Chapter14_Maker_DomainPackage_Step6",
            targets[2]["outputStem"],
        )

    def test_slug_is_deterministic(self):
        self.assertEqual("maker", slugify_domain_name("Maker"))
        self.assertEqual("signal-ghost", slugify_domain_name("Signal Ghost"))

    def test_rejects_duplicate_domain_key(self):
        with self.assertRaisesRegex(ValueError, "Duplicate DomainPackage domainKey"):
            discover_domain_package_targets(
                {
                    "domainPackages": [
                        {"domainKey": "maker", "name": "Maker", "cardCount": 0, "cards": []},
                        {"domainKey": "maker", "name": "Maker Two", "cardCount": 0, "cards": []},
                    ]
                }
            )

    def test_reconciles_step4_domain_semantics_totals(self):
        with self.assertRaisesRegex(ValueError, "domainSemantics.cardCount"):
            discover_domain_package_targets(
                {
                    "domainSemantics": {"domainCount": 1, "cardCount": 2},
                    "domainPackages": [
                        {"domainKey": "maker", "name": "Maker", "cardCount": 1, "cards": ["m1"]}
                    ],
                }
            )

    def _write_validate_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        source_root = root / "source"
        for rel in (
            "assets/icons/domains/maker.png",
            "assets/icons/domains/maker.svg",
            "assets/icons/domains/bullet.png",
            "assets/icons/domains/bullet.svg",
            "assets/cards/maker-alpha.png",
            "assets/cards/bullet-alpha.png",
        ):
            path = source_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("asset:" + rel).encode("utf-8"))

        def card(sid: str, name: str, domain: str, image: str):
            return {
                "semanticId": sid,
                "family": "domains",
                "sourceId": sid.rsplit(":", 1)[-1],
                "name": name,
                "publicationData": {
                    "description": f"{name} rules text.",
                    "domainKey": domain,
                    "level": 1,
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
                "domainCount": 2,
                "cardCount": 2,
            },
            "entities": [
                card("entity:domains:b", "Bullet Alpha", "bullet", "assets/cards/bullet-alpha.png"),
                card("entity:domains:m", "Maker Alpha", "maker", "assets/cards/maker-alpha.png"),
            ],
            "domainPackages": [
                {
                    "domainKey": "maker",
                    "name": "Maker",
                    "artwork": {
                        "image": "assets/icons/domains/maker.png",
                        "mask": "assets/icons/domains/maker.svg",
                    },
                    "cardCount": 1,
                    "cards": ["entity:domains:m"],
                    "levels": [{"level": 1, "cards": ["entity:domains:m"]}],
                },
                {
                    "domainKey": "bullet",
                    "name": "Bullet",
                    "artwork": {
                        "image": "assets/icons/domains/bullet.png",
                        "mask": "assets/icons/domains/bullet.svg",
                    },
                    "cardCount": 1,
                    "cards": ["entity:domains:b"],
                    "levels": [{"level": 1, "cards": ["entity:domains:b"]}],
                },
            ],
        }
        config = {
            "schema": "cybermancy-step6-domain-package-config-v1.0",
            "chapter": 14,
            "title": "Domains and Domain Cards",
            "prototype": {"domainKey": "maker"},
            "composition": {
                "kind": "domain-package",
                "pageColumns": 3,
                "defaultCardType": "ability",
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
        sidecar_path = root / "structured-entities.json"
        config_path = root / "domain-package-v1.json"
        sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return source_root, sidecar_path, config_path

    def test_batch_validate_dispatches_every_discovered_domain(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, sidecar_path, config_path = self._write_validate_fixture(root)
            aggregate = root / "all.json"
            report_dir = root / "reports"

            proc = subprocess.run(
                [
                    sys.executable,
                    str(BATCH_CLI),
                    "validate",
                    "--config",
                    str(config_path),
                    "--sidecar",
                    str(sidecar_path),
                    "--source-root",
                    str(source_root),
                    "--report",
                    str(aggregate),
                    "--report-dir",
                    str(report_dir),
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout, "build-rulebook-all-domain-packages.py: PASS\n")
            report = json.loads(aggregate.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["targetCount"], 2)
            self.assertEqual(report["cardCount"], 2)
            self.assertEqual(["Bullet", "Maker"], [row["name"] for row in report["domains"]])
            self.assertEqual(report["summary"], {"domains": 2, "cards": 2, "passed": 2, "failed": 0})
            self.assertTrue((report_dir / "bullet.json").is_file())
            self.assertTrue((report_dir / "maker.json").is_file())


if __name__ == "__main__":
    unittest.main()
