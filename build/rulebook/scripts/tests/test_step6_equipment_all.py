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
    discover_equipment_configs,
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


class TestEquipmentAllDiscovery(unittest.TestCase):
    def test_repository_configs_are_discovered_in_chapter_order(self):
        config_dir = HERE.parents[2] / "layout" / "equipment"
        discovered, errors = discover_equipment_configs(config_dir)
        self.assertEqual(errors, [])
        self.assertEqual(
            [(item["chapter"], item["family"]) for item in discovered],
            [(16, "weapons"), (17, "ammo")],
        )

    def test_duplicate_chapters_fail_discovery(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            (config_dir / "alpha-v1.json").write_text(
                json.dumps(_config("alpha", 18, "Alpha")), encoding="utf-8"
            )
            (config_dir / "beta-v1.json").write_text(
                json.dumps(_config("beta", 18, "Beta")), encoding="utf-8"
            )
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
            builder.parser().parse_args([
                "validate-equipment", "--all", "--family", "ammo"
            ])


class TestEquipmentAllFailClosedBuild(unittest.TestCase):
    def test_build_preflight_failure_starts_no_builds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "configs"
            report_dir = root / "reports"
            config_dir.mkdir()
            (config_dir / "weapons-v1.json").write_text(
                json.dumps(_config("weapons", 16, "Weapons")), encoding="utf-8"
            )
            (config_dir / "ammo-v1.json").write_text(
                json.dumps(_config("ammo", 17, "Ammunition")), encoding="utf-8"
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
                "failed = operation == 'validate-equipment' and family == 'ammo'\n"
                "print(json.dumps({'status': 'FAIL' if failed else 'PASS', 'errors': []}))\n"
                "raise SystemExit(2 if failed else 0)\n",
                encoding="utf-8",
            )

            args = argparse.Namespace(
                all=True,
                family=None,
                config=None,
                sidecar=None,
                manuscript=None,
                report_dir=str(report_dir),
                output_dir=None,
                tex_only=True,
            )
            rc = run_all_equipment_command(
                "build",
                args,
                script_path=fake_script,
                config_dir=config_dir,
                default_sidecar=root / "structured-entities.json",
                default_manuscript=root / "player-guide.md",
                default_report_dir=report_dir,
            )
            invocations = log_path.read_text(encoding="utf-8").splitlines()
            aggregate = json.loads(
                (report_dir / "equipment-all.json").read_text(encoding="utf-8")
            )

        self.assertEqual(rc, 2)
        self.assertEqual(invocations, [
            "validate-equipment:weapons",
            "validate-equipment:ammo",
        ])
        self.assertFalse(any(line.startswith("build-equipment:") for line in invocations))
        self.assertEqual(aggregate["status"], "FAIL")
        checks = {check["code"]: check["status"] for check in aggregate["checks"]}
        self.assertEqual(checks["EQUIPMENT_BUILD_PREFLIGHT"], "ERROR")


if __name__ == "__main__":
    unittest.main()
