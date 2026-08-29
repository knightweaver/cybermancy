from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProfilePaths:
    profile: str
    work: Path
    reports: Path
    release_root: Path
    release_pdf: Path
    stage130_ast: Path
    stage140_ast: Path
    stage150_output: Path
    stage150_work: Path
    stage160_output: Path
    stage160_work: Path
    stage170_work: Path
    release_candidate: Path

    def report(self, stage: int) -> Path:
        return self.reports / f"stage{stage}.json"


def profile_paths(repo_root: Path, contract: dict, profile: str) -> ProfilePaths:
    workspace = contract["workspace"]
    work = repo_root / workspace["workRoot"] / profile
    reports = repo_root / workspace["reportRoot"] / profile
    release_root = repo_root / workspace["releaseRoot"]
    release_pdf = release_root / contract["profiles"][profile]["releaseFilename"]
    return ProfilePaths(
        profile=profile,
        work=work,
        reports=reports,
        release_root=release_root,
        release_pdf=release_pdf,
        stage130_ast=work / "stage130" / f"{profile}.ast.json",
        stage140_ast=work / "stage140" / f"{profile}.ast.json",
        stage150_output=work / "stage150" / "output",
        stage150_work=work / "stage150" / "work",
        stage160_output=work / "stage160" / "output",
        stage160_work=work / "stage160" / "compile",
        stage170_work=work / "stage170",
        release_candidate=work / "stage170" / contract["profiles"][profile]["releaseFilename"],
    )


def _assert_child(target: Path, root: Path) -> None:
    target_resolved = target.resolve()
    root_resolved = root.resolve()
    if target_resolved == root_resolved or root_resolved not in target_resolved.parents:
        raise ValueError(f"Refusing unsafe workspace operation: {target_resolved}")


def remove_path(target: Path, allowed_root: Path) -> None:
    _assert_child(target, allowed_root)
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def clean_profile(repo_root: Path, contract: dict, paths: ProfilePaths) -> None:
    work_root = repo_root / contract["workspace"]["workRoot"]
    report_root = repo_root / contract["workspace"]["reportRoot"]
    release_root = repo_root / contract["workspace"]["releaseRoot"]
    remove_path(paths.work, work_root)
    remove_path(paths.reports, report_root)
    remove_path(paths.release_pdf, release_root)
    paths.work.mkdir(parents=True, exist_ok=True)
    paths.reports.mkdir(parents=True, exist_ok=True)
    paths.release_root.mkdir(parents=True, exist_ok=True)


def invalidate_release(repo_root: Path, contract: dict, profile: str) -> None:
    paths = profile_paths(repo_root, contract, profile)
    release_root = repo_root / contract["workspace"]["releaseRoot"]
    remove_path(paths.release_pdf, release_root)


def publish_release(candidate: Path, destination: Path, release_root: Path) -> None:
    _assert_child(destination, release_root)
    if not candidate.is_file() or candidate.read_bytes()[:5] != b"%PDF-":
        raise ValueError(f"Validated release candidate is missing or not a PDF: {candidate}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    try:
        shutil.copy2(candidate, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
