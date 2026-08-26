import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_normalize.publication import SCHEMA_VERSION
from rulebook_step4_class_relationships import _postprocess_materialization


def _uuid(pack: str, source_id: str) -> str:
    return f"Compendium.cybermancy.{pack}.Item.{source_id}"


def _entity(family: str, source_id: str, source_path: str = "") -> dict:
    return {
        "semanticId": f"entity:{family}:{source_id}",
        "family": family,
        "sourceId": source_id,
        "name": source_id,
        "audience": "player",
        "sourcePath": source_path or f"src/{family}/{source_id}.json",
        "publicationData": {},
    }


def _add_check(report, code, status, message, details=None):
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


class TestStep4RelationshipMaterializationIntegration(unittest.TestCase):
    def _fixture(self, root: Path, *, broken_feature=False):
        class_rel = "src/packs/system/classes/Class_One_c1.json"
        subclass_rel = "src/packs/system/subclasses/Subclass_One_s1.json"
        class_path = root / class_rel
        subclass_path = root / subclass_rel
        class_path.parent.mkdir(parents=True, exist_ok=True)
        subclass_path.parent.mkdir(parents=True, exist_ok=True)

        class_path.write_text(
            json.dumps(
                {
                    "name": "Class One",
                    "type": "class",
                    "_id": "c1",
                    "system": {
                        "features": [
                            {
                                "type": "hope",
                                "item": _uuid(
                                    "cybermancy-features",
                                    "missing" if broken_feature else "fh",
                                ),
                            }
                        ],
                        "subclasses": [_uuid("cybermancy-subclasses", "s1")],
                        "classItems": [],
                    },
                }
            ),
            encoding="utf-8",
        )
        subclass_path.write_text(
            json.dumps(
                {
                    "name": "Subclass One",
                    "type": "subclass",
                    "_id": "s1",
                    "system": {
                        "linkedClass": _uuid("cybermancy-classes", "c1"),
                        "features": [
                            {"type": "foundation", "item": _uuid("cybermancy-features", "ff")},
                            {"type": "specialization", "item": _uuid("cybermancy-features", "fs")},
                            {"type": "mastery", "item": _uuid("cybermancy-features", "fm")},
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )

        entities = [
            _entity("classes", "c1", class_rel),
            _entity("subclasses", "s1", subclass_rel),
            _entity("features", "fh"),
            _entity("features", "ff"),
            _entity("features", "fs"),
            _entity("features", "fm"),
        ]
        outroot = root / "build-output"
        metadata = outroot / "source" / "metadata"
        metadata.mkdir(parents=True, exist_ok=True)
        (metadata / "structured-entities.json").write_text(
            json.dumps({"schema": SCHEMA_VERSION, "entities": entities}),
            encoding="utf-8",
        )
        report = {"status": "PASS", "checks": [], "warnings": [], "errors": []}
        return outroot, report

    def test_materialization_postpass_persists_semantic_graph_and_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outroot, report = self._fixture(root)
            _postprocess_materialization(
                root,
                outroot,
                report,
                add_check=_add_check,
            )
            sidecar = json.loads(
                (outroot / "source" / "metadata" / "structured-entities.json").read_text(
                    encoding="utf-8"
                )
            )
            validation = json.loads(
                (outroot / "source" / "metadata" / "validation.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(sidecar["relationshipSemantics"]["status"], "PASS")
        self.assertEqual(sidecar["relationshipSemantics"]["classCount"], 1)
        self.assertEqual(sidecar["relationshipSemantics"]["subclassCount"], 1)
        self.assertEqual(sidecar["relationshipSemantics"]["featureEdgeCount"], 4)
        self.assertEqual(validation["status"], "PASS")

        by_id = {entity["semanticId"]: entity for entity in sidecar["entities"]}
        class_data = by_id["entity:classes:c1"]["publicationData"]
        subclass_data = by_id["entity:subclasses:s1"]["publicationData"]
        self.assertEqual(class_data["subclasses"], ["entity:subclasses:s1"])
        self.assertEqual(class_data["features"][0]["semanticId"], "entity:features:fh")
        self.assertEqual(subclass_data["linkedClass"], "entity:classes:c1")
        self.assertEqual(subclass_data["progression"]["foundation"], ["entity:features:ff"])
        self.assertNotIn("Compendium.", json.dumps(class_data))
        self.assertNotIn("Compendium.", json.dumps(subclass_data))

    def test_materialization_postpass_fails_closed_on_unresolved_relationship(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outroot, report = self._fixture(root, broken_feature=True)
            _postprocess_materialization(
                root,
                outroot,
                report,
                add_check=_add_check,
            )
            sidecar = json.loads(
                (outroot / "source" / "metadata" / "structured-entities.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(sidecar["relationshipSemantics"]["status"], "FAIL")
        relationship_checks = [
            check for check in report["checks"] if check["code"] == "CLASS_RELATIONSHIP_SEMANTICS"
        ]
        self.assertEqual(len(relationship_checks), 1)
        self.assertEqual(relationship_checks[0]["status"], "ERROR")
        codes = {item["code"] for item in relationship_checks[0]["details"]}
        self.assertIn("RELATION_REFERENCE_UNRESOLVED", codes)


if __name__ == "__main__":
    unittest.main()
