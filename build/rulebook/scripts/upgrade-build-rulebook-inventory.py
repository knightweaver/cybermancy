#!/usr/bin/env python3
"""
Upgrade Cybermancy build-rulebook-inventory.py from v0.2.3 to v0.2.4.

This is an in-place source upgrader. It preserves the existing scanner and
replaces only the structured entity identity/reconciliation logic that was
incorrectly keyed by display-name slug.

Typical use from repository root:
    python build/rulebook/scripts/upgrade-build-rulebook-inventory.py

Target default:
    pyCybermancy/build-rulebook-inventory.py

Backup default:
    pyCybermancy/build-rulebook-inventory.py.v0.2.3.bak
"""

from __future__ import annotations

import argparse
import py_compile
import re
import shutil
import sys
from pathlib import Path

UPGRADER_VERSION = "1.0.0"


def infer_repo_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name == "scripts" and here.parent.parent.name == "rulebook":
        return here.parent.parent.parent.parent
    return Path.cwd().resolve()


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    new, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not uniquely replace {label}; matches={count}")
    return new


FOUNDRY_ID_HELPER = '''
def foundry_stable_id(obj: dict) -> str:
    """Return durable Foundry/source identity for one unpacked record.

    Identity precedence matches the Step 4 normalizer:
      1. top-level ``_id``;
      2. final document ID segment in ``_key``.

    Display name and slug are intentionally NOT identity.
    """
    value = obj.get("_id")
    if isinstance(value, str) and value.strip():
        return value.strip()

    key = obj.get("_key")
    if isinstance(key, str) and key.strip():
        tail = key.rsplit("!", 1)[-1].strip()
        if tail and tail != key:
            return tail

    raise ValueError("STRUCTURED_ID_MISSING")
'''


READ_SOURCE_RECORDS = '''
def read_source_records(
    root: Path,
    family_or_kind: dict | str,
    type_key: str | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return (publication entities, Foundry folder records).

    Canonical publication entities are keyed by stable Foundry/source ID.
    Folder records remain keyed by display slug because they are used only for
    generated-page organizational reconciliation.

    Multiple distinct source records may share a display-name slug. They must
    remain distinct canonical entities.
    """
    if isinstance(family_or_kind, dict):
        family = family_or_kind
        base = root / str(family.get("source_path") or "")
        actor_type = str(family.get("actor_type") or "").strip()
    else:
        kind = str(family_or_kind)
        if not type_key:
            return {}, {}
        base = root / "src" / "packs" / kind / type_key
        actor_type = ""

    entities: dict[str, str] = {}
    folders: dict[str, str] = {}
    if not base.exists():
        return entities, folders

    for source_path in sorted(base.rglob("*.json")):
        try:
            obj = json.loads(source_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        name = obj.get("name")
        if not name:
            continue

        rel = norm_rel(source_path, root)
        slug = slugify(str(name))

        if is_foundry_folder_obj(obj):
            folders.setdefault(slug, rel)
            continue

        if actor_type and str(obj.get("type") or "") != actor_type:
            continue

        try:
            source_id = foundry_stable_id(obj)
        except ValueError as exc:
            raise RuntimeError(f"{exc}: {rel}") from exc

        previous = entities.get(source_id)
        if previous is not None and previous != rel:
            raise RuntimeError(
                "STRUCTURED_ID_DUPLICATE: "
                f"{source_id!r} occurs in both {previous!r} and {rel!r}"
            )
        entities[source_id] = rel

    return entities, folders
'''


RECONCILE = '''
def _source_page_slug(root: Path, source_rel: str) -> tuple[str, str]:
    """Return (display name, generated-page slug) for a structured source."""
    path = root / source_rel
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return Path(source_rel).stem, slugify(Path(source_rel).stem)
    name = str(obj.get("name") or Path(source_rel).stem)
    return name, slugify(name)


def reconcile_generator_outputs(
    root: Path,
    generator_families: dict[str, dict],
) -> list[dict]:
    """Reconcile canonical source entities with configured generated outputs.

    Canonical entity counts are stable-ID based. Generated pages remain
    display-slug based. Same-name canonical entities therefore produce explicit
    ``structured_slug_collisions`` diagnostics rather than being silently
    collapsed from ``source_entities``.
    """
    rows: list[dict] = []

    for type_key, family in sorted(generator_families.items()):
        kind = str(family.get("kind") or "")
        entities, folders = read_source_records(root, family)

        slug_to_entities: dict[str, list[dict[str, str]]] = defaultdict(list)
        for source_id, source_rel in sorted(entities.items()):
            display_name, page_slug = _source_page_slug(root, source_rel)
            slug_to_entities[page_slug].append({
                "source_id": source_id,
                "name": display_name,
                "source_path": source_rel,
            })

        expected_page_slugs = set(slug_to_entities)
        folder_slugs = set(folders)

        slug_collisions = []
        for page_slug, records in sorted(slug_to_entities.items()):
            if len(records) > 1:
                slug_collisions.append({
                    "slug": page_slug,
                    "record_count": len(records),
                    "records": records,
                })

        for audience in family.get("audiences", []):
            out_rel = str(family.get("output_dirs", {}).get(audience, ""))
            actual: set[str] = set()
            if out_rel:
                out_base = root / "docs" / out_rel
                if out_base.exists():
                    actual = {
                        page.parent.name
                        for page in out_base.glob("*/index.md")
                        if page.is_file()
                    }

            organizational = sorted((actual - expected_page_slugs) & folder_slugs)
            missing = sorted(expected_page_slugs - actual)
            orphan = sorted(actual - expected_page_slugs - folder_slugs)

            rows.append({
                "audience": "player" if audience == "player-facing" else "gm",
                "type": type_key,
                "kind": kind,
                "source_path": str(family.get("source_path") or ""),
                "output_dir": f"docs/{out_rel}" if out_rel else "",
                "source_entities": len(entities),
                "source_page_slugs": len(expected_page_slugs),
                "foundry_folders": len(folders),
                "generated_pages": len(actual),
                "missing_generated_pages": missing,
                "organizational_generated_pages": organizational,
                "orphan_generated_pages": orphan,
                "structured_slug_collision_count": len(slug_collisions),
                "structured_slug_collisions": slug_collisions,
            })

    return rows
'''


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        help="Inventory builder to upgrade; defaults to pyCybermancy/build-rulebook-inventory.py",
    )
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args(argv)

    repo_root = infer_repo_root()
    target = Path(args.target).expanduser() if args.target else (
        repo_root / "pyCybermancy" / "build-rulebook-inventory.py"
    )
    if not target.is_absolute():
        target = (repo_root / target).resolve()

    if not target.is_file():
        raise RuntimeError(f"Target inventory builder does not exist: {target}")

    text = target.read_text(encoding="utf-8")

    if 'SCRIPT_VERSION = "0.2.4"' in text:
        print(f"PASS: {target} is already v0.2.4")
        return 0

    if 'SCRIPT_VERSION = "0.2.3"' not in text:
        raise RuntimeError(
            "This upgrader expects the known v0.2.3 inventory builder. "
            f"Target version marker not found in {target}."
        )

    text = text.replace('SCRIPT_VERSION = "0.2.3"', 'SCRIPT_VERSION = "0.2.4"', 1)
    text = text.replace(
        'SCHEMA_VERSION = "cybermancy-rulebook-inventory-v0.2.3"',
        'SCHEMA_VERSION = "cybermancy-rulebook-inventory-v0.2.4"',
        1,
    )

    anchor = "\n\ndef parse_json_object("
    if anchor not in text:
        raise RuntimeError("Could not locate parse_json_object() insertion anchor.")
    text = text.replace(anchor, "\n\n" + FOUNDRY_ID_HELPER.strip() + anchor, 1)

    text = replace_once(
        text,
        r"def read_source_records\([\s\S]*?\n\ndef read_source_entities\(",
        READ_SOURCE_RECORDS.strip() + "\n\n\ndef read_source_entities(",
        "read_source_records()",
    )

    text = replace_once(
        text,
        r"def reconcile_generator_outputs\([\s\S]*?\n\ndef classify_authorship\(",
        RECONCILE.strip() + "\n\n\ndef classify_authorship(",
        "reconcile_generator_outputs()",
    )

    if not args.no_backup:
        backup = target.with_name(target.name + ".v0.2.3.bak")
        if not backup.exists():
            shutil.copy2(target, backup)

    target.write_text(text, encoding="utf-8")
    py_compile.compile(str(target), doraise=True)

    print(f"PASS: upgraded {target}")
    print('  SCRIPT_VERSION = "0.2.4"')
    print('  SCHEMA_VERSION = "cybermancy-rulebook-inventory-v0.2.4"')
    print("  canonical structured entities now use stable Foundry/source IDs")
    print("  duplicate generated-page slugs are explicit diagnostics")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
