#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from rulebook_production.baseline import run_baseline_check
from rulebook_production.contract import load_production_contract, version_key
from rulebook_production.freeze_state import git_tracked, load_selected_freeze
from rulebook_production.reporting import load_json

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[3]
INVENTORY_RELATIVE = Path("build/rulebook/inventory/rulebook-inventory.json")
MANIFEST_DIR_RELATIVE = Path("build/rulebook/manifests")
PRODUCTION_CONTRACT_RELATIVE = Path("build/rulebook/production/production-renderer-v1.json")
STEP4_METADATA_RELATIVE = Path("build/rulebook/source/metadata")
PROFILES = ("complete-rulebook", "player-guide")
PROFILE_CHOICES = (*PROFILES, "all")
INVENTORY_OUTPUT_ROLES = ("inventoryJson", "inventoryCsv", "inventoryReport")
Runner = Callable[..., subprocess.CompletedProcess]


class MaintenanceError(RuntimeError):
    pass


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", check=False,
    )


def _head(repo: Path) -> str:
    result = _git(repo, "rev-parse", "HEAD")
    if result.returncode:
        raise MaintenanceError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def _status(repo: Path) -> list[dict[str, str]]:
    result = _git(repo, "-c", "core.quotepath=false", "status", "--porcelain=v1", "--untracked-files=all")
    if result.returncode:
        raise MaintenanceError((result.stderr or result.stdout).strip())
    rows = []
    for raw in result.stdout.splitlines():
        if len(raw) >= 4:
            rows.append({"status": raw[:2], "path": raw[3:].split(" -> ", 1)[-1].replace("\\", "/"), "raw": raw})
    return rows


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _binding_summary(binding: dict[str, Any]) -> dict[str, Any]:
    artifacts = binding.get("artifacts") if isinstance(binding.get("artifacts"), dict) else {}
    result = {
        "status": binding.get("status"),
        "publicationCommit": binding.get("publicationCommit"),
        "inventoryCommit": binding.get("inventoryCommit"),
        "artifacts": {
            role: (row.get("status") if isinstance(row, dict) else "FAIL")
            for role, row in artifacts.items()
        },
    }
    if binding.get("status") != "PASS":
        result["errors"] = list(binding.get("errors") or [])
    return result


def _freeze_state(repo: Path, changes: list[dict[str, str]]) -> dict[str, Any]:
    contract = load_production_contract(repo)
    shared = load_selected_freeze(repo, contract)
    paths = shared["paths"]
    publication = shared["publication"]
    binding = shared["inventoryBinding"]
    inventory_row = (binding.get("artifacts") or {}).get("inventoryJson") or {}
    inventory_relative = str(inventory_row.get("path") or INVENTORY_RELATIVE.as_posix())
    inventory = repo / inventory_relative
    baseline = run_baseline_check(repo)
    dirty = {row["path"] for row in changes}
    tracked = {"inventory": bool(inventory_row.get("tracked"))}
    modified = {"inventory": _rel(repo, inventory) in dirty}
    for role, path in paths.items():
        tracked[role] = git_tracked(repo, path)
        modified[role] = _rel(repo, path) in dirty
    return {
        "contract": contract, "paths": paths, "publication": publication,
        "inventoryPath": inventory,
        "inventoryCommit": str(binding.get("inventoryCommit") or ""),
        "inventoryBinding": binding,
        "baseline": baseline,
        "compatible": bool(shared["compatible"]),
        "tracked": tracked, "modified": modified,
    }


def _canonical_changes(changes: list[dict[str, str]], publication: dict[str, Any]) -> list[str]:
    inputs = publication.get("publicationInputs") or {}
    exact = {str(row.get("path") or "").replace("\\", "/").strip("/") for row in inputs.get("authoredDocuments") or [] if isinstance(row, dict)}
    prefixes = {"assets/"} | {str(row.get("sourcePath") or "").replace("\\", "/").strip("/") + "/" for row in inputs.get("structuredFamilies") or [] if isinstance(row, dict)}
    return sorted({row["path"] for row in changes if row["path"].strip("/") in exact or any(row["path"].startswith(prefix) for prefix in prefixes if prefix != "/")})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _step4_state(repo: Path, freeze: dict[str, Any]) -> dict[str, Any]:
    required = []
    for relative in freeze["contract"].get("upstreamReadiness", {}).get("requiredArtifacts", []):
        path = repo / str(relative)
        required.append({"path": str(relative), "exists": path.is_dir() if str(relative).endswith("/assets") else path.is_file()})
    result: dict[str, Any] = {"exists": bool(required) and all(row["exists"] for row in required), "fresh": False, "requiredArtifacts": required}
    if not result["exists"]:
        return result
    try:
        metadata = repo / STEP4_METADATA_RELATIVE
        validation = load_json(metadata / "validation.json")
        sidecar = load_json(metadata / "structured-entities.json")
        hashes = json.loads((metadata / "source-hashes.json").read_text(encoding="utf-8-sig"))
        if not isinstance(hashes, list):
            raise MaintenanceError("source-hashes.json is not a list")
        drift = []
        for row in hashes:
            if not isinstance(row, dict):
                drift.append({"error": "invalid source-hash record"}); continue
            path = repo / str(row.get("path") or "")
            actual = _sha256(path) if path.is_file() else None
            if actual != str(row.get("sha256") or ""):
                drift.append({"path": row.get("path"), "expected": row.get("sha256"), "actual": actual})
        expected = str((freeze["publication"].get("repository") or {}).get("gitCommit") or "")
        actual = str(sidecar.get("sourceCommit") or "")
        result.update(validationStatus=validation.get("status"), sourceHashDrift=drift[:100], sourceCommit=actual, publicationCommit=expected)
        result["fresh"] = validation.get("status") == "PASS" and not drift and actual == expected
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def status_report(repo: Path) -> dict[str, Any]:
    report: dict[str, Any] = {"schema": "cybermancy-rulebook-maintenance-status-v1", "command": "status", "status": "PASS", "childCommands": [], "exitCode": 0}
    try:
        head, changes = _head(repo), _status(repo)
        freeze = _freeze_state(repo, changes)
        canonical = _canonical_changes(changes, freeze["publication"])
        step4 = _step4_state(repo, freeze)
        binding = freeze["inventoryBinding"]
        binding_ok = binding.get("status") == "PASS"
        binding_artifacts = binding.get("artifacts") if isinstance(binding.get("artifacts"), dict) else {}
        binding_untracked = any(
            isinstance(row, dict) and row.get("regularFile") and not row.get("tracked")
            for row in binding_artifacts.values()
        )
        pending = not all(freeze["tracked"].values()) or any(freeze["modified"].values()) or binding_untracked
        eligible = not changes and binding_ok and freeze["baseline"].get("status") == "PASS" and all(freeze["tracked"].get(role, False) for role in ("publicationManifest", "assemblyManifest", "normalizationConfig")) and step4.get("fresh", False)
        if pending:
            next_action = "Generated freeze artifacts must be committed before production build."
        elif canonical:
            next_action = "Commit canonical source changes, then run: python build\\rulebook\\scripts\\maintain-rulebook.py prepare"
        elif changes:
            next_action = "Commit or discard working-tree changes, then rerun maintain-rulebook.py status."
        elif not binding_ok:
            next_action = "Restore the committed inventory files bound by the selected publication manifest before building."
        elif not freeze["compatible"]:
            next_action = "Restore or regenerate a compatible freeze set before building."
        else:
            next_action = "python build\\rulebook\\scripts\\maintain-rulebook.py build --profile all"
        report.update(
            head=head, workingTreeClean=not changes, workingTreeChanges=changes,
            changedCanonicalSourcePaths=canonical,
            inventory={"path": _rel(repo, freeze["inventoryPath"]), "recordedCommit": freeze["inventoryCommit"], "tracked": freeze["tracked"]["inventory"], "modified": freeze["modified"]["inventory"]},
            inventoryBinding=_binding_summary(binding),
            selectedFreezes={role: {"path": _rel(repo, path), "tracked": freeze["tracked"][role], "modified": freeze["modified"][role]} for role, path in freeze["paths"].items()},
            freezeCompatibility={"status": "PASS" if freeze["compatible"] else "FAIL", "baselineStatus": freeze["baseline"].get("status")},
            step4GeneratedSource=step4, productionPreflightEligible=eligible,
            freezeArtifactsPendingCommit=pending, recommendedNextAction=next_action,
        )
    except Exception as exc:
        report.update(status="FAIL", exitCode=2, error=f"{type(exc).__name__}: {exc}", recommendedNextAction="Resolve the status error and rerun.")
    return report


def _new_report(command: str, profile: str | None, dry_run: bool) -> dict[str, Any]:
    report = {"schema": "cybermancy-rulebook-maintenance-command-v1", "command": command, "status": "PASS", "dryRun": dry_run, "plannedCommands": [], "childCommands": [], "exitCode": 0, "recommendedNextAction": None}
    if profile:
        report["profile"] = profile
    return report


def _display(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _run_child(repo: Path, spec: dict[str, Any], runner: Runner) -> dict[str, Any]:
    result = runner(spec["command"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", check=False)
    reports = spec.get("reportPaths") or []
    return {"name": spec["name"], "command": spec["command"], "displayCommand": _display(spec["command"]), "mutating": spec["mutating"], "status": "PASS" if result.returncode == 0 else "FAIL", "returnCode": int(result.returncode), "stdout": result.stdout or "", "stderr": result.stderr or "", "reportPaths": [_rel(repo, path) for path in reports], "existingReportPaths": [_rel(repo, path) for path in reports if path.exists()]}


def _append(report: dict[str, Any], child: dict[str, Any]) -> bool:
    report["childCommands"].append(child)
    if child["status"] == "PASS":
        return True
    report.update(status="FAIL", exitCode=child["returnCode"] or 2, failedCommand=child["name"], recommendedNextAction=f"Correct the {child['name']} failure using its diagnostics/report paths, then rerun.")
    return False


def _require_clean(repo: Path, report: dict[str, Any]) -> tuple[str | None, list[dict[str, str]]]:
    try:
        head, changes = _head(repo), _status(repo)
    except Exception as exc:
        report.update(status="FAIL", exitCode=2, error=f"{type(exc).__name__}: {exc}"); return None, []
    report.update(head=head, workingTreeCleanAtStartup=not changes)
    if changes:
        report.update(status="BLOCKED", exitCode=2, workingTreeChanges=changes, recommendedNextAction="Commit or discard working-tree changes before running this maintenance command."); return None, changes
    return head, changes


def _build_safety(repo: Path, report: dict[str, Any]) -> dict[str, Any] | None:
    head, changes = _require_clean(repo, report)
    if head is None:
        return None
    try:
        freeze = _freeze_state(repo, changes)
    except Exception as exc:
        report.update(status="BLOCKED", exitCode=2, error=f"{type(exc).__name__}: {exc}", recommendedNextAction="Restore the accepted tracked freeze set before building."); return None
    report["selectedInventory"] = _rel(repo, freeze["inventoryPath"])
    report["selectedFreezes"] = {role: _rel(repo, path) for role, path in freeze["paths"].items()}
    report["trackedInputs"] = freeze["tracked"]
    report["inventoryBinding"] = _binding_summary(freeze["inventoryBinding"])
    if not all(freeze["tracked"].values()):
        report.update(status="BLOCKED", exitCode=2, recommendedNextAction="Generated freeze artifacts must be committed before production build."); return None
    if freeze["inventoryBinding"].get("status") != "PASS":
        report.update(status="BLOCKED", exitCode=2, recommendedNextAction="Restore the committed inventory files bound by the selected publication manifest before building."); return None
    if freeze["baseline"].get("status") != "PASS" or not freeze["compatible"]:
        report.update(status="BLOCKED", exitCode=2, recommendedNextAction="Restore a compatible accepted freeze baseline before building."); return None
    return freeze


def _next_version(path: Path) -> str:
    version, _ = version_key(path)
    parts = list(version)
    if len(parts) == 1: parts.append(1)
    else: parts[-1] += 1
    return ".".join(map(str, parts))


def _prepare_plan(repo: Path, base: Path) -> tuple[list[dict[str, Any]], dict[str, Path], str]:
    py, scripts, manifests = sys.executable, repo / "build/rulebook/scripts", repo / MANIFEST_DIR_RELATIVE
    invdir, inventory, version = repo / INVENTORY_RELATIVE.parent, repo / INVENTORY_RELATIVE, _next_version(base)
    outputs = {
        "inventoryJson": inventory, "inventoryCsv": invdir / "rulebook-inventory.csv", "inventoryReport": invdir / "rulebook-inventory-report.md",
        "publicationJson": manifests / f"cybermancy-rulebook-publication-manifest-v{version}.json", "publicationMarkdown": manifests / f"cybermancy-rulebook-publication-manifest-v{version}.md",
        "assemblyJson": manifests / f"cybermancy-rulebook-assembly-manifest-v{version}.json", "assemblyMarkdown": manifests / f"cybermancy-rulebook-assembly-manifest-v{version}.md",
        "normalizationConfig": manifests / f"cybermancy-rulebook-normalization-config-v{version}.json", "normalizationStandard": manifests / f"cybermancy-rulebook-normalization-standard-v{version}.md",
    }
    plan = [
        {"name": "strict-inventory", "mutating": True, "command": [py, str(scripts / "build-rulebook-inventory.py"), "--repo-root", str(repo), "--output-dir", str(invdir), "--strict"], "reportPaths": [outputs["inventoryJson"], outputs["inventoryCsv"], outputs["inventoryReport"]]},
        {"name": "publication-manifest", "mutating": True, "command": [py, str(scripts / "build-rulebook-publication-manifest.py"), "--repo-root", str(repo), "--manifest-dir", str(manifests), "--base-manifest", str(base), "--inventory-json", str(inventory), "--version", version], "reportPaths": [outputs["publicationJson"], outputs["publicationMarkdown"]]},
        {"name": "assembly-manifest", "mutating": True, "command": [py, str(scripts / "build-rulebook-assembly-manifest.py"), "--publication-manifest", str(outputs["publicationJson"]), "--manifests-dir", str(manifests)], "reportPaths": [outputs["assemblyJson"], outputs["assemblyMarkdown"]]},
        {"name": "normalization-artifacts", "mutating": True, "command": [py, str(scripts / "build-rulebook-normalization-artifacts.py"), "--manifest-dir", str(manifests), "--publication-manifest", str(outputs["publicationJson"]), "--assembly-manifest", str(outputs["assemblyJson"])], "reportPaths": [outputs["normalizationConfig"], outputs["normalizationStandard"]]},
    ]
    return plan, outputs, version


def _planned(repo: Path, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"name": row["name"], "command": row["command"], "displayCommand": _display(row["command"]), "mutating": row["mutating"], "reportPaths": [_rel(repo, path) for path in row.get("reportPaths") or []]} for row in plan]


def _prepare_preexistence(outputs: dict[str, Path]) -> dict[str, bool]:
    return {role: path.exists() or path.is_symlink() for role, path in outputs.items()}


def _snapshot_inventory_outputs(outputs: dict[str, Path]) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for role in INVENTORY_OUTPUT_ROLES:
        path = outputs[role]
        if path.is_symlink() or not path.is_file():
            raise MaintenanceError(f"Cannot preserve inventory rollback baseline for {path}")
        info = path.stat()
        data = path.read_bytes()
        snapshots[role] = {
            "bytes": data,
            "mode": stat.S_IMODE(info.st_mode),
            "atimeNs": info.st_atime_ns,
            "mtimeNs": info.st_mtime_ns,
        }
    return snapshots


def _inventory_snapshot_report(repo: Path, outputs: dict[str, Path], snapshots: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": role,
            "path": _rel(repo, outputs[role]),
            "sha256": hashlib.sha256(snapshots[role]["bytes"]).hexdigest(),
            "size": len(snapshots[role]["bytes"]),
            "mode": oct(snapshots[role]["mode"]),
            "mtimeNs": snapshots[role]["mtimeNs"],
        }
        for role in INVENTORY_OUTPUT_ROLES
    ]


def _restore_inventory_output(path: Path, snapshot: dict[str, Any]) -> str:
    changed = False
    if path.is_symlink():
        path.unlink()
        changed = True
    elif path.exists() and not path.is_file():
        raise MaintenanceError(f"Rollback target is not a regular file: {path}")
    current = path.read_bytes() if path.is_file() else None
    if current != snapshot["bytes"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(snapshot["bytes"])
        changed = True
    info = path.stat()
    if stat.S_IMODE(info.st_mode) != snapshot["mode"]:
        path.chmod(snapshot["mode"])
        changed = True
    info = path.stat()
    if info.st_atime_ns != snapshot["atimeNs"] or info.st_mtime_ns != snapshot["mtimeNs"]:
        os.utime(path, ns=(snapshot["atimeNs"], snapshot["mtimeNs"]))
        changed = True
    return "restored-inventory" if changed else "verified-inventory"


def _rollback_prepare(
    repo: Path,
    report: dict[str, Any],
    outputs: dict[str, Path],
    preexisting: dict[str, bool],
    inventory_snapshots: dict[str, dict[str, Any]],
) -> None:
    actions: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    for role in INVENTORY_OUTPUT_ROLES:
        path = outputs[role]
        try:
            action = _restore_inventory_output(path, inventory_snapshots[role])
            actions.append({"action": action, "path": _rel(repo, path)})
        except Exception as exc:
            failures.append({"action": "restore-inventory", "path": _rel(repo, path), "error": f"{type(exc).__name__}: {exc}"})
    for role, path in outputs.items():
        if preexisting.get(role, False) or (not path.exists() and not path.is_symlink()):
            continue
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
            else:
                raise MaintenanceError(f"Rollback target has unsupported file type: {path}")
            actions.append({"action": "deleted-new-generated-file", "path": _rel(repo, path)})
        except Exception as exc:
            failures.append({"action": "delete-new-generated-file", "path": _rel(repo, path), "error": f"{type(exc).__name__}: {exc}"})
    rollback: dict[str, Any] = {"attempted": True, "status": "FAIL" if failures else "PASS", "actions": actions}
    if failures:
        rollback["failures"] = failures
    report["rollback"] = rollback


def prepare_report(repo: Path, *, dry_run: bool = False, runner: Runner = subprocess.run) -> dict[str, Any]:
    report = _new_report("prepare", None, dry_run)
    head, changes = _require_clean(repo, report)
    if head is None: return report
    try:
        freeze = _freeze_state(repo, changes)
        if freeze["baseline"].get("status") != "PASS" or not freeze["compatible"]: raise MaintenanceError("Current freeze baseline is not accepted/compatible")
        if not all(freeze["tracked"].get(role, False) for role in ("publicationManifest", "assemblyManifest", "normalizationConfig")): raise MaintenanceError("Current freeze baseline is not fully tracked")
        plan, outputs, version = _prepare_plan(repo, freeze["paths"]["publicationManifest"])
    except Exception as exc:
        report.update(status="BLOCKED", exitCode=2, error=f"{type(exc).__name__}: {exc}", recommendedNextAction="Restore the accepted freeze baseline before preparing a refresh."); return report
    preexisting = _prepare_preexistence(outputs)
    report.update(
        basePublicationManifest=_rel(repo, freeze["paths"]["publicationManifest"]),
        outputVersion=version,
        plannedCommands=_planned(repo, plan),
        generatedFiles=[_rel(repo, path) for path in outputs.values()],
        generatedFilePreexistence=[
            {"role": role, "path": _rel(repo, path), "existedBeforeRun": preexisting[role]}
            for role, path in outputs.items()
        ],
    )
    if dry_run:
        report["recommendedNextAction"] = "Run maintain-rulebook.py prepare without --dry-run after reviewing the plan."; return report
    target_roles = [role for role in outputs if role not in INVENTORY_OUTPUT_ROLES]
    preexisting_targets = [_rel(repo, outputs[role]) for role in target_roles if preexisting[role]]
    if preexisting_targets:
        report.update(
            status="BLOCKED", exitCode=2, preexistingTargetFiles=preexisting_targets,
            recommendedNextAction="Remove or resolve the preexisting next-version target files before preparing a refresh.",
        )
        return report
    try:
        inventory_snapshots = _snapshot_inventory_outputs(outputs)
    except Exception as exc:
        report.update(status="BLOCKED", exitCode=2, error=f"{type(exc).__name__}: {exc}", recommendedNextAction="Restore the accepted tracked inventory outputs before preparing a refresh."); return report
    report["inventoryRollbackBaseline"] = _inventory_snapshot_report(repo, outputs, inventory_snapshots)
    active_command: str | None = None
    try:
        active_command = plan[0]["name"]
        if not _append(report, _run_child(repo, plan[0], runner)):
            _rollback_prepare(repo, report, outputs, preexisting, inventory_snapshots); return report
        active_command = None
        inventory = load_json(outputs["inventoryJson"])
        recorded = str((inventory.get("repository") or {}).get("git_commit") or "")
        report["inventoryRecordedCommit"] = recorded
        if recorded != head:
            report.update(status="FAIL", exitCode=2, error=f"Generated inventory records {recorded or '<missing>'}; expected startup HEAD {head}", recommendedNextAction="Correct inventory provenance before generating freeze artifacts.")
            _rollback_prepare(repo, report, outputs, preexisting, inventory_snapshots); return report
        for spec in plan[1:]:
            active_command = spec["name"]
            if not _append(report, _run_child(repo, spec, runner)):
                _rollback_prepare(repo, report, outputs, preexisting, inventory_snapshots); return report
        active_command = None
        missing = [path for path in outputs.values() if not path.is_file()]
        if missing:
            report.update(status="FAIL", exitCode=2, missingGeneratedFiles=[_rel(repo, path) for path in missing], recommendedNextAction="Restore the missing generator outputs before committing the freeze refresh.")
            _rollback_prepare(repo, report, outputs, preexisting, inventory_snapshots); return report
        pub, asm, cfg = load_json(outputs["publicationJson"]), load_json(outputs["assemblyJson"]), load_json(outputs["normalizationConfig"])
        compatible = pub.get("status") == "FROZEN" and (asm.get("authority") or {}).get("parentPublicationManifest") == outputs["publicationJson"].name and (asm.get("authority") or {}).get("sourceCommit") == (pub.get("repository") or {}).get("gitCommit") and (cfg.get("authority") or {}).get("publicationManifest") == outputs["publicationJson"].name and (cfg.get("authority") or {}).get("assemblyManifest") == outputs["assemblyJson"].name and (cfg.get("baseline") or {}).get("commit") == (pub.get("repository") or {}).get("gitCommit") == head
        report["generatedFreezeCompatibility"] = "PASS" if compatible else "FAIL"
        if not compatible:
            report.update(status="FAIL", exitCode=2, recommendedNextAction="Review generated freeze compatibility before committing anything.")
            _rollback_prepare(repo, report, outputs, preexisting, inventory_snapshots); return report
    except Exception as exc:
        report.update(status="FAIL", exitCode=2, error=f"{type(exc).__name__}: {exc}")
        if active_command and not report.get("failedCommand"):
            report["failedCommand"] = active_command
            report["recommendedNextAction"] = f"Correct the {active_command} exception using its diagnostics, then rerun."
        elif not report.get("recommendedNextAction"):
            report["recommendedNextAction"] = "Correct the prepare failure using its diagnostics, then rerun."
        _rollback_prepare(repo, report, outputs, preexisting, inventory_snapshots)
        return report
    report["recommendedNextAction"] = "Review and commit every generated file listed above. Generated freeze artifacts must be committed before production build."
    return report


def _production_reports(repo: Path, action: str, profile: str) -> list[Path]:
    root = repo / "build/rulebook/reports"
    if action == "preflight": return [root / "preflight.json"]
    paths = [root / "preflight.json", root / f"{action}-{profile}.json"]
    for current in PROFILES if profile == "all" else (profile,):
        paths.append(root / current / ("build-report.json" if action == "build" else "reproducibility.json"))
    return paths


def _build_plan(repo: Path, profile: str, release: bool) -> list[dict[str, Any]]:
    py, scripts = sys.executable, repo / "build/rulebook/scripts"
    source, prod = scripts / "build-rulebook-source.py", scripts / "build-rulebook.py"
    plan = [
        {"name": "step4-build", "mutating": True, "command": [py, str(source), "build"], "reportPaths": [repo / "build/rulebook/source/metadata/validation.json"]},
        {"name": "production-build", "mutating": True, "command": [py, str(prod), "build", "--profile", profile], "reportPaths": _production_reports(repo, "build", profile)},
    ]
    if release: plan.append({"name": "production-reproducibility", "mutating": True, "command": [py, str(prod), "reproducibility", "--profile", profile], "reportPaths": _production_reports(repo, "reproducibility", profile)})
    return plan


def _dry_run_step4_validation(repo: Path) -> dict[str, Any]:
    source = repo / "build/rulebook/scripts/build-rulebook-source.py"
    return {"name": "step4-validate", "mutating": False, "command": [sys.executable, str(source), "validate"], "reportPaths": []}


def build_or_release_report(repo: Path, profile: str, *, release: bool, dry_run: bool = False, runner: Runner = subprocess.run) -> dict[str, Any]:
    name = "release" if release else "build"
    report = _new_report(name, profile, dry_run)
    if _build_safety(repo, report) is None: return report
    plan = _build_plan(repo, profile, release)
    report["plannedCommands"] = _planned(repo, plan)
    if dry_run:
        validation = _dry_run_step4_validation(repo)
        if not _append(report, _run_child(repo, validation, runner)):
            report.update(status="BLOCKED", recommendedNextAction="Refresh/commit the canonical freeze with maintain-rulebook.py prepare, or correct the Step 4 validation failure.")
            return report
        report["canonicalSourcesMatchSelectedPublicationManifest"] = True
        report["recommendedNextAction"] = f"Run maintain-rulebook.py {name} --profile {profile} without --dry-run after reviewing the plan."
        return report
    for spec in plan:
        if not _append(report, _run_child(repo, spec, runner)):
            return report
        if spec["name"] == "step4-build":
            report["canonicalSourcesMatchSelectedPublicationManifest"] = True
    if release:
        contract = load_production_contract(repo)
        selected = PROFILES if profile == "all" else (profile,)
        output = repo / str((contract.get("workspace") or {}).get("releaseRoot") or "build/rulebook/output")
        report["releaseFiles"] = [_rel(repo, output / contract["profiles"][current]["releaseFilename"]) for current in selected]
        report_paths = [path for child in report["childCommands"] for path in child.get("reportPaths") or [] if "reports/" in path]
        report["releaseReportPaths"] = list(dict.fromkeys(report_paths))
        report["recommendedNextAction"] = "Review the release PDFs and reproducibility reports; no Git tag, push, or GitHub Release was created."
    else:
        report["recommendedNextAction"] = "Review the built output; use maintain-rulebook.py release only at a release checkpoint."
    return report


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Safe orchestration wrapper for the existing Cybermancy rulebook maintenance pipeline.")
    sub = root.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="Report maintenance/freeze/Step 4 readiness without writing files."); status.add_argument("--verbose", action="store_true")
    prepare = sub.add_parser("prepare", help="Refresh inventory and versioned Step 2-4 freeze inputs."); prepare.add_argument("--dry-run", action="store_true"); prepare.add_argument("--verbose", action="store_true")
    build = sub.add_parser("build", help="Materialize Step 4 and build one or both production profiles."); build.add_argument("--profile", choices=PROFILE_CHOICES, required=True); build.add_argument("--dry-run", action="store_true"); build.add_argument("--verbose", action="store_true")
    release = sub.add_parser("release", help="Build and then run production reproducibility."); release.add_argument("--profile", choices=PROFILE_CHOICES, required=True); release.add_argument("--dry-run", action="store_true"); release.add_argument("--verbose", action="store_true")
    return root


def _emit(report: dict[str, Any], verbose: bool) -> None:
    if verbose:
        print(json.dumps(report, indent=2, ensure_ascii=False)); return
    print(f"maintain-rulebook.py {report.get('command')}: {report.get('status')}")
    if report.get("command") == "status" and report.get("status") == "PASS":
        inv = report.get("inventory") or {}
        binding = report.get("inventoryBinding") or {}
        print(f"  HEAD: {report.get('head')}")
        print(f"  Working tree: {'clean' if report.get('workingTreeClean') else 'dirty'}")
        print(f"  Inventory: {inv.get('path')} @ {inv.get('recordedCommit') or 'unknown'}")
        print(f"  Inventory binding: {binding.get('status') or 'unknown'}")
        print(f"  Step 4: {'fresh' if (report.get('step4GeneratedSource') or {}).get('fresh') else 'not fresh'}")
        print(f"  Production preflight eligible: {'yes' if report.get('productionPreflightEligible') else 'no'}")
    if report.get("dryRun"):
        for row in report.get("plannedCommands") or []: print(f"  PLAN: {row['displayCommand']}")
    if report.get("generatedFiles") and report.get("status") == "PASS" and not report.get("dryRun"):
        print("  Generated files to review/commit:")
        for path in report["generatedFiles"]: print(f"    {path}")
    if report.get("status") in {"FAIL", "BLOCKED"}:
        if report.get("error"): print(f"  Error: {report['error']}")
        if report.get("failedCommand"): print(f"  Failed command: {report['failedCommand']}")
        children = report.get("childCommands") or []
        if children and children[-1].get("status") == "FAIL":
            child = children[-1]; print(f"  Return code: {child.get('returnCode')}")
            for path in child.get("existingReportPaths") or child.get("reportPaths") or []: print(f"  Report: {path}")
            if child.get("stdout"): print(child["stdout"][-4000:].rstrip())
            if child.get("stderr"): print(child["stderr"][-4000:].rstrip())
    for path in report.get("releaseFiles") or []: print(f"  Release: {path}")
    if report.get("recommendedNextAction"): print(f"  Next: {report['recommendedNextAction']}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "status": report = status_report(REPO_ROOT)
    elif args.command == "prepare": report = prepare_report(REPO_ROOT, dry_run=args.dry_run)
    elif args.command == "build": report = build_or_release_report(REPO_ROOT, args.profile, release=False, dry_run=args.dry_run)
    else: report = build_or_release_report(REPO_ROOT, args.profile, release=True, dry_run=args.dry_run)
    _emit(report, args.verbose)
    return int(report.get("exitCode") or (0 if report.get("status") == "PASS" else 2))


if __name__ == "__main__":
    raise SystemExit(main())
