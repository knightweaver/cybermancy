import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout import equipment_bootstrap
from rulebook_layout_cli_compat import (
    STEP4_CLASS_RELATIONSHIP_SCHEMA,
    configure_layout_machine_output,
)
from rulebook_normalize.publication import SCHEMA_VERSION, structured_publication_data
from rulebook_normalize.relationships import apply_class_relationship_semantics


def _entity(family: str, source_id: str, name: str | None = None) -> dict:
    return {
        "semanticId": f"entity:{family}:{source_id}",
        "family": family,
        "sourceId": source_id,
        "name": name or source_id,
        "audience": "player",
        "sourcePath": f"src/{family}/{source_id}.json",
        "publicationData": {},
    }


def _uuid(pack: str, source_id: str) -> str:
    return f"Compendium.cybermancy.{pack}.Item.{source_id}"


def _record(family: str, source_id: str, system: dict) -> dict:
    return {
        "semanticId": f"entity:{family}:{source_id}",
        "family": family,
        "document": {
            "name": source_id,
            "type": family.rstrip("s"),
            "_id": source_id,
            "system": system,
        },
    }


class TestClassRelationshipProjection(unittest.TestCase):
    def test_class_and_subclass_reader_facing_fields_are_projected(self):
        class_doc = {
            "system": {
                "description": "<p>A class description.</p>",
                "hitPoints": 6,
                "evasion": 10,
                "domains": ["circuit", "midnight"],
                "backgroundQuestions": ["", "Who trained you?", "   "],
                "connections": ["", "Who trusts you?"],
                "isMulticlass": False,
            }
        }
        data = structured_publication_data("classes", class_doc, {})
        self.assertEqual(SCHEMA_VERSION, "cybermancy-step4-structured-entities-v1.3")
        self.assertEqual(data["description"], "A class description.")
        self.assertEqual(data["hitPoints"], 6)
        self.assertEqual(data["evasion"], 10)
        self.assertEqual(data["domains"], ["circuit", "midnight"])
        self.assertEqual(data["backgroundQuestions"], ["Who trained you?"])
        self.assertEqual(data["connections"], ["Who trusts you?"])

        blank = structured_publication_data(
            "classes",
            {"system": {"backgroundQuestions": ["", ""], "connections": ["", ""]}},
            {},
        )
        self.assertNotIn("backgroundQuestions", blank)
        self.assertNotIn("connections", blank)

        subclass = structured_publication_data(
            "subclasses",
            {"system": {"spellcastingTrait": "presence", "isMulticlass": False}},
            {},
        )
        self.assertEqual(subclass["spellcastingTrait"], "presence")
        self.assertFalse(subclass["isMulticlass"])


class TestClassRelationshipResolution(unittest.TestCase):
    def _corpus(self):
        entities = [
            _entity("classes", "c1", "Class One"),
            _entity("subclasses", "s1", "Subclass One"),
            _entity("features", "fh", "Hope Feature"),
            _entity("features", "fc", "Class Feature"),
            _entity("features", "ff", "Foundation Feature"),
            _entity("features", "fs", "Specialization Feature"),
            _entity("features", "fm", "Mastery Feature"),
            _entity("loot", "l1", "Starting Loot"),
            _entity("consumables", "co1", "Starting Consumable"),
            _entity("weapons", "w1", "Primary Weapon"),
            _entity("armors", "a1", "Starting Armor"),
        ]
        class_system = {
            "features": [
                {"type": "hope", "item": _uuid("cybermancy-features", "fh")},
                {"type": "class", "item": _uuid("cybermancy-features", "fc")},
            ],
            "subclasses": [_uuid("cybermancy-subclasses", "s1")],
            "inventory": {
                "take": [_uuid("cybermancy-loot", "l1")],
                "choiceA": [_uuid("cybermancy-consumables", "co1")],
                "choiceB": [],
            },
            "characterGuide": {
                "suggestedTraits": {"agility": 2, "knowledge": 1},
                "suggestedPrimaryWeapon": _uuid("cybermancy-weapons", "w1"),
                "suggestedSecondaryWeapon": None,
                "suggestedArmor": _uuid("cybermancy-armors", "a1"),
            },
        }
        subclass_system = {
            "linkedClass": _uuid("cybermancy-classes", "c1"),
            "features": [
                {"type": "foundation", "item": _uuid("cybermancy-features", "ff")},
                {"type": "specialization", "item": _uuid("cybermancy-features", "fs")},
                {"type": "mastery", "item": _uuid("cybermancy-features", "fm")},
            ],
        }
        records = [
            _record("classes", "c1", class_system),
            _record("subclasses", "s1", subclass_system),
        ]
        return records, entities

    def test_relationship_graph_resolves_to_semantic_ids(self):
        records, entities = self._corpus()
        result = apply_class_relationship_semantics(records, entities)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["classCount"], 1)
        self.assertEqual(result["subclassCount"], 1)
        self.assertEqual(result["featureEdgeCount"], 5)

        by_id = {entity["semanticId"]: entity for entity in entities}
        class_data = by_id["entity:classes:c1"]["publicationData"]
        self.assertEqual(
            class_data["features"],
            [
                {"type": "hope", "semanticId": "entity:features:fh"},
                {"type": "class", "semanticId": "entity:features:fc"},
            ],
        )
        self.assertEqual(class_data["subclasses"], ["entity:subclasses:s1"])
        self.assertEqual(class_data["startingInventory"]["take"], ["entity:loot:l1"])
        self.assertEqual(class_data["startingInventory"]["choiceA"], ["entity:consumables:co1"])
        self.assertEqual(class_data["characterGuide"]["suggestedPrimaryWeapon"], "entity:weapons:w1")
        self.assertIsNone(class_data["characterGuide"]["suggestedSecondaryWeapon"])
        self.assertEqual(class_data["characterGuide"]["suggestedArmor"], "entity:armors:a1")

        subclass_data = by_id["entity:subclasses:s1"]["publicationData"]
        self.assertEqual(subclass_data["linkedClass"], "entity:classes:c1")
        self.assertEqual(subclass_data["progression"]["foundation"], ["entity:features:ff"])
        self.assertEqual(subclass_data["progression"]["specialization"], ["entity:features:fs"])
        self.assertEqual(subclass_data["progression"]["mastery"], ["entity:features:fm"])

        used_by = by_id["entity:features:ff"]["publicationData"]["usedBy"]
        self.assertEqual(
            used_by,
            [{
                "ownerSemanticId": "entity:subclasses:s1",
                "ownerFamily": "subclasses",
                "relationship": "foundation",
            }],
        )

        publication_json = json.dumps(
            [
                by_id["entity:classes:c1"]["publicationData"],
                by_id["entity:subclasses:s1"]["publicationData"],
            ]
        )
        self.assertNotIn("Compendium.", publication_json)

    def test_unresolved_feature_reference_fails_closed(self):
        records, entities = self._corpus()
        records[0]["document"]["system"]["features"][0]["item"] = _uuid(
            "cybermancy-features", "missing"
        )
        result = apply_class_relationship_semantics(records, entities)
        codes = {error["code"] for error in result["errors"]}
        self.assertIn("RELATION_REFERENCE_UNRESOLVED", codes)

    def test_bidirectional_class_subclass_mismatch_fails_closed(self):
        records, entities = self._corpus()
        entities.append(_entity("classes", "c2", "Class Two"))
        records[1]["document"]["system"]["linkedClass"] = _uuid("cybermancy-classes", "c2")
        result = apply_class_relationship_semantics(records, entities)
        codes = {error["code"] for error in result["errors"]}
        self.assertIn("SUBCLASS_CLASS_BIDIRECTIONAL_MISMATCH", codes)


class TestStep6SidecarCompatibility(unittest.TestCase):
    def test_step6_accepts_relationship_sidecar_without_dropping_prior_versions(self):
        supported = {
            "cybermancy-step4-structured-entities-v1.1",
            "cybermancy-step4-structured-entities-v1.2",
        }
        equipment = set(supported)
        namespace = {
            "SUPPORTED_SIDECAR_SCHEMAS": supported,
            "EQUIPMENT_SIDECAR_SCHEMAS": equipment,
        }
        configure_layout_machine_output(namespace)
        self.assertIn(STEP4_CLASS_RELATIONSHIP_SCHEMA, supported)
        self.assertIn(STEP4_CLASS_RELATIONSHIP_SCHEMA, equipment)
        self.assertIn(STEP4_CLASS_RELATIONSHIP_SCHEMA, equipment_bootstrap.SIDECAR_SCHEMAS)
        self.assertIn("cybermancy-step4-structured-entities-v1.2", supported)


if __name__ == "__main__":
    unittest.main()
