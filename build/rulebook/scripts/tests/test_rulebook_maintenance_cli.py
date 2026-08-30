from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[4]
SCRIPTS = REPO_ROOT / "build/rulebook/scripts"
MODULE_PATH = SCRIPTS / "maintain-rulebook.py"
if not MODULE_PATH.is_file():  # local generation validation only
    MODULE_PATH = Path("/mnt/data/localrepo2/build/rulebook/scripts/maintain-rulebook.py")
    REPO_ROOT = Path("/mnt/data/localrepo2")
    SCRIPTS = REPO_ROOT / "build/rulebook/scripts"
spec = importlib.util.spec_from_file_location("maintain_rulebook", MODULE_PATH)
maintain = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(maintain)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def baseline() -> dict:
    return {"status": "PASS", "checks": [{"code": "FREEZE_ARTIFACT_COMPATIBILITY", "status": "PASS"}]}


def fixture(root: Path) -> Path:
    repo = root / "repo"; repo.mkdir(); git(repo, "init")
    git(repo, "config", "user.email", "test@example.com"); git(repo, "config", "user.name", "Test")
    scripts = repo / "build/rulebook/scripts"; scripts.mkdir(parents=True)
    for name in ("build-rulebook-inventory.py", "build-rulebook-publication-manifest.py", "build-rulebook-assembly-manifest.py", "build-rulebook-normalization-artifacts.py", "build-rulebook-source.py", "build-rulebook.py"):
        (scripts / name).write_text("# fixture\n", encoding="utf-8")
    write_json(repo / maintain.PRODUCTION_CONTRACT_RELATIVE, {
        "schema": "cybermancy-production-renderer-contract-v1", "version": "1.0", "contractStatus": "ACCEPTED",
        "authorities": {
            "publicationManifest": {"directory": "build/rulebook/manifests", "pattern": "cybermancy-rulebook-publication-manifest-v*.json"},
            "assemblyManifest": {"directory": "build/rulebook/manifests", "pattern": "cybermancy-rulebook-assembly-manifest-v*.json"},
            "normalizationConfig": {"directory": "build/rulebook/manifests", "pattern": "cybermancy-rulebook-normalization-config-v*.json"},
        },
        "workspace": {"releaseRoot": "build/rulebook/output", "reportRoot": "build/rulebook/reports"},
        "profiles": {"complete-rulebook": {"releaseFilename": "Cybermancy_Core_Rulebook.pdf"}, "player-guide": {"releaseFilename": "Cybermancy_Player_Guide.pdf"}},
        "upstreamReadiness": {"requiredArtifacts": []},
    })
    m = repo / maintain.MANIFEST_DIR_RELATIVE
    write_json(m / "cybermancy-rulebook-publication-manifest-v1.24.json", {
        "status": "FROZEN", "repository": {"gitCommit": "source"},
        "validationSources": {"inventoryJson": {"file": "rulebook-inventory.json"}},
        "publicationInputs": {"authoredDocuments": [], "structuredFamilies": []},
    })
    write_json(m / "cybermancy-rulebook-assembly-manifest-v1.24.json", {"status": "NORMATIVE", "authority": {"parentPublicationManifest": "cybermancy-rulebook-publication-manifest-v1.24.json", "sourceCommit": "source"}})
    write_json(m / "cybermancy-rulebook-normalization-config-v1.24.json", {"authority": {"publicationManifest": "cybermancy-rulebook-publication-manifest-v1.24.json", "assemblyManifest": "cybermancy-rulebook-assembly-manifest-v1.24.json"}, "baseline": {"commit": "source"}})
    write_json(repo / maintain.INVENTORY_RELATIVE, {"repository": {"git_commit": "inventory"}})
    (repo / "build/rulebook/inventory/rulebook-inventory.csv").write_text("x\n", encoding="utf-8")
    (repo / "build/rulebook/inventory/rulebook-inventory-report.md").write_text("x\n", encoding="utf-8")
    git(repo, "add", "."); git(repo, "commit", "-m", "fixture")
    return repo


class PrepareRunner:
    def __init__(self, repo: Path, fail: str | None = None): self.repo, self.fail, self.calls = repo, fail, []
    def __call__(self, command, **_kwargs):
        self.calls.append(list(command)); script = Path(command[1]).name
        label = {"build-rulebook-inventory.py": "strict-inventory", "build-rulebook-publication-manifest.py": "publication-manifest", "build-rulebook-assembly-manifest.py": "assembly-manifest", "build-rulebook-normalization-artifacts.py": "normalization-artifacts"}.get(script, script)
        if label == self.fail: return SimpleNamespace(returncode=7, stdout="out", stderr="err")
        if script == "build-rulebook-inventory.py":
            d = Path(command[command.index("--output-dir") + 1]); write_json(d / "rulebook-inventory.json", {"repository": {"git_commit": git(self.repo, "rev-parse", "HEAD")}}); (d / "rulebook-inventory.csv").write_text("x\n"); (d / "rulebook-inventory-report.md").write_text("x\n")
        elif script == "build-rulebook-publication-manifest.py":
            d = Path(command[command.index("--manifest-dir") + 1]); v = command[command.index("--version") + 1]; head = git(self.repo, "rev-parse", "HEAD"); stem = f"cybermancy-rulebook-publication-manifest-v{v}"
            write_json(d / f"{stem}.json", {"status": "FROZEN", "repository": {"gitCommit": head}, "validationSources": {"inventoryJson": {"file": "rulebook-inventory.json"}}, "publicationInputs": {"authoredDocuments": [], "structuredFamilies": []}}); (d / f"{stem}.md").write_text("pub\n")
        elif script == "build-rulebook-assembly-manifest.py":
            pub = Path(command[command.index("--publication-manifest") + 1]); d = Path(command[command.index("--manifests-dir") + 1]); v = pub.stem.split("-v", 1)[1]; data = json.loads(pub.read_text()); stem = f"cybermancy-rulebook-assembly-manifest-v{v}"
            write_json(d / f"{stem}.json", {"status": "NORMATIVE", "authority": {"parentPublicationManifest": pub.name, "sourceCommit": data["repository"]["gitCommit"]}}); (d / f"{stem}.md").write_text("asm\n")
        elif script == "build-rulebook-normalization-artifacts.py":
            pub = Path(command[command.index("--publication-manifest") + 1]); asm = Path(command[command.index("--assembly-manifest") + 1]); d = Path(command[command.index("--manifest-dir") + 1]); v = pub.stem.split("-v", 1)[1]; data = json.loads(pub.read_text())
            write_json(d / f"cybermancy-rulebook-normalization-config-v{v}.json", {"authority": {"publicationManifest": pub.name, "assemblyManifest": asm.name}, "baseline": {"commit": data["repository"]["gitCommit"]}}); (d / f"cybermancy-rulebook-normalization-standard-v{v}.md").write_text("norm\n")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")


class BuildRunner:
    def __init__(self, fail: tuple[str, str] | None = None): self.fail, self.calls = fail, []
    def __call__(self, command, **_kwargs):
        self.calls.append(list(command)); key = (Path(command[1]).name, command[2] if len(command) > 2 else "")
        return SimpleNamespace(returncode=5, stdout="boom", stderr="bad") if key == self.fail else SimpleNamespace(returncode=0, stdout="ok", stderr="")


class MaintenanceCliTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(maintain, "run_baseline_check", side_effect=lambda _repo: baseline()); p.start(); self.addCleanup(p.stop)

    def test_prepare_exact_order_and_no_step4_or_production(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); runner = PrepareRunner(repo); r = maintain.prepare_report(repo, runner=runner)
            self.assertEqual(r["status"], "PASS"); self.assertEqual([x["name"] for x in r["childCommands"]], ["strict-inventory", "publication-manifest", "assembly-manifest", "normalization-artifacts"])
            self.assertFalse({"build-rulebook-source.py", "build-rulebook.py"} & {Path(x[1]).name for x in runner.calls})

    def test_prepare_refuses_dirty_tree(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); (repo / "dirty").write_text("x"); runner = PrepareRunner(repo); r = maintain.prepare_report(repo, runner=runner)
            self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(runner.calls, [])

    def test_prepare_stops_after_first_failure(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); runner = PrepareRunner(repo, "publication-manifest"); r = maintain.prepare_report(repo, runner=runner)
            self.assertEqual(r["status"], "FAIL"); self.assertEqual(len(runner.calls), 2); self.assertEqual(r["failedCommand"], "publication-manifest"); self.assertEqual(r["childCommands"][-1]["returnCode"], 7)

    def test_build_refuses_untracked_freezes(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); m = repo / maintain.MANIFEST_DIR_RELATIVE
            write_json(m / "cybermancy-rulebook-publication-manifest-v1.25.json", {"status": "FROZEN", "repository": {"gitCommit": "x"}, "validationSources": {"inventoryJson": {"file": "rulebook-inventory.json"}}, "publicationInputs": {"authoredDocuments": [], "structuredFamilies": []}})
            write_json(m / "cybermancy-rulebook-assembly-manifest-v1.25.json", {"status": "NORMATIVE", "authority": {"parentPublicationManifest": "cybermancy-rulebook-publication-manifest-v1.25.json", "sourceCommit": "x"}})
            write_json(m / "cybermancy-rulebook-normalization-config-v1.25.json", {"authority": {"publicationManifest": "cybermancy-rulebook-publication-manifest-v1.25.json", "assemblyManifest": "cybermancy-rulebook-assembly-manifest-v1.25.json"}, "baseline": {"commit": "x"}})
            with patch.object(maintain, "_status", return_value=[]): r = maintain.build_or_release_report(repo, "complete-rulebook", release=False, runner=BuildRunner())
            self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["recommendedNextAction"], "Generated freeze artifacts must be committed before production build.")

    def test_build_order_and_complete_profile_scope(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); runner = BuildRunner(); r = maintain.build_or_release_report(repo, "complete-rulebook", release=False, runner=runner)
            self.assertEqual(r["status"], "PASS"); self.assertEqual([(Path(x[1]).name, x[2:]) for x in runner.calls], [("build-rulebook-source.py", ["validate"]), ("build-rulebook-source.py", ["build"]), ("build-rulebook.py", ["preflight"]), ("build-rulebook.py", ["build", "--profile", "complete-rulebook"])]); self.assertNotIn("player-guide", " ".join(map(str, runner.calls)))

    def test_build_all_delegates_to_existing_all_profile(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); runner = BuildRunner(); maintain.build_or_release_report(repo, "all", release=False, runner=runner)
            self.assertIn(["build", "--profile", "all"], [x[2:] for x in runner.calls if Path(x[1]).name == "build-rulebook.py"])

    def test_release_reproducibility_only_after_successful_build(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); good = maintain.build_or_release_report(repo, "all", release=True, runner=BuildRunner()); self.assertEqual([x["name"] for x in good["childCommands"]][-2:], ["production-build", "production-reproducibility"])
            bad = maintain.build_or_release_report(repo, "all", release=True, runner=BuildRunner(("build-rulebook.py", "build"))); self.assertNotIn("production-reproducibility", [x["name"] for x in bad["childCommands"]])

    def test_dry_run_invokes_no_mutating_child_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); before = {p.relative_to(repo).as_posix(): p.read_bytes() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}; runner = BuildRunner()
            r = maintain.build_or_release_report(repo, "all", release=True, dry_run=True, runner=runner); self.assertEqual(runner.calls[0][2:], ["validate"]); self.assertTrue(all(not x["mutating"] for x in r["childCommands"])); prep = PrepareRunner(repo); maintain.prepare_report(repo, dry_run=True, runner=prep); self.assertEqual(prep.calls, [])
            after = {p.relative_to(repo).as_posix(): p.read_bytes() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}; self.assertEqual(before, after)

    def test_child_failure_exposes_diagnostics_and_report_paths(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); r = maintain.build_or_release_report(repo, "complete-rulebook", release=False, runner=BuildRunner(("build-rulebook.py", "preflight"))); child = r["childCommands"][-1]
            self.assertEqual(child["returnCode"], 5); self.assertIn("boom", child["stdout"]); self.assertIn("bad", child["stderr"]); self.assertIn("build/rulebook/reports/preflight.json", child["reportPaths"])

    def test_status_after_prepare_requires_commit(self):
        with tempfile.TemporaryDirectory() as t:
            repo = fixture(Path(t)); self.assertEqual(maintain.prepare_report(repo, runner=PrepareRunner(repo))["status"], "PASS"); status = maintain.status_report(repo)
            self.assertTrue(status["freezeArtifactsPendingCommit"]); self.assertEqual(status["recommendedNextAction"], "Generated freeze artifacts must be committed before production build.")

    def test_commands_are_windows_safe_argument_lists(self):
        with tempfile.TemporaryDirectory() as t:
            r = maintain.build_or_release_report(fixture(Path(t)), "all", release=True, dry_run=True, runner=BuildRunner())
            for row in r["plannedCommands"]: self.assertIsInstance(row["command"], list); self.assertNotIn("&&", row["command"]); self.assertNotIn(";", row["command"])

    def test_parser_exposes_required_commands_and_profiles(self):
        self.assertEqual(maintain.parser().parse_args(["status"]).command, "status"); self.assertTrue(maintain.parser().parse_args(["prepare", "--dry-run"]).dry_run); self.assertEqual(maintain.parser().parse_args(["build", "--profile", "complete-rulebook"]).profile, "complete-rulebook"); self.assertEqual(maintain.parser().parse_args(["release", "--profile", "all"]).profile, "all")

    @unittest.skipUnless((SCRIPTS / "build-rulebook.py").is_file(), "requires real repository checkout")
    def test_existing_individual_commands_remain_usable(self):
        for name in ("build-rulebook-inventory.py", "build-rulebook-publication-manifest.py", "build-rulebook-assembly-manifest.py", "build-rulebook-normalization-artifacts.py", "build-rulebook-source.py", "build-rulebook.py"):
            result = subprocess.run([sys.executable, str(SCRIPTS / name), "--help"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr); self.assertIn("usage:", result.stdout.lower())


if __name__ == "__main__": unittest.main()
