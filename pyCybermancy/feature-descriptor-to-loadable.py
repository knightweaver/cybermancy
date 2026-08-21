#!/usr/bin/env python3

from __future__ import annotations
import argparse, csv, json, re, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ------------------------
# Foldering helpers
# ------------------------
_SANITIZE_CHARS = re.compile(r'[^A-Za-z0-9._ \-]+')


def _safe(name: str, default: str = "Unknown") -> str:
    if name is None:
        return default
    s = str(name).strip()
    if not s:
        return default
    s = _SANITIZE_CHARS.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or default


def _row_get(row: dict, *keys, default=None):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


def compute_folder_parts(item: Dict[str, Any], row: Dict[str, Any]) -> List[str]:
    """
    domainCard -> [system.domain]
    feature    -> [class , subclass]
    Fallbacks to Unknown tokens if missing.
    """
    itype = (item.get("type") or "").strip().lower()
    sys_ = item.get("system") or {}
    if itype == "domaincard":
        domain = sys_.get("domain") or _row_get(row, "domain", "Domain")
        return [_safe(domain, "UnknownDomain")]
    # default: feature
    cls = (
            sys_.get("class")
            or _row_get(row, "class", "Class", "className", "parentClass")
    )
    sub = (
            sys_.get("subclass")
            or _row_get(row, "subclass", "Subclass", "subClass", "Archetype", "Track")
    )
    return [_safe(cls, "UnknownClass"), _safe(sub, "General")]


"""
build_features_from_descriptors.py
Create Foundry/Daggerheart loadable JSON Items for Features (class/subclass) and Domain Cards
from a flat descriptor CSV/JSON/Excel. Each row becomes one loadable file and can include a configured Action.

New:
- Excel support (.xlsx/.xlsm/.xls) via --sheet SHEET_NAME (or index).
  Requires pandas + openpyxl for .xlsx/.xlsm.

Usage:
  python build_features_from_descriptors.py input.csv  -o out/
  python build_features_from_descriptors.py input.json -o out/
  python build_features_from_descriptors.py input.xlsx --sheet "Features" -o out/
  python build_features_from_descriptors.py input.xlsx --sheet 0 -o out/
"""
"""
build_features_from_descriptors.py
Create Foundry/Daggerheart loadable JSON Items for **Features** (class, subclass) and **Domain Cards**
from a flat descriptor CSV/JSON. Each row becomes one loadable file and includes a configured Action.

Input: CSV (recommended) or JSON (array/object). Columns (case-insensitive; hyphens/underscores ignored):
  Core:
    - name, type, img, description
    - domain            (required for type=domainCard)
    - system.level      (number, domainCard)
    - recallCost        (number, domainCard; defaults to 1)
    - system.type       (string, domainCard; defaults "ability")
    - tier              (number, cybernetics; defaults to 1
  Action (single action per row; all optional unless noted):
    - action.name           (required to emit an action)
    - action.kind           (attack|effect)  -> maps to action["type"]; default "effect"
    - action.actionType     (action|reaction) default "action"
    - action.description    (HTML/text)
    - action.img            (falls back to row img)
    - action.range          (e.g., "melee","veryFar","")
    - action.target.type    (e.g., "any")
    - action.target.amount  (int or blank)
    - action.cost           (JSON or "stress:1, hope:1"  -> parsed to [{"key":"stress","value":1,...}, ...])
    - action.uses.value / action.uses.max / action.uses.recovery / action.uses.consumeOnSuccess
    - action.damage         ("d8+2" etc.) + action.damage.type ("physical,magical") + action.damage.applyTo ("hitPoints")
    - action.save.trait     (e.g., "agility")
    - action.save.difficulty (int)
    - action.save.damageMod (none|half|negate)
    - action.roll.useDefault (bool) | action.roll.trait | action.roll.type | action.roll.difficulty | action.roll.advState

Usage:
  python build_features_from_descriptors.py input.csv -o out_dir/
  python build_features_from_descriptors.py input.json -o out_dir/

Notes:
- No action _id fields are written (Foundry will assign).
- Unknown columns are ignored. Explicit JSON path headers like "system.level" are honored.
"""

# ----------------------- helpers -----------------------

TOP_LEVEL_FIELDS = {"name", "img", "type"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _coerce_scalar(x: Any) -> Any:
    if x is None: return None
    if isinstance(x, (bool, int, float, dict, list)): return x
    s = str(x).strip()
    if s == "": return ""
    low = s.lower()
    if low == "true": return True
    if low == "false": return False
    if low in {"null", "none"}: return None
    # try JSON
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")) or (
            s.startswith('"') and s.endswith('"')):
        try:
            return json.loads(s)
        except Exception:
            pass
    if re.fullmatch(r"[+-]?\d+", s): return int(s)
    if re.fullmatch(r"[+-]?\d+\.\d+", s): return float(s)
    return s


def _read_records(path: Path, sheet: Optional[str | int] = None) -> List[Dict[str, Any]]:
    suf = path.suffix.lower()
    if suf == ".csv":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                rows.append({k: _coerce_scalar(v) for k, v in row.items()})
        if not rows: raise SystemExit("CSV has no rows.")
        return rows

    if suf in {".json"}:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict): return [data]
        if isinstance(data, list): return [dict(x) for x in data]
        raise SystemExit("Descriptor JSON must be object or array of objects.")

    if suf in {".xlsx", ".xlsm", ".xls"}:
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise SystemExit("Reading Excel requires pandas (and openpyxl for .xlsx/.xlsm).") from e
        # sheet can be int or str; default to first sheet
        sheet_arg = sheet if sheet is not None else 0
        try:
            df = pd.read_excel(path, sheet_name=sheet_arg, dtype=str)
        except Exception as e:
            raise SystemExit(f"Failed to read Excel sheet '{sheet_arg}': {e}")
        # Convert to list of dicts with coercion
        df = df.fillna("")  # keep blanks consistent
        rows = [{str(k): _coerce_scalar(v) for k, v in rec.items()} for rec in df.to_dict(orient="records")]
        if not rows: raise SystemExit("Excel sheet has no rows.")
        return rows

    raise SystemExit(f"Unsupported descriptor format: {suf}")


def _path_for_header(h: str) -> List[str]:
    if "." in h:
        return [p for p in h.split(".") if p]
    if h in TOP_LEVEL_FIELDS:
        return [h]
    return ["system", h]


def _set_in(obj: Dict[str, Any], path: List[str], value: Any) -> None:
    cur = obj
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value


def _get(d: Dict[str, Any], *aliases: str, default=None):
    """Fetch value by alias; hyphen/underscore/case-insensitive."""
    if not isinstance(d, dict): return default
    norm_map = {_norm(k): k for k in d.keys()}
    for a in aliases:
        key = norm_map.get(_norm(a))
        if key is not None:
            return d.get(key)
    return default


def _parse_damage_str(s: Any) -> Dict[str, Any]:
    m = re.match(r"^\s*([A-Za-z0-9]*\d*d\d+)(?:\s*([+\-])\s*(\d+))?\s*$", str(s or ""))
    if not m: return {"dice": "d6", "bonus": 0}
    dice = m.group(1)
    bonus = (-1 if m.group(2) == "-" else 1) * int(m.group(3)) if m.group(3) else 0
    return {"dice": dice, "bonus": bonus}


def _parse_cost(s: Any) -> List[Dict[str, Any]]:
    """
    Accepts JSON array or a shorthand like "stress:1, hope:2"
    -> [{"key":"stress","value":1,"keyIsID":False,"scalable":False,"step":None}, ...]
    """
    if isinstance(s, list):
        return s
    if isinstance(s, dict):
        return [{"key": k, "value": v, "keyIsID": False, "scalable": False, "step": None} for k, v in s.items()]
    txt = str(s or "").strip()
    if not txt: return []
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    out = []
    for p in parts:
        m = re.match(r"^([A-Za-z_][\w\-]*?)\s*:\s*([+-]?\d+)$", p)
        if not m: continue
        out.append({"key": m.group(1), "value": int(m.group(2)), "keyIsID": False, "scalable": False, "step": None, "consumeOnSuccess": False})
    return out


def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w.\- ]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s or "unnamed"


# ----------------------- action builder -----------------------

def build_action(row: Dict[str, Any], fallback_img: str) -> Optional[Dict[str, Any]]:
    aname = _get(row, "action.name", "action_name", "action")
    if not aname or str(aname).strip() == "":
        return None

    kind = (_get(row, "action.kind", "action_type") or "effect").strip().lower()
    if kind not in {"attack", "effect"}:
        kind = "effect"

    actionType = (_get(row, "action.actionType", "action_actiontype") or "action").strip().lower()
    if actionType not in {"action", "reaction", "passive"}:
        actionType = "action"

    # damage
    dmg_str = _get(row, "action.damage", "damage")
    dmg_type = _get(row, "action.damage.type", "damageType", "action.damageType")
    dmg_apply = _get(row, "action.damage.applyTo", "applyTo", "action.applyTo") or "hitPoints"
    dmg = _parse_damage_str(dmg_str) if dmg_str else None
    types = []
    if isinstance(dmg_type, list):
        types = [str(x) for x in dmg_type]
    elif isinstance(dmg_type, str) and dmg_type.strip():
        types = [t.strip() for t in dmg_type.split(",") if t.strip()]

    # save
    save_trait = _get(row, "action.save.trait", "save_trait")
    save_diff = _get(row, "action.save.difficulty", "save_dc", "save_difficulty")
    save_mod = (_get(row, "action.save.damageMod", "save_damagemod") or "none") if (save_trait or save_diff) else "none"

    # roll
    useDefault = _get(row, "action.roll.useDefault", "roll_useDefault")
    roll = {
        "type": _get(row, "action.roll.type", "roll_type"),
        "trait": _get(row, "action.roll.trait", "roll_trait"),
        "difficulty": _get(row, "action.roll.difficulty", "roll_difficulty"),
        "bonus": _get(row, "action.roll.bonus", "roll_bonus"),
        "advState": _get(row, "action.roll.advState", "roll_advState") or "neutral",
        "diceRolling": {"multiplier": "prof", "flatMultiplier": 1, "dice": "d6", "compare": None, "treshold": None},
        "useDefault": bool(useDefault) if isinstance(useDefault, bool) else False
    }

    action = {
        "type": kind,
        "systemPath": "actions",
        "description": _get(row, "action.description", "action_desc", "action.text", "description") or "",
        "chatDisplay": True,
        "actionType": actionType,
        "cost": _parse_cost(_get(row, "action.cost")),
        "uses": {
            "value": _get(row, "action.uses.value"),
            "max": _get(row, "action.uses.max", "uses_max") or "",
            "recovery": _get(row, "action.uses.recovery"),
            "consumeOnSuccess": bool(_get(row, "action.uses.consumeOnSuccess")) if isinstance(
                _get(row, "action.uses.consumeOnSuccess"), bool) else False
        },
        "effects": [],
        "target": {
            "type": _get(row, "action.target.type", "target_type") or "any",
            "amount": _get(row, "action.target.amount", "target_amount")
        },
        "name": str(aname),
        "img": _get(row, "action.img",
                    "action_icon") or fallback_img or "icons/skills/melee/blade-tip-smoke-green.webp",
        "range": _get(row, "action.range") or ""
    }

    if kind == "attack":
        parts = []
        if dmg:
            parts.append({
                "value": {
                    "custom": {"enabled": False, "formula": ""},
                    "multiplier": "prof",
                    "dice": dmg["dice"],
                    "bonus": dmg["bonus"],
                    "flatMultiplier": 1
                },
                "applyTo": dmg_apply,
                "type": types or ["physical"],
                "base": False,
                "resultBased": False,
                "valueAlt": {
                    "multiplier": "prof", "flatMultiplier": 1, "dice": "d6", "bonus": None,
                    "custom": {"enabled": False, "formula": ""}
                }
            })
        action["damage"] = {"parts": parts, "includeBase": False}
        action["roll"] = roll
        if save_trait or save_diff:
            try:
                sd = int(save_diff) if (isinstance(save_diff, (int, float)) or (
                            isinstance(save_diff, str) and save_diff.isdigit())) else None
            except Exception:
                sd = None
            action["save"] = {"trait": save_trait or None, "difficulty": sd, "damageMod": save_mod}
    return action


# ----------------------- row -> item -----------------------

def build_item_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    name = _get(row, "name") or ""
    itype = (_get(row, "type") or "feature").strip()
    img = _get(row, "img") or ""
    tier = _get(row, "tier") or ""

    item: Dict[str, Any] = {
        "name": name,
        "type": itype,
        "img": img,
        "tier": tier,
        "system": {"description": _get(row, "description") or ""},
        "effects": []
    }

    # Domain card specifics
    if itype.lower() == "domaincard":
        level = _get(row, "system.level", "level")
        if level is not None:
            try:
                level = int(level)
            except Exception:
                pass
        item["system"]["level"] = level if level is not None else 1
        item["system"]["domain"] = _get(row, "domain") or ""
        rc = _get(row, "recallCost", "system.recallCost")
        item["system"]["recallCost"] = rc if (rc is not None and str(rc) != "") else 1
        item["system"]["type"] = _get(row, "system.type") or "ability"
        inv = _get(row, "system.inVault")
        item["system"]["inVault"] = bool(inv) if isinstance(inv, bool) else False

    # Build action
    action = build_action(row, img)
    if action:
        item["system"]["actions"] = { action["name"]: action }

    return item


# ----------------------- CLI -----------------------

def main():
    ap = argparse.ArgumentParser(
        description="Build Daggerheart Feature/Domain Card Items with configured Action from CSV/JSON/Excel descriptors.")
    ap.add_argument("descriptor", help="CSV, JSON (array/object), or Excel (.xlsx/.xlsm/.xls)")
    ap.add_argument("-o", "--out", required=True, help="Output directory")
    ap.add_argument("--sheet", help="Excel sheet name or 0-based index when reading .xlsx/.xlsm/.xls")
    args = ap.parse_args()

    in_path = Path(args.descriptor)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Normalize sheet argument to int if numeric
    sheet_arg: Optional[str | int] = None
    if args.sheet is not None:
        if re.fullmatch(r"\d+", str(args.sheet)):
            sheet_arg = int(args.sheet)
        else:
            sheet_arg = args.sheet

    rows = _read_records(in_path, sheet=sheet_arg)

    written = 0
    for i, row in enumerate(rows, start=1):
        item = build_item_from_row(row)
        fname_base = item.get("name") or f"row-{i}"

        # Determine organized output folder(s)
        parts = compute_folder_parts(item, row)
        out_dir_p = out_dir.joinpath(*parts)
        out_dir_p.mkdir(parents=True, exist_ok=True)

        fname = _sanitize_filename(str(fname_base)) + ".json"
        out_path = out_dir_p / fname
        if out_path.exists():
            n = 2
            while (out_dir_p / f"{_sanitize_filename(str(fname_base))}#{n}.json").exists():
                n += 1
            out_path = out_dir_p / f"{_sanitize_filename(str(fname_base))}#{n}.json"
        out_path.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1

    print(f"Wrote {written} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
