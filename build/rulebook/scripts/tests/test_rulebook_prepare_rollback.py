from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_rulebook_maintenance_cli as support

maintain = support.maintain


class MutatingFailureRunner(support.PrepareRunner):
    """Run the fixture mutation first, then inject the requested child failure."""

    def __init__(self, repo: Path, fail: str | None = None, *, exception: bool = False, unrelated: bool = False):
        super().__init__(repo)
        self.fail_after = fail
        self.raise_exception = exception
        self.create_unrelated = unrelated

    def __call__(self, command, **kwargs):
        result = super().__call__(command, **kwargs)
        script = Path(command[1]).name
        label = {
            "build-rulebook-inventory.py": "strict-inventory",
            "build-rulebook-publication-manifest.py": "publication-manifest",
            "build-rulebook-assembly-manifest.py": "assembly-manifest",
            "build-rulebook-normalization-artifacts.py": "normalization-artifacts",
        }.get(script, script)
        if self.create_unrelated and label == "strict-inventory":
            (self.repo / "unrelated-after-start.txt").write_bytes(b"leave me alone\r\n")
        if label == self.fail_after:
            if self.raise_exception:
                raise RuntimeError(f"injected {label} exception")
            return SimpleNamespace(returncode=7, stdout=f"{label} stdout", stderr=f"{label} stderr")
        return result


class CompletenessFailureRunner(support.PrepareRunner):
    def __call__(self, command, **kwargs):
        result = super().__call__(command, **kwargs)
        if Path(command[1]).name == "build-rulebook-normalization-artifacts.py":
            pub = Path(command[command.index("--publication-manifest") + 1])
            version = pub.stem.split("-v", 1)[1]
            target = self.repo / maintain.MANIFEST_DIR_RELATIVE / f"cybermancy-rulebook-normalization-standard-v{version}.md"
            target.unlink()
        return result


class CompatibilityFailureRunner(support.PrepareRunner):
    def __call__(self, command, **kwargs):
        result = super().__call__(command, **kwargs)
        if Path(command[1]).name == "build-rulebook-normalization-artifacts.py":
            pub = Path(command[command.index("--publication-manifest") + 1])
            version = pub.stem.split("-v", 1)[1]
            target = self.repo / maintain.MANIFEST_DIR_RELATIVE / f"cybermancy-rulebook-normalization-config-v{version}.json"
            data = json.loads(target.read_text(encoding="utf-8"))
            data["baseline"]["commit"] = "wrong-commit"
            support.write_json(target, data)
        return result


def declared_outputs(repo: Path) -> dict[str, Path]:
    base = repo / maintain.MANIFEST_DIR_RELATIVE / "cybermancy-rulebook-publication-manifest-v1.24.json"
    _plan, outputs, _version = maintain._prepare_plan(repo, base)
    return outputs


def output_bytes(outputs: dict[str, Path]) -> dict[str, bytes | None]:
    return {role: path.read_bytes() if path.is_file() else None for role, path in outputs.items()}


def inventory_metadata(outputs: dict[str, Path]) -> dict[str, tuple[int, int]]:
    result = {}
    for role in maintain.INVENTORY_OUTPUT_ROLES:
        info = outputs[role].stat()
        result[role] = (stat.S_IMODE(info.st_mode), info.st_mtime_ns)
    return result


class PrepareRollbackTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(maintain, "run_baseline_check", side_effect=lambda _repo: support.baseline())
        p.start()
        self.addCleanup(p.stop)

    def assert_outputs_restored(self, outputs: dict[str, Path], before: dict[str, bytes | None]) -> None:
        self.assertEqual(output_bytes(outputs), before)
        for role, prior in before.items():
            if prior is None:
                self.assertFalse(outputs[role].exists(), role)
                self.assertFalse(outputs[role].is_symlink(), role)

    def test_declared_output_preexistence_is_recorded_without_dry_run_writes(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            before = output_bytes(outputs)
            runner = support.PrepareRunner(repo)
            report = maintain.prepare_report(repo, dry_run=True, runner=runner)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(runner.calls, [])
            recorded = {row["role"]: row["existedBeforeRun"] for row in report["generatedFilePreexistence"]}
            self.assertEqual(recorded, {role: prior is not None for role, prior in before.items()})
            self.assertNotIn("inventoryRollbackBaseline", report)
            self.assertNotIn("rollback", report)
            self.assert_outputs_restored(outputs, before)

    def test_inventory_rollback_baseline_records_bytes_and_metadata(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            before = output_bytes(outputs)
            metadata = inventory_metadata(outputs)
            report = maintain.prepare_report(repo, runner=MutatingFailureRunner(repo, "strict-inventory"))
            self.assertEqual(report["status"], "FAIL")
            rows = {row["role"]: row for row in report["inventoryRollbackBaseline"]}
            for role in maintain.INVENTORY_OUTPUT_ROLES:
                self.assertEqual(rows[role]["size"], len(before[role] or b""))
                self.assertEqual(rows[role]["mode"], oct(metadata[role][0]))
                self.assertEqual(rows[role]["mtimeNs"], metadata[role][1])
            self.assert_outputs_restored(outputs, before)
            self.assertEqual(inventory_metadata(outputs), metadata)

    def test_failure_at_each_child_rolls_back_all_declared_outputs(self):
        for failed in ("strict-inventory", "publication-manifest", "assembly-manifest", "normalization-artifacts"):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as t:
                repo = support.fixture(Path(t))
                outputs = declared_outputs(repo)
                before = output_bytes(outputs)
                report = maintain.prepare_report(repo, runner=MutatingFailureRunner(repo, failed))
                self.assertEqual(report["status"], "FAIL")
                self.assertEqual(report["exitCode"], 7)
                self.assertEqual(report["failedCommand"], failed)
                self.assertEqual(report["childCommands"][-1]["returnCode"], 7)
                self.assertIn(f"{failed} stderr", report["childCommands"][-1]["stderr"])
                self.assertEqual(report["rollback"]["status"], "PASS")
                self.assert_outputs_restored(outputs, before)

    def test_generated_file_completeness_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            before = output_bytes(outputs)
            report = maintain.prepare_report(repo, runner=CompletenessFailureRunner(repo))
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["exitCode"], 2)
            self.assertIn("missingGeneratedFiles", report)
            self.assertEqual(report["rollback"]["status"], "PASS")
            self.assert_outputs_restored(outputs, before)

    def test_final_compatibility_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            before = output_bytes(outputs)
            report = maintain.prepare_report(repo, runner=CompatibilityFailureRunner(repo))
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["exitCode"], 2)
            self.assertEqual(report["generatedFreezeCompatibility"], "FAIL")
            self.assertEqual(report["rollback"]["status"], "PASS")
            self.assert_outputs_restored(outputs, before)

    def test_python_exception_uses_same_rollback_and_preserves_exception(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            before = output_bytes(outputs)
            report = maintain.prepare_report(repo, runner=MutatingFailureRunner(repo, "assembly-manifest", exception=True))
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["exitCode"], 2)
            self.assertEqual(report["failedCommand"], "assembly-manifest")
            self.assertIn("injected assembly-manifest exception", report["error"])
            self.assertEqual(report["rollback"]["status"], "PASS")
            self.assert_outputs_restored(outputs, before)

    def test_rollback_never_removes_unrelated_file_created_after_start(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            before = output_bytes(outputs)
            report = maintain.prepare_report(repo, runner=MutatingFailureRunner(repo, "publication-manifest", unrelated=True))
            unrelated = repo / "unrelated-after-start.txt"
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(unrelated.is_file())
            self.assertEqual(unrelated.read_bytes(), b"leave me alone\r\n")
            self.assertNotIn("unrelated-after-start.txt", json.dumps(report.get("rollback")))
            self.assert_outputs_restored(outputs, before)

    def test_preexisting_target_blocks_before_any_child_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            accepted_freeze = maintain._freeze_state(repo, [])
            target = outputs["publicationJson"]
            target.write_bytes(b"preexisting target\n")
            before = output_bytes(outputs)
            runner = support.PrepareRunner(repo)
            with (
                patch.object(maintain, "_status", return_value=[]),
                patch.object(maintain, "_freeze_state", return_value=accepted_freeze),
            ):
                report = maintain.prepare_report(repo, runner=runner)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["exitCode"], 2)
            self.assertEqual(runner.calls, [])
            self.assertIn(maintain._rel(repo, target), report["preexistingTargetFiles"])
            self.assertNotIn("inventoryRollbackBaseline", report)
            self.assertNotIn("rollback", report)
            self.assert_outputs_restored(outputs, before)

    def test_successful_prepare_generated_bytes_and_exit_behavior_remain_stable(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            runner = support.PrepareRunner(repo)
            report = maintain.prepare_report(repo, runner=runner)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["exitCode"], 0)
            self.assertNotIn("rollback", report)
            self.assertEqual([x["name"] for x in report["childCommands"]], [
                "strict-inventory", "publication-manifest", "assembly-manifest", "normalization-artifacts"
            ])
            self.assertEqual(outputs["inventoryCsv"].read_bytes(), b"x\n")
            self.assertEqual(outputs["inventoryReport"].read_bytes(), b"x\n")
            self.assertEqual(outputs["publicationMarkdown"].read_bytes(), b"pub\n")
            self.assertEqual(outputs["assemblyMarkdown"].read_bytes(), b"asm\n")
            self.assertEqual(outputs["normalizationStandard"].read_bytes(), b"norm\n")
            self.assertEqual(json.loads(outputs["publicationJson"].read_text(encoding="utf-8"))["status"], "FROZEN")
            self.assertEqual(json.loads(outputs["assemblyJson"].read_text(encoding="utf-8"))["status"], "NORMATIVE")
            self.assertEqual(report["generatedFreezeCompatibility"], "PASS")

    def test_rollback_failure_is_reported_without_replacing_primary_child_failure(self):
        with tempfile.TemporaryDirectory() as t:
            repo = support.fixture(Path(t))
            outputs = declared_outputs(repo)
            original_restore = maintain._restore_inventory_output

            def fail_one(path: Path, snapshot):
                if path == outputs["inventoryCsv"]:
                    raise OSError("injected rollback failure")
                return original_restore(path, snapshot)

            with patch.object(maintain, "_restore_inventory_output", side_effect=fail_one):
                report = maintain.prepare_report(repo, runner=MutatingFailureRunner(repo, "publication-manifest"))
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["exitCode"], 7)
            self.assertEqual(report["failedCommand"], "publication-manifest")
            self.assertEqual(report["childCommands"][-1]["returnCode"], 7)
            self.assertEqual(report["rollback"]["status"], "FAIL")
            self.assertIn("injected rollback failure", report["rollback"]["failures"][0]["error"])


if __name__ == "__main__":
    unittest.main()
