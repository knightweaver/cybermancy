import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_normalize.foundry_folders import (
    build_folder_map,
    resolve_publication_tier,
)
from rulebook_normalize.publication import (
    SCHEMA_VERSION,
    sidecar_entity,
    structured_publication_data,
)
from rulebook_normalize.snapshot import (
    STRUCTURED_DIGEST_VERSION,
    structured_family_snapshot,
)
from rulebook_normalize.structured import collect_source_warnings, render_entity


class TestFolderTierResolution(unittest.TestCase):
    def _folders(self):
        return build_folder_map([
            {"_key": "!folders!T1", "_id": "T1", "name": "Tier 1", "folder": None},
            {"_key": "!folders!T2", "_id": "T2", "name": "Tier 2", "folder": None},
            {"_key": "!folders!NEST", "_id": "NEST", "name": "Brainiac", "folder": "T2"},
        ])

    def test_folder_is_fallback_when_intrinsic_tier_is_absent(self):
        resolved = resolve_publication_tier(
            {"_id": "A", "name": "Item", "folder": "T1", "system": {}},
            self._folders(),
        )
        self.assertEqual(resolved.value, 1)
        self.assertEqual(resolved.source, "foundry-folder")
        self.assertEqual(resolved.folder_name, "Tier 1")

    def test_nested_folder_walks_to_tier_ancestor(self):
        resolved = resolve_publication_tier(
            {"_id": "A", "name": "Item", "folder": "NEST", "system": {}},
            self._folders(),
        )
        self.assertEqual(resolved.value, 2)
        self.assertEqual(resolved.folder_path, ("Brainiac", "Tier 2"))

    def test_intrinsic_tier_wins_and_conflict_is_visible(self):
        resolved = resolve_publication_tier(
            {"_id": "A", "name": "Item", "folder": "T2", "system": {"tier": 1}},
            self._folders(),
        )
        self.assertEqual(resolved.value, 1)
        self.assertEqual(resolved.source, "system.tier")
        self.assertTrue(resolved.conflict)
        self.assertEqual(resolved.folder_tier, 2)

    def test_genuinely_tierless_item_stays_tierless(self):
        resolved = resolve_publication_tier(
            {"_id": "A", "name": "Item", "folder": None, "system": {}},
            self._folders(),
        )
        self.assertIsNone(resolved.value)
        self.assertEqual(resolved.source, "absent")


class TestFolderDigestAuthority(unittest.TestCase):
    def test_folder_change_changes_digest_without_changing_entity_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            family = root / "src" / "packs" / "items" / "cybernetics"
            family.mkdir(parents=True)
            folder = family / "Tier_1_T1.json"
            item = family / "item.json"
            folder.write_text(json.dumps({
                "_key": "!folders!T1", "_id": "T1", "name": "Tier 1", "folder": None,
            }), encoding="utf-8")
            item.write_text(json.dumps({
                "_id": "A", "_key": "!items!A", "name": "Item", "folder": "T1", "system": {},
            }), encoding="utf-8")

            first = structured_family_snapshot(root, "src/packs/items/cybernetics")
            folder.write_text(json.dumps({
                "_key": "!folders!T1", "_id": "T1", "name": "Tier 2", "folder": None,
            }), encoding="utf-8")
            second = structured_family_snapshot(root, "src/packs/items/cybernetics")

        self.assertEqual(STRUCTURED_DIGEST_VERSION, 3)
        self.assertEqual(first.entity_count, 1)
        self.assertEqual(second.entity_count, 1)
        self.assertEqual(first.foundry_folder_count, 1)
        self.assertEqual(len(first.folder_records), 1)
        self.assertNotEqual(first.digest_sha256, second.digest_sha256)


class TestStep4TierIntegration(unittest.TestCase):
    def test_registered_snapshot_drives_render_sidecar_and_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            family = root / "src" / "packs" / "items" / "cybernetics"
            family.mkdir(parents=True)
            (family / "Tier_1_T1.json").write_text(json.dumps({
                "_key": "!folders!T1", "_id": "T1", "name": "Tier 1", "folder": None,
            }), encoding="utf-8")
            (family / "item.json").write_text(json.dumps({
                "_id": "A", "_key": "!items!A", "name": "Brainiac Test", "folder": "T1",
                "system": {"description": "Rule text."},
            }), encoding="utf-8")
            snapshot = structured_family_snapshot(root, "src/packs/items/cybernetics")
            doc = snapshot.logical_records[0].document
            markdown, metadata = render_entity("cybernetics", doc, [])
            publication = structured_publication_data("cybernetics", doc, metadata)
            metadata["sourcePath"] = snapshot.logical_records[0].repo_path
            metadata["audience"] = "player"
            entity = sidecar_entity(metadata, publication)

        self.assertEqual(SCHEMA_VERSION, "cybermancy-step4-structured-entities-v1.2")
        self.assertIn("| Tier | 1 |", markdown)
        self.assertEqual(publication["tier"], 1)
        self.assertEqual(entity["publicationData"]["tier"], 1)
        provenance = entity["publicationProvenance"]["tier"]
        self.assertEqual(provenance["source"], "foundry-folder")
        self.assertEqual(provenance["folderId"], "T1")
        self.assertEqual(provenance["folderName"], "Tier 1")

    def test_intrinsic_folder_conflict_surfaces_warning(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            family = root / "src" / "packs" / "items" / "armors"
            family.mkdir(parents=True)
            (family / "Tier_2_T2.json").write_text(json.dumps({
                "_key": "!folders!T2", "_id": "T2", "name": "Tier 2", "folder": None,
            }), encoding="utf-8")
            (family / "item.json").write_text(json.dumps({
                "_id": "A", "_key": "!items!A", "name": "Conflict Armor", "folder": "T2",
                "system": {"tier": 1},
            }), encoding="utf-8")
            snapshot = structured_family_snapshot(root, "src/packs/items/armors")
            warnings = collect_source_warnings("armors", snapshot.logical_records[0].document)

        codes = {warning["code"] for warning in warnings}
        self.assertIn("TIER_SOURCE_CONFLICT", codes)


if __name__ == "__main__":
    unittest.main()
