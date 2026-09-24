#!/usr/bin/env python3
"""Deterministically project Cybermancy v0.1.14 Compendium source to DH 2.10.5.

This projection deliberately does NOT rewrite Armor slot fields or Action damage
fields. Daggerheart 2.10.5 explicitly migrates legacy Armor baseScore/marks and
Action damage.parts through its own data-model migration hooks. Rewriting those
values here would duplicate system-owned migration logic and increase semantic
risk before runtime qualification.

Canonical source changes owned by Cybermancy:
- remove obsolete Class.system.subclasses arrays (Subclass.linkedClass is retained);
- normalize Feature Items to DH2 Feature fields by removing empty legacy origin
  fields and adding explicit featureForm where it is deterministically derivable;
- externalize nonportable Environment world Actor.* potential-adversary UUIDs
  without inventing replacements, while retaining an auditable legacy-ref flag;
- update Foundry/Daggerheart _stats version metadata on documents/embedded data.

The script compares against the frozen v0.1.14 tag and emits a machine-readable
migration report. It never changes IDs, _keys, folders, names, artwork, prose,
actions, or stable Compendium UUIDs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

LEGACY_TAG = "v0.1.14"
TARGET_CORE = "14.368"
TARGET_SYSTEM = "2.10.5"
ALLOWED_FORMS = {"passive", "action", "reaction", "evolution"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git_show(repo: Path, ref: str, rel: str) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{rel}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(f"git show failed for {ref}:{rel}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def sha256_json(data: Any) -> str:
    raw = (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def is_folder(doc: dict) -> bool:
    return str(doc.get("_key") or "").startswith("!folders!")


def update_stats(node: Any, counters: Counter) -> None:
    if isinstance(node, dict):
        stats = node.get("_stats")
        if isinstance(stats, dict) and stats.get("systemId") == "daggerheart":
            before = (stats.get("coreVersion"), stats.get("systemVersion"))
            stats["coreVersion"] = TARGET_CORE
            stats["systemVersion"] = TARGET_SYSTEM
            after = (stats.get("coreVersion"), stats.get("systemVersion"))
            if before != after:
                counters["statsVersion"] += 1
        for value in node.values():
            update_stats(value, counters)
    elif isinstance(node, list):
        for value in node:
            update_stats(value, counters)


def infer_feature_form(item: dict, context: str) -> str:
    existing = item.get("system", {}).get("featureForm")
    if existing in ALLOWED_FORMS:
        return existing
    actions = item.get("system", {}).get("actions") or {}
    if not isinstance(actions, dict):
        raise ValueError(f"{context}: Feature system.actions must be an object")
    forms: list[str] = []
    for action_id, action in actions.items():
        if not isinstance(action, dict):
            raise ValueError(f"{context}: action {action_id} is not an object")
        if action.get("type") == "evolution":
            form = "evolution"
        else:
            form = action.get("actionType") or "passive"
        if form not in ALLOWED_FORMS:
            raise ValueError(f"{context}: unsupported Feature action form {form!r}")
        if form not in forms:
            forms.append(form)
    if not forms:
        return "passive"
    if len(forms) == 1:
        return forms[0]
    # Multiple actions can coexist, but Feature form is a single presentation
    # category. Refuse to guess; a future explicit mapping may resolve it.
    raise ValueError(f"{context}: ambiguous Feature forms {forms}; explicit mapping required")


def migrate_feature(item: dict, context: str, counters: Counter) -> None:
    system = item.get("system")
    if not isinstance(system, dict):
        raise ValueError(f"{context}: Feature missing system object")

    origin = system.get("originItemType")
    multiclass = system.get("multiclassOrigin")
    identifier = system.get("identifier")
    granter = system.get("granter")
    if origin not in (None, ""):
        raise ValueError(f"{context}: populated legacy originItemType={origin!r} requires explicit granter mapping")
    if multiclass not in (None, False):
        raise ValueError(f"{context}: populated legacy multiclassOrigin={multiclass!r} requires explicit granter mapping")
    if identifier not in (None, "") and not granter:
        raise ValueError(f"{context}: populated legacy identifier={identifier!r} requires explicit granter mapping")

    removed = False
    for key in ("originItemType", "multiclassOrigin"):
        if key in system:
            del system[key]
            removed = True
    if "identifier" in system and identifier in (None, ""):
        del system["identifier"]
        removed = True
    if removed:
        counters["featureLegacyOriginFieldsRemoved"] += 1

    form = infer_feature_form(item, context)
    if system.get("featureForm") != form:
        system["featureForm"] = form
        counters[f"featureForm:{form}"] += 1


def migrate_environment_refs(doc: dict, rel: str, counters: Counter) -> list[dict]:
    system = doc.get("system") or {}
    groups = system.get("potentialAdversaries")
    if not isinstance(groups, dict):
        return []

    unresolved: list[dict] = []
    for group_id, group in groups.items():
        if not isinstance(group, dict):
            raise ValueError(f"{rel}: potentialAdversaries.{group_id} must be an object")
        refs = group.get("adversaries") or []
        if not isinstance(refs, list):
            raise ValueError(f"{rel}: potentialAdversaries.{group_id}.adversaries must be an array")
        world_refs = [ref for ref in refs if isinstance(ref, str) and ref.startswith("Actor.")]
        other_refs = [ref for ref in refs if ref not in world_refs]
        if world_refs:
            group["adversaries"] = other_refs
            unresolved.append({
                "groupId": group_id,
                "label": str(group.get("label") or ""),
                "legacyWorldActorRefs": world_refs,
                "status": "external-unresolved",
            })
            counters["worldActorReferenceOccurrencesExternalized"] += len(world_refs)
            counters["environmentGroupsExternalized"] += 1

    if unresolved:
        flags = doc.setdefault("flags", {})
        cyber = flags.setdefault("cybermancy", {})
        migration = cyber.setdefault("migration", {})
        migration["unresolvedPotentialAdversaries"] = unresolved
    return unresolved


def migrate_document(doc: dict, rel: str, counters: Counter) -> list[dict]:
    unresolved: list[dict] = []
    if is_folder(doc):
        return unresolved

    if doc.get("type") == "class":
        system = doc.get("system") or {}
        subclasses = system.get("subclasses")
        if subclasses is not None:
            if not isinstance(subclasses, list):
                raise ValueError(f"{rel}: Class system.subclasses must be an array")
            counters["classSubclassRefsRemoved"] += len(subclasses)
            counters["classesWithSubclassFieldRemoved"] += 1
            del system["subclasses"]

    if doc.get("type") == "feature":
        migrate_feature(doc, rel, counters)

    if doc.get("type") in {"adversary", "environment"}:
        actor_id = doc.get("_id")
        items = doc.get("items") or []
        if not isinstance(items, list):
            raise ValueError(f"{rel}: Actor items must be an array")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{rel}: embedded Actor Item must be an object")
            if item.get("type") == "feature":
                migrate_feature(item, f"{rel}#Item.{item.get('_id')}", counters)
                counters["embeddedFeaturesVisited"] += 1
                expected_key = f"!actors.items!{actor_id}.{item.get('_id')}"
                if item.get("_key") != expected_key:
                    raise ValueError(
                        f"{rel}: embedded Feature {item.get('_id')} _key changed or malformed: "
                        f"{item.get('_key')!r} != {expected_key!r}"
                    )

    if doc.get("type") == "environment":
        unresolved = migrate_environment_refs(doc, rel, counters)

    update_stats(doc, counters)
    return unresolved


def canonical_identity(doc: dict) -> dict:
    return {
        "_id": doc.get("_id"),
        "_key": doc.get("_key"),
        "folder": doc.get("folder"),
        "name": doc.get("name"),
        "type": doc.get("type"),
        "img": doc.get("img"),
        "sort": doc.get("sort"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", type=Path, default=Path("maintenance/baseline-v0.2.0.json"))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    baseline_path = args.baseline if args.baseline.is_absolute() else repo / args.baseline

    manifest = load_json(repo / "module.json")
    baseline = load_json(baseline_path)
    expected_paths = {entry["path"]: entry for entry in baseline["sourceEntries"]}
    pack_dirs = [repo / "src" / pack["path"] for pack in manifest.get("packs", [])]
    if len(pack_dirs) != baseline["counts"]["declaredCompendia"]:
        raise ValueError("declared Compendium count differs from frozen baseline")

    current_paths: list[str] = []
    for pack_dir in pack_dirs:
        current_paths.extend(
            path.relative_to(repo).as_posix()
            for path in sorted(pack_dir.glob("*.json"))
        )
    if set(current_paths) != set(expected_paths):
        missing = sorted(set(expected_paths) - set(current_paths))
        extra = sorted(set(current_paths) - set(expected_paths))
        raise ValueError(f"source path set differs from frozen baseline; missing={missing[:10]} extra={extra[:10]}")

    counters: Counter = Counter()
    changed_files: list[dict] = []
    unresolved_all: list[dict] = []
    pack_counts: dict[str, dict[str, int]] = {}

    for rel in sorted(current_paths):
        path = repo / rel
        source = load_json(path)
        legacy = git_show(repo, LEGACY_TAG, rel)

        if canonical_identity(source) != canonical_identity(legacy):
            raise ValueError(f"{rel}: current source identity differs from frozen {LEGACY_TAG}")

        before = copy.deepcopy(source)
        unresolved = migrate_document(source, rel, counters)
        for row in unresolved:
            unresolved_all.append({"path": rel, "actorId": source.get("_id"), **row})

        if canonical_identity(source) != canonical_identity(legacy):
            raise ValueError(f"{rel}: migration changed a protected document identity field")

        pack_rel = "/".join(rel.split("/")[:-1])
        bucket = pack_counts.setdefault(pack_rel, {"entries": 0, "documents": 0, "folders": 0, "changed": 0})
        bucket["entries"] += 1
        bucket["folders" if is_folder(source) else "documents"] += 1

        if source != before:
            bucket["changed"] += 1
            changed_files.append({
                "path": rel,
                "id": source.get("_id"),
                "kind": "folder" if is_folder(source) else "document",
                "beforeSha256": sha256_json(before),
                "afterSha256": sha256_json(source),
            })
            if args.write:
                dump_json(path, source)

    report = {
        "schemaVersion": "1.0",
        "migration": "cybermancy-v0.2.0-dh2-compendium-source",
        "legacyTag": LEGACY_TAG,
        "legacyCommit": baseline["legacyReference"]["sourceCommit"],
        "target": {"foundryCore": TARGET_CORE, "daggerheart": TARGET_SYSTEM},
        "declaredCompendia": len(pack_dirs),
        "sourceEntryCount": len(current_paths),
        "documentCount": sum(v["documents"] for v in pack_counts.values()),
        "folderCount": sum(v["folders"] for v in pack_counts.values()),
        "changedFileCount": len(changed_files),
        "changes": dict(sorted(counters.items())),
        "unresolvedPotentialAdversaries": unresolved_all,
        "packCounts": dict(sorted(pack_counts.items())),
        "changedFiles": changed_files,
        "armorActionPolicy": {
            "armorValuesRewritten": False,
            "actionDamageValuesRewritten": False,
            "reason": "Daggerheart 2.10.5 explicitly migrates Armor baseScore/marks and Action damage.parts through its data-model migration hooks; source values are preserved pending runtime qualification."
        },
        "writeMode": bool(args.write),
    }
    report_path = repo / "maintenance" / "migration" / "v0.2.0-source-migration-report.json"
    if args.write:
        dump_json(report_path, report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
