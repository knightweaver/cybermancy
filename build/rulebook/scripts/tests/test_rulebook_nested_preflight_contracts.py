from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPTS = HERE.parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


source = load_script("rulebook_source_preflight_contract", SCRIPTS / "build-rulebook-source.py")
production = load_script("rulebook_production_preflight_contract", SCRIPTS / "build-rulebook.py")


class NestedPreflightCharacterizationTests(unittest.TestCase):
    def _source_args(self, root: Path):
        return SimpleNamespace(
            output_root=str(root / "output"),
            repo_root=str(root / "repo"),
            config=str(root / "config.json"),
            publication_manifest=str(root / "publication.json"),
            assembly_manifest=str(root / "assembly.json"),
            _resolved_inputs={"characterization": True},
        )

    def test_step4_build_runs_same_repository_manifest_preflight_as_validate_before_materialization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            args = self._source_args(root)
            events: list[tuple[str, object]] = []

            def fake_preflight(_args, include_repo=True):
                events.append(("preflight", include_repo))
                return {"status": "PASS"}, {"pub": 1}, {"asm": 1}, {"config": 1}

            def fake_materialize(_repo_root, stage_root, _pub, _asm, _config, report):
                events.append(("materialize", None))
                stage_root.mkdir(parents=True, exist_ok=True)
                return report

            output = io.StringIO()
            with patch.object(source, "preflight", side_effect=fake_preflight), contextlib.redirect_stdout(output):
                validate_code = source.command_validate(args)
            self.assertEqual(validate_code, 0)
            self.assertEqual(events, [("preflight", True)])

            events.clear()
            output = io.StringIO()
            with (
                patch.object(source, "preflight", side_effect=fake_preflight),
                patch.object(source, "deterministic_build", side_effect=fake_materialize),
                contextlib.redirect_stdout(output),
            ):
                build_code = source.command_build(args)
            self.assertEqual(build_code, 0)
            self.assertEqual(events, [("preflight", True), ("materialize", None)])

    def test_step4_failed_nested_preflight_prevents_materialization_and_surfaces_diagnostics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            args = self._source_args(root)
            report = {
                "status": "BLOCKED",
                "checks": [
                    {
                        "code": "SYNTHETIC_MANIFEST_PREFLIGHT",
                        "status": "BLOCKED",
                        "message": "synthetic manifest mismatch",
                    }
                ],
            }
            output = io.StringIO()
            with (
                patch.object(source, "preflight", return_value=(report, None, None, {})),
                patch.object(source, "deterministic_build") as materialize,
                contextlib.redirect_stdout(output),
            ):
                code = source.command_build(args)
            self.assertEqual(code, 2)
            materialize.assert_not_called()
            self.assertIn("SYNTHETIC_MANIFEST_PREFLIGHT", output.getvalue())
            self.assertIn("synthetic manifest mismatch", output.getvalue())
            validation = root / "output/source/metadata/validation.json"
            self.assertTrue(validation.is_file())
            self.assertIn("synthetic manifest mismatch", validation.read_text(encoding="utf-8"))

    def _production_contract(self):
        return {"workspace": {"reportRoot": "build/rulebook/reports"}}

    def test_production_build_runs_preflight_before_any_production_stage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events: list[str] = []

            def fake_preflight(_repo, _path):
                events.append("preflight")
                return {"status": "PASS"}

            def fake_build(_repo, profile):
                events.append(f"build:{profile}")
                return {"status": "PASS", "profile": profile}

            with (
                patch.object(production, "REPO_ROOT", root),
                patch.object(production, "load_production_contract", return_value=self._production_contract()),
                patch.object(production, "invalidate_release"),
                patch.object(production, "run_preflight", side_effect=fake_preflight),
                patch.object(production, "build_profile", side_effect=fake_build),
                patch.object(production, "write_json"),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = production.main(["build", "--profile", "complete-rulebook"])
            self.assertEqual(code, 0)
            self.assertEqual(events, ["preflight", "build:complete-rulebook"])

    def test_production_reproducibility_runs_preflight_before_both_reproducibility_builds(self):
        from rulebook_production.reproducibility import run_reproducibility as real_reproducibility

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events: list[str] = []

            def fake_preflight(_repo, _path):
                events.append("preflight")
                return {"status": "PASS"}

            def fake_builder(_repo, profile):
                events.append(f"repro-build:{profile}")
                return {"status": "PASS", "profile": profile, "signature": {"stable": True}}

            def reproducibility_with_probe(repo, profile, report_path):
                return real_reproducibility(repo, profile, report_path, builder=fake_builder)

            with (
                patch.object(production, "REPO_ROOT", root),
                patch.object(production, "load_production_contract", return_value=self._production_contract()),
                patch.object(production, "invalidate_release"),
                patch.object(production, "run_preflight", side_effect=fake_preflight),
                patch.object(production, "run_reproducibility", side_effect=reproducibility_with_probe),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = production.main(["reproducibility", "--profile", "complete-rulebook"])
            self.assertEqual(code, 0)
            self.assertEqual(
                events,
                [
                    "preflight",
                    "repro-build:complete-rulebook",
                    "repro-build:complete-rulebook",
                ],
            )

    def test_production_failed_nested_preflight_prevents_rendering_and_surfaces_diagnostics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = {
                "status": "FAIL",
                "checks": [
                    {
                        "code": "SYNTHETIC_PRODUCTION_PREFLIGHT",
                        "status": "FAIL",
                        "message": "synthetic renderer readiness failure",
                    }
                ],
            }
            output = io.StringIO()
            with (
                patch.object(production, "REPO_ROOT", root),
                patch.object(production, "load_production_contract", return_value=self._production_contract()),
                patch.object(production, "invalidate_release"),
                patch.object(production, "run_preflight", return_value=report),
                patch.object(production, "build_profile") as build_profile,
                contextlib.redirect_stdout(output),
            ):
                code = production.main(["build", "--profile", "complete-rulebook"])
            self.assertEqual(code, 2)
            build_profile.assert_not_called()
            self.assertIn("SYNTHETIC_PRODUCTION_PREFLIGHT", output.getvalue())
            self.assertIn("synthetic renderer readiness failure", output.getvalue())


if __name__ == "__main__":
    unittest.main()
