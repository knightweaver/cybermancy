#!/usr/bin/env python3
"""Validate Cybermancy v0.2.0 DH2 Compendium source against frozen v0.1.14."""
from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

LEGACY_TAG = "v0.1.14"
TARGET_CORE = "14.368"
TARGET_SYSTEM = "2.10.5"
CUSTOM_DOMAINS = {"circuit", "maker", "bullet"}
FIXTURES = {
    "b052B7vEbJN5tSB1": "equipment/armor",
    "pjN7ciiS9yyGB7rP": "class",
    "qxZt0FgPJJ5icWji": "subclass",
    "s0WW3VsQHwUfqi1X": "domain/circuit",
    "41cNX3rZNCbl34ra": "domain/maker",
    "BgW4OBFfHHrTS0QG": "domain/bullet",
    "JUYmyWUgti1my9nG": "adversary",
    "h5LbBi4TNmuMEzo5": "environment",
    "qST6XFvhsrHJE1UO": "environment",
    "nzH9MmLg9aeVLFqV": "environment",
    "kClQ3R1arK0iaohd": "environment",
}
COMPENDIUM_RE = re.compile(r"^Compendium\.cybermancy\.([^.]+)\.(?:Item|Actor)\.([A-Za-z0-9]{16})$")
WORLD_ACTOR_RE = re.compile(r"^Actor\.[A-Za-z0-9]{16}$")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_show(repo: Path, rel: str) -> Any:
    p = subprocess.run(["git", "-C", str(repo), "show", f"{LEGACY_TAG}:{rel}"], capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        raise RuntimeError(p.stderr.strip())
    return json.loads(p.stdout)


def is_folder(doc: dict) -> bool:
    return str(doc.get("_key") or "").startswith("!folders!")


def iter_nodes(node: Any):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from iter_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_nodes(value)


def normalized_for_preservation(doc: dict) -> dict:
    """Remove only migration-owned shape fields, leaving content for deep compare."""
    doc = copy.deepcopy(doc)
    for node in iter_nodes(doc):
        if not isinstance(node, dict):
            continue
        stats = node.get("_stats")
        if isinstance(stats, dict):
            stats.pop("coreVersion", None)
            stats.pop("systemVersion", None)
        if node.get("type") == "feature" and isinstance(node.get("system"), dict):
            system = node["system"]
            for key in ("originItemType", "multiclassOrigin", "identifier", "featureForm"):
                system.pop(key, None)
    if doc.get("type") == "class" and isinstance(doc.get("system"), dict):
        doc["system"].pop("subclasses", None)
    if doc.get("type") == "environment":
        # Environment world UUID migration is validated separately.
        if isinstance(doc.get("system"), dict):
            doc["system"].pop("potentialAdversaries", None)
        flags = doc.get("flags")
        if isinstance(flags, dict):
            cyber = flags.get("cybermancy")
            if isinstance(cyber, dict):
                migration = cyber.get("migration")
                if isinstance(migration, dict):
                    migration.pop("unresolvedPotentialAdversaries", None)
                    if not migration:
                        cyber.pop("migration", None)
                if not cyber:
                    flags.pop("cybermancy", None)
            if not flags:
                doc["flags"] = {}
    return doc


def expected_feature_form(feature: dict) -> str:
    actions = (feature.get("system") or {}).get("actions") or {}
    forms = []
    for action in actions.values() if isinstance(actions, dict) else []:
        form = "evolution" if action.get("type") == "evolution" else (action.get("actionType") or "passive")
        if form not in forms:
            forms.append(form)
    if not forms:
        return "passive"
    if len(forms) != 1:
        raise ValueError(f"ambiguous feature action forms: {forms}")
    return forms[0]


def asset_refs(node: Any):
    if isinstance(node, str):
        if node.startswith("modules/cybermancy/assets/"):
            yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from asset_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from asset_refs(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--baseline", type=Path, default=Path("maintenance/baseline-v0.2.0.json"))
    args = ap.parse_args()
    repo = args.repo.resolve()
    baseline_path = args.baseline if args.baseline.is_absolute() else repo / args.baseline
    baseline = load_json(baseline_path)
    manifest = load_json(repo / "module.json")
    errors: list[str] = []

    expected_pack_counts = {
        row["name"]: (row["entryCount"], row["documentCount"], row["folderCount"])
        for row in baseline["compendia"]
    }
    pack_ids: dict[str, set[str]] = {}
    all_docs: dict[str, tuple[str, dict]] = {}
    domain_counts = Counter()
    unresolved_world_refs = []
    stable_compendium_refs = []
    env_feature_count = 0
    env_feature_forms = Counter()
    actual_total = docs_total = folders_total = 0

    for pack in manifest.get("packs", []):
        pack_name = pack["name"]
        directory = repo / "src" / pack["path"]
        entries = []
        docs = 0
        folders = 0
        ids = set()
        if not directory.is_dir():
            errors.append(f"{pack_name}: missing source directory {directory.relative_to(repo)}")
            continue
        for path in sorted(directory.glob("*.json")):
            rel = path.relative_to(repo).as_posix()
            current = load_json(path)
            legacy = git_show(repo, rel)
            entries.append(current)
            doc_id = current.get("_id")
            if not isinstance(doc_id, str) or len(doc_id) != 16:
                errors.append(f"{rel}: invalid _id {doc_id!r}")
            elif doc_id in ids:
                errors.append(f"{rel}: duplicate ID in pack: {doc_id}")
            else:
                ids.add(doc_id)
            if is_folder(current):
                folders += 1
            else:
                docs += 1
                all_docs[doc_id] = (rel, current)

            if current.get("_id") != legacy.get("_id") or current.get("_key") != legacy.get("_key"):
                errors.append(f"{rel}: stable _id/_key changed from v0.1.14")
            for field in ("name", "type", "folder", "img", "sort"):
                if current.get(field) != legacy.get(field):
                    errors.append(f"{rel}: protected field {field} changed")

            if normalized_for_preservation(current) != normalized_for_preservation(legacy):
                errors.append(f"{rel}: content differs from v0.1.14 outside documented migration-owned shape fields")

            if current.get("type") == "class" and "subclasses" in (current.get("system") or {}):
                errors.append(f"{rel}: obsolete Class system.subclasses remains")
            if current.get("type") == "subclass":
                if (current.get("system") or {}).get("linkedClass") != (legacy.get("system") or {}).get("linkedClass"):
                    errors.append(f"{rel}: Subclass linkedClass changed")

            if current.get("type") == "domainCard":
                domain = (current.get("system") or {}).get("domain")
                domain_counts[domain] += 1
                if domain not in CUSTOM_DOMAINS:
                    errors.append(f"{rel}: unexpected Cybermancy Domain Card domain {domain!r}")

            if current.get("type") == "feature":
                form = (current.get("system") or {}).get("featureForm")
                try:
                    expected = expected_feature_form(legacy)
                    if form != expected:
                        errors.append(f"{rel}: featureForm {form!r} != deterministic legacy form {expected!r}")
                except ValueError as exc:
                    errors.append(f"{rel}: {exc}")
                for key in ("originItemType", "multiclassOrigin"):
                    if key in (current.get("system") or {}):
                        errors.append(f"{rel}: obsolete Feature field {key} remains")

            if current.get("type") in {"adversary", "environment"}:
                actor_id = current.get("_id")
                legacy_items = {i.get("_id"): i for i in (legacy.get("items") or []) if isinstance(i, dict)}
                current_items = current.get("items") or []
                if len(current_items) != len(legacy_items):
                    errors.append(f"{rel}: embedded Item count changed")
                for item in current_items:
                    item_id = item.get("_id")
                    old = legacy_items.get(item_id)
                    if old is None:
                        errors.append(f"{rel}: new/unrecognized embedded Item {item_id}")
                        continue
                    expected_key = f"!actors.items!{actor_id}.{item_id}"
                    if item.get("_key") != expected_key or old.get("_key") != expected_key:
                        errors.append(f"{rel}: embedded Item {item_id} _key mismatch")
                    for field in ("name", "type", "img", "sort"):
                        if item.get(field) != old.get(field):
                            errors.append(f"{rel}: embedded Item {item_id} changed {field}")
                    if normalized_for_preservation(item) != normalized_for_preservation(old):
                        errors.append(f"{rel}: embedded Item {item_id} content changed outside migration shape")
                    if item.get("type") == "feature":
                        env_feature_count += current.get("type") == "environment"
                        form = (item.get("system") or {}).get("featureForm")
                        expected = expected_feature_form(old)
                        env_feature_forms[form] += current.get("type") == "environment"
                        if form != expected:
                            errors.append(f"{rel}: embedded Feature {item_id} form {form!r} != {expected!r}")
                        if (item.get("system") or {}).get("actions") != (old.get("system") or {}).get("actions"):
                            errors.append(f"{rel}: embedded Feature {item_id} actions changed")
                        if (item.get("system") or {}).get("description") != (old.get("system") or {}).get("description"):
                            errors.append(f"{rel}: embedded Feature {item_id} text changed")

            if current.get("type") == "environment":
                old_groups = (legacy.get("system") or {}).get("potentialAdversaries") or {}
                new_groups = (current.get("system") or {}).get("potentialAdversaries") or {}
                if set(old_groups) != set(new_groups):
                    errors.append(f"{rel}: potential-adversary group IDs changed")
                for gid, old_group in old_groups.items():
                    new_group = new_groups.get(gid) or {}
                    if new_group.get("label") != old_group.get("label"):
                        errors.append(f"{rel}: potential-adversary label changed for {gid}")
                    old_refs = old_group.get("adversaries") or []
                    expected_refs = [r for r in old_refs if not (isinstance(r, str) and WORLD_ACTOR_RE.match(r))]
                    if new_group.get("adversaries") != expected_refs:
                        errors.append(f"{rel}: potential-adversary refs for {gid} are not preserved/externalized deterministically")
                    stable_compendium_refs.extend(r for r in expected_refs if isinstance(r, str) and r.startswith("Compendium."))
                    unresolved_world_refs.extend(r for r in old_refs if isinstance(r, str) and WORLD_ACTOR_RE.match(r))
                migration_rows = (((current.get("flags") or {}).get("cybermancy") or {}).get("migration") or {}).get("unresolvedPotentialAdversaries") or []
                flattened = [r for row in migration_rows for r in row.get("legacyWorldActorRefs", [])]
                old_world = [r for g in old_groups.values() for r in (g.get("adversaries") or []) if isinstance(r, str) and WORLD_ACTOR_RE.match(r)]
                if sorted(flattened) != sorted(old_world):
                    errors.append(f"{rel}: unresolved world Actor reference evidence does not exactly preserve legacy refs")

            for node in iter_nodes(current):
                if isinstance(node, dict):
                    stats = node.get("_stats")
                    if isinstance(stats, dict) and stats.get("systemId") == "daggerheart":
                        if stats.get("coreVersion") != TARGET_CORE or stats.get("systemVersion") != TARGET_SYSTEM:
                            errors.append(f"{rel}: stale _stats target {stats.get('coreVersion')}/{stats.get('systemVersion')}")
            for ref in asset_refs(current):
                asset = repo / ref.removeprefix("modules/cybermancy/")
                if not asset.is_file():
                    errors.append(f"{rel}: missing artwork {ref}")

        expected = expected_pack_counts.get(pack_name)
        actual = (len(entries), docs, folders)
        if expected != actual:
            errors.append(f"{pack_name}: count mismatch expected={expected} actual={actual}")
        pack_ids[pack_name] = ids
        actual_total += len(entries)
        docs_total += docs
        folders_total += folders

    if actual_total != baseline["counts"]["declaredSourceEntries"]:
        errors.append(f"declared source total changed: {actual_total}")
    if docs_total != baseline["counts"]["declaredDocuments"] or folders_total != baseline["counts"]["declaredFolders"]:
        errors.append(f"document/folder totals changed: docs={docs_total} folders={folders_total}")

    # Stable Cybermancy Compendium references must resolve to the same declared pack IDs.
    pack_alias = {pack["name"]: pack["name"] for pack in manifest.get("packs", [])}
    for _, (_, doc) in all_docs.items():
        for node in iter_nodes(doc):
            if not isinstance(node, str):
                continue
            m = COMPENDIUM_RE.match(node)
            if not m:
                continue
            pack_name, target_id = m.groups()
            if pack_name not in pack_alias:
                errors.append(f"undeclared Cybermancy Compendium reference pack: {node}")
            elif target_id not in pack_ids.get(pack_name, set()):
                errors.append(f"unresolved Cybermancy Compendium reference: {node}")

    if domain_counts.total() != baseline["counts"]["domainCardDocuments"]:
        errors.append(f"Domain Card count changed: {domain_counts.total()}")
    if set(domain_counts) != CUSTOM_DOMAINS:
        errors.append(f"Domain set changed: {sorted(domain_counts)}")
    if env_feature_count != baseline["counts"]["embeddedEnvironmentFeatures"]:
        errors.append(f"Environment embedded Feature count changed: {env_feature_count}")
    if len(unresolved_world_refs) != baseline["counts"]["environmentWorldActorUuidOccurrences"]:
        errors.append(f"world Actor reference occurrence count changed from baseline evidence: {len(unresolved_world_refs)}")
    if len(stable_compendium_refs) != baseline["counts"]["environmentCompendiumActorUuidOccurrences"]:
        errors.append(f"stable environment Compendium reference count changed: {len(stable_compendium_refs)}")

    missing_fixtures = [f"{id}:{label}" for id, label in FIXTURES.items() if id not in all_docs]
    if missing_fixtures:
        errors.append(f"missing regression fixtures: {missing_fixtures}")

    report = {
        "status": "FAIL" if errors else "PASS",
        "sourceEntries": actual_total,
        "documents": docs_total,
        "folders": folders_total,
        "domainCards": dict(sorted(domain_counts.items())),
        "environmentEmbeddedFeatures": env_feature_count,
        "environmentFeatureForms": dict(sorted(env_feature_forms.items())),
        "externalizedWorldActorOccurrences": len(unresolved_world_refs),
        "stableEnvironmentCompendiumRefs": len(stable_compendium_refs),
        "fixtures": FIXTURES,
        "errors": errors,
    }
    out = repo / "maintenance" / "migration" / "v0.2.0-source-validation-report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if errors:
        print("Cybermancy v0.2.0 DH2 source validation FAILED", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print("Cybermancy v0.2.0 DH2 source validation PASS")
    print(f" - entries: {actual_total} ({docs_total} documents + {folders_total} folders)")
    print(f" - Domain Cards: {dict(sorted(domain_counts.items()))}")
    print(f" - Environment embedded Features: {env_feature_count} {dict(sorted(env_feature_forms.items()))}")
    print(f" - Externalized world Actor refs: {len(unresolved_world_refs)}")
    print(f" - Stable Environment Compendium refs: {len(stable_compendium_refs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
