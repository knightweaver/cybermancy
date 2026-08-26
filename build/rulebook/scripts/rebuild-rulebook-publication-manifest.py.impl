#!/usr/bin/env python3
"""
Rebuild the Cybermancy Rulebook publication manifest from:
  1) a previously approved publication manifest (authority template), and
  2) a fresh rulebook inventory JSON.

This script is intended for routine repository-content commits where the
publication-scope / source-authority decisions have NOT changed.

It uses only the Python standard library.

Example:
    python tools/rebuild-rulebook-publication-manifest.py \
      --template rulebook/cybermancy-rulebook-publication-manifest-v1.1.json \
      --inventory build/rulebook-inventory.json \
      --inventory-csv build/rulebook-inventory.csv \
      --inventory-report build/rulebook-inventory-report.md \
      --output-dir rulebook

If --version is omitted, the patch component of the template manifestVersion
is incremented automatically (e.g. 1.1 -> 1.2).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Cannot auto-increment manifestVersion {version!r}; pass --version explicitly.")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def decision_fingerprint(decisions: list[dict[str, Any]]) -> str:
    fields = (
        "id", "level", "sourceLocator", "titleOrFamily", "audience",
        "contentScope", "sourceKind", "authority", "disposition",
        "bookSection", "decisionStatus",
    )
    normalized = [
        {k: d.get(k) for k in fields}
        for d in sorted(decisions, key=lambda x: x.get("id", ""))
    ]
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def family_digest(inventory_items: list[dict[str, Any]], source_path: str) -> tuple[str, int]:
    """
    Match the established manifest digest:
      sha256(sorted path + TAB + inventory file sha256)
    over publication entities in a structured source family, excluding
    Foundry folder records.
    """
    prefix = source_path.rstrip("/") + "/"
    rows: list[tuple[str, str]] = []
    for item in inventory_items:
        path = item.get("path", "")
        if not path.startswith(prefix):
            continue
        if item.get("foundry_record_type") == "folder":
            continue
        rows.append((path, item["sha256"]))
    rows.sort()
    payload = "\n".join(f"{path}\t{digest}" for path, digest in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), len(rows)


def validation_source(path: Path | None) -> dict[str, str] | None:
    if path is None:
        return None
    return {"file": path.name, "sha256": sha256_file(path)}


def build_manifest(
    template: dict[str, Any],
    inventory: dict[str, Any],
    *,
    version: str,
    frozen_at: str,
    inventory_path: Path,
    inventory_csv: Path | None,
    inventory_report: Path | None,
    template_path: Path,
) -> dict[str, Any]:
    out = copy.deepcopy(template)

    # Version / snapshot identity.
    previous_version = str(template["manifestVersion"])
    out["manifestVersion"] = version
    out["status"] = "FROZEN"
    out["frozenAt"] = frozen_at
    out["purpose"] = (
        "Freeze the approved Rulebook Step 2 authority and publication-scope decisions "
        "against the current repository inventory snapshot."
    )
    out["supersedes"] = {
        "manifest": template_path.name,
        "reason": "Repository snapshot refresh; publication-scope and source-authority decisions are unchanged.",
        "authorityDecisionDeltas": [],
    }

    # Repository / inventory snapshot.
    out["repository"] = {
        "name": inventory["repository"]["root_name"],
        "gitCommit": inventory["repository"]["git_commit"],
        "inventorySchema": inventory["schema"],
        "inventoryScannerVersion": inventory["script_version"],
    }

    out["validationSources"] = {
        "inventoryJson": validation_source(inventory_path),
        "inventoryCsv": validation_source(inventory_csv),
        "inventoryReport": validation_source(inventory_report),
    }
    out["validationSources"] = {k: v for k, v in out["validationSources"].items() if v is not None}

    # Authority decision fingerprint: routine rebuilds must preserve this.
    decisions = out["decisions"]
    authority_fp = decision_fingerprint(decisions)
    previous_fp = template.get("authorityDecisionFingerprint") or decision_fingerprint(template["decisions"])
    if authority_fp != previous_fp:
        raise RuntimeError(
            "Authority decisions differ from the template. This routine rebuild script is only for "
            "repository-content refreshes. Perform a deliberate authority-manifest rebuild first."
        )
    out["authorityDecisionFingerprint"] = authority_fp

    item_by_path = {item["path"]: item for item in inventory["items"]}
    recon_by_type = {r["type"]: r for r in inventory["generator_reconciliation"]}

    # Refresh authored publication inputs.
    authored_changes = []
    authored_new = []
    for prior in template["publicationInputs"]["authoredDocuments"]:
        d = copy.deepcopy(prior)
        path = d["path"]
        item = item_by_path.get(path)
        if item is None:
            raise RuntimeError(f"Included authored publication source is missing from inventory: {path}")
        old_hash = d.get("sha256")
        new_hash = item["sha256"]
        if old_hash != new_hash:
            authored_changes.append({
                "id": d["id"],
                "path": path,
                "fromSha256": old_hash,
                "toSha256": new_hash,
            })
        d["wordCount"] = item.get("word_count", 0)
        d["sha256"] = new_hash
        d["normalizationFlags"] = item.get("normalization_flags", [])
        d["reviewFlags"] = item.get("review_flags", [])
        authored_new.append(d)

    # Refresh structured publication families and recompute family digests.
    structured_changes = []
    structured_new = []
    for prior in template["publicationInputs"]["structuredFamilies"]:
        f = copy.deepcopy(prior)
        family = f["generatorFamily"]
        if family not in recon_by_type:
            raise RuntimeError(f"Structured publication family {family!r} is absent from inventory reconciliation.")
        recon = recon_by_type[family]
        digest, digest_entity_count = family_digest(inventory["items"], recon["source_path"])
        old_digest = f.get("contentDigestSha256")
        if old_digest != digest:
            structured_changes.append({
                "id": f["id"],
                "generatorFamily": family,
                "sourcePath": recon["source_path"],
                "fromDigestSha256": old_digest,
                "toDigestSha256": digest,
            })

        f["sourcePath"] = recon["source_path"]
        f["entityCount"] = recon["source_entities"]
        f["foundryFolderCount"] = recon["foundry_folders"]
        f["generatedPageCount"] = recon["generated_pages"]
        f["organizationalGeneratedPageCount"] = len(recon["organizational_generated_pages"])
        f["missingGeneratedPageCount"] = len(recon["missing_generated_pages"])
        f["actionableOrphanGeneratedPageCount"] = len(recon["orphan_generated_pages"])
        f["contentDigestAlgorithm"] = "sha256(sorted path + tab + inventory file sha256)"
        f["contentDigestSha256"] = digest
        f["contentDigestValidation"] = (
            f"Recomputed directly from {digest_entity_count} non-folder structured-source records "
            f"under {recon['source_path']} in the current inventory."
        )
        f["generatedOutputDir"] = recon["output_dir"]
        structured_new.append(f)

    out["publicationInputs"]["authoredDocuments"] = authored_new
    out["publicationInputs"]["structuredFamilies"] = structured_new

    # Refresh generated derivative family stats.
    derivative_by_family = {
        f["family"]: f for f in out["generatedDerivativePolicy"]["families"]
    }
    refreshed_derivatives = []
    for sf in structured_new:
        family = sf["generatorFamily"]
        d = copy.deepcopy(derivative_by_family.get(family, {}))
        d.update({
            "family": family,
            "sourcePath": sf["sourcePath"],
            "generatedOutputDir": sf["generatedOutputDir"],
            "authority": "DERIVATIVE",
            "disposition": "EXCLUDE",
            "generatedPages": sf["generatedPageCount"],
            "organizationalPages": sf["organizationalGeneratedPageCount"],
            "policy": (
                "Do not consume generated MkDocs pages as rulebook authority; generate publication "
                "content directly from the structured source family."
            ),
        })
        refreshed_derivatives.append(d)
    out["generatedDerivativePolicy"]["families"] = refreshed_derivatives
    out["generatedDerivativePolicy"]["foundryFolderRecords"]["count"] = inventory["counts"]["foundry_folder_records"]
    out["generatedDerivativePolicy"]["knownOrganizationalGeneratedPages"]["count"] = sum(
        f["organizationalGeneratedPageCount"] for f in structured_new
    )

    # Refresh summary.
    disp_counts = Counter(d["disposition"] for d in decisions)
    status_counts = Counter(d["decisionStatus"] for d in decisions)
    section_counts = Counter(d["bookSection"] for d in decisions if d["disposition"] == "INCLUDE")
    section_order = [
        "Front Matter / Navigation",
        "World / Setting",
        "Playing Cybermancy",
        "Netrunning",
        "Gamemastering / Adversaries",
        "Gamemastering / Environments",
        "Equipment & Augmentation",
        "Characters",
    ]
    out["summary"] = {
        "decisionRows": len(decisions),
        "decidedRows": status_counts.get("DECIDED", 0),
        "includeRows": disp_counts.get("INCLUDE", 0),
        "excludeRows": disp_counts.get("EXCLUDE", 0),
        "authoredPublicationInputs": len(authored_new),
        "structuredPublicationFamilies": len(structured_new),
        "structuredPublicationEntities": sum(f["entityCount"] for f in structured_new),
        "generatedDerivativeDetailPages": inventory["counts"]["generated_documents"],
        "bookSections": [s for s in section_order if section_counts.get(s, 0)],
    }

    # Snapshot change summary versus template.
    out["snapshotChangeSummary"] = {
        "previousManifestVersion": previous_version,
        "previousGitCommit": template["repository"]["gitCommit"],
        "currentGitCommit": inventory["repository"]["git_commit"],
        "authorityDecisionsChanged": False,
        "authoredPublicationInputsChanged": authored_changes,
        "structuredPublicationFamiliesChanged": structured_changes,
        "publicationContentChanged": bool(authored_changes or structured_changes),
    }

    # Validation.
    included_decisions = [d for d in decisions if d["disposition"] == "INCLUDE"]
    included_authored_ids = {d["id"] for d in included_decisions if d["id"].startswith("A")}
    included_structured_ids = {d["id"] for d in included_decisions if d["id"].startswith("B")}

    checks = {
        "all77DecisionRowsPresent": len(decisions) == 77,
        "allDecisionRowsDecided": status_counts.get("DECIDED", 0) == len(decisions),
        "userDispositionValuesRestrictedToIncludeExclude": all(
            d["disposition"] in {"INCLUDE", "EXCLUDE"} for d in decisions
        ),
        "includedAuthoredDecisionSetMatchesPublicationInputs": (
            included_authored_ids == {d["id"] for d in authored_new}
        ),
        "includedStructuredDecisionSetMatchesPublicationInputs": (
            included_structured_ids == {f["id"] for f in structured_new}
        ),
        "allIncludedAuthoredPathsExistInFreezeInventory": all(
            d["path"] in item_by_path for d in authored_new
        ),
        "allStructuredFamiliesReconcile": all(
            f["entityCount"] == recon_by_type[f["generatorFamily"]]["source_entities"]
            for f in structured_new
        ),
        "zeroMissingGeneratedPagesAcrossIncludedStructuredFamilies": all(
            f["missingGeneratedPageCount"] == 0 for f in structured_new
        ),
        "zeroActionableOrphansAcrossIncludedStructuredFamilies": all(
            f["actionableOrphanGeneratedPageCount"] == 0 for f in structured_new
        ),
        "zeroReviewFlagsOnAuthoredPublicationInputs": all(
            not d.get("reviewFlags") for d in authored_new
        ),
        "authorityDecisionFingerprintUnchanged": authority_fp == previous_fp,
    }
    passed = all(checks.values())

    inv_counts = inventory["counts"]
    out["validation"] = {
        "passed": passed,
        "checks": checks,
        "inventorySnapshot": {
            "filesScanned": inv_counts["total_files"],
            "documents": inv_counts["documents"],
            "generatedDocuments": inv_counts["generated_documents"],
            "handAuthoredDocuments": inv_counts["hand_authored_documents"],
            "stubDocuments": inv_counts["stub_documents"],
            "unresolvedLocalDependencyFiles": inv_counts["unresolved_dependency_files"],
            "flaggedFiles": inv_counts["flagged_files"],
            "knownExceptionFiles": inv_counts["known_exception_files"],
        },
        "nonGatingRepositoryDebt": [
            "Remaining stub documents are outside the publication corpus.",
            "Remaining unresolved local dependencies are outside publication inputs.",
            "Title-collision candidates remain in generated/excluded repository material; no authored publication input carries a review flag.",
            "Foundry folder records and generated organizational pages remain known exceptions and are explicitly non-publication entities.",
        ],
    }

    if not passed:
        failed = [name for name, ok in checks.items() if not ok]
        raise RuntimeError("Manifest validation failed: " + ", ".join(failed))

    return out


def markdown_summary(manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    lines += [
        f"# Cybermancy Rulebook Publication Manifest v{manifest['manifestVersion']}",
        "",
        "**Status:** FROZEN  ",
        "**Phase:** Rulebook Step 2 — Publication Scope & Source Authority Audit  ",
        f"**Repository commit:** `{manifest['repository']['gitCommit']}`  ",
        f"**Inventory:** `{manifest['repository']['inventorySchema']}` / scanner `{manifest['repository']['inventoryScannerVersion']}`  ",
        f"**Supersedes:** `{manifest['supersedes']['manifest']}`",
        "",
        "## Snapshot refresh",
        "",
        "Publication-scope and source-authority decisions are unchanged from the superseded manifest.",
        "",
        f"- Previous Git commit: `{manifest['snapshotChangeSummary']['previousGitCommit']}`",
        f"- Current Git commit: `{manifest['snapshotChangeSummary']['currentGitCommit']}`",
        f"- Authored publication inputs changed: **{len(manifest['snapshotChangeSummary']['authoredPublicationInputsChanged'])}**",
        f"- Structured publication families changed: **{len(manifest['snapshotChangeSummary']['structuredPublicationFamiliesChanged'])}**",
        f"- Publication content changed: **{'YES' if manifest['snapshotChangeSummary']['publicationContentChanged'] else 'NO'}**",
        "",
        "## Frozen authority rule",
        "",
        "- `CANONICAL-CANDIDATE + INCLUDE + DECIDED` is an accepted authoritative input for this rulebook snapshot.",
        "- Included authored Markdown is consumed directly.",
        "- Included `src/packs` structured JSON is the authoritative source for structured publication families.",
        "- Generated MkDocs detail pages and dynamic aggregation outputs are `DERIVATIVE / EXCLUDE` and must not be consumed as rulebook authority.",
        "- Campaign/adventure-specific material remains excluded unless explicitly elevated later.",
        "- Adversary/environment Fast Play is consumed structurally from `flags.cybermancy.fastPlay`.",
        "",
        "## Decision summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Decision rows | {manifest['summary']['decisionRows']} |",
        f"| DECIDED | {manifest['summary']['decidedRows']} |",
        f"| INCLUDE | {manifest['summary']['includeRows']} |",
        f"| EXCLUDE | {manifest['summary']['excludeRows']} |",
        f"| Authored publication inputs | {manifest['summary']['authoredPublicationInputs']} |",
        f"| Structured publication families | {manifest['summary']['structuredPublicationFamilies']} |",
        f"| Structured publication entities | {manifest['summary']['structuredPublicationEntities']} |",
        "",
        "## Authored publication inputs",
        "",
        "| ID | Section | Source | SHA-256 |",
        "|---|---|---|---|",
    ]
    for d in manifest["publicationInputs"]["authoredDocuments"]:
        lines.append(f"| {d['id']} | {d['bookSection']} | `{d['path']}` | `{d['sha256']}` |")

    lines += [
        "",
        "## Structured publication families",
        "",
        "| ID | Section | Canonical source | Entities | Family digest |",
        "|---|---|---|---:|---|",
    ]
    for f in manifest["publicationInputs"]["structuredFamilies"]:
        lines.append(
            f"| {f['id']} | {f['bookSection']} | `{f['sourcePath']}` | "
            f"{f['entityCount']} | `{f['contentDigestSha256']}` |"
        )

    lines += [
        "",
        "## Validation",
        "",
        f"**Manifest validation:** {'PASS' if manifest['validation']['passed'] else 'FAIL'}",
        "",
    ]
    for name, ok in manifest["validation"]["checks"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — {name}")

    lines += [
        "",
        "### Fresh inventory snapshot",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    labels = [
        ("Files scanned", "filesScanned"),
        ("Documents", "documents"),
        ("Generated documents", "generatedDocuments"),
        ("Hand-authored/source documents", "handAuthoredDocuments"),
        ("Stub documents", "stubDocuments"),
        ("Unresolved local dependency files", "unresolvedLocalDependencyFiles"),
        ("Flagged files", "flaggedFiles"),
        ("Known-exception files", "knownExceptionFiles"),
    ]
    for label, key in labels:
        lines.append(f"| {label} | {manifest['validation']['inventorySnapshot'][key]} |")

    lines += [
        "",
        "The JSON manifest is the normative machine-readable freeze artifact. "
        "This Markdown file is a convenience summary and does not replace the JSON decisions.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, type=Path, help="Previously approved publication manifest JSON.")
    ap.add_argument("--inventory", required=True, type=Path, help="Fresh rulebook inventory JSON.")
    ap.add_argument("--inventory-csv", type=Path, default=None)
    ap.add_argument("--inventory-report", type=Path, default=None)
    ap.add_argument("--output-dir", type=Path, default=Path("."))
    ap.add_argument("--version", default=None, help="New manifest version. Defaults to patch+1.")
    ap.add_argument("--frozen-at", default=None, help="ISO-8601 timestamp. Defaults to local current time.")
    args = ap.parse_args()

    template = json.loads(args.template.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))

    version = args.version or bump_patch(str(template["manifestVersion"]))
    frozen_at = args.frozen_at or datetime.now().astimezone().isoformat(timespec="seconds")

    manifest = build_manifest(
        template,
        inventory,
        version=version,
        frozen_at=frozen_at,
        inventory_path=args.inventory,
        inventory_csv=args.inventory_csv,
        inventory_report=args.inventory_report,
        template_path=args.template,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"cybermancy-rulebook-publication-manifest-v{version}"
    json_out = args.output_dir / f"{stem}.json"
    md_out = args.output_dir / f"{stem}.md"

    json_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(markdown_summary(manifest), encoding="utf-8")

    print(f"PASS: {json_out}")
    print(f"PASS: {md_out}")
    print(f"Git commit: {manifest['repository']['gitCommit']}")
    print(
        f"Publication content changed: "
        f"{'YES' if manifest['snapshotChangeSummary']['publicationContentChanged'] else 'NO'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
