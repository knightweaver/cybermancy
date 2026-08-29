#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounters import esc, load_json, render_package, validate_sidecar
from rulebook_layout.render_assets import prepare_lualatex_render_assets

DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_CONFIG_ROOT = REPO_ROOT / "build/rulebook/layout/encounters"
DEFAULT_PROOF_OUTPUT = DEFAULT_CONFIG_ROOT / "proof-output"
DEFAULT_BUILD_OUTPUT = DEFAULT_CONFIG_ROOT / "chapter-output"

PROOF_CONFIGS = {
    "adversary": "proof/adversary-package-phase-c-v1.json",
    "environment": "proof/environment-package-phase-c-v1.json",
    "feature-reference": "proof/adversary-feature-reference-phase-c-v1.json",
}
PRODUCTION_CONFIGS = {
    "adversary": "adversary-package-v1.json",
    "environment": "environment-package-v1.json",
    "feature-reference": "adversary-feature-reference-v1.json",
}
PROOF_STEMS = {
    "adversary": "Cybermancy_Chapter30_Adversaries_PhaseC_Proof",
    "environment": "Cybermancy_Chapter31_Environments_PhaseC_Proof",
    "feature-reference": "Cybermancy_Chapter32_Adversary_Feature_Reference_PhaseC_Proof",
}
BUILD_STEMS = {
    "adversary": "Cybermancy_Chapter30_Adversaries_Step6",
    "environment": "Cybermancy_Chapter31_Environments_Step6",
    "feature-reference": "Cybermancy_Chapter32_Adversary_Feature_Reference_Step6",
}
FAMILY_BY_KIND = {
    "adversary": "adversaries",
    "environment": "environments",
    "feature-reference": "adversaries-features",
}
EXPECTED_PACKAGE_VERSIONS = {
    "adversary": "v1.1",
    "environment": "v1.0",
    "feature-reference": "v1.0",
}


def _resolve(value: str | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _compile(tex: Path) -> tuple[bool, str]:
    exe = shutil.which("lualatex")
    if not exe:
        return False, "LuaLaTeX not found on PATH"
    logs = []
    for _ in range(2):
        proc = subprocess.run(
            [exe, "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=tex.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        logs.append(proc.stdout or "")
        if proc.returncode:
            return False, "\n".join(logs)
    return True, "\n".join(logs)


def _tier_sort(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10**9


def _feature_reference_display_name(entity: dict[str, Any]) -> str:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    reference = pdata.get("referenceEntry") if isinstance(pdata.get("referenceEntry"), dict) else {}
    return str(reference.get("name") or entity.get("name") or "")


def _feature_is_publication_representative(entity: dict[str, Any]) -> bool:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    equivalence = pdata.get("publicationEquivalence") if isinstance(pdata.get("publicationEquivalence"), dict) else {}
    return equivalence.get("isRepresentative") is not False


def _ordered_full_corpus(sidecar: dict[str, Any], family: str) -> tuple[list[str], list[str]]:
    rows = [
        entity
        for entity in sidecar.get("entities") or []
        if isinstance(entity, dict) and str(entity.get("family") or "") == family
    ]
    if family == "adversaries-features":
        rows = [entity for entity in rows if _feature_is_publication_representative(entity)]
        rows.sort(
            key=lambda entity: (
                _feature_reference_display_name(entity).casefold(),
                str(entity.get("semanticId") or ""),
            )
        )
    else:
        rows.sort(
            key=lambda entity: (
                _tier_sort((entity.get("publicationData") or {}).get("tier")),
                str((entity.get("publicationData") or {}).get("classification") or "").casefold(),
                str(entity.get("name") or "").casefold(),
                str(entity.get("semanticId") or ""),
            )
        )

    semantic_ids: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for entity in rows:
        semantic_id = str(entity.get("semanticId") or "").strip()
        if not semantic_id:
            errors.append(f"{family} contains an entity without semanticId: {entity.get('name')!r}")
            continue
        if semantic_id in seen:
            errors.append(f"{family} contains duplicate semanticId {semantic_id}")
            continue
        seen.add(semantic_id)
        semantic_ids.append(semantic_id)
    return semantic_ids, errors


def _productionize_config(
    sidecar: dict[str, Any],
    config: dict[str, Any],
    kind: str,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    family = FAMILY_BY_KIND[kind]
    errors: list[str] = []
    lifecycle = config.get("lifecycle") if isinstance(config.get("lifecycle"), dict) else {}
    selection = config.get("selection") if isinstance(config.get("selection"), dict) else {}
    policy = config.get("publicationPolicy") if isinstance(config.get("publicationPolicy"), dict) else {}

    if str(lifecycle.get("status") or "") != "frozen":
        errors.append("Production Encounter Toolkit config must have lifecycle.status='frozen'.")
    expected_version = EXPECTED_PACKAGE_VERSIONS[kind]
    if str(lifecycle.get("version") or "") != expected_version:
        errors.append(
            f"Production Encounter Toolkit {kind} config must have lifecycle.version='{expected_version}'."
        )
    if str(selection.get("mode") or "") != "full-corpus":
        errors.append("Production Encounter Toolkit config must select mode='full-corpus'.")
    if not bool(policy.get("requireFullCorpusSelection", False)):
        errors.append("Production Encounter Toolkit config must require full-corpus selection.")

    semantics = sidecar.get("encounterSemantics") if isinstance(sidecar.get("encounterSemantics"), dict) else {}
    if str(semantics.get("status") or "").upper() == "FAIL":
        errors.append("Step 4 encounterSemantics status is FAIL; production build is blocked.")

    semantic_ids, identity_errors = _ordered_full_corpus(sidecar, family)
    errors.extend(identity_errors)

    expected = policy.get("expectedEntryCount")
    try:
        expected_count = int(expected)
    except (TypeError, ValueError):
        expected_count = -1
        errors.append("Production Encounter Toolkit config is missing integer publicationPolicy.expectedEntryCount.")
    if expected_count >= 0 and len(semantic_ids) != expected_count:
        errors.append(
            f"{family} publication corpus contains {len(semantic_ids)} representatives; frozen contract expects {expected_count}."
        )

    feature_publication_status = None
    if kind == "feature-reference":
        feature_equivalence = (
            semantics.get("adversaryFeatureEquivalence")
            if isinstance(semantics.get("adversaryFeatureEquivalence"), dict)
            else {}
        )
        feature_publication_status = str(feature_equivalence.get("publicationStatus") or "")
        if feature_publication_status != "APPLIED":
            errors.append(
                "Chapter 32 requires Step 4 approved Adversary Feature publication equivalence with publicationStatus='APPLIED'."
            )
        applied_count = feature_equivalence.get("publicationRepresentativeCount")
        try:
            applied_count = int(applied_count)
        except (TypeError, ValueError):
            applied_count = -1
        if expected_count >= 0 and applied_count != expected_count:
            errors.append(
                f"Step 4 reports {applied_count} Chapter 32 representatives; frozen contract expects {expected_count}."
            )

    runtime = dict(config)
    runtime["selection"] = {"mode": "full-corpus", "semanticIds": semantic_ids}
    contract = {
        "version": lifecycle.get("version"),
        "status": lifecycle.get("status"),
        "family": family,
        "expectedEntryCount": expected_count,
        "actualEntryCount": len(semantic_ids),
        "ordering": policy.get("ordering"),
        "step4EncounterStatus": semantics.get("status"),
    }
    if kind == "feature-reference":
        contract["step4FeaturePublicationStatus"] = feature_publication_status
    return runtime, contract, errors


def _prepare_feature_reference_sidecar(sidecar: dict[str, Any]) -> dict[str, Any]:
    """Project Step 4 reader-neutral referenceEntry values into the existing renderer view.

    The canonical entity name/rules remain untouched in the saved Step 4 sidecar;
    only this in-memory Chapter 32 render view is overridden.
    """
    rendered = copy.deepcopy(sidecar)
    for entity in rendered.get("entities") or []:
        if not isinstance(entity, dict) or str(entity.get("family") or "") != "adversaries-features":
            continue
        pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
        reference = pdata.get("referenceEntry") if isinstance(pdata.get("referenceEntry"), dict) else None
        if reference is None:
            continue
        if str(reference.get("name") or "").strip():
            entity["name"] = str(reference["name"])
        if str(reference.get("rulesMarkdown") or "").strip():
            pdata["rulesMarkdown"] = str(reference["rulesMarkdown"])
            pdata["description"] = str(reference["rulesMarkdown"])
        if "actions" in reference and isinstance(reference.get("actions"), list):
            pdata["actions"] = copy.deepcopy(reference["actions"])
    return rendered


def _selected_publication_art_references(
    sidecar: dict[str, Any],
    semantic_ids: list[Any],
) -> list[str]:
    wanted = {str(value) for value in semantic_ids if str(value or "").strip()}
    references: set[str] = set()
    for entity in sidecar.get("entities") or []:
        if not isinstance(entity, dict) or str(entity.get("semanticId") or "") not in wanted:
            continue
        publication = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
        art = publication.get("publicationArt") if isinstance(publication.get("publicationArt"), dict) else {}
        reference = str(art.get("image") or publication.get("image") or "").strip().replace("\\", "/")
        if reference:
            references.add(reference)
    return sorted(references)


def _source_asset_path(source_root: Path, reference: str) -> Path:
    return source_root / Path(*PurePosixPath(reference).parts)


def _rewrite_render_asset_paths(
    tex_text: str,
    mapping: dict[str, str],
    source_root: Path,
) -> str:
    rewritten = tex_text
    for reference, render_path in mapping.items():
        source = _source_asset_path(source_root, reference).resolve()
        render = Path(render_path).resolve()
        rewritten = rewritten.replace(
            esc(source.as_posix()),
            esc(render.as_posix()),
        )
    return rewritten


def _prepare_render_assets(
    tex_text: str,
    sidecar: dict[str, Any],
    report: dict[str, Any],
    source_root: Path,
    output: Path,
    kind: str,
) -> tuple[str, dict[str, Any]]:
    references = _selected_publication_art_references(
        sidecar,
        report.get("selectedSemanticIds") if isinstance(report.get("selectedSemanticIds"), list) else [],
    )
    mapping, details = prepare_lualatex_render_assets(
        references,
        source_root,
        output / "_render-assets" / kind,
    )
    return _rewrite_render_asset_paths(tex_text, mapping, source_root), details


def _merge_environment_chapter_opener(tex_text: str) -> tuple[str, bool]:
    """Keep the Chapter 31 title block on the same page as the first Environment."""
    marker = r"\clearpage"
    index = tex_text.find(marker)
    if index < 0:
        return tex_text, False
    return tex_text[:index] + tex_text[index + len(marker):], True


def _make_adversary_needspace_multicol_safe(tex_text: str) -> tuple[str, int]:
    """Use the multicol-safe needspace form for Chapter 30 flow guards.

    Uppercase ``\\Needspace`` uses an explicit break when space is short. Inside
    ``multicols`` that break can terminate the entire page instead of advancing
    to the next column, leaving nearly blank pages. Lowercase ``\\needspace``
    uses penalty/glue-based reservation and lets multicol advance naturally.
    """
    marker = r"\Needspace{"
    count = tex_text.count(marker)
    return tex_text.replace(marker, r"\needspace{"), count


def build_one(
    command: str,
    kind: str,
    sidecar_path: Path,
    source_root: Path,
    config_root: Path,
    output: Path,
    tex_only: bool,
) -> dict[str, Any]:
    sidecar = load_json(sidecar_path)
    errors = validate_sidecar(sidecar)
    if errors:
        return {"status": "FAIL", "command": command, "kind": kind, "errors": errors}

    config_names = PROOF_CONFIGS if command == "proof" else PRODUCTION_CONFIGS
    config_path = config_root / config_names[kind]
    config = load_json(config_path)
    contract: dict[str, Any] | None = None
    if command == "build":
        config, contract, errors = _productionize_config(sidecar, config, kind)
        if errors:
            report = {
                "schema": "cybermancy-step6-encounter-package-build-report-v1.0",
                "status": "FAIL",
                "command": command,
                "kind": kind,
                "config": str(config_path),
                "sidecar": str(sidecar_path),
                "contract": contract,
                "errors": errors,
            }
            output.mkdir(parents=True, exist_ok=True)
            report_path = output / f"{BUILD_STEMS[kind]}.report.json"
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return report

    render_sidecar = _prepare_feature_reference_sidecar(sidecar) if kind == "feature-reference" else sidecar
    tex_text, report = render_package(render_sidecar, config, source_root)
    output.mkdir(parents=True, exist_ok=True)
    stem = (PROOF_STEMS if command == "proof" else BUILD_STEMS)[kind]

    if kind == "adversary":
        tex_text, rewrites = _make_adversary_needspace_multicol_safe(tex_text)
        report["multicolNeedspaceRewrites"] = rewrites

    if kind == "environment":
        tex_text, merged = _merge_environment_chapter_opener(tex_text)
        report["chapterOpenerMergedWithFirstEntry"] = merged

    tex_text, render_assets = _prepare_render_assets(
        tex_text,
        render_sidecar,
        report,
        source_root,
        output,
        kind,
    )
    report["renderAssets"] = render_assets
    if render_assets.get("status") != "PASS":
        report["status"] = "FAIL"
        report.setdefault("errors", []).append(
            "Publication artwork could not be prepared for LuaLaTeX. "
            "See renderAssets.missing/unsupported for details."
        )

    tex_path = output / f"{stem}.tex"
    tex_path.write_text(tex_text, encoding="utf-8")

    report["schema"] = "cybermancy-step6-encounter-package-build-report-v1.0"
    report["command"] = command
    report["kind"] = kind
    report["config"] = str(config_path)
    report["sidecar"] = str(sidecar_path)
    report["tex"] = str(tex_path)
    if contract is not None:
        report["contract"] = contract
        if report.get("entryCount") != contract.get("expectedEntryCount"):
            report["status"] = "FAIL"
            report.setdefault("errors", []).append(
                "Rendered entry count does not match the frozen full-corpus contract."
            )

    if not tex_only and report.get("status") == "PASS":
        ok, log = _compile(tex_path)
        report["status"] = "PASS" if ok else "FAIL"
        report["pdf"] = str(tex_path.with_suffix(".pdf")) if ok else None
        if not ok:
            report.setdefault("errors", []).append("LuaLaTeX compilation failed.")
            report["compileLogTail"] = "\n".join(log.splitlines()[-50:])

    report_path = output / f"{stem}.report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Build Cybermancy Part VI Encounter Toolkit packages from Step 4 structured semantics. "
            "'proof' reproduces the approved Phase C test corpus; 'build' enforces the frozen "
            "full-corpus contracts for Chapters 30-32."
        )
    )
    p.add_argument("command", choices=["proof", "build"])
    p.add_argument("--family", choices=["adversary", "environment", "feature-reference", "all"], default="all")
    p.add_argument("--sidecar")
    p.add_argument("--source-root")
    p.add_argument("--config-root")
    p.add_argument("--output-dir")
    p.add_argument("--tex-only", action="store_true")
    args = p.parse_args()

    sidecar = _resolve(args.sidecar, DEFAULT_SIDECAR)
    source_root = _resolve(args.source_root, DEFAULT_SOURCE_ROOT)
    config_root = _resolve(args.config_root, DEFAULT_CONFIG_ROOT)
    default_output = DEFAULT_PROOF_OUTPUT if args.command == "proof" else DEFAULT_BUILD_OUTPUT
    output = _resolve(args.output_dir, default_output)
    kinds = list(PRODUCTION_CONFIGS) if args.family == "all" else [args.family]
    reports = [
        build_one(args.command, kind, sidecar, source_root, config_root, output, args.tex_only)
        for kind in kinds
    ]
    failed = [report for report in reports if report.get("status") != "PASS"]
    print(json.dumps({"status": "FAIL" if failed else "PASS", "command": args.command, "packages": reports}, indent=2, ensure_ascii=False))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
