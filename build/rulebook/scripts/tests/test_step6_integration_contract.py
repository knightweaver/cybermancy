from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


RULEBOOK_DIR = Path(__file__).resolve().parents[2]
LAYOUT_DIR = RULEBOOK_DIR / "layout"
INTEGRATION = LAYOUT_DIR / "integration" / "step6-integration-v1.json"
SCRIPT_DIR = RULEBOOK_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounter_authority import count_authority_descriptor


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Step6IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(INTEGRATION)

    def test_profiles_and_reserved_chapter(self) -> None:
        complete = self.contract["profiles"]["complete-rulebook"]
        player = self.contract["profiles"]["player-guide"]
        self.assertEqual(
            complete["chapters"],
            [*range(1, 13), *range(14, 33)],
        )
        self.assertEqual(
            player["chapters"],
            [*range(1, 13), *range(14, 23)],
        )
        self.assertEqual(complete["audiences"], ["shared", "player", "gm"])
        self.assertEqual(player["audiences"], ["shared", "player"])
        self.assertNotIn(13, complete["chapters"])
        self.assertNotIn(13, player["chapters"])
        self.assertEqual(complete["gmDividerCount"], 1)
        self.assertEqual(player["gmDividerCount"], 0)
        reserved = self.contract["reservedChapters"]["13"]
        self.assertEqual(reserved["status"], "reserved")
        self.assertFalse(reserved["chapterNodeAllowed"])
        self.assertFalse(reserved["placeholderAllowed"])

    def test_structured_targets_are_unique_and_exact(self) -> None:
        targets = self.contract["structuredTargets"]
        chapters = [target["chapter"] for target in targets]
        self.assertEqual(len(chapters), len(set(chapters)))
        expected = {
            12: ["classes", "subclasses"],
            14: ["domains"],
            15: ["weapons"],
            16: ["ammo"],
            17: ["armors"],
            18: ["cybernetics"],
            19: ["drones-devices"],
            20: ["consumables"],
            21: ["mods"],
            22: ["loot"],
            29: ["features"],
            30: ["adversaries"],
            31: ["environments"],
            32: ["adversaries-features"],
        }
        self.assertEqual({target["chapter"]: target["families"] for target in targets}, expected)
        for target in targets:
            if target["chapter"] >= 29:
                self.assertEqual(target.get("profiles"), ["complete-rulebook"])

    def test_transformation_order(self) -> None:
        stages = self.contract["transformationOrder"]
        orders = [stage["order"] for stage in stages]
        self.assertEqual(orders, list(range(10, 171, 10)))
        self.assertEqual(len(orders), len(set(orders)))
        by_name = {stage["stage"]: stage for stage in stages}
        self.assertEqual(by_name["prose-player"]["chapters"], [1, 2, 3])
        self.assertEqual(by_name["rules"]["chapters"], [4, 5, 6, 7, 8, 9])
        self.assertEqual(by_name["character-origins"]["chapters"], [10, 11])
        self.assertEqual(by_name["classes"]["chapters"], [12])
        self.assertEqual(by_name["domains"]["chapters"], [14])
        self.assertEqual(by_name["equipment"]["chapters"], list(range(15, 23)))
        self.assertEqual(by_name["prose-gm"]["chapters"], list(range(23, 29)))

    def test_prose_contract_matches_current_architecture(self) -> None:
        prose = load_json(LAYOUT_DIR / "prose" / "prose-layout-v1.json")
        self.assertEqual(prose["validation"]["requiredChapters"], [1, 2, 3, 23, 24, 25, 26, 27, 28])
        self.assertEqual(prose["partOpener"]["rectoPolicy"], "preserve-current-clearpage")
        defects = {(item["chapter"], item["classification"]) for item in prose["knownSourceDefects"]}
        self.assertIn((24, "conversation-residue"), defects)
        self.assertNotIn((25, "conversation-residue"), defects)

    def test_class_and_domain_ast_targets(self) -> None:
        classes = load_json(LAYOUT_DIR / "classes" / "class-package-v1.json")
        domains = load_json(LAYOUT_DIR / "domains" / "domain-package-v1.json")
        self.assertEqual(classes["chapter"], 12)
        self.assertEqual(
            classes["prototypePolicy"]["astIntegration"],
            "chapter12-family-classes-subclasses-replacement",
        )
        self.assertEqual(domains["chapter"], 14)
        self.assertEqual(
            domains["prototypePolicy"]["astIntegration"],
            "chapter14-family-domains-replacement",
        )

    def test_equipment_registry_and_configs(self) -> None:
        registry = load_json(LAYOUT_DIR / "equipment" / "equipment-section-v1.json")
        expected = [
            (15, "weapons", "weapons-v1.json", 47),
            (16, "ammo", "ammo-v1.json", 13),
            (17, "armors", "armors-v1.json", 36),
            (18, "cybernetics", "cybernetics-v1.json", 103),
            (19, "drones-devices", "drones-devices-v1.json", 19),
            (20, "consumables", "consumables-v1.json", 59),
            (21, "mods", "mods-v1.json", 20),
            (22, "loot", "loot-v1.json", 60),
        ]
        self.assertEqual(
            [(item["chapter"], item["family"], item["config"]) for item in registry["families"]],
            [(chapter, family, config) for chapter, family, config, _ in expected],
        )
        for chapter, family, config_name, expected_count in expected:
            config = load_json(LAYOUT_DIR / "equipment" / config_name)
            self.assertEqual(config["chapter"], chapter, family)
            self.assertEqual(config["family"], family)
            self.assertEqual(config["expectedEntityCount"], expected_count)
            if family not in {"weapons", "ammo"}:
                self.assertEqual(config.get("configStatus"), "accepted", family)
            stem = config.get("outputStem")
            if stem:
                self.assertIn(f"Chapter{chapter}", stem, family)

    def test_frozen_corpus_counts(self) -> None:
        regression = self.contract["regressionExpectations"]

        origins = load_json(
            LAYOUT_DIR / "character-origins" / "character-origins-layout-v1.json"
        )
        origin_counts = origins["freeze"]["acceptanceCorpus"]
        self.assertEqual(origin_counts["ancestories"], regression["characterOrigins"]["ancestories"])
        self.assertEqual(origin_counts["communities"], regression["characterOrigins"]["communities"])
        self.assertEqual(origin_counts["stagedArtwork"], regression["characterOrigins"]["artwork"])

        domains = load_json(LAYOUT_DIR / "domains" / "domain-package-v1.json")
        domain_counts = domains["lifecycle"]["acceptance"]
        self.assertEqual(domain_counts["domainCount"], regression["domains"]["domains"])
        self.assertEqual(domain_counts["cardCount"], regression["domains"]["cards"])

        ice = load_json(LAYOUT_DIR / "ice" / "ice-reference-package-v1.json")
        self.assertEqual(ice["publicationPolicy"]["expectedIceTotal"], regression["ice"]["entries"])

        adversaries = load_json(LAYOUT_DIR / "encounters" / "adversary-package-v1.json")
        environments = load_json(LAYOUT_DIR / "encounters" / "environment-package-v1.json")
        features = load_json(LAYOUT_DIR / "encounters" / "adversary-feature-reference-v1.json")

        for family, config in (
            ("adversaries", adversaries),
            ("environments", environments),
        ):
            descriptor = count_authority_descriptor(family)
            self.assertEqual(regression[family]["countAuthority"], descriptor)
            self.assertEqual(config["publicationPolicy"]["countAuthority"], descriptor)
            self.assertNotIn("entries", regression[family])
            self.assertNotIn("expectedEntryCount", config["publicationPolicy"])
            self.assertTrue(config["publicationPolicy"]["requireFullCorpusSelection"])
            self.assertEqual(config["selection"]["mode"], "full-corpus")
            self.assertEqual(config["fastPlayPolicy"], "render structured Fast Play only when present")

        self.assertEqual(
            adversaries["publicationPolicy"]["ordering"],
            ["normalized-name", "semanticId"],
        )
        self.assertEqual(
            environments["publicationPolicy"]["ordering"],
            ["tier", "classification", "name", "semanticId"],
        )

        self.assertEqual(adversaries["lifecycle"]["version"], "v1.1")
        self.assertEqual(environments["lifecycle"]["version"], "v1.0")
        self.assertEqual(
            features["publicationPolicy"]["expectedEntryCount"],
            regression["adversaryFeatures"]["publishedRepresentatives"],
        )
        self.assertEqual(
            features["publicationPolicy"]["canonicalSourceEntryCount"],
            regression["adversaryFeatures"]["canonicalSourceEntries"],
        )

    def test_encounter_routes_remain_frozen(self) -> None:
        chapter_map = {row["chapter"]: row for row in self.contract["chapterMap"]}
        targets = {row["chapter"]: row for row in self.contract["structuredTargets"]}
        for chapter, family, adapter in (
            (30, "adversaries", "adversary-package"),
            (31, "environments", "environment-package"),
        ):
            self.assertEqual(chapter_map[chapter]["audience"], "gm")
            self.assertEqual(targets[chapter]["families"], [family])
            self.assertEqual(targets[chapter]["adapter"], adapter)
            self.assertEqual(targets[chapter]["profiles"], ["complete-rulebook"])

    def test_integration_policies(self) -> None:
        policies = self.contract["integrationPolicies"]
        self.assertTrue(policies["oneBasePandocAstPerProfile"])
        self.assertTrue(policies["semanticReplacementBeforeShellLowering"])
        self.assertTrue(policies["failClosed"])
        self.assertTrue(policies["preserveFrozenPackageGrammar"])
        self.assertEqual(policies["rectoPolicy"], "preserve-current-clearpage")
        self.assertFalse(policies["generatedArtifactsCanonical"])


if __name__ == "__main__":
    unittest.main()
