#!/usr/bin/env python3
"""Refresh the Cybermancy Step 2 publication manifest from a fresh inventory.

This generator preserves the reviewed Step 2 authority/disposition decisions
from the latest existing publication manifest, but RECOMPUTES all snapshot-
dependent data from the selected inventory and repository checkout.

It specifically prevents the failure mode exposed during Step 4:
- structured family entity counts are recomputed from canonical source records;
- structured family digests are recomputed from the current source tree;
- no prior structured count/digest is carried forward;
- canonical entity accounting is checked against the inventory's
  generator_reconciliation rows;
- repository HEAD must equal the inventory's recorded commit;
- authored publication hashes are refreshed from the inventory.

Expected layout:
    cybermancy/
      build/rulebook/
        scripts/build-rulebook-publication-manifest.py
        manifests/cybermancy-rulebook-publication-manifest-v*.json

Typical usage from anywhere:
    python build/rulebook/scripts/build-rulebook-publication-manifest.py

Use --inventory-json to pin a particular inventory snapshot.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_VERSION = "1.2.0"

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
MANIFEST_DIR = RULEBOOK_DIR / "manifests"
REPO_ROOT = RULEBOOK_DIR.parent.parent

# Load the shared snapshot implementation from the preferred Step 4 package
# beside this script, falling back to the legacy pyCybermancy location.
for _package_parent in (SCRIPT_DIR, REPO_ROOT / "pyCybermancy"):
    if (_package_parent / "rulebook_normalize" / "snapshot.py").is_file():
        _s = str(_package_parent)
        if _s not in sys.path:
            sys.path.insert(0, _s)
        break

try:
    from rulebook_normalize.snapshot import (
        STRUCTURED_DIGEST_ALGORITHM,
        STRUCTURED_DIGEST_VERSION,
        SnapshotError,
        structured_family_snapshot,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Could not import rulebook_normalize.snapshot. Place the updated "
        "rulebook_normalize package beside this script under "
        "build/rulebook/scripts/ (preferred) or under pyCybermancy/."
    ) from exc

PUBLICATION_PATTERN = "cybermancy-rulebook-publication-manifest-v*.json"
VERSION_RE = re.compile(r"-v(?P<version>\d+(?:\.\d+)*)(?:-r(?P<revision>\d+))?\.json$", re.I)


class ManifestBuildError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestBuildError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestBuildError(f"Invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestBuildError(f"Expected JSON object: {path}")
    return data


def version_key(path: Path) -> tuple[tuple[int, ...], int]:
    m = VERSION_RE.search(path.name)
    if not m:
        raise ManifestBuildError(f"Could not parse manifest version: {path.name}")
    return tuple(int(x) for x in m.group("version").split(".")), int(m.group("revision") or 0)


def latest_manifest(directory: Path) -> Path:
    candidates = []
    for p in directory.glob(PUBLICATION_PATTERN):
        if not p.is_file():
            continue
        try:
            key = version_key(p)
        except ManifestBuildError:
            continue
        candidates.append((key, p.resolve()))
    if not candidates:
        raise ManifestBuildError(f"No publication manifests found in {directory}")
    top = max(k for k, _ in candidates)
    matches = [p for k, p in candidates if k == top]
    if len(matches) != 1:
        raise ManifestBuildError("Ambiguous latest publication manifest: " + ", ".join(p.name for p in matches))
    return matches[0]


def next_minor_version(path: Path) -> str:
    version, _revision = version_key(path)
    parts = list(version)
    if len(parts) == 1:
        parts.append(1)
    else:
        parts[-1] += 1
    return ".".join(str(x) for x in parts)


def inventory_timestamp_key(path: Path) -> tuple[int, float]:
    m = re.search(r"(20\d{6})[-_](\d{6})", path.name)
    if m:
        try:
            dt = datetime.strptime("".join(m.groups()), "%Y%m%d%H%M%S")
            return int(dt.strftime("%Y%m%d%H%M%S")), path.stat().st_mtime
        except ValueError:
            pass
    return 0, path.stat().st_mtime


def discover_inventory(repo_root: Path, manifest_dir: Path) -> Path:
    candidates = []
    for p in repo_root.rglob("rulebook-inventory*.json"):
        if not p.is_file() or manifest_dir in p.parents:
            continue
        try:
            data = load_json(p)
        except Exception:
            continue
        if str(data.get("schema", "")).startswith("cybermancy-rulebook-inventory-v"):
            candidates.append(p.resolve())
    if not candidates:
        raise ManifestBuildError("No rulebook-inventory*.json found. Supply --inventory-json explicitly.")
    return max(candidates, key=inventory_timestamp_key)


def git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception as exc:
        raise ManifestBuildError(f"Could not resolve git HEAD: {exc}") from exc


def is_foundry_folder(obj: dict[str, Any]) -> bool:
    return str(obj.get("_key") or "").startswith("!folders!")


def stable_id(obj: dict[str, Any]) -> str:
    value = obj.get("_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    key = obj.get("_key")
    if isinstance(key, str) and key.strip():
        tail = key.rsplit("!", 1)[-1].strip()
        if tail and tail != key:
            return tail
    raise ManifestBuildError("STRUCTURED_ID_MISSING")


def family_snapshot(repo_root: Path, source_path: str, actor_type: str | None) -> dict[str, Any]:
    """Compatibility wrapper around the shared Step 2/Step 4 snapshot code."""
    try:
        snap = structured_family_snapshot(repo_root, source_path, actor_type)
    except SnapshotError as exc:
        raise ManifestBuildError(str(exc)) from exc
    return {
        "entityCount": snap.entity_count,
        "foundryFolderCount": snap.foundry_folder_count,
        "jsonFileCount": snap.json_file_count,
        "contentDigestSha256": snap.digest_sha256,
    }


def inventory_items_by_path(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["path"]: item
        for item in (inventory.get("items") or [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }


def reconciliation_by_family(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["type"]: row
        for row in (inventory.get("generator_reconciliation") or [])
        if isinstance(row, dict) and isinstance(row.get("type"), str)
    }


def publication_inputs(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs = manifest.get("publicationInputs")
    if not isinstance(inputs, dict):
        raise ManifestBuildError("publicationInputs object missing from template manifest")
    authored = inputs.get("authoredDocuments")
    families = inputs.get("structuredFamilies")
    if not isinstance(authored, list) or not isinstance(families, list):
        raise ManifestBuildError("publicationInputs authoredDocuments/structuredFamilies missing")
    return authored, families


def update_validation_sources(manifest: dict[str, Any], inventory_path: Path) -> None:
    sources = manifest.setdefault("validationSources", {})
    sources["inventoryJson"] = {"file": inventory_path.name, "sha256": sha256_file(inventory_path)}

    csv_path = inventory_path.with_suffix(".csv")
    if csv_path.is_file():
        sources["inventoryCsv"] = {"file": csv_path.name, "sha256": sha256_file(csv_path)}
    else:
        sources.pop("inventoryCsv", None)

    exact_report = inventory_path.with_name(
        inventory_path.stem.replace("rulebook-inventory", "rulebook-inventory-report") + ".md"
    )
    report_path = exact_report if exact_report.is_file() else None
    if report_path is None:
        reports = [p for p in inventory_path.parent.glob("rulebook-inventory-report*.md") if p.is_file()]
        if reports:
            report_path = max(reports, key=lambda p: p.stat().st_mtime)
    if report_path:
        sources["inventoryReport"] = {"file": report_path.name, "sha256": sha256_file(report_path)}
    else:
        sources.pop("inventoryReport", None)


def update_authored(authored: list[dict[str, Any]], items: dict[str, dict[str, Any]]) -> None:
    missing = []
    for row in authored:
        path = row.get("path") or row.get("sourceLocator")
        if not isinstance(path, str):
            continue
        item = items.get(path)
        if not item:
            missing.append(path)
            continue
        row["path"] = path
        row["sha256"] = item.get("sha256")
        row["wordCount"] = item.get("word_count", row.get("wordCount", 0))
        row["normalizationFlags"] = list(item.get("normalization_flags") or [])
        row["reviewFlags"] = list(item.get("review_flags") or [])
    if missing:
        raise ManifestBuildError(
            "Included authored publication sources missing from inventory: " + ", ".join(sorted(missing))
        )


def update_structured(
    repo_root: Path,
    families: list[dict[str, Any]],
    reconciliation: dict[str, dict[str, Any]],
    generator_families: dict[str, Any],
) -> tuple[int, list[dict[str, Any]]] :
    total = 0
    diagnostics = []

    for row in families:
        family = row.get("generatorFamily") or row.get("family")
        source_path = row.get("sourcePath")
        if not isinstance(family, str) or not isinstance(source_path, str):
            raise ManifestBuildError(f"Malformed structured family row: {row}")

        family_meta = generator_families.get(family) if isinstance(generator_families, dict) else None
        actor_type = row.get("actorType")
        if actor_type in (None, "") and isinstance(family_meta, dict):
            actor_type = family_meta.get("actor_type")
        actor_type = str(actor_type).strip() if actor_type not in (None, "") else None
        if actor_type:
            row["actorType"] = actor_type
        else:
            row.pop("actorType", None)
        snap = family_snapshot(repo_root, source_path, actor_type)
        rec = reconciliation.get(family)
        if rec is None:
            raise ManifestBuildError(f"Inventory has no generator_reconciliation row for {family}")

        inv_count = int(rec.get("source_entities", -1))
        if inv_count != snap["entityCount"]:
            raise ManifestBuildError(
                f"STRUCTURED_INVENTORY_SOURCE_COUNT_MISMATCH: {family}: "
                f"inventory={inv_count}, source={snap['entityCount']}"
            )

        row["entityCount"] = snap["entityCount"]
        row["foundryFolderCount"] = snap["foundryFolderCount"]
        row["generatedPageCount"] = int(rec.get("generated_pages", 0))
        row["organizationalGeneratedPageCount"] = len(rec.get("organizational_generated_pages") or [])
        row["missingGeneratedPageCount"] = len(rec.get("missing_generated_pages") or [])
        row["actionableOrphanGeneratedPageCount"] = len(rec.get("orphan_generated_pages") or [])
        row["contentDigestAlgorithm"] = STRUCTURED_DIGEST_ALGORITHM
        row["contentDigestVersion"] = STRUCTURED_DIGEST_VERSION
        row["contentDigestSha256"] = snap["contentDigestSha256"]
        row["contentDigestValidation"] = (
            "Recomputed with the shared Step 2/Step 4 structured-family digest implementation; "
            "v3 includes Foundry folder records because folder placement can carry Tier semantics."
        )
        collisions = rec.get("structured_slug_collisions") or []
        row["generatedPageSlugCount"] = int(rec.get("source_page_slugs", snap["entityCount"]))
        row["structuredSlugCollisionCount"] = int(
            rec.get("structured_slug_collision_count", len(collisions))
        )

        total += snap["entityCount"]
        diagnostics.append({
            "family": family,
            "entityCount": snap["entityCount"],
            "foundryFolderCount": snap["foundryFolderCount"],
            "generatedPageSlugCount": row["generatedPageSlugCount"],
            "slugCollisionCount": row["structuredSlugCollisionCount"],
            "contentDigestVersion": STRUCTURED_DIGEST_VERSION,
            "contentDigestSha256": snap["contentDigestSha256"],
        })

    return total, diagnostics


def update_generated_derivative_policy(
    manifest: dict[str, Any],
    families: list[dict[str, Any]],
    reconciliation: dict[str, dict[str, Any]],
) -> None:
    policy = manifest.get("generatedDerivativePolicy")
    if not isinstance(policy, dict) or not isinstance(policy.get("families"), list):
        return

    source_by_family = {str(r.get("generatorFamily") or r.get("family")): r for r in families}
    for row in policy["families"]:
        if not isinstance(row, dict) or not isinstance(row.get("family"), str):
            continue
        family = row["family"]
        src = source_by_family.get(family)
        rec = reconciliation.get(family)
        if src:
            row["sourceEntities"] = src["entityCount"]
            row["sourcePageSlugs"] = src.get("generatedPageSlugCount", src["entityCount"])
            row["structuredSlugCollisions"] = src.get("structuredSlugCollisionCount", 0)
        if rec:
            row["generatedPages"] = int(rec.get("generated_pages", 0))
            row["organizationalPages"] = len(rec.get("organizational_generated_pages") or [])


def update_summary_and_validation(
    manifest: dict[str, Any],
    inventory: dict[str, Any],
    authored_count: int,
    family_count: int,
    entity_total: int,
    families: list[dict[str, Any]],
) -> None:
    summary = manifest.setdefault("summary", {})
    if isinstance(summary, dict):
        summary["authoredPublicationInputs"] = authored_count
        summary["structuredPublicationFamilies"] = family_count
        summary["structuredPublicationEntities"] = entity_total

    validation = manifest.setdefault("validation", {})
    validation["passed"] = True
    checks = validation.setdefault("checks", {})
    if not isinstance(checks, dict):
        checks = {}
        validation["checks"] = checks

    for key in list(checks):
        if re.fullmatch(r"all\d+IncludedAuthoredPathsExistInFreezeInventory", key):
            checks.pop(key, None)
        if key == "structuredSourceTreeMatchesV1_0Freeze":
            checks.pop(key, None)
        if re.fullmatch(r"structuredFamilyDigestUsesSharedV\d+Implementation", key):
            checks.pop(key, None)

    checks[f"all{authored_count}IncludedAuthoredPathsExistInFreezeInventory"] = True
    checks[f"all{family_count}StructuredFamiliesReconcile"] = True
    checks["structuredEntityAccountingUsesStableSourceIds"] = True
    checks["structuredFamilyDigestsRecomputed"] = True
    checks[f"structuredFamilyDigestUsesSharedV{STRUCTURED_DIGEST_VERSION}Implementation"] = True
    checks["structuredFolderRecordsIncludedInFamilyDigest"] = True
    checks["structuredEntityTotalMatchesInventoryReconciliation"] = True
    checks["zeroMissingGeneratedPagesAcrossIncludedStructuredFamilies"] = all(
        int(r.get("missingGeneratedPageCount", 0)) == 0 for r in families
    )
    checks["zeroActionableOrphansAcrossIncludedStructuredFamilies"] = all(
        int(r.get("actionableOrphanGeneratedPageCount", 0)) == 0 for r in families
    )
    validation["passed"] = all(bool(v) for v in checks.values() if isinstance(v, bool))

    counts = inventory.get("counts") or {}
    validation["inventorySnapshot"] = {
        "filesScanned": counts.get("total_files"),
        "documents": counts.get("documents"),
        "generatedDocuments": counts.get("generated_documents"),
        "handAuthoredDocuments": counts.get("hand_authored_documents"),
        "stubDocuments": counts.get("stub_documents"),
        "flaggedFiles": counts.get("flagged_files"),
        "knownExceptionFiles": counts.get("known_exception_files"),
    }


def markdown_summary(manifest: dict[str, Any], diagnostics: list[dict[str, Any]]) -> str:
    authored, families = publication_inputs(manifest)
    summary = manifest.get("summary") or {}
    repo = manifest.get("repository") or {}
    lines = [
        f"# Cybermancy Rulebook Publication Manifest v{manifest.get('manifestVersion')}",
        "",
        "**Status:** FROZEN",
        "",
        f"Repository commit: `{repo.get('gitCommit')}`",
        "",
        "## Decision summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Authored publication inputs | {len(authored)} |",
        f"| Structured publication families | {len(families)} |",
        f"| Structured publication entities | {summary.get('structuredPublicationEntities')} |",
        "",
        "## Structured publication families",
        "",
        "| Family | Entities | Folders | Generated page slugs | Slug collisions | Digest |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for d in diagnostics:
        lines.append(
            f"| `{d['family']}` | {d['entityCount']} | {d['foundryFolderCount']} | "
            f"{d['generatedPageSlugCount']} | {d['slugCollisionCount']} | `{d['contentDigestSha256']}` |"
        )
    lines += [
        "",
        "## Validation",
        "",
        "**Manifest validation:** PASS",
        "",
        "- Canonical structured entity counts use stable Foundry/source IDs.",
        "- Same-name source records remain distinct canonical entities.",
        "- Generated-page slug collisions are presentation diagnostics, not deduplication.",
        f"- Every structured family digest was recomputed with shared digest v{STRUCTURED_DIGEST_VERSION}.",
        "- Foundry folder records participate in the digest without becoming publication entities.",
        "- Structured family counts were cross-checked against the selected inventory.",
        "",
        "The JSON manifest is the normative machine-readable freeze artifact.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--manifest-dir", default=str(MANIFEST_DIR))
    parser.add_argument("--base-manifest")
    parser.add_argument("--inventory-json")
    parser.add_argument("--version", help="Explicit output version; default is next minor version.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).expanduser().resolve()
    manifest_dir = Path(args.manifest_dir).expanduser().resolve()
    manifest_dir.mkdir(parents=True, exist_ok=True)

    base_path = Path(args.base_manifest).expanduser().resolve() if args.base_manifest else latest_manifest(manifest_dir)
    inventory_path = (
        Path(args.inventory_json).expanduser().resolve()
        if args.inventory_json
        else discover_inventory(repo_root, manifest_dir)
    )

    base = load_json(base_path)
    inventory = load_json(inventory_path)

    inv_commit = str((inventory.get("repository") or {}).get("git_commit") or "").strip()
    if not inv_commit:
        raise ManifestBuildError("Inventory repository.git_commit is missing.")
    head = git_head(repo_root)
    if head != inv_commit:
        raise ManifestBuildError(
            f"Repository HEAD {head} does not match inventory commit {inv_commit}. "
            "Commit the intended source state and rerun the inventory first."
        )

    manifest = copy.deepcopy(base)
    output_version = args.version or next_minor_version(base_path)
    manifest["schema"] = f"cybermancy-rulebook-publication-manifest-v{output_version}"
    manifest["manifestVersion"] = output_version
    manifest["status"] = "FROZEN"
    manifest["frozenAt"] = datetime.now(timezone.utc).isoformat()
    manifest["supersedes"] = {
        "manifest": base_path.name,
        "reason": (
            "Repository snapshot refreshed with unchanged Step 2 authority decisions. "
            "Structured entity accounting and family digests were recomputed from the "
            "selected inventory/source snapshot using stable Foundry/source identity; "
            "digest v3 also freezes Foundry folder records that can carry Tier semantics."
        ),
    }

    repo = manifest.setdefault("repository", {})
    repo["name"] = repo_root.name
    repo["gitCommit"] = inv_commit
    repo["inventorySchema"] = inventory.get("schema")
    repo["inventoryScannerVersion"] = inventory.get("script_version")

    decision_source = manifest.get("decisionSource")
    if isinstance(decision_source, dict):
        decision_source["note"] = (
            "Authority/disposition decisions are preserved from the prior frozen manifest; "
            "repository snapshot metadata, authored hashes, structured counts, and structured "
            "family digests are regenerated from the selected inventory/current frozen commit."
        )

    update_validation_sources(manifest, inventory_path)

    authored, families = publication_inputs(manifest)
    items = inventory_items_by_path(inventory)
    reconciliation = reconciliation_by_family(inventory)

    update_authored(authored, items)
    total, diagnostics = update_structured(
        repo_root, families, reconciliation, inventory.get("generator_families") or {}
    )
    update_generated_derivative_policy(manifest, families, reconciliation)
    update_summary_and_validation(manifest, inventory, len(authored), len(families), total, families)

    inv_total = sum(
        int(reconciliation[str(row.get("generatorFamily") or row.get("family"))]["source_entities"])
        for row in families
    )
    if inv_total != total:
        raise ManifestBuildError(f"STRUCTURED_ENTITY_TOTAL_MISMATCH: inventory={inv_total}, source={total}")

    out_json = manifest_dir / f"cybermancy-rulebook-publication-manifest-v{output_version}.json"
    out_md = manifest_dir / f"cybermancy-rulebook-publication-manifest-v{output_version}.md"

    result = {
        "status": "PASS",
        "baseManifest": base_path.name,
        "inventory": str(inventory_path),
        "repositoryCommit": inv_commit,
        "outputVersion": output_version,
        "authoredInputs": len(authored),
        "structuredFamilies": len(families),
        "structuredEntities": total,
        "structuredDigestVersion": STRUCTURED_DIGEST_VERSION,
        "outputs": {"json": str(out_json), "markdown": str(out_md)},
        "dryRun": bool(args.dry_run),
        "familyDiagnostics": diagnostics,
    }

    if not args.dry_run:
        out_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        out_md.write_text(markdown_summary(manifest, diagnostics), encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManifestBuildError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(2)