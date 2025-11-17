#!/usr/bin/env python3
"""
Generate Foundry/Daggerheart loadable Actor JSON files for adversaries from a flat CSV/JSON descriptor.

The script focuses on producing lean, import-ready files (no _stats, flags, etc.) similar
in spirit to `feature-descriptor-to-loadable.py`.

Supported input formats
- CSV (recommended)
- JSON array/object

Column guidance (case-insensitive; hyphens/underscores ignored):
  Core actor fields
    - name, img, description
    - tier (number, default 1)
    - adversaryType / system.type (standard | elite | horde | etc., default "standard")
    - difficulty (number, default 1)
    - motivesAndTactics (string)
    - notes (HTML/text)

  Resources
    - hp / hitPoints (value+max) or hpValue / hpMax
    - stress (value+max) or stressValue / stressMax
    - hordeHp (number, horde-only)
    - damageThreshold.major / damageThreshold.severe (numbers)

  Base attack (single attack block stored in system.attack)
    - attack.name (default "Attack")
    - attack.range (melee|close|far|veryFar|etc.)
    - attack.description (HTML/text)
    - attack.img (falls back to actor img)
    - attack.target.type, attack.target.amount
    - attack.roll.type, attack.roll.trait, attack.roll.difficulty, attack.roll.bonus, attack.roll.advState
    - attack.damage (e.g., "d8+2")
    - attack.damage.type (comma separated list)
    - attack.damage.applyTo (hitPoints|stress|custom)

  Additional actions (action1.*, action2.*, ... -> stored under system.actions)
    - action<N>.name (required to emit an action)
    - action<N>.type (attack|effect; default effect)
    - action<N>.description
    - action<N>.img (fallback actor img)
    - action<N>.range
    - action<N>.target.type, action<N>.target.amount
    - action<N>.roll.* (same shape as attack.roll.*)
    - action<N>.damage / action<N>.damage.type / action<N>.damage.applyTo
    - action<N>.actionType (action|reaction|passive; default action)
    - action<N>.cost (JSON or "stress:1, hope:2")
    - action<N>.uses.value / uses.max / uses.recovery / uses.consumeOnSuccess

  Experiences (optional; stored as keyed objects under system.experiences)
    - experience1.name, experience1.value, experience1.description
    - experience2.name, ... (any positive integer suffix)

Unknown columns are ignored. Values are coerced to numbers/bools/JSON when possible.
"""

from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------- Utils ----------------
_TOP_LEVEL_FIELDS = {"name", "img", "type"}
_SANITIZE_CHARS = re.compile(r"[^A-Za-z0-9._ \-]+")


def _safe(text: Any, default: str = "") -> str:
    if text is None:
        return default
    s = str(text).strip()
    if not s:
        return default
    s = _SANITIZE_CHARS.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or default


def _coerce_scalar(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, (bool, int, float, dict, list)):
        return x
    s = str(x).strip()
    if s == "":
        return ""
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in {"null", "none"}:
        return None
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")) or (
        s.startswith('"') and s.endswith('"')
    ):
        try:
            return json.loads(s)
        except Exception:
            pass
    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)
    if re.fullmatch(r"[+-]?\d+\.\d+", s):
        return float(s)
    return s


def _read_records(path: Path) -> List[Dict[str, Any]]:
    suf = path.suffix.lower()
    if suf == ".csv":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                rows.append({k: _coerce_scalar(v) for k, v in row.items()})
        if not rows:
            raise SystemExit("CSV has no rows.")
        return rows

    if suf == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [dict(x) for x in data]
        raise SystemExit("Descriptor JSON must be object or array of objects.")

    raise SystemExit(f"Unsupported descriptor format: {suf}")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _get(row: Dict[str, Any], *aliases: str, default=None):
    norm_map = {_norm(k): k for k in row.keys()}
    for a in aliases:
        key = norm_map.get(_norm(a))
        if key is not None:
            return row.get(key)
    return default


def _parse_damage_str(s: Any) -> Dict[str, Any]:
    m = re.match(r"^\s*([A-Za-z0-9]*\d*d\d+)(?:\s*([+\-])\s*(\d+))?\s*$", str(s or ""))
    if not m:
        return {"dice": "d6", "bonus": 0}
    dice = m.group(1)
    bonus = (-1 if m.group(2) == "-" else 1) * int(m.group(3)) if m.group(3) else 0
    return {"dice": dice, "bonus": bonus}


def _parse_cost(s: Any) -> List[Dict[str, Any]]:
    if isinstance(s, list):
        return s
    if isinstance(s, dict):
        return [
            {"key": k, "value": v, "keyIsID": False, "scalable": False, "step": None, "consumeOnSuccess": False}
            for k, v in s.items()
        ]
    txt = str(s or "").strip()
    if not txt:
        return []
    out = []
    for part in [p.strip() for p in txt.split(",") if p.strip()]:
        m = re.match(r"^([A-Za-z_][\w\-]*?)\s*:\s*([+-]?\d+)$", part)
        if not m:
            continue
        out.append(
            {
                "key": m.group(1),
                "value": int(m.group(2)),
                "keyIsID": False,
                "scalable": False,
                "step": None,
                "consumeOnSuccess": False,
            }
        )
    return out


def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w.\- ]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s or "unnamed"


# ---------------- Action helpers ----------------

def build_action(row: Dict[str, Any], prefix: str, fallback_img: str, *, default_name: str = "", default_kind: str = "effect") -> Optional[Dict[str, Any]]:
    """Create an action dict from prefixed columns (e.g., action1.name, attack.name)."""
    name = _get(row, f"{prefix}name") or default_name
    if not name:
        return None

    kind = (_get(row, f"{prefix}type") or default_kind).strip().lower()
    if kind not in {"attack", "effect"}:
        kind = default_kind

    actionType = (_get(row, f"{prefix}actionType") or "action").strip().lower()
    if actionType not in {"action", "reaction", "passive"}:
        actionType = "action"

    dmg_str = _get(row, f"{prefix}damage")
    dmg_type = _get(row, f"{prefix}damage.type", f"{prefix}damagetype")
    dmg_apply = _get(row, f"{prefix}damage.applyTo", f"{prefix}applyto") or "hitPoints"
    dmg = _parse_damage_str(dmg_str) if dmg_str else None
    types: List[str] = []
    if isinstance(dmg_type, list):
        types = [str(x) for x in dmg_type]
    elif isinstance(dmg_type, str) and dmg_type.strip():
        types = [t.strip() for t in dmg_type.split(",") if t.strip()]

    save_trait = _get(row, f"{prefix}save.trait")
    save_diff = _get(row, f"{prefix}save.difficulty")
    save_mod = (_get(row, f"{prefix}save.damageMod") or "none") if (save_trait or save_diff) else "none"

    useDefault = _get(row, f"{prefix}roll.useDefault")
    roll = {
        "type": _get(row, f"{prefix}roll.type"),
        "trait": _get(row, f"{prefix}roll.trait"),
        "difficulty": _get(row, f"{prefix}roll.difficulty"),
        "bonus": _get(row, f"{prefix}roll.bonus"),
        "advState": _get(row, f"{prefix}roll.advState") or "neutral",
        "diceRolling": {"multiplier": "prof", "flatMultiplier": 1, "dice": "d6", "compare": None, "treshold": None},
        "useDefault": bool(useDefault) if isinstance(useDefault, bool) else False,
    }

    action = {
        "type": kind,
        "systemPath": "actions",
        "description": _get(row, f"{prefix}description") or "",
        "chatDisplay": True,
        "actionType": actionType,
        "cost": _parse_cost(_get(row, f"{prefix}cost")),
        "uses": {
            "value": _get(row, f"{prefix}uses.value"),
            "max": _get(row, f"{prefix}uses.max") or "",
            "recovery": _get(row, f"{prefix}uses.recovery"),
            "consumeOnSuccess": bool(_get(row, f"{prefix}uses.consumeOnSuccess"))
            if isinstance(_get(row, f"{prefix}uses.consumeOnSuccess"), bool)
            else False,
        },
        "effects": [],
        "target": {
            "type": _get(row, f"{prefix}target.type") or "any",
            "amount": _get(row, f"{prefix}target.amount"),
        },
        "name": str(name),
        "img": _get(row, f"{prefix}img") or fallback_img or "icons/skills/melee/blood-slash-foam-red.webp",
        "range": _get(row, f"{prefix}range") or "",
    }

    if kind == "attack":
        parts = []
        if dmg:
            parts.append(
                {
                    "value": {
                        "custom": {"enabled": False, "formula": ""},
                        "multiplier": "prof",
                        "dice": dmg["dice"],
                        "bonus": dmg["bonus"],
                        "flatMultiplier": 1,
                    },
                    "applyTo": dmg_apply,
                    "type": types or ["physical"],
                    "base": False,
                    "resultBased": False,
                    "valueAlt": {
                        "multiplier": "prof",
                        "flatMultiplier": 1,
                        "dice": "d6",
                        "bonus": None,
                        "custom": {"enabled": False, "formula": ""},
                    },
                }
            )
        action["damage"] = {"parts": parts, "includeBase": False}
        action["roll"] = roll
        if save_trait or save_diff:
            sd = None
            try:
                if isinstance(save_diff, (int, float)):
                    sd = int(save_diff)
                elif isinstance(save_diff, str) and save_diff.isdigit():
                    sd = int(save_diff)
            except Exception:
                sd = None
            action["save"] = {"trait": save_trait or None, "difficulty": sd, "damageMod": save_mod}
    return action


# ---------------- Row -> Actor ----------------

def _parse_int(val: Any, default: int) -> int:
    try:
        if val is None or val == "":
            return default
        return int(val)
    except Exception:
        return default


def build_actor_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    name = _get(row, "name") or ""
    img = _get(row, "img") or ""

    hp_val = _parse_int(_get(row, "hp", "hitPoints", "hpValue", "hpCurrent"), 0)
    hp_max = _parse_int(_get(row, "hpmax", "hitpointsmax", "hp", "hitPoints"), hp_val)
    stress_val = _parse_int(_get(row, "stress", "stressValue"), 0)
    stress_max = _parse_int(_get(row, "stressmax", "stressMax", "stress"), stress_val)

    actor: Dict[str, Any] = {
        "name": name,
        "type": "adversary",
        "img": img,
        "system": {
            "description": _get(row, "description") or "",
            "tier": _parse_int(_get(row, "tier"), 1),
            "type": _get(row, "adversaryType", "system.type") or "standard",
            "motivesAndTactics": _get(row, "motivesAndTactics") or "",
            "notes": _get(row, "notes") or "",
            "difficulty": _parse_int(_get(row, "difficulty"), 1),
            "hordeHp": _parse_int(_get(row, "hordeHp"), 1),
            "damageThresholds": {
                "major": _parse_int(_get(row, "damageThreshold.major", "majorThreshold"), 0),
                "severe": _parse_int(_get(row, "damageThreshold.severe", "severeThreshold"), 0),
            },
            "resources": {
                "hitPoints": {"value": hp_val, "max": hp_max, "temp": 0, "min": 0},
                "stress": {"value": stress_val, "max": stress_max, "temp": 0, "min": 0},
            },
            "attack": None,  # populated below
            "actions": {},
            "experiences": {},
            "bonuses": {
                "roll": {
                    "attack": {"bonus": _parse_int(_get(row, "bonus.attackRoll", "attackBonus"), 0)},
                    "action": {"bonus": _parse_int(_get(row, "bonus.actionRoll", "actionBonus"), 0)},
                    "reaction": {"bonus": _parse_int(_get(row, "bonus.reactionRoll", "reactionBonus"), 0)},
                },
                "damage": {
                    "physical": {"bonus": _parse_int(_get(row, "bonus.physicalDamage", "physicalBonus"), 0)},
                    "magical": {"bonus": _parse_int(_get(row, "bonus.magicalDamage", "magicalBonus"), 0)},
                },
            },
        },
        "items": [],
        "effects": [],
    }

    # Attack block (system.attack expects systemPath "attack")
    attack_action = build_action(row, "attack.", img, default_name="Attack", default_kind="attack")
    if attack_action:
        attack_action["systemPath"] = "attack"
        attack_action.setdefault("chatDisplay", False)
        actor["system"]["attack"] = attack_action
    else:
        actor["system"]["attack"] = {
            "name": "Attack",
            "img": img or "icons/skills/melee/blood-slash-foam-red.webp",
            "systemPath": "attack",
            "type": "attack",
            "range": "melee",
            "target": {"type": "any", "amount": 1},
            "roll": {"type": "attack"},
            "damage": {"parts": [{"type": ["physical"], "value": {"multiplier": "flat"}}]},
            "chatDisplay": False,
        }

    # Additional actions (action1.*, action2.*, ...)
    action_indices = set()
    for key in row.keys():
        m = re.match(r"action(\d+)\.name", _norm(key))
        if m:
            action_indices.add(int(m.group(1)))
    for idx in sorted(action_indices):
        prefix = f"action{idx}."
        act = build_action(row, prefix, img, default_name="", default_kind="effect")
        if act:
            actor["system"]["actions"][act["name"]] = act

    # Experiences (experience1.*, experience2.*, ...)
    exp_indices = set()
    for key in row.keys():
        m = re.match(r"experience(\d+)\.name", _norm(key))
        if m:
            exp_indices.add(int(m.group(1)))
    for idx in sorted(exp_indices):
        name_key = _get(row, f"experience{idx}.name")
        if not name_key:
            continue
        actor["system"]["experiences"][str(name_key)] = {
            "name": name_key,
            "value": _parse_int(_get(row, f"experience{idx}.value"), 1),
            "description": _get(row, f"experience{idx}.description") or "",
        }

    return actor


# ---------------- CLI ----------------

def main():
    ap = argparse.ArgumentParser(description="Build Daggerheart Adversary Actors from CSV/JSON descriptors")
    ap.add_argument("descriptor", help="CSV or JSON (array/object)")
    ap.add_argument("-o", "--out", required=True, help="Output directory")
    args = ap.parse_args()

    in_path = Path(args.descriptor)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_records(in_path)

    written = 0
    for i, row in enumerate(rows, start=1):
        actor = build_actor_from_row(row)
        fname_base = actor.get("name") or f"row-{i}"

        adv_type = _safe(actor.get("system", {}).get("type"), "standard")
        tier = _safe(actor.get("system", {}).get("tier"), "1")
        out_dir_p = out_dir / adv_type / f"tier-{tier}"
        out_dir_p.mkdir(parents=True, exist_ok=True)

        fname = _sanitize_filename(str(fname_base)) + ".json"
        out_path = out_dir_p / fname
        if out_path.exists():
            n = 2
            while (out_dir_p / f"{_sanitize_filename(str(fname_base))}#{n}.json").exists():
                n += 1
            out_path = out_dir_p / f"{_sanitize_filename(str(fname_base))}#{n}.json"

        out_path.write_text(json.dumps(actor, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1

    print(f"Wrote {written} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
