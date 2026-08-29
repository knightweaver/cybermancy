import importlib.util
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "build/rulebook/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from rulebook_production.contract import canonical_text_sha256, load_production_contract
from rulebook_production.orchestrator import build_profile, stage_commands
from rulebook_production.preflight import _run_step4_validate
from rulebook_production.reporting import write_json
from rulebook_production.reproducibility import compare_signatures
from rulebook_production.workspace import profile_paths, remove_path


def load_cli():
    path = SCRIPTS / "build-rulebook.py"
    spec = importlib.util.spec_from_file_location("cybermancy_production_cli", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ProductionCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_production_contract(REPO_ROOT)
        cls.cli = load_cli()

    def test_parser_exposes_official_commands_and_profiles(self):
        self.assertEqual(self.cli.REPO_ROOT, REPO_ROOT)
        self.assertEqual(self.cli.parser().parse_args(["preflight"]).command, "preflight")
        build = self.cli.parser().parse_args(["build", "--profile", "all"])
        self.assertEqual(build.profile, "all")
        reproducibility = self.cli.parser().parse_args(
            ["reproducibility", "--profile", "complete-rulebook"]
        )
        self.assertEqual(reproducibility.profile, "complete-rulebook")

    def test_profile_paths_use_release_contract(self):
        complete = profile_paths(REPO_ROOT, self.contract, "complete-rulebook")
        player = profile_paths(REPO_ROOT, self.contract, "player-guide")
        self.assertEqual(complete.release_pdf.name, "Cybermancy_Core_Rulebook.pdf")
        self.assertEqual(player.release_pdf.name, "Cybermancy_Player_Guide.pdf")
        self.assertNotEqual(complete.work, player.work)

    def test_stage_commands_preserve_accepted_order_and_handoffs(self):
        paths = profile_paths(REPO_ROOT, self.contract, "complete-rulebook")
        commands = stage_commands(REPO_ROOT, self.contract, paths)
        self.assertEqual([stage for stage, _ in commands], [130, 140, 150, 160, 170])
        rendered = " ".join(part for _, command in commands for part in command)
        self.assertIn(str(paths.stage130_ast), rendered)
        self.assertIn(str(paths.stage140_ast), rendered)
        self.assertIn(str(paths.release_candidate), rendered)
        self.assertNotIn(str(paths.release_pdf), rendered)

    def test_hash_contract_is_cross_platform(self):
        lf = b"one\ntwo\n"
        self.assertEqual(canonical_text_sha256(lf), canonical_text_sha256(lf.replace(b"\n", b"\r\n")))

    def test_step4_validation_requests_verbose_structured_output(self):
        completed = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"status": "PASS", "checks": []}),
            stderr="Could not find platform independent libraries <prefix>\n",
        )
        with patch("rulebook_production.preflight.subprocess.run", return_value=completed) as run:
            result = _run_step4_validate(REPO_ROOT)

        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["--verbose", "validate"])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["report"]["status"], "PASS")
        self.assertIn("platform independent libraries", result["stderr"])

    def test_step4_validation_fails_closed_on_malformed_output(self):
        completed = SimpleNamespace(
            returncode=0,
            stdout="build-rulebook-source.py: PASS\n",
            stderr="",
        )
        with patch("rulebook_production.preflight.subprocess.run", return_value=completed):
            result = _run_step4_validate(REPO_ROOT)

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("structured JSON", result["report"]["error"])

    def test_step4_validation_requires_zero_exit_code_and_pass_status(self):
        cases = [
            SimpleNamespace(returncode=2, stdout=json.dumps({"status": "PASS"}), stderr=""),
            SimpleNamespace(returncode=0, stdout=json.dumps({"status": "FAIL"}), stderr=""),
        ]
        for completed in cases:
            with self.subTest(returncode=completed.returncode, stdout=completed.stdout):
                with patch("rulebook_production.preflight.subprocess.run", return_value=completed):
                    result = _run_step4_validate(REPO_ROOT)
                self.assertEqual(result["status"], "FAIL")

    def test_workspace_removal_rejects_root_and_outside(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "work"
            root.mkdir()
            with self.assertRaises(ValueError):
                remove_path(root, root)
            with self.assertRaises(ValueError):
                remove_path(Path(temporary) / "outside", root)

    def test_reproducibility_ignores_pdf_byte_identity(self):
        first = {"semanticAstSha256": "a", "pageCount": 10, "pageTextSha256": "b"}
        second = dict(first)
        self.assertEqual(compare_signatures(first, second)["status"], "PASS")
        second["pageCount"] = 11
        self.assertEqual(compare_signatures(first, second)["status"], "FAIL")

    def test_profile_build_publishes_only_after_all_stages_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            contract = deepcopy(self.contract)
            production = repo / "build/rulebook/production"
            production.mkdir(parents=True)
            write_json(production / "production-renderer-v1.json", contract)
            write_json(
                production / "publication-metadata-v1.json",
                {
                    "schema": "cybermancy-publication-metadata-v1",
                    "profiles": {
                        "complete-rulebook": {"readerFacingName": "Cybermancy Core Rulebook"},
                        "player-guide": {"readerFacingName": "Cybermancy Player Guide"},
                    },
                },
            )
            step6 = repo / contract["authorities"]["step6IntegrationContract"]["path"]
            write_json(
                step6,
                {"profiles": {"complete-rulebook": {"chapters": [1, 2]}}},
            )

            def fake_runner(command, **_kwargs):
                report_path = Path(command[command.index("--report") + 1])
                stage = int(report_path.stem.removeprefix("stage"))
                payload = {"status": "PASS", "checks": []}
                if stage == 140:
                    payload["outputAstSha256"] = "semantic"
                elif stage == 150:
                    payload["generation"] = {
                        "assetStaging": {
                            "assets": [{"staged": "assets/a.png", "stagedSha256": "asset"}]
                        }
                    }
                elif stage == 160:
                    payload["pageCount"] = 12
                    payload["checks"] = [
                        {
                            "code": "STAGE160_LUALATEX_AVAILABLE",
                            "details": {"version": "LuaLaTeX test"},
                        }
                    ]
                elif stage == 170:
                    payload["pdfInfo"] = {"pageWidthPt": 612.0, "pageHeightPt": 792.0}
                    payload["renderedStructure"] = {"status": "PASS"}
                    candidate = Path(command[command.index("--output-pdf") + 1])
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    candidate.write_bytes(b"%PDF-test")
                    profile = command[command.index("--profile") + 1]
                    (Path(command[command.index("--work-dir") + 1]) / f"{profile}-layout.txt").write_text(
                        "rendered\n", encoding="utf-8"
                    )
                write_json(report_path, payload)
                return SimpleNamespace(returncode=0)

            result = build_profile(repo, "complete-rulebook", runner=fake_runner)
            paths = profile_paths(repo, contract, "complete-rulebook")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["chapterCount"], 2)
            self.assertTrue(paths.release_pdf.is_file())
            self.assertEqual(paths.release_pdf.read_bytes(), b"%PDF-test")

    def test_contract_json_remains_valid(self):
        path = REPO_ROOT / "build/rulebook/production/production-renderer-v1.json"
        self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
