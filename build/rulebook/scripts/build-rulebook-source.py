#!/usr/bin/env python3
"""Cybermancy Step 4 rulebook source normalizer.

Expected repository layout::

    cybermancy/
      build/
        rulebook/
          scripts/
            build-rulebook-source.py
            rulebook_normalize/        # preferred package location
          manifests/
            cybermancy-rulebook-publication-manifest-v*.json
            cybermancy-rulebook-assembly-manifest-v*.json
            cybermancy-rulebook-normalization-config-v*.json

The script is location-aware: it resolves the repository root, manifest directory,
and output root from its own path rather than from the current working directory.
For each run it automatically selects the highest versioned publication manifest,
assembly manifest, and normalization config in build/rulebook/manifests.

Typical usage from the repository root::

    python build/rulebook/scripts/build-rulebook-source.py validate
    python build/rulebook/scripts/build-rulebook-source.py build
    python build/rulebook/scripts/build-rulebook-source.py inspect-manifests

Explicit path overrides remain available for diagnostics, but they are optional.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterable


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
DEFAULT_MANIFEST_DIR = RULEBOOK_DIR / "manifests"
DEFAULT_REPO_ROOT = RULEBOOK_DIR.parent.parent
DEFAULT_OUTPUT_ROOT = RULEBOOK_DIR

# Prefer keeping the normalization package beside this launcher under
# build/rulebook/scripts. Retain the legacy pyCybermancy location as a fallback
# so the launcher can be adopted before the package is moved.
for _package_parent in (
    SCRIPT_DIR,
    DEFAULT_REPO_ROOT / "pyCybermancy",
):
    if (_package_parent / "rulebook_normalize").is_dir():
        _s = str(_package_parent)
        if _s not in sys.path:
            sys.path.insert(0, _s)
        break

try:
    from rulebook_normalize.manifest import (
        ManifestError,
        candidate_collections,
        load_json,
        resolve_pointer,
    )
    from rulebook_normalize.pipeline import (
        deterministic_build,
        manifest_contract_report,
        repository_preflight,
    )
    from rulebook_normalize.snapshot import (
        SnapshotError,
        structured_family_snapshot,
    )
    from rulebook_normalize.structured import collect_source_warnings
    from rulebook_normalize.validate import (
        add_check,
        new_report,
        sum_expected_family_counts,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - startup diagnostic
    raise SystemExit(
        "Could not import the rulebook_normalize package. Place the package at "
        f"{SCRIPT_DIR / 'rulebook_normalize'} (preferred) or "
        f"{DEFAULT_REPO_ROOT / 'pyCybermancy' / 'rulebook_normalize'}.\n"
        f"Original import error: {exc}"
    ) from exc


PUBLICATION_PATTERN = "cybermancy-rulebook-publication-manifest-v*.json"
ASSEMBLY_PATTERN = "cybermancy-rulebook-assembly-manifest-v*.json"
CONFIG_PATTERN = "cybermancy-rulebook-normalization-config-v*.json"

_VERSION_RE = re.compile(
    r"-v(?P<version>\d+(?:\.\d+)*)(?:-r(?P<revision>\d+))?",
    re.IGNORECASE,
)
_CANONICAL_VERSION_SUFFIX_RE = re.compile(
    r"-v\d+(?:\.\d+)*(?:-r\d+)?\.json$",
    re.IGNORECASE,
)

# The Step 4 materializer historically deletes its output root before every
# clean build. Because scripts/ and manifests/ now live inside build/rulebook,
# this launcher builds in a temporary staging root and publishes only generated
# children back into build/rulebook. These source directories are never removed.
RESERVED_OUTPUT_CHILDREN = {"scripts", "manifests"}


class InputDiscoveryError(RuntimeError):
    pass


def load_config(path: Path):
    return load_json(path)


def _version_key(path: Path) -> tuple[tuple[int, ...], int]:
    match = _VERSION_RE.search(path.name)
    if not match:
        raise InputDiscoveryError(f"Could not parse a version from {path.name}")
    version = tuple(int(part) for part in match.group("version").split("."))
    revision = int(match.group("revision") or 0)
    return version, revision


def _display_version(path: Path) -> str:
    match = _VERSION_RE.search(path.name)
    if not match:
        return "unknown"
    value = f"v{match.group('version')}"
    if match.group("revision"):
        value += f"-r{match.group('revision')}"
    return value


def discover_latest(directory: Path, pattern: str, label: str) -> Path:
    """Return the highest numeric version matching *pattern*.

    Versions are compared numerically, so v1.10 sorts after v1.9. Optional
    ``-rN`` revisions are supported. If multiple files represent the same
    highest version, an exact canonical ``...-vX[.Y][-rN].json`` filename wins;
    otherwise the ambiguity is rejected rather than resolved by timestamp.
    """
    if not directory.is_dir():
        raise InputDiscoveryError(f"Manifest directory does not exist: {directory}")

    candidates: list[tuple[tuple[tuple[int, ...], int], Path]] = []
    for path in sorted(directory.glob(pattern)):
        if not path.is_file():
            continue
        try:
            key = _version_key(path)
        except InputDiscoveryError:
            continue
        candidates.append((key, path.resolve()))

    if not candidates:
        raise InputDiscoveryError(
            f"No {label} files found in {directory} matching {pattern}"
        )

    top_key = max(key for key, _ in candidates)
    top = [path for key, path in candidates if key == top_key]
    if len(top) == 1:
        return top[0]

    canonical = [p for p in top if _CANONICAL_VERSION_SUFFIX_RE.search(p.name)]
    if len(canonical) == 1:
        return canonical[0]

    names = ", ".join(p.name for p in top)
    raise InputDiscoveryError(
        f"Multiple {label} files have the same latest version "
        f"({_display_version(top[0])}): {names}. Remove/rename duplicates or "
        "use the explicit override option."
    )


def _resolve_explicit(value: str | None, base: Path) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    # Explicit filenames are most commonly names inside manifests/. Prefer that
    # location, then fall back to the caller's current working directory.
    from_base = (base / path).resolve()
    if from_base.exists():
        return from_base
    return path.resolve()


def _resolve_dir(value: str | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    return Path(value).expanduser().resolve()


def resolve_runtime_paths(args: argparse.Namespace) -> argparse.Namespace:
    manifest_dir = _resolve_dir(getattr(args, "manifest_dir", None), DEFAULT_MANIFEST_DIR)
    repo_root = _resolve_dir(getattr(args, "repo_root", None), DEFAULT_REPO_ROOT)
    output_root = _resolve_dir(getattr(args, "output_root", None), DEFAULT_OUTPUT_ROOT)

    publication = _resolve_explicit(getattr(args, "publication_manifest", None), manifest_dir)
    assembly = _resolve_explicit(getattr(args, "assembly_manifest", None), manifest_dir)
    config = _resolve_explicit(getattr(args, "config", None), manifest_dir)

    if publication is None:
        publication = discover_latest(manifest_dir, PUBLICATION_PATTERN, "publication manifest")
    if assembly is None:
        assembly = discover_latest(manifest_dir, ASSEMBLY_PATTERN, "assembly manifest")
    if args.cmd != "inspect-manifests" and config is None:
        config = discover_latest(manifest_dir, CONFIG_PATTERN, "normalization config")

    args.manifest_dir = str(manifest_dir)
    args.repo_root = str(repo_root)
    args.output_root = str(output_root)
    args.publication_manifest = str(publication)
    args.assembly_manifest = str(assembly)
    args.config = str(config) if config is not None else None

    details = {
        "manifestDirectory": str(manifest_dir),
        "publicationManifest": {
            "path": str(publication),
            "version": _display_version(publication),
        },
        "assemblyManifest": {
            "path": str(assembly),
            "version": _display_version(assembly),
        },
        "repoRoot": str(repo_root),
        "outputRoot": str(output_root),
    }
    if config is not None:
        details["normalizationConfig"] = {
            "path": str(config),
            "version": _display_version(config),
        }
    args._resolved_inputs = details
    return args


def _print_selected_inputs(args: argparse.Namespace) -> None:
    details = args._resolved_inputs
    print(
        "Rulebook inputs:\n"
        f"  publication: {details['publicationManifest']['path']}\n"
        f"  assembly:    {details['assemblyManifest']['path']}\n"
        + (
            f"  config:      {details['normalizationConfig']['path']}\n"
            if "normalizationConfig" in details
            else ""
        )
        + f"  repo root:   {details['repoRoot']}\n"
        + f"  output root: {details['outputRoot']}",
        file=sys.stderr,
    )


def inspect(args: argparse.Namespace) -> int:
    pub = load_json(Path(args.publication_manifest))
    asm = load_json(Path(args.assembly_manifest))
    result = {
        "selectedInputs": args._resolved_inputs,
        "publicationCandidates": candidate_collections(pub),
        "assemblyCandidates": candidate_collections(asm),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _surface_structured_source_warnings(repo_root: Path, asm: dict, report: dict) -> None:
    """Report non-blocking structured-source issues discovered during Step 4."""
    for family_rec in asm.get("structuredFamilies", []):
        family = family_rec.get("familyId")
        source_path = family_rec.get("sourcePath")
        if not family or not source_path:
            continue
        actor_type = family_rec.get("actorType") or ""
        try:
            snapshot = structured_family_snapshot(repo_root, source_path, actor_type)
        except SnapshotError:
            # repository_preflight already reports snapshot/source failures.
            continue
        for record in snapshot.logical_records:
            try:
                warnings = collect_source_warnings(family, record.document)
            except Exception as exc:
                add_check(
                    report,
                    "STRUCTURED_SOURCE_WARNING_SCAN",
                    "WARNING",
                    f"Could not inspect {family} source {record.path}: {exc}",
                )
                continue
            for warning in warnings:
                details = dict(warning.get("details") or {})
                try:
                    details["sourcePath"] = record.path.relative_to(repo_root).as_posix()
                except ValueError:
                    details["sourcePath"] = str(record.path)
                add_check(
                    report,
                    warning.get("code") or "STRUCTURED_SOURCE_WARNING",
                    "WARNING",
                    warning.get("message") or "Structured source warning.",
                    details,
                )


def preflight(args: argparse.Namespace, include_repo: bool = True):
    config = load_config(Path(args.config))
    report = new_report()
    add_check(
        report,
        "AUTO_INPUT_SELECTION",
        "PASS",
        "Latest versioned rulebook inputs resolved automatically.",
        args._resolved_inputs,
    )

    pub_path = Path(args.publication_manifest)
    asm_path = Path(args.assembly_manifest)
    if not pub_path.exists():
        add_check(
            report,
            "PUBLICATION_MANIFEST_PRESENT",
            "BLOCKED",
            f"Required frozen manifest not found: {pub_path}",
        )
    else:
        add_check(report, "PUBLICATION_MANIFEST_PRESENT", "PASS", pub_path.name)
    if not asm_path.exists():
        add_check(
            report,
            "ASSEMBLY_MANIFEST_PRESENT",
            "BLOCKED",
            f"Required frozen manifest not found: {asm_path}",
        )
    else:
        add_check(report, "ASSEMBLY_MANIFEST_PRESENT", "PASS", asm_path.name)

    expected_sum = sum_expected_family_counts(config)
    add_check(
        report,
        "EXPECTED_STRUCTURED_COUNT",
        "PASS"
        if expected_sum == config["baseline"]["expectedLogicalEntities"]
        else "ERROR",
        f"Configured family counts sum to {expected_sum}; baseline expects "
        f"{config['baseline']['expectedLogicalEntities']}.",
    )
    if not (pub_path.exists() and asm_path.exists()):
        return report, None, None, config

    pub = load_json(pub_path)
    asm = load_json(asm_path)
    bindings = config.get("manifestAdapter", {})
    unresolved: list[str] = []
    for manifest_name, doc, section in (
        ("publication", pub, bindings.get("publication", {})),
        ("assembly", asm, bindings.get("assembly", {})),
    ):
        for key, ptr in section.items():
            if key == "notes":
                continue
            if ptr is None:
                unresolved.append(f"{manifest_name}.{key}")
            else:
                try:
                    resolve_pointer(doc, ptr)
                except ManifestError as exc:
                    add_check(report, "MANIFEST_BINDING_INVALID", "ERROR", str(exc))
    if unresolved:
        add_check(
            report,
            "MANIFEST_BINDINGS",
            "BLOCKED",
            "Manifest files are present but strict adapter bindings are not configured.",
            unresolved,
        )
        return report, pub, asm, config

    add_check(report, "MANIFEST_BINDINGS", "PASS", "All configured JSON pointers resolve.")
    contract = manifest_contract_report(pub, asm, config)
    for item in contract["checks"]:
        status = item["status"]
        if status == "PASS":
            add_check(report, item["code"], "PASS", item["message"], item.get("details"))
        elif status == "WARNING":
            add_check(report, item["code"], "WARNING", item["message"], item.get("details"))
        elif status == "BLOCKED":
            add_check(report, item["code"], "BLOCKED", item["message"], item.get("details"))
        else:
            add_check(report, item["code"], "ERROR", item["message"], item.get("details"))

    if include_repo and report["status"] == "PASS":
        repo_root = Path(args.repo_root)
        repository_preflight(repo_root, pub, asm, config, report)
        _surface_structured_source_warnings(repo_root, asm, report)
    return report, pub, asm, config


def command_validate(args: argparse.Namespace) -> int:
    report, _, _, _ = preflight(args, include_repo=True)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _publish_stage(stage_root: Path, output_root: Path) -> None:
    """Publish generated build children without touching scripts/manifests."""
    output_root.mkdir(parents=True, exist_ok=True)
    for child in sorted(stage_root.iterdir(), key=lambda p: p.name.lower()):
        if child.name in RESERVED_OUTPUT_CHILDREN:
            raise RuntimeError(
                f"Build stage unexpectedly produced reserved directory: {child.name}"
            )
        destination = output_root / child.name
        if destination.exists() or destination.is_symlink():
            _remove_existing(destination)
        shutil.move(str(child), str(destination))


def command_build(args: argparse.Namespace) -> int:
    report, pub, asm, config = preflight(args, include_repo=True)
    outroot = Path(args.output_root)
    if report["status"] != "PASS":
        meta = outroot / "source" / "metadata"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "validation.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    # Never hand build/rulebook directly to materialize(): it deletes its output
    # root. Build in a temporary sibling, then publish generated children only.
    outroot.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".cybermancy-rulebook-stage-", dir=str(outroot.parent)
    ) as temp_dir:
        stage_root = Path(temp_dir) / "rulebook"
        report = deterministic_build(
            Path(args.repo_root), stage_root, pub, asm, config, report
        )
        try:
            _publish_stage(stage_root, outroot)
        except Exception as exc:
            add_check(
                report,
                "OUTPUT_PUBLISH",
                "ERROR",
                f"Could not publish staged rulebook output: {exc}",
            )
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 2

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


def _add_common_input_options(parser: argparse.ArgumentParser, include_config: bool) -> None:
    parser.add_argument(
        "--manifest-dir",
        help=(
            "Directory containing versioned manifests/config. Defaults to "
            "build/rulebook/manifests relative to this script."
        ),
    )
    parser.add_argument(
        "--publication-manifest",
        help="Explicit publication manifest override; otherwise latest version is selected.",
    )
    parser.add_argument(
        "--assembly-manifest",
        help="Explicit assembly manifest override; otherwise latest version is selected.",
    )
    if include_config:
        parser.add_argument(
            "--config",
            help="Explicit normalization config override; otherwise latest version is selected.",
        )
        parser.add_argument(
            "--repo-root",
            help=(
                "Repository root override. Defaults to the cybermancy repository inferred "
                "from build/rulebook/scripts."
            ),
        )
        parser.add_argument(
            "--output-root",
            help=(
                "Generated output root. Defaults to build/rulebook; scripts/ and manifests/ "
                "are preserved during clean builds."
            ),
        )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Cybermancy Step 4 rulebook normalizer")
    sub = root.add_subparsers(dest="cmd", required=True)

    build_parser = sub.add_parser("build", help="Validate and materialize the rulebook corpus.")
    _add_common_input_options(build_parser, include_config=True)

    validate_parser = sub.add_parser("validate", help="Run preflight validation only.")
    _add_common_input_options(validate_parser, include_config=True)

    inspect_parser = sub.add_parser(
        "inspect-manifests", help="Inspect automatically selected manifest schemas."
    )
    _add_common_input_options(inspect_parser, include_config=False)

    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args = resolve_runtime_paths(args)
    except InputDiscoveryError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    _print_selected_inputs(args)
    if args.cmd == "inspect-manifests":
        return inspect(args)
    if args.cmd == "validate":
        return command_validate(args)
    if args.cmd == "build":
        return command_build(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
