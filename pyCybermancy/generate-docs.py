#!/usr/bin/env python3
"""
Generate CSV indexes and Markdown detail pages (canonical layout) for Cybermancy.

What's new vs. your original:
1) Per-type templates and CSV columns via CONFIG & TEMPLATES (easy to extend).
2) Supports system packs: classes, subclasses, domains, features.
3) Emits a CSV index for every processed type (items & system).

Default layout:
- Reads JSON from:
    items:  <repo-root>/src/packs/items/<type>/**/*.json
    system: <repo-root>/src/packs/system/<type>/**/*.json
- Writes CSV to:  <repo-root>/docs/data/<type>.csv
- Writes pages to:
    items:  <repo-root>/docs/<audience>/items/<type>/<slug>/index.md
    system: <repo-root>/docs/<audience>/<type>/<slug>/index.md

Usage:
  python generate-docs.py --audience player-facing
  python generate-docs.py --audience gm-facing
  python generate-docs.py --repo-root .
"""

from pathlib import Path
import argparse, csv, json, re
from typing import Dict, Any, List

# ---------------------------- Utilities --------------------------------------

def get_in(obj: Dict[str, Any], dotted: str, default: str = "") -> Any:
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur if cur is not None else default

_slug_re = re.compile(r"[^a-z0-9\-]+")
def slugify(s: str) -> str:
    s = (s or "").strip().lower().replace(" ", "-")
    s = _slug_re.sub("-", s)
    return re.sub(r"-+", "-", s).strip("-") or "item"

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def md_escape(s: str) -> str:
    return (s or "").replace("<", "&lt;").replace(">", "&gt;")

def titleize(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s

# ---------------------------- Templates --------------------------------------
# Each template gets values from a per-type "context" dict assembled in the loop.
# Keep these minimal; type-specific sections can be added as needed.

TEMPLATES: Dict[str, str] = {
    # Generic item page template ---------------------------------------------
    "item_default": """<div class="item" markdown="1">

<div class="grid item-grid" markdown="1">

<div markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image">

### {name}
<div class="item-subtitle">{type_title} • {rarity} • {domain}</div>

<div class="item-flavor">
*{flavor}*
</div>

<div class="badges">
  <span class="badge">{category}</span>
  {badge_domain}
  {badge_weight}
  {badge_cost}
</div>
</div>

<div markdown="1">

#### Stats
<table class="stat-table">
  <thead><tr><th>Attribute</th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Category</td><td>{category}</td></tr>
    <tr><td>Damage</td><td>{damage}</td></tr>
    <tr><td>Range</td><td>{range}</td></tr>
    <tr><td>Hands</td><td>{hands}</td></tr>
    <tr><td>Reload/Charges</td><td>{reload}</td></tr>
    <tr><td>Requirements</td><td>{requirements}</td></tr>
  </tbody>
</table>

#### Effects
- *(Map rules/effects here if provided in JSON.)*

#### Usage
- *(Notes on reload/drawbacks/synergies.)*

</div>
</div>

---

#### Description
{description}

<div class="meta" markdown="1">
**Source:** *(fill in)* • **UUID:** `Compendium.cybermancy.{comp_key}.{slug}`
</div>

</div>
""",

    # Classes (system) --------------------------------------------------------
    "class": """<div class="class" markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image">

# {name}
<div class="item-subtitle">Class • {rarity}</div>

<div class="badges">
  {badge_role}
  {badge_domain}
</div>

## Overview
{summary}

## Playstyle
{playstyle}

## Starting Features
{starting_features_md}

---

## Description
{description}

<div class="meta" markdown="1">
**Source:** *(fill in)* • **UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
""",

    # Subclasses (system) -----------------------------------------------------
    "subclass": """<div class="subclass" markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image">

# {name}
<div class="item-subtitle">Subclass • {parent_class}</div>

<div class="badges">
  {badge_domain}
</div>

## Concept
{summary}

## Features
{features_md}

---

## Description
{description}

<div class="meta" markdown="1">
**Source:** *(fill in)* • **UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
""",

    # Domains (system) --------------------------------------------------------
    "domain": """<div class="domain" markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image">

# {name} Domain
<div class="item-subtitle">{theme}</div>

## Tenets
{tenets_md}

## Domain Moves / Boons
{moves_md}

---

## Description
{description}

<div class="meta" markdown="1">
**Source:** *(fill in)* • **UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
""",

    # Features (system) -------------------------------------------------------
    "feature": """<div class="feature" markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image">

# {name}
<div class="item-subtitle">Feature • {rarity}</div>

<div class="badges">
  {badge_domain}
  {badge_level}
</div>

## Effect
{effect_text}

---

## Description
{description}

<div class="meta" markdown="1">
**Source:** *(fill in)* • **UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
"""
}

# ---------------------------- Configuration ----------------------------------
# Each entry describes one output "type_key".
# - kind: "item" or "system" (controls source dirs and output dirs)
# - src_subdir: subdirectory under src/packs/<kind> where JSONs live
# - csv_fields: columns for the index CSV
# - field_map: dotted lookups to lift into page contexts/CSV
# - template: key in TEMPLATES
# - image_rel: function to compute relative image path from detail page
#
# To customize a type: edit csv_fields, field_map, or template here.

DEFAULT_ITEM_FIELD_MAP = {
    "name": "name",
    "category": "system.category",
    "damage": "system.damage",
    "range": "system.range",
    "rarity": "system.rarity",
    "domain": "system.domain",
    "hands": "system.hands",
    "reload": "system.reload",
    "requirements": "system.requirements",
    "flavor": "system.flavor",
    "description": "system.description",
    "img": "img"
}

CONFIG: Dict[str, Dict[str, Any]] = {
    # ---------------- Items ----------------
    "weapons": {
        "kind": "items",
        "src_subdir": "weapons",
        "csv_fields": ["name","slug","category","damage","range","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "weapons",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "armors": {
        "kind": "items",
        "src_subdir": "armors",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "armors",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "ammo": {
        "kind": "items",
        "src_subdir": "ammo",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "ammo",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "consumables": {
        "kind": "items",
        "src_subdir": "consumables",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "consumables",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "cybernetics": {
        "kind": "items",
        "src_subdir": "cybernetics",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP | {
            # example extra fields you might have in cyberware
            "slot": "system.slot",
            "essence": "system.essence"
        },
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "cybernetics",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "drones-devices": {
        "kind": "items",
        "src_subdir": "drones-devices",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "drones-devices",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "mods": {
        "kind": "items",
        "src_subdir": "mods",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "mods",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "loot": {
        "kind": "items",
        "src_subdir": "loot",
        "csv_fields": ["name","slug","category","rarity","domain"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "loot",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },

    # ---------------- System ----------------
    "classes": {
        "kind": "system",
        "src_subdir": "classes",
        "csv_fields": ["name","slug","rarity","role","domain"],
        "field_map": {
            "name": "name",
            "rarity": "system.rarity",
            "role": "system.role",
            "domain": "system.domain",
            "summary": "system.summary",
            "playstyle": "system.playstyle",
            "starting_features": "system.startingFeatures",
            "description": "system.description",
            "img": "img"
        },
        "template": "class",
        "image_rel": lambda audience, key, slug: f"../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/{key}"
    },
    "subclasses": {
        "kind": "system",
        "src_subdir": "subclasses",
        "csv_fields": ["name","slug","parent_class","domain"],
        "field_map": {
            "name": "name",
            "parent_class": "system.parentClass",
            "domain": "system.domain",
            "summary": "system.summary",
            "features": "system.features",
            "description": "system.description",
            "img": "img"
        },
        "template": "subclass",
        "image_rel": lambda audience, key, slug: f"../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/{key}"
    },
    "domains": {
        "kind": "system",
        "src_subdir": "domains",
        "csv_fields": ["name","slug","theme"],
        "field_map": {
            "name": "name",
            "theme": "system.theme",
            "tenets": "system.tenets",
            "moves": "system.moves",
            "description": "system.description",
            "img": "img"
        },
        "template": "domain",
        "image_rel": lambda audience, key, slug: f"../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/{key}"
    },
    "features": {
        "kind": "system",
        "src_subdir": "features",
        "csv_fields": ["name","slug","rarity","level","domain"],
        "field_map": {
            "name": "name",
            "rarity": "system.rarity",
            "level": "system.level",
            "domain": "system.domain",
            "effect_text": "system.effect",
            "description": "system.description",
            "img": "img"
        },
        "template": "feature",
        "image_rel": lambda audience, key, slug: f"../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/{key}"
    }
}

# ---------------------------- Rendering helpers ------------------------------

def render_template(tmpl_key: str, ctx: Dict[str, Any]) -> str:
    tmpl = TEMPLATES[tmpl_key]
    return tmpl.format(**ctx)

def list_to_md_bullets(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return "\n".join(f"- {md_escape(str(x))}" for x in val)
    return f"- {md_escape(str(val))}"

def features_to_md(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return "\n".join(f"- **{md_escape(str(x.get('name','')))}** — {md_escape(str(x.get('text','')))}" for x in val)
    if isinstance(val, dict):
        return "\n".join(f"- **{md_escape(k)}** — {md_escape(str(v))}" for k, v in val.items())
    return md_escape(str(val))

# ---------------------------- Main -------------------------------------------

def process_type(root: Path, docs_root: Path, data_root: Path, audience: str, type_key: str):
    cfg = CONFIG[type_key]
    kind = cfg["kind"]
    src_dir = root / "src" / "packs" / kind / cfg["src_subdir"]
    if not src_dir.exists():
        return 0, None

    rows: List[Dict[str, Any]] = []
    field_map = cfg["field_map"]
    template_key = cfg["template"]
    out_dir_rel = cfg["out_dir_name"](audience, type_key)
    out_dir = docs_root / out_dir_rel
    ensure_dir(out_dir)

    count = 0
    for p in sorted(src_dir.rglob("*.json")):
        obj = read_json(p)
        name = get_in(obj, field_map.get("name", "name"))
        if not name:
            continue
        slug = slugify(name)

        # Common basics
        img_hint = get_in(obj, field_map.get("img", "img"))
        rarity = get_in(obj, field_map.get("rarity", "system.rarity"))
        domain = get_in(obj, field_map.get("domain", "system.domain"))
        category = get_in(obj, field_map.get("category", "system.category"))
        description = get_in(obj, field_map.get("description", "system.description"))

        # CSV row (columns per config)
        csv_row = {"name": name, "slug": slug}
        for col in cfg["csv_fields"]:
            if col in ("name","slug"):  # already set
                continue
            src = field_map.get(col, col)  # allow direct JSON col if mapped
            csv_row[col] = get_in(obj, src, "")
        rows.append(csv_row)

        # Per-type context
        ctx: Dict[str, Any] = {
            "name": md_escape(name),
            "slug": slug,
            "rarity": md_escape(rarity or "Common"),
            "domain": md_escape(domain or "—"),
            "category": md_escape(category or titleize(type_key)),
            "description": md_escape(description or "(No description yet.)"),
            "comp_key": cfg.get("comp_key", type_key),
            "type_title": titleize(type_key[:-1]) if type_key.endswith("s") else titleize(type_key),
        }

        # Item-specific enrichments
        if kind == "items":
            damage = get_in(obj, field_map.get("damage",""))
            rng = get_in(obj, field_map.get("range",""))
            hands = get_in(obj, field_map.get("hands",""))
            reload_ = get_in(obj, field_map.get("reload",""))
            requirements = get_in(obj, field_map.get("requirements",""))
            flavor = get_in(obj, field_map.get("flavor",""))

            ctx.update({
                "damage": md_escape(damage or "—"),
                "range": md_escape(rng or "—"),
                "hands": md_escape(hands or "—"),
                "reload": md_escape(reload_ or "—"),
                "requirements": md_escape(requirements or "—"),
                "flavor": md_escape(flavor or ""),
                "badge_domain": f'<span class="badge tag">{md_escape(domain)}</span>' if domain else "",
                "badge_weight": "",
                "badge_cost": ""
            })

            # Image relative to detail page (under docs/<audience>/items/<type>/<slug>/index.md)
            image_rel = cfg["image_rel"](audience, type_key, slug)

            detail_dir = docs_root / out_dir_rel / slug
            ensure_dir(detail_dir)
            ctx["image_rel"] = image_rel

        # System types enrichments
        else:
            # All system types write to docs/<audience>/<type>/<slug>/index.md
            image_rel = cfg["image_rel"](audience, type_key, slug)
            detail_dir = docs_root / out_dir_rel / slug
            ensure_dir(detail_dir)
            ctx["image_rel"] = image_rel

            if type_key == "classes":
                ctx["badge_role"] = f'<span class="badge">{md_escape(get_in(obj, field_map["role"]))}</span>' if get_in(obj, field_map["role"]) else ""
                ctx["badge_domain"] = f'<span class="badge tag">{md_escape(domain)}</span>' if domain else ""
                ctx["summary"] = md_escape(get_in(obj, field_map["summary"], ""))
                ctx["playstyle"] = md_escape(get_in(obj, field_map["playstyle"], ""))
                starts = get_in(obj, field_map["starting_features"], [])
                ctx["starting_features_md"] = list_to_md_bullets(starts)

            elif type_key == "subclasses":
                ctx["parent_class"] = md_escape(get_in(obj, field_map["parent_class"], ""))
                ctx["badge_domain"] = f'<span class="badge tag">{md_escape(domain)}</span>' if domain else ""
                features = get_in(obj, field_map["features"], [])
                ctx["features_md"] = features_to_md(features)
                ctx["summary"] = md_escape(get_in(obj, field_map["summary"], ""))

            elif type_key == "domains":
                ctx["theme"] = md_escape(get_in(obj, field_map["theme"], ""))
                ctx["tenets_md"] = list_to_md_bullets(get_in(obj, field_map["tenets"], []))
                ctx["moves_md"]  = features_to_md(get_in(obj, field_map["moves"], []))

            elif type_key == "features":
                level = get_in(obj, field_map["level"], "")
                ctx["badge_domain"] = f'<span class="badge tag">{md_escape(domain)}</span>' if domain else ""
                ctx["badge_level"] = f'<span class="badge">Level {md_escape(str(level))}</span>' if level != "" else ""
                ctx["effect_text"] = md_escape(get_in(obj, field_map["effect_text"], ""))

        # Render and write
        page_md = render_template(template_key, ctx)
        (detail_dir / "index.md").write_text(page_md, encoding="utf-8")
        count += 1

    # CSV index
    if rows:
        csv_path = data_root / f"{type_key}.csv"
        ensure_dir(csv_path.parent)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CONFIG[type_key]["csv_fields"])
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {csv_path} ({len(rows)} rows)")

    return count, out_dir

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument("--audience", default="player-facing",
                    choices=["player-facing", "gm-facing"])
    # Optional: only generate a subset of types, comma-separated
    ap.add_argument("--types", default="",
                    help="Comma-separated type keys to build (default: all). "
                         "Examples: weapons,armors,classes,domains")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    docs_root = root / "docs"
    data_root = docs_root / "data"
    ensure_dir(docs_root)
    ensure_dir(data_root)

    # Determine which types to run
    all_types = list(CONFIG.keys())
    selected = [t.strip() for t in args.types.split(",") if t.strip()] if args.types else all_types

    total = 0
    for type_key in selected:
        if type_key not in CONFIG:
            print(f"[skip] Unknown type: {type_key}")
            continue
        n, out_dir = process_type(root, docs_root, data_root, args.audience, type_key)
        if n:
            print(f"[ok] {type_key}: {n} pages -> {out_dir}")
            total += n
        else:
            print(f"[warn] {type_key}: no JSON found")

    print(f"Done. Wrote {total} pages total.")

if __name__ == "__main__":
    main()
