from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from rulebook_layout.toolchain import resolve_tool

from .contract import load_production_contract, selected_manifests, verify_frozen_bindings
from .reporting import add_check, load_json, new_report, repo_relative, timestamp, write_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked(repo_root: Path, path: Path) -> bool:
    relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _tool_version(executable: str, name: str) -> str:
    args = ["-v"] if name in {"pdfinfo", "pdftotext", "pdffonts"} else ["--version"]
    result = subprocess.run(
        [executable, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    lines = ((result.stdout or "") + "\n" + (result.stderr or "")).splitlines()
    return lines[0].strip() if lines else executable


def _check_source_hashes(repo_root: Path, path: Path) -> tuple[bool, dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list) or not records:
        return False, {"error": "source-hashes.json is empty or not a list"}
    drift = []
    for record in records:
        if not isinstance(record, dict):
            drift.append({"record": record, "error": "not an object"})
            continue
        relative = str(record.get("path") or "")
        source = repo_root / relative
        actual = _sha256(source) if source.is_file() else None
        expected = str(record.get("sha256") or "")
        if actual != expected:
            drift.append({"path": relative, "expected": expected, "actual": actual})
    return not drift, {"records": len(records), "drift": drift[:100]}


def _run_step4_validate(repo_root: Path) -> dict[str, Any]:
    script = repo_root / "build/rulebook/scripts/build-rulebook-source.py"
    result = subprocess.run(
        [sys.executable, str(script), "--verbose", "validate"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {
            "status": "FAIL",
            "error": "Step 4 validator did not emit the required structured JSON report.",
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
        }
    return {
        "status": "PASS" if result.returncode == 0 and payload.get("status") == "PASS" else "FAIL",
        "returnCode": result.returncode,
        "report": payload,
        "stderr": result.stderr[-12000:],
    }


def run_preflight(
    repo_root: Path,
    report_path: Path,
    *,
    check_tools: bool = True,
    run_step4_validator: bool = True,
) -> dict[str, Any]:
    report = new_report(
        "cybermancy-production-preflight-v1",
        rendererVersion="1.0",
        buildTimestamp=timestamp(),
        toolchain={"python": {"path": sys.executable, "version": sys.version.split()[0]}},
        selectedManifests={},
    )
    try:
        contract = load_production_contract(repo_root)
    except Exception as exc:
        add_check(report, "PRODUCTION_CONTRACT", "FAIL", str(exc))
        write_json(report_path, report)
        return report
    add_check(report, "PRODUCTION_CONTRACT", "PASS", "Accepted Production Renderer v1 contract loaded.")

    bindings = verify_frozen_bindings(repo_root, contract)
    binding_ok = all(item["status"] == "PASS" for item in bindings)
    add_check(
        report,
        "FROZEN_STEP6_BINDINGS",
        "PASS" if binding_ok else "FAIL",
        "Frozen Step 6 integration and package bindings match canonical text hashes."
        if binding_ok
        else "One or more frozen Step 6 bindings changed or are missing.",
        bindings,
    )

    manifests: dict[str, Path] = {}
    try:
        manifests = selected_manifests(repo_root, contract)
        report["selectedManifests"] = {
            role: repo_relative(path, repo_root) for role, path in manifests.items()
        }
        add_check(report, "FREEZE_ARTIFACT_SELECTION", "PASS", "Selected one versioned freeze artifact for each required role.", report["selectedManifests"])
    except Exception as exc:
        add_check(report, "FREEZE_ARTIFACT_SELECTION", "FAIL", str(exc))

    if manifests:
        tracking = {role: _tracked(repo_root, path) for role, path in manifests.items()}
        add_check(
            report,
            "FREEZE_ARTIFACT_TRACKING",
            "PASS" if all(tracking.values()) else "FAIL",
            "Selected freeze artifacts are tracked by Git."
            if all(tracking.values())
            else "Every selected freeze artifact must be committed to Git.",
            tracking,
        )

    required = []
    for relative in contract["upstreamReadiness"]["requiredArtifacts"]:
        path = repo_root / relative
        exists = path.is_dir() if relative.endswith("/assets") else path.is_file()
        required.append({"path": relative, "status": "PASS" if exists else "FAIL"})
    required_ok = all(item["status"] == "PASS" for item in required)
    add_check(
        report,
        "STEP4_REQUIRED_ARTIFACTS",
        "PASS" if required_ok else "FAIL",
        "All required generated Step 4 artifacts are present."
        if required_ok
        else "Required generated Step 4 artifacts are missing.",
        required,
    )

    metadata_root = repo_root / "build/rulebook/source/metadata"
    if required_ok:
        validation = load_json(metadata_root / "validation.json")
        add_check(
            report,
            "STEP4_VALIDATION_STATUS",
            "PASS" if validation.get("status") == "PASS" else "FAIL",
            "Step 4 validation status is PASS."
            if validation.get("status") == "PASS"
            else "Step 4 validation status is not PASS.",
            {"status": validation.get("status")},
        )
        selection = load_json(metadata_root / "adversary-feature-publication-selection.json")
        selection_ok = (
            selection.get("status") == "APPLIED"
            and selection.get("canonicalSourceFeatureCount") == 419
            and selection.get("publicationRepresentativeCount") == 344
        )
        add_check(
            report,
            "STEP4_FEATURE_SELECTION",
            "PASS" if selection_ok else "FAIL",
            "Approved Adversary Feature projection reconciles 419 canonical entries to 344 representatives."
            if selection_ok
            else "Adversary Feature publication selection is absent, unapplied, or count-drifted.",
            {
                "status": selection.get("status"),
                "canonical": selection.get("canonicalSourceFeatureCount"),
                "published": selection.get("publicationRepresentativeCount"),
            },
        )
        hashes_ok, hash_details = _check_source_hashes(repo_root, metadata_root / "source-hashes.json")
        add_check(
            report,
            "STEP4_SOURCE_FRESHNESS",
            "PASS" if hashes_ok else "FAIL",
            "Recorded Step 4 canonical source hashes match the current checkout."
            if hashes_ok
            else "Step 4 output is stale relative to current canonical source files.",
            hash_details,
        )
        if manifests:
            publication = load_json(manifests["publicationManifest"])
            sidecar = load_json(metadata_root / "structured-entities.json")
            expected_commit = publication.get("repository", {}).get("gitCommit")
            provenance_ok = bool(expected_commit) and sidecar.get("sourceCommit") == expected_commit
            add_check(
                report,
                "STEP4_MANIFEST_PROVENANCE",
                "PASS" if provenance_ok else "FAIL",
                "Generated Step 4 sidecar is bound to the selected publication freeze."
                if provenance_ok
                else "Generated Step 4 sidecar source commit does not match the selected publication freeze.",
                {"expected": expected_commit, "actual": sidecar.get("sourceCommit")},
            )

    if manifests and run_step4_validator:
        step4 = _run_step4_validate(repo_root)
        report["step4Validation"] = step4
        add_check(
            report,
            "CURRENT_CANONICAL_SOURCE_VALIDATION",
            step4["status"],
            "Current canonical sources satisfy the accepted Step 4 manifest contract."
            if step4["status"] == "PASS"
            else "Current canonical sources do not satisfy the accepted Step 4 manifest contract.",
            {"returnCode": step4["returnCode"], "stderr": step4["stderr"]},
        )

    if check_tools:
        for name in contract["requiredTools"]:
            if name == "python":
                continue
            executable = resolve_tool(name)
            if executable:
                report["toolchain"][name] = {
                    "path": executable,
                    "version": _tool_version(executable, name),
                }
            add_check(
                report,
                f"TOOL_{name.upper()}",
                "PASS" if executable else "FAIL",
                f"{name} is available." if executable else f"{name} was not found through the production resolver.",
                report["toolchain"].get(name),
            )

    write_json(report_path, report)
    return report
