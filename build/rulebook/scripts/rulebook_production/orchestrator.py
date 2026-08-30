from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from rulebook_layout.encounter_authority import sidecar_encounter_counts

from .contract import (
    canonical_text_sha256,
    load_production_contract,
    load_publication_metadata,
    selected_manifests,
)
from .reporting import add_check, load_json, new_report, repo_relative, timestamp, write_json
from .workspace import ProfilePaths, clean_profile, profile_paths, publish_release


PROFILE_STEMS = {
    "player-guide": "Cybermancy_Player_Guide_Step6_Integrated",
    "complete-rulebook": "Cybermancy_Complete_Rulebook_Step6_Integrated",
}


def stage_commands(repo_root: Path, contract: dict, paths: ProfilePaths) -> list[tuple[int, list[str]]]:
    scripts = repo_root / "build/rulebook/scripts"
    step6_contract = repo_root / contract["authorities"]["step6IntegrationContract"]["path"]
    profile = paths.profile
    stem = PROFILE_STEMS[profile]
    stage160_pdf = paths.stage160_output / f"{stem}.pdf"
    production_contract = repo_root / "build/rulebook/production/production-renderer-v1.json"
    publication_metadata = repo_root / "build/rulebook/production/publication-metadata-v1.json"
    sidecar = repo_root / "build/rulebook/source/metadata/structured-entities.json"
    return [
        (130, [sys.executable, str(scripts / "build-rulebook-step6-publication-shell.py"), "--profile", profile, "--contract", str(step6_contract), "--ast-output", str(paths.stage130_ast), "--report", str(paths.report(130)), "--work-dir", str(paths.work)]),
        (140, [sys.executable, str(scripts / "build-rulebook-step6-post-transform-validation.py"), "--profile", profile, "--contract", str(step6_contract), "--ast-input", str(paths.stage130_ast), "--ast-output", str(paths.stage140_ast), "--report", str(paths.report(140))]),
        (150, [sys.executable, str(scripts / "build-rulebook-step6-integrated-latex.py"), "--profile", profile, "--contract", str(step6_contract), "--ast-input", str(paths.stage140_ast), "--output-dir", str(paths.stage150_output), "--work-dir", str(paths.stage150_work), "--integration-work-root", str(paths.work), "--report", str(paths.report(150)), "--production-contract", str(production_contract), "--publication-metadata", str(publication_metadata), "--sidecar", str(sidecar)]),
        (160, [sys.executable, str(scripts / "build-rulebook-step6-lualatex.py"), "--profile", profile, "--contract", str(step6_contract), "--stage150-dir", str(paths.stage150_output), "--stage150-report", str(paths.report(150)), "--work-dir", str(paths.stage160_work), "--output-dir", str(paths.stage160_output), "--report", str(paths.report(160)), "--production-contract", str(production_contract)]),
        (170, [sys.executable, str(scripts / "build-rulebook-step6-rendered-regression.py"), "--profile", profile, "--contract", str(step6_contract), "--stage160-dir", str(paths.stage160_output), "--stage160-report", str(paths.report(160)), "--pdf-input", str(stage160_pdf), "--work-dir", str(paths.stage170_work), "--output-dir", str(paths.stage170_work), "--output-pdf", str(paths.release_candidate), "--report", str(paths.report(170)), "--production-contract", str(production_contract)]),
    ]


def _git_commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _check_details(report: dict[str, Any], code: str) -> dict[str, Any]:
    for check in report.get("checks") or []:
        if isinstance(check, dict) and check.get("code") == code:
            details = check.get("details")
            return details if isinstance(details, dict) else {}
    return {}


def build_signature(paths: ProfilePaths) -> dict[str, Any]:
    stage140 = load_json(paths.report(140))
    stage150 = load_json(paths.report(150))
    stage160 = load_json(paths.report(160))
    stage170 = load_json(paths.report(170))
    layout_text = paths.stage170_work / f"{paths.profile}-layout.txt"
    asset_rows = stage150.get("generation", {}).get("assetStaging", {}).get("assets") or []
    asset_identity = [
        {"staged": row.get("staged"), "sha256": row.get("stagedSha256")}
        for row in asset_rows
        if isinstance(row, dict)
    ]
    pdf_info = stage170.get("pdfInfo", {})
    return {
        "semanticAstSha256": stage140.get("outputAstSha256"),
        "assetResolutionSha256": _canonical_json_sha256(asset_identity),
        "pageCount": stage160.get("pageCount"),
        "pageTextSha256": canonical_text_sha256(layout_text.read_bytes())
        if layout_text.is_file()
        else None,
        "pageGeometry": {
            "widthPt": pdf_info.get("pageWidthPt"),
            "heightPt": pdf_info.get("pageHeightPt"),
        },
        "renderedStructure": stage170.get("renderedStructure"),
        "publicationShell": stage170.get("productionPublicationShell"),
        "bookmarkStructure": stage160.get("bookmarkStructure"),
    }


def build_profile(
    repo_root: Path,
    profile: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict[str, Any]:
    contract = load_production_contract(repo_root)
    metadata = load_publication_metadata(repo_root)
    if profile not in contract["profiles"]:
        raise ValueError(f"Unknown production profile: {profile}")
    paths = profile_paths(repo_root, contract, profile)
    clean_profile(repo_root, contract, paths)
    report = new_report(
        "cybermancy-production-build-report-v1",
        profile=profile,
        buildTimestamp=timestamp(),
        rendererVersion=contract["version"],
        gitCommit=_git_commit(repo_root),
        step6IntegrationContractVersion="1.0",
        releaseFilename=contract["profiles"][profile]["releaseFilename"],
        stages=[],
    )
    try:
        manifests = selected_manifests(repo_root, contract)
        report["manifestVersions"] = {role: path.name for role, path in manifests.items()}
        report["normalizationVersion"] = manifests["normalizationConfig"].name
    except Exception:
        report["manifestVersions"] = {}
        report["normalizationVersion"] = None

    for stage, command in stage_commands(repo_root, contract, paths):
        print(f"[{profile}] Stage {stage}", flush=True)
        result = runner(command, cwd=repo_root, check=False)
        stage_report = load_json(paths.report(stage)) if paths.report(stage).is_file() else {}
        passed = result.returncode == 0 and stage_report.get("status") == "PASS"
        report["stages"].append(
            {
                "stage": stage,
                "status": "PASS" if passed else "FAIL",
                "returnCode": result.returncode,
                "report": repo_relative(paths.report(stage), repo_root),
            }
        )
        if not passed:
            add_check(report, f"STAGE_{stage}", "FAIL", f"Production stage {stage} failed.")
            break
        add_check(report, f"STAGE_{stage}", "PASS", f"Production stage {stage} passed.")

    if report["status"] == "PASS" and len(report["stages"]) == 5:
        publish_release(paths.release_candidate, paths.release_pdf, paths.release_root)
        stage150 = load_json(paths.report(150))
        stage160 = load_json(paths.report(160))
        stage170 = load_json(paths.report(170))
        preflight_path = repo_root / contract["workspace"]["reportRoot"] / "preflight.json"
        preflight = load_json(preflight_path) if preflight_path.is_file() else {}
        report["pandocVersion"] = preflight.get("toolchain", {}).get("pandoc", {}).get("version")
        report["lualatexVersion"] = _check_details(stage160, "STAGE160_LUALATEX_AVAILABLE").get("version")
        step6_contract = load_json(
            repo_root / contract["authorities"]["step6IntegrationContract"]["path"]
        )
        report["chapterCount"] = len(step6_contract["profiles"][profile]["chapters"])
        structured_counts = dict(contract["structuredExpectations"])
        sidecar = load_json(
            repo_root / "build/rulebook/source/metadata/structured-entities.json"
        )
        structured_counts.update(sidecar_encounter_counts(sidecar))
        report["structuredEntityCounts"] = structured_counts
        report["pageCount"] = stage160.get("pageCount")
        report["validationResult"] = stage170.get("status")
        report["outputPath"] = repo_relative(paths.release_pdf, repo_root)
        report["outputSha256"] = _sha256(paths.release_pdf)
        report["signature"] = build_signature(paths)
        report["publicationShell"] = stage150.get("generation", {}).get("productionShell")
        report["bookmarkStructure"] = stage160.get("bookmarkStructure")
        report["readerFacingName"] = metadata["profiles"][profile]["readerFacingName"]
        add_check(report, "RELEASE_PUBLISH", "PASS", "Validated release candidate published atomically.", report["outputPath"])
    else:
        report["validationResult"] = "FAIL"
        report["outputPath"] = None

    write_json(paths.reports / "build-report.json", report)
    return report
