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
from rulebook_step4_encounter_semantics import (
    ENCOUNTER_CORPUS_SCHEMA,
    ENCOUNTER_SEMANTICS_SCHEMA,
    _postprocess_encounter_semantics,
)


class TestEncounterSemantics(unittest.TestCase):
    def _fixture(self, root: Path):
        repo = root / "repo"
        outroot = root / "build" / "rulebook"
        metadata = outroot / "source" / "metadata"
        metadata.mkdir(parents=True)

        adversary_id = "ADV1234567890ABC"
        environment_id = "ENV1234567890ABC"
        feature_id = "FEA1234567890ABC"
        embedded_feature_id = "EMB1234567890ABC"
        adversary_rel = f"src/packs/adventures/adversaries/Test_Adversary_{adversary_id}.json"
        environment_rel = f"src/packs/adventures/environments/Test_Environment_{environment_id}.json"
        feature_rel = f"src/packs/system/adversaries-features/Test_Feature_{feature_id}.json"
        for rel in (adversary_rel, environment_rel, feature_rel):
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)

        adversary = {
            "name": "Test Adversary",
            "_id": adversary_id,
            "type": "adversary",
            "img": "worlds/cybermancer/assets/images/adversaries/test-adversary.png",
            "system": {
                "tier": 2,
                "type": "leader",
                "difficulty": 15,
                "description": (
                    "<p>Canonical adversary description.</p>"
                    '<section class="cybermancy-fast-play">'
                    "<h3>FAST PLAY</h3><p>Foundry mirror that must not enter Description.</p>"
                    "</section>"
                ),
                "damageThresholds": {"major": 8, "severe": 15},
                "resources": {
                    "hitPoints": {"max": 7},
                    "stress": {"max": 4},
                },
                "motivesAndTactics": "command, pressure, reposition",
                "experiences": {
                    "exp1": {"name": "Command", "value": 3},
                },
                "attack": {
                    "name": "Arc Shot",
                    "roll": {"bonus": 4, "trait": None, "difficulty": None},
                    "range": "far",
                    "damage": {
                        "parts": [
                            {
                                "value": {"dice": "d8", "bonus": 3},
                                "type": ["magical"],
                            }
                        ],
                        "direct": False,
                    },
                },
            },
            "flags": {
                "cybermancy": {
                    "fastPlay": {
                        "prompts": [
                            {
                                "label": "Opening",
                                "text": "Take command and establish pressure.",
                                "featureRefs": ["Command Field"],
                            },
                            {
                                "label": "Default",
                                "text": "Use Arc Shot on an exposed target.",
                                "featureRefs": [],
                            },
                        ],
                        "goal": "Force the party to react to the leader's tempo.",
                    }
                }
            },
            "items": [
                {
                    "name": "Command Field",
                    "type": "feature",
                    "_id": embedded_feature_id,
                    "sort": 100000,
                    "system": {
                        "description": "<p>Allies within Close range gain positional support.</p>",
                        "actions": {
                            "ACT1234567890ABC": {
                                "_id": "ACT1234567890ABC",
                                "name": "Command Field",
                                "type": "effect",
                                "actionType": "passive",
                                "description": "<p>Allies within Close range gain positional support.</p>",
                                "cost": [],
                                "uses": {},
                                "target": {"type": "any", "amount": None},
                            }
                        },
                    },
                }
            ],
        }
        environment = {
            "name": "Test Environment",
            "_id": environment_id,
            "type": "environment",
            "system": {
                "tier": 1,
                "type": "event",
                "difficulty": 12,
                "description": "<p>A volatile test environment.</p>",
                "impulses": "escalate pressure, split attention",
                "potentialAdversaries": {
                    "group": {
                        "label": "Potential Adversaries",
                        "adversaries": [f"Actor.{adversary_id}"],
                    }
                },
            },
            "items": [],
        }
        standalone_feature = {
            "name": "Test Standalone Feature",
            "_id": feature_id,
            "type": "feature",
            "system": {
                "description": (
                    "<p>Call @UUID[Compendium.test.Actor.X]{Named Adversary} "
                    "and place @Template[type:emanation|range:f].</p>"
                ),
                "actions": {
                    "ACT2234567890ABC": {
                        "_id": "ACT2234567890ABC",
                        "name": "Trigger",
                        "type": "effect",
                        "actionType": "action",
                        "description": "<p>Resolve @UUID[Compendium.test.Actor.X]{Named Adversary}.</p>",
                        "cost": [],
                        "uses": {},
                        "target": {"type": "any", "amount": None},
                    }
                },
            },
        }
        (repo / adversary_rel).write_text(json.dumps(adversary), encoding="utf-8")
        (repo / environment_rel).write_text(json.dumps(environment), encoding="utf-8")
        (repo / feature_rel).write_text(json.dumps(standalone_feature), encoding="utf-8")

        art = repo / "docs" / "gm-facing" / "assets" / "images" / "adversaries" / "test-adversary.png"
        art.parent.mkdir(parents=True)
        art.write_bytes(b"encounter-art")

        sidecar = {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "entities": [
                {
                    "semanticId": f"entity:adversaries:{adversary_id}",
                    "family": "adversaries",
                    "sourceId": adversary_id,
                    "name": "Test Adversary",
                    "audience": "gm",
                    "sourcePath": adversary_rel,
                    "publicationData": {"tier": 2},
                },
                {
                    "semanticId": f"entity:environments:{environment_id}",
                    "family": "environments",
                    "sourceId": environment_id,
                    "name": "Test Environment",
                    "audience": "gm",
                    "sourcePath": environment_rel,
                    "publicationData": {"tier": 1},
                },
                {
                    "semanticId": f"entity:adversaries-features:{feature_id}",
                    "family": "adversaries-features",
                    "sourceId": feature_id,
                    "name": "Test Standalone Feature",
                    "audience": "gm",
                    "sourcePath": feature_rel,
                    "publicationData": {},
                },
            ],
        }
        (metadata / "structured-entities.json").write_text(json.dumps(sidecar), encoding="utf-8")
        (metadata / "assets.json").write_text("[]\n", encoding="utf-8")

        config = {
            "assets": {
                "foundryRuntimeMappings": [
                    {"prefix": "modules/cybermancy/", "repoPrefix": ""},
                    {"prefix": "worlds/cybermancer/", "repoPrefix": ""},
                ]
            }
        }
        return repo, outroot, metadata, config, adversary_id, environment_id, feature_id

    def test_part_vi_semantics_fast_play_art_and_corpus_are_materialized(self):
        with tempfile.TemporaryDirectory() as td:
            repo, outroot, metadata, config, _, _, _ = self._fixture(Path(td))
            report = new_report()

            _postprocess_encounter_semantics(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            by_family = {entity["family"]: entity for entity in sidecar["entities"]}

            adversary = by_family["adversaries"]["publicationData"]
            self.assertEqual(adversary["classification"], "leader")
            self.assertEqual(adversary["difficulty"], 15)
            self.assertEqual(adversary["hitPoints"], 7)
            self.assertEqual(adversary["stress"], 4)
            self.assertEqual(adversary["attack"]["damageFormula"], "d8+3")
            self.assertEqual(adversary["attack"]["damageTypes"], ["magical"])
            self.assertEqual(adversary["description"], "Canonical adversary description.")
            self.assertNotIn("FAST PLAY", adversary["description"])
            self.assertEqual(adversary["fastPlay"]["prompts"][0]["label"], "Opening")
            self.assertEqual(adversary["fastPlay"]["prompts"][0]["featureRefs"], ["Command Field"])
            self.assertEqual(adversary["features"][0]["name"], "Command Field")
            self.assertEqual(
                adversary["publicationArt"],
                {"role": "portrait", "image": "assets/images/adversaries/test-adversary.png"},
            )
            self.assertTrue(
                (outroot / "source" / "assets" / "images" / "adversaries" / "test-adversary.png").is_file()
            )

            environment = by_family["environments"]["publicationData"]
            self.assertEqual(environment["classification"], "event")
            self.assertEqual(environment["potentialAdversaries"], ["Test Adversary"])

            feature = by_family["adversaries-features"]["publicationData"]
            self.assertIn("Named Adversary", feature["rulesMarkdown"])
            self.assertNotIn("@UUID", feature["rulesMarkdown"])
            self.assertNotIn("@Template", feature["rulesMarkdown"])
            self.assertEqual(feature["actions"][0]["name"], "Trigger")
            self.assertNotIn("@UUID", feature["actions"][0]["rulesMarkdown"])

            summary = sidecar["encounterSemantics"]
            self.assertEqual(summary["schema"], ENCOUNTER_SEMANTICS_SCHEMA)
            self.assertEqual(summary["entityCounts"]["adversaries"], 1)
            self.assertEqual(summary["entityCounts"]["environments"], 1)
            self.assertEqual(summary["entityCounts"]["adversaries-features"], 1)
            self.assertEqual(summary["fastPlayCounts"]["adversaries"], 1)
            self.assertEqual(summary["publicationArtCounts"]["adversaries"], 1)
            self.assertEqual(summary["status"], "PASS")

            corpus = json.loads((metadata / "encounter-corpus.json").read_text(encoding="utf-8"))
            self.assertEqual(corpus["schema"], ENCOUNTER_CORPUS_SCHEMA)
            self.assertEqual(corpus["families"]["adversaries"]["tierDistribution"], {"2": 1})
            self.assertEqual(corpus["families"]["adversaries"]["classificationDistribution"], {"leader": 1})
            self.assertGreater(corpus["families"]["adversaries"]["rulesWordCount"]["max"], 0)

            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["ENCOUNTER_PUBLICATION_SEMANTICS"]["status"], "PASS")

    def test_invalid_fast_play_feature_ref_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo, outroot, metadata, config, adversary_id, _, _ = self._fixture(Path(td))
            source = repo / f"src/packs/adventures/adversaries/Test_Adversary_{adversary_id}.json"
            doc = json.loads(source.read_text(encoding="utf-8"))
            doc["flags"]["cybermancy"]["fastPlay"]["prompts"][0]["featureRefs"] = ["Missing Feature"]
            source.write_text(json.dumps(doc), encoding="utf-8")
            report = new_report()

            _postprocess_encounter_semantics(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["encounterSemantics"]["status"], "FAIL")
            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["ENCOUNTER_PUBLICATION_SEMANTICS"]["status"], "ERROR")
            issue_codes = {item["code"] for item in checks["ENCOUNTER_PUBLICATION_SEMANTICS"]["details"]}
            self.assertIn("ENCOUNTER_FAST_PLAY_FEATURE_REF_UNRESOLVED", issue_codes)

    def test_missing_legacy_environment_fields_warn_without_inventing_content(self):
        with tempfile.TemporaryDirectory() as td:
            repo, outroot, metadata, config, _, environment_id, _ = self._fixture(Path(td))
            source = repo / f"src/packs/adventures/environments/Test_Environment_{environment_id}.json"
            doc = json.loads(source.read_text(encoding="utf-8"))
            doc["system"]["type"] = ""
            doc["system"]["description"] = ""
            doc["system"]["impulses"] = ""
            source.write_text(json.dumps(doc), encoding="utf-8")
            report = new_report()

            _postprocess_encounter_semantics(
                repo,
                outroot,
                config,
                report,
                add_check=add_check,
            )

            sidecar = json.loads((metadata / "structured-entities.json").read_text(encoding="utf-8"))
            environment = next(entity for entity in sidecar["entities"] if entity["family"] == "environments")
            pdata = environment["publicationData"]
            self.assertIn(pdata.get("classification"), (None, ""))
            self.assertEqual(pdata["description"], "")
            self.assertEqual(pdata["impulses"], "")
            self.assertEqual(sidecar["encounterSemantics"]["status"], "WARNING")
            checks = {item["code"]: item for item in report["checks"]}
            self.assertEqual(checks["ENCOUNTER_PUBLICATION_SEMANTICS"]["status"], "WARNING")
            issue_codes = {item["code"] for item in checks["ENCOUNTER_PUBLICATION_SEMANTICS"]["details"]}
            self.assertIn("ENCOUNTER_CLASSIFICATION_MISSING", issue_codes)
            self.assertIn("ENCOUNTER_DESCRIPTION_MISSING", issue_codes)
            self.assertIn("ENCOUNTER_IMPULSES_MISSING", issue_codes)


if __name__ == "__main__":
    unittest.main()
