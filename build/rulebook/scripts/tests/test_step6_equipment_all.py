import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_batch import (
    _invoke_child,
    discover_equipment_configs,
    resolve_equipment_section,
    run_all_equipment_command,
)


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-layout.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_layout_all", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _config(family: str, chapter: int, title: str) -> dict:
    return {
        "schema": "cybermancy-step6-equipment-catalog-config-v1.1",
        "family": family,
        "chapter": chapter,
        "title": title,
        "columns": [{"key": "name", "label": "Name", "widthIn": 1.0}],
    }


def _section(entries: list[tuple[int, str, str]]) -> dict:
    return {
        "schema": "cybermancy-step6-equipment-section-v1.0",
        "partLabel": "EQUIPMENT & TECHNOLOGY",
        "families": [
            {"chapter": chapter, "family": family, "title": title, "config": f"{family}-v1.json"}
            for chapter, family, title in entries
        ],
    }


class TestEquipmentAllDiscovery(unittest.TestCase):
    def test_repository_section_contract_is_chapters_16_through_23(self):
        config_dir = HERE.parents[2] / "layout" / "equipment"
        registry = config_dir / "equipment-section-v1.json"
        resolved, errors = resolve_equipment_section(registry, config_dir)
        self.assertEqual(errors, [])
        self.assertEqual(
            [(item["chapter"], item["family"]) for item in resolved],
            [
                (16, "weapons"),
                (17, "ammo"),
                (18, "armors"),
                (19, "cybernetics"),
                (20, "drones-devices"),
                (21, "consumables"),
                (22, "mods"),
                (23, "loot"),
            ],
        )
        by_family = {item["family"]: item for item in resolved}
        self.assertTrue(by_family["weapons"]["configPresent"])
        self.assertTrue(by_family["ammo"]["configPresent"])

    def test_section_registry_is_not_misread_as_family_config(self):
        config_dir = HERE.parents[2] / "layout" / "equipment"
        discovered, errors = discover_equipment_configs(config_dir)
        self.assertEqual(errors, [])
        self.assertNotIn("equipment-section-v1.json", [Path(item["config"]).name for item in discovered])

    def test_duplicate_chapters_fail_discovery(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            (config_dir / "alpha-v1.json").write_text(json.dumps(_config("alpha", 18, "Alpha")), encoding="utf-8")
            (config_dir / "beta-v1.json").write_text(json.dumps(_config("beta", 18, "Beta")), encoding="utf-8")
            discovered, errors = discover_equipment_configs(config_dir)
        self.assertEqual(len(discovered), 2)
        self.assertTrue(any(error["issue"] == "duplicate-chapter-config" for error in errors))


class TestEquipmentAllParser(unittest.TestCase):
    def test_equipment_commands_accept_all_selector(self):
        builder = _load_builder()
        args = builder.parser().parse_args(["validate-equipment", "--all"])
        self.assertTrue(args.all)
        self.assertIsNone(args.family)

    def test_equipment_commands_require_exactly_one_selector(self):
        builder = _load_builder()
        with self.assertRaises(SystemExit):
            builder.parser().parse_args(["validate-equipment"])
        with self.assertRaises(SystemExit):
            builder.parser().parse_args(["validate-equipment", "--all", "--family", "ammo"])


class TestEquipmentBatchUtf8(unittest.TestCase):
    def test_child_process_can_emit_unicode_rulebook_labels(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "unicode-child.py"
            script.write_text(
                "import json\n"
                "print(json.dumps({'status': 'PASS', 'message': 'Trait → Name'}, ensure_ascii=False))\n",
                encoding="utf-8",
            )
            returncode, payload = _invoke_child([sys.executable, str(script)])
        self.assertEqual(returncode, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["message"], "Trait → Name")


class TestEquipmentAllImplementedProgress(unittest.TestCase):
    def test_missing_later_configs_do_not_prevent_weapons_and_ammo_builds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "configs"
            report_dir = root / "reports"
            config_dir.mkdir()
            for chapter, family, title in ((16, "weapons", "Weapons"), (17, "ammo", "Ammunition")):
                (config_dir / f"{family}-v1.json").write_text(json.dumps(_config(family, chapter, title)), encoding="utf-8")
            registry = config_dir / "equipment-section-v1.json"
            registry.write_text(
                json.dumps(_section([
                    (16, "weapons", "Weapons"),
                    (17, "ammo", "Ammunition"),
                    (18, "armors", "Armor"),
                    (19, "cybernetics", "Cybernetics"),
                ])),
                encoding="utf-8",
            )
            log_path = root / "child.log"
            fake_script = root / "fake-builder.py"
            fake_script.write_text(
                "import json, sys\n"
                "from pathlib import Path\n"
                f"log = Path({str(log_path)!r})\n"
                "operation = sys.argv[1]\n"
                "family = sys.argv[sys.argv.index('--family') + 1]\n"
                "with log.open('a', encoding='utf-8') as handle:\n"
                "    handle.write(f'{operation}:{family}\\n')\n"
                "print(json.dumps({'status': 'PASS', 'message': 'Trait → Name'}, ensure_ascii=False))\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(all=True, family=None, config=None, sidecar=None, manuscript=None, report_dir=str(report_dir), output_dir=None, tex_only=True)
            rc = run_all_equipment_command(
                "build", args, script_path=fake_script, config_dir=config_dir,
                section_registry=registry,
                default_sidecar=root / "structured-entities.json",
                default_manuscript=root / "player-guide.md",
                default_report_dir=report_dir,
            )
            invocations = log_path.read_text(encoding="utf-8").splitlines()
            aggregate = json.loads((report_dir / "equipment-all.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 2)  # Section remains incomplete until every required config exists.
        self.assertEqual(invocations, [
            "validate-equipment:weapons",
            "validate-equipment:ammo",
            "build-equipment:weapons",
            "build-equipment:ammo",
        ])
        status = {(item["chapter"], item["family"]): item["status"] for item in aggregate["families"]}
        self.assertEqual(status[(16, "weapons")], "PASS")
        self.assertEqual(status[(17, "ammo")], "PASS")
        self.assertEqual(status[(18, "armors")], "BLOCKED")
        self.assertEqual(status[(19, "cybernetics")], "BLOCKED")
        checks = {check["code"]: check["status"] for check in aggregate["checks"]}
        self.assertEqual(checks["EQUIPMENT_CONFIG_COVERAGE"], "BLOCKED")
        self.assertEqual(checks["EQUIPMENT_BUILD_PREFLIGHT"], "PASS")
        self.assertEqual(checks["EQUIPMENT_FAMILY_RESULTS"], "PASS")


class TestEquipmentAllFailClosedBuild(unittest.TestCase):
    def test_implemented_preflight_failure_starts_no_builds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "configs"
            report_dir = root / "reports"
            config_dir.mkdir()
            for chapter, family, title in ((16, "weapons", "Weapons"), (17, "ammo", "Ammunition")):
                (config_dir / f"{family}-v1.json").write_text(json.dumps(_config(family, chapter, title)), encoding="utf-8")
            registry = config_dir / "equipment-section-v1.json"
            registry.write_text(json.dumps(_section([(16, "weapons", "Weapons"), (17, "ammo", "Ammunition")])), encoding="utf-8")
            log_path = root / "child.log"
            fake_script = root / "fake-builder.py"
            fake_script.write_text(
                "import json, sys\n"
                "from pathlib import Path\n"
                f"log = Path({str(log_path)!r})\n"
                "operation = sys.argv[1]\n"
                "family = sys.argv[sys.argv.index('--family') + 1]\n"
                "with log.open('a', encoding='utf-8') as handle:\n"
                "    handle.write(f'{operation}:{family}\\n')\n"
                "failed = operation == 'validate-equipment' and family == 'ammo'\n"
                "print(json.dumps({'status': 'FAIL' if failed else 'PASS', 'errors': []}))\n"
                "raise SystemExit(2 if failed else 0)\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(all=True, family=None, config=None, sidecar=None, manuscript=None, report_dir=str(report_dir), output_dir=None, tex_only=True)
            rc = run_all_equipment_command(
                "build", args, script_path=fake_script, config_dir=config_dir,
                section_registry=registry,
                default_sidecar=root / "structured-entities.json",
                default_manuscript=root / "player-guide.md",
                default_report_dir=report_dir,
            )
            invocations = log_path.read_text(encoding="utf-8").splitlines()
            aggregate = json.loads((report_dir / "equipment-all.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 2)
        self.assertEqual(invocations, ["validate-equipment:weapons", "validate-equipment:ammo"])
        self.assertFalse(any(line.startswith("build-equipment:") for line in invocations))
        checks = {check["code"]: check["status"] for check in aggregate["checks"]}
        self.assertEqual(checks["EQUIPMENT_BUILD_PREFLIGHT"], "ERROR")


if __name__ == "__main__":
    unittest.main()
