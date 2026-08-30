from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from . import PROFILES
from .contract import (
    load_production_contract,
    load_publication_metadata,
    selected_manifests,
    verify_frozen_bindings,
    version_key,
)
from .reporting import add_check, load_json, new_report, repo_relative


EXPECTED_PROFILES = ("complete-rulebook", "player-guide")
EXPECTED_RELEASE_FILENAMES = {
    "complete-rulebook": "Cybermancy_Core_Rulebook.pdf",
    "player-guide": "Cybermancy_Player_Guide.pdf",
}
EXPECTED_PRODUCTION_STAGE_ORDER = (130, 140, 150, 160, 170)
EXPECTED_CHAPTER_TOPOLOGY = {
    "complete-rulebook": (
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
    ),
    "player-guide": (
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        14, 15, 16, 17, 18, 19, 20, 21, 22,
    ),
}


def _worktree_status(repo_root: Path) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def _compatibility_details(
    manifests: dict[str, Path],
    publication: dict[str, Any],
    assembly: dict[str, Any],
    normalization: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    publication_path = manifests["publicationManifest"]
    assembly_path = manifests["assemblyManifest"]
    normalization_path = manifests["normalizationConfig"]
    publication_commit = str(publication.get("repository", {}).get("gitCommit") or "")
    assembly_authority = assembly.get("authority") if isinstance(assembly.get("authority"), dict) else {}
    normalization_authority = (
        normalization.get("authority") if isinstance(normalization.get("authority"), dict) else {}
    )
    baseline = normalization.get("baseline") if isinstance(normalization.get("baseline"), dict) else {}
    keys = {
        "publicationManifest": version_key(publication_path),
        "assemblyManifest": version_key(assembly_path),
        "normalizationConfig": version_key(normalization_path),
    }
    same_version = len(set(keys.values())) == 1
    checks = {
        "sameSelectedVersion": same_version,
        "publicationFrozen": publication.get("status") == "FROZEN",
        "assemblyNormative": assembly.get("status") == "NORMATIVE",
        "assemblyParent": assembly_authority.get("parentPublicationManifest") == publication_path.name,
        "assemblyCommit": assembly_authority.get("sourceCommit") == publication_commit,
        "normalizationPublication": normalization_authority.get("publicationManifest") == publication_path.name,
        "normalizationAssembly": normalization_authority.get("assemblyManifest") == assembly_path.name,
        "normalizationCommit": baseline.get("commit") == publication_commit,
    }
    return all(checks.values()), {
        "selected": {role: path.name for role, path in manifests.items()},
        "versionKeys": {role: [list(key[0]), key[1]] for role, key in keys.items()},
        "repositoryCommit": publication_commit,
        "checks": checks,
    }


def run_baseline_check(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    report = new_report(
        "cybermancy-maintenance-baseline-v1",
        rendererVersion="1.0",
        selectedManifests={},
        profiles={},
        productionStages=[],
        chapterTopology={},
    )

    before_rc, before_status, before_stderr = _worktree_status(repo_root)
    add_check(
        report,
        "WORKTREE_STATUS_AVAILABLE",
        "PASS" if before_rc == 0 else "FAIL",
        "Git working-tree state captured for read-only verification."
        if before_rc == 0
        else "Could not capture Git working-tree state.",
        {"returnCode": before_rc, "stderr": before_stderr[-4000:]},
    )

    contract: dict[str, Any] | None = None
    try:
        contract = load_production_contract(repo_root)
        add_check(report, "PRODUCTION_CONTRACT", "PASS", "Accepted Production Renderer v1 contract loaded.")
    except Exception as exc:
        add_check(report, "PRODUCTION_CONTRACT", "FAIL", f"{type(exc).__name__}: {exc}")

    if contract is not None:
        try:
            bindings = verify_frozen_bindings(repo_root, contract)
            bindings_ok = bool(bindings) and all(item.get("status") == "PASS" for item in bindings)
            add_check(
                report,
                "FROZEN_STEP6_BINDINGS",
                "PASS" if bindings_ok else "FAIL",
                "Frozen Step 6 integration/package hashes match."
                if bindings_ok
                else "One or more frozen Step 6 integration/package hashes changed or are missing.",
                bindings,
            )
        except Exception as exc:
            add_check(report, "FROZEN_STEP6_BINDINGS", "FAIL", f"{type(exc).__name__}: {exc}")

        manifests: dict[str, Path] = {}
        try:
            manifests = selected_manifests(repo_root, contract)
            report["selectedManifests"] = {
                role: repo_relative(path, repo_root) for role, path in manifests.items()
            }
            add_check(
                report,
                "FREEZE_ARTIFACT_SELECTION",
                "PASS",
                "Exactly one highest versioned freeze artifact was selected for each required role.",
                report["selectedManifests"],
            )
        except Exception as exc:
            add_check(report, "FREEZE_ARTIFACT_SELECTION", "FAIL", f"{type(exc).__name__}: {exc}")

        if manifests:
            try:
                publication = load_json(manifests["publicationManifest"])
                assembly = load_json(manifests["assemblyManifest"])
                normalization = load_json(manifests["normalizationConfig"])
                compatible, details = _compatibility_details(
                    manifests, publication, assembly, normalization
                )
                add_check(
                    report,
                    "FREEZE_ARTIFACT_COMPATIBILITY",
                    "PASS" if compatible else "FAIL",
                    "Selected publication, assembly, and normalization freezes are mutually compatible."
                    if compatible
                    else "Selected freeze artifacts are not mutually compatible.",
                    details,
                )
            except Exception as exc:
                add_check(
                    report,
                    "FREEZE_ARTIFACT_COMPATIBILITY",
                    "FAIL",
                    f"{type(exc).__name__}: {exc}",
                )

        try:
            metadata = load_publication_metadata(repo_root)
            contract_profiles = contract.get("profiles") if isinstance(contract.get("profiles"), dict) else {}
            metadata_profiles = metadata.get("profiles") if isinstance(metadata.get("profiles"), dict) else {}
            profile_names_ok = tuple(PROFILES) == EXPECTED_PROFILES and set(contract_profiles) == set(EXPECTED_PROFILES) and set(metadata_profiles) == set(EXPECTED_PROFILES)
            release_details: dict[str, Any] = {}
            release_ok = True
            for profile in EXPECTED_PROFILES:
                expected = EXPECTED_RELEASE_FILENAMES[profile]
                contract_name = (contract_profiles.get(profile) or {}).get("releaseFilename")
                metadata_name = (metadata_profiles.get(profile) or {}).get("releaseFilename")
                current_ok = contract_name == expected and metadata_name == expected
                release_ok = release_ok and current_ok
                release_details[profile] = {
                    "expected": expected,
                    "contract": contract_name,
                    "metadata": metadata_name,
                    "status": "PASS" if current_ok else "FAIL",
                }
            profiles_ok = profile_names_ok and release_ok
            report["profiles"] = release_details
            add_check(
                report,
                "PRODUCTION_PROFILES",
                "PASS" if profiles_ok else "FAIL",
                "Official production profiles and release filenames are unchanged."
                if profiles_ok
                else "Production profile names or release filenames changed.",
                {"profiles": list(PROFILES), "releases": release_details},
            )
        except Exception as exc:
            add_check(report, "PRODUCTION_PROFILES", "FAIL", f"{type(exc).__name__}: {exc}")

        production_tail = tuple(
            int(row.get("order"))
            for row in contract.get("transformOrder") or []
            if isinstance(row, dict) and int(row.get("order") or 0) >= 130
        )
        report["productionStages"] = list(production_tail)
        add_check(
            report,
            "PRODUCTION_STAGE_ORDER",
            "PASS" if production_tail == EXPECTED_PRODUCTION_STAGE_ORDER else "FAIL",
            "Production stage order remains 130 -> 140 -> 150 -> 160 -> 170."
            if production_tail == EXPECTED_PRODUCTION_STAGE_ORDER
            else "Production stage order changed.",
            {"expected": list(EXPECTED_PRODUCTION_STAGE_ORDER), "actual": list(production_tail)},
        )

        try:
            step6_path = repo_root / contract["authorities"]["step6IntegrationContract"]["path"]
            step6 = load_json(step6_path)
            topology: dict[str, list[int]] = {}
            topology_ok = (
                step6.get("schema") == "cybermancy-step6-integration-contract-v1"
                and step6.get("version") == "1.0"
                and step6.get("status") == "accepted"
            )
            for profile, expected in EXPECTED_CHAPTER_TOPOLOGY.items():
                actual = tuple(
                    int(value)
                    for value in (step6.get("profiles", {}).get(profile, {}).get("chapters") or [])
                )
                topology[profile] = list(actual)
                topology_ok = topology_ok and actual == expected
            reserved = step6.get("reservedChapters", {}).get("13", {})
            topology_ok = topology_ok and reserved.get("chapterNodeAllowed") is False and reserved.get("placeholderAllowed") is False
            report["chapterTopology"] = topology
            add_check(
                report,
                "CHAPTER_TOPOLOGY",
                "PASS" if topology_ok else "FAIL",
                "Accepted chapter topology, including reserved Chapter 13, is unchanged."
                if topology_ok
                else "Accepted chapter topology changed.",
                {
                    "profiles": topology,
                    "reservedChapter13": reserved,
                },
            )
        except Exception as exc:
            add_check(report, "CHAPTER_TOPOLOGY", "FAIL", f"{type(exc).__name__}: {exc}")

    after_rc, after_status, after_stderr = _worktree_status(repo_root)
    worktree_unchanged = before_rc == 0 and after_rc == 0 and before_status == after_status
    add_check(
        report,
        "READ_ONLY_WORKTREE",
        "PASS" if worktree_unchanged else "FAIL",
        "Baseline check left repository content unchanged."
        if worktree_unchanged
        else "Repository working-tree state changed while running the baseline check.",
        {
            "beforeReturnCode": before_rc,
            "afterReturnCode": after_rc,
            "before": before_status,
            "after": after_status,
            "afterStderr": after_stderr[-4000:],
        },
    )
    return report
