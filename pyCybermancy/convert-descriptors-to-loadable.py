#!/usr/bin/env python3
"""
main.py — Descriptor -> Foundry/Daggerheart Item JSON (catalog-aware; JSON/CSV; batch)

Baseline:
- Catalog root: "actions-effects"
- Category key is descriptor["type"] verbatim (no pluralization)
- Reference fields: "additionalActions", "intrinsicEffects"
- Batch input: JSON object/array or CSV rows; each record -> one output named by 'name'
- system.weaponFeatures from "DHFeature" (CSV-delimited/string/list), sluggified to {"value":"<slug>"}

Updates:
1) Feature/critical actions from CSV/JSON columns:
   - cybermancy-feature-name, cybermancy-feature-effect  -> Action (type "effect", actionType "action")
   - critical-effect-name,   critical-effect             -> Generic action (type "effect", actionType "action")
   Description is HTML-formatted per spec.
2) Action image path: modules/cybermancy/assets/icons/features/{hyphen-slug}.png
3) Column name robustness: hyphens/underscores/case-insensitive (aliases supported).

Usage:
  python main.py descriptors.json -c actions-by-category.json -o outdir/
  python main.py descriptors.csv  -c actions-by-category.json -o outdir/
"""

from __future__ import annotations
import argparse, csv, json, re, sys
from pathlib import Path
from typing import Any, Dict, List

# -------------------- helpers --------------------
def as_list(v: Any) -> List[Any]:
    if v is None: return []
    return v if isinstance(v, list) else [v]

def to_int_or_default(v: Any, default: int) -> int:
    try: return int(v)
    except Exception: return default

def sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w.\- ]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s or "unnamed"

_DAMAGE_RE = re.compile(r"""^\s*([A-Za-z0-9]*\d*d\d+)(?:\s*([+\-])\s*(\d+))?\s*$""")

def parse_damage(s: Any) -> Dict[str, Any]:
    if not s: return {"dice": "d6", "bonus": 0}
    m = _DAMAGE_RE.match(str(s))
    if not m: return {"dice": "d6", "bonus": 0}
    dice = m.group(1)
    bonus = (-1 if m.group(2) == "-" else 1) * int(m.group(3)) if m.group(3) else 0
    return {"dice": dice, "bonus": bonus}

def _coerce_scalar(x: str) -> Any:
    if x is None: return None
    s = str(x).strip()
    if s == "": return ""
    low = s.lower()
    if low == "true": return True
    if low == "false": return False
    if low in ("null","none"): return None
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")) or (s.startswith('"') and s.endswith('"')):
        try: return json.loads(s)
        except Exception: pass
    if re.fullmatch(r"[+-]?\d+", s): return int(s)
    if re.fullmatch(r"[+-]?\d+\.\d+", s): return float(s)
    return s

def _split_list_cell(s: Any) -> List[str]:
    if s is None: return []
    if isinstance(s, list): return [str(x) for x in s]
    if isinstance(s, dict): return [json.dumps(s, ensure_ascii=False)]
    txt = str(s).strip()
    if txt == "": return []
    return [p for p in re.split(r"\s*[|,]\s*", txt) if p != ""]

def _slug_feature(s: str) -> str:
    out = re.sub(r"[^\w]+", "_", str(s).strip().lower())
    out = re.sub(r"_+", "_", out).strip("_")
    return out

def _slug_hyphen(s: str) -> str:
    out = re.sub(r"[^\w]+", "-", str(s).strip().lower())
    out = re.sub(r"-+", "-", out).strip("-")
    return out

def _norm_key(k: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (k or "").lower())

def get_field(d: Dict[str, Any], aliases: List[str]) -> Any:
    """Fetch value by any alias; hyphen/underscore/case insensitive."""
    if not isinstance(d, dict): return None
    norm_map = { _norm_key(k): k for k in d.keys() }
    for a in aliases:
        nk = _norm_key(a)
        if nk in norm_map:
            return d.get(norm_map[nk])
    return None

# -------------------- descriptor loading --------------------
def load_descriptors(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                d = {k: _coerce_scalar(v) for k, v in row.items()}
                for k in ("additionalActions", "intrinsicEffects", "damageType"):
                    if isinstance(d.get(k), str):
                        d[k] = _split_list_cell(d[k])
                if "DHFeature" in d:
                    feats = _split_list_cell(d["DHFeature"])
                    d["DHFeature"] = [_slug_feature(x) for x in feats if x]
                rows.append(d)
        if not rows:
            raise SystemExit("CSV descriptor has no rows.")
        return rows

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list):
        rows = data
    else:
        raise SystemExit("JSON descriptor must be an object or an array of objects.")

    for d in rows:
        for k in ("additionalActions", "intrinsicEffects", "damageType"):
            if isinstance(d.get(k), str):
                d[k] = _split_list_cell(d[k])
        if "DHFeature" in d:
            feats = d["DHFeature"]
            if isinstance(feats, str):
                feats = _split_list_cell(feats)
            elif isinstance(feats, list):
                feats = [str(x) for x in feats]
            else:
                feats = []
            d["DHFeature"] = [_slug_feature(x) for x in feats if x]
    return rows

# -------------------- builders --------------------
def build_attack(desc: Dict[str, Any]) -> Dict[str, Any]:
    dmg = parse_damage(desc.get("damage"))
    dmg_types = as_list(desc.get("damageType") or "physical")
    return {
        "name": "Attack",
        "img": desc.get("attackImg") or desc.get("img") or "icons/skills/melee/blood-slash-foam-red.webp",
        "systemPath": "attack",
        "type": "attack",
        "range": desc.get("range") or "melee",
        "target": {"type": "any", "amount": to_int_or_default(desc.get("numtargets"), 1)},
        "roll": {
            "trait": desc.get("trait") or "strength",
            "type": "attack",
            "difficulty": None,
            "bonus": None,
            "advState": "neutral",
            "diceRolling": {"multiplier": "prof", "flatMultiplier": 1, "dice": "d6"},
        },
        "damage": {
            "parts": [{
                "value": {
                    "dice": dmg["dice"],
                    "bonus": dmg["bonus"],
                    "multiplier": "prof",
                    "flatMultiplier": 1,
                    "custom": {"enabled": False, "formula": ""},
                },
                "type": dmg_types,
                "applyTo": desc.get("damageTo") or "hitPoints",
                "resultBased": False,
                "valueAlt": {
                    "multiplier": "prof", "flatMultiplier": 1,
                    "dice": "d6", "bonus": None,
                    "custom": {"enabled": False, "formula": ""},
                },
                "base": False,
            }],
            "includeBase": False,
        },
        "chatDisplay": True,
        "actionType": "action",
    }

def html_description_block(title: str, bullet: str, is_critical: bool = False) -> str:
    title_text = f"Critical Effect - {title}:" if is_critical else f"{title}:"
    return (
        "<p></p>"
        f"<p><span style=\"font-family: 'Bruno Ace'\"><strong>{title_text}</strong></span></p>"
        "<ul><li>"
        f"<p><span style=\"font-family: Montserrat, sans-serif\">{bullet}</span></p>"
        "</li></ul>"
    )

def build_feature_action(feature_name: str, feature_effect: str) -> Dict[str, Any]:
    """Cybermancy feature → Daggerheart action (type 'effect', actionType 'action')."""
    img = f"modules/cybermancy/assets/icons/features/{_slug_hyphen(feature_name)}.png"
    return {
        "type": "effect",
        "systemPath": "actions",
        "description": html_description_block(feature_name, feature_effect, is_critical=False),
        "chatDisplay": True,
        "actionType": "action",
        "cost": [],
        "uses": {"value": None, "max": "", "recovery": None, "consumeOnSuccess": False},
        "effects": [],
        "target": {"type": "any", "amount": None},
        "name": feature_name,
        "img": img,
        "range": "",
    }

def build_critical_effect_action(crit_name: str, crit_effect: str) -> Dict[str, Any]:
    """Critical effect → generic action (type 'effect', actionType 'action')."""
    img = f"modules/cybermancy/assets/icons/features/{_slug_hyphen(crit_name)}.png"
    return {
        "type": "effect",
        "systemPath": "actions",
        "description": html_description_block(crit_name, crit_effect, is_critical=True),
        "chatDisplay": True,
        "actionType": "action",
        "cost": [],
        "uses": {"value": None, "max": "", "recovery": None, "consumeOnSuccess": False},
        "effects": [],
        "target": {"type": "any", "amount": None},
        "name": f"Critical Effect:  {crit_name}",
        "img": img,
        "range": "",
    }

# -------------------- catalog resolution --------------------
def load_catalog(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read catalog {path}: {e}")

def resolve_ref_actions(catalog: Dict[str, Any], category: str, key: str) -> Dict[str, Any]:
    root = catalog.get("actions-effects")
    if not isinstance(root, dict):
        raise ValueError("Catalog missing 'actions-effects' root.")
    bucket_cat = root.get(category)
    if not isinstance(bucket_cat, dict):
        raise ValueError(f"Unknown category '{category}' in catalog.")
    entry = bucket_cat.get(key)
    if not isinstance(entry, dict):
        raise ValueError(f"Reference '{key}' not found under category '{category}'.")
    actions = entry.get("actions")
    if not isinstance(actions, dict) or not actions:
        raise ValueError(f"Reference '{key}' under '{category}' has no 'actions'.")
    return actions

def merge_actions(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        else:
            if json.dumps(dst[k], sort_keys=True) == json.dumps(v, sort_keys=True):
                continue

# -------------------- compile one item --------------------
def compile_one(desc: Dict[str, Any], catalog: Dict[str, Any]) -> Dict[str, Any]:
    if "name" not in desc or not str(desc["name"]).strip():
        raise ValueError("Descriptor is missing required 'name'.")
    category = (desc.get("type") or "").strip()
    if not category:
        raise ValueError("Descriptor is missing required 'type' (used as catalog category key).")

    system: Dict[str, Any] = {
        "description": desc.get("description") or "",
        "tier": to_int_or_default(desc.get("tier"), 1),
        "equipped": bool(desc.get("equipped", False)),
        "secondary": bool(desc.get("secondary", False)),
        "burden": desc.get("burden") or "twoHanded",
    }

    if (desc.get("primaryAction") or "attack") == "attack":
        system["attack"] = build_attack(desc)

    # weaponFeatures from DHFeature slugs
    feats = [f for f in as_list(desc.get("DHFeature")) if f]
    if feats:
        system["weaponFeatures"] = [{"value": f} for f in feats]

    # Catalog-referenced actions (additionalActions + intrinsicEffects)
    resolved_actions: Dict[str, Any] = {}
    for field in ("additionalActions", "intrinsicEffects"):
        for ref in as_list(desc.get(field)):
            if not ref: continue
            src_actions = resolve_ref_actions(catalog, category, ref)
            merge_actions(resolved_actions, src_actions)

    # Cybermancy feature -> action
    feat_name = (get_field(desc, ["cybermancy-feature-name", "cybermancy_feature_name", "cybermancyfeaturename"]) or "").strip()
    feat_text = (get_field(desc, ["cybermancy-feature-effect", "cybermancy_feature_effect", "cybermancyfeatureeffect"]) or "").strip()
    if feat_name:
        resolved_actions[feat_name] = build_feature_action(feat_name, feat_text)

    # Critical effect -> generic action
    crit_name = (get_field(desc, ["critical-effect-name", "critical_effect_name", "criticaleffectname"]) or "").strip()
    crit_text = (get_field(desc, ["critical-effect", "critical_effect", "criticaleffect"]) or "").strip()
    if crit_name:
        resolved_actions[crit_name] = build_critical_effect_action(crit_name, crit_text)

    if resolved_actions:
        system["actions"] = resolved_actions

    return {
        "name": desc["name"],
        "type": desc.get("type") or "weapon",
        "img": desc.get("img") or "",
        "system": system,
        "effects": [],
    }

# -------------------- CLI --------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Compile descriptor(s) (JSON object/array or CSV) -> Foundry/Daggerheart Item JSON (catalog-aware + cybermancy/critical actions)")
    ap.add_argument("descriptor", help="Descriptor file (.json or .csv)")
    ap.add_argument("-c", "--catalog", default="actions-by-category.json", help="Path to actions-by-category.json")
    ap.add_argument("-o", "--out", required=True, help="Output directory")
    args = ap.parse_args(argv)

    in_path = Path(args.descriptor)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog(Path(args.catalog))
    records = load_descriptors(in_path)

    written = 0
    for d in records:
        try:
            compiled = compile_one(d, catalog)
        except ValueError as e:
            raise SystemExit(f"Descriptor '{d.get('name','<unnamed>')}' error: {e}")
        fname = sanitize_filename(compiled["name"]) + ".json"
        target = out_dir / fname
        if target.exists():
            i = 2
            base = sanitize_filename(compiled["name"])
            while (out_dir / f"{base}#{i}.json").exists():
                i += 1
            target = out_dir / f"{base}#{i}.json"
        target.write_text(json.dumps(compiled, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1

    print(f"Wrote {written} file(s) to {out_dir}")

if __name__ == "__main__":
    main()
