#!/usr/bin/env python3
"""
Generate Foundry/Daggerheart loadable Actor JSON files for adversaries from a flat CSV/JSON descriptor.

The script focuses on producing lean, import-ready files (no _stats, flags, etc.) similar
in spirit to `feature-descriptor-to-loadable.py`.

Supported input formats
- CSV (recommended)
- JSON array/object

Unknown columns are ignored. Values are coerced to numbers/bools/JSON when possible.
"""

from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

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
        return  False
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


def _parse_damage_str(s: Any) -> Tuple[int, str, int]:
    """
    Parse strings like '1d6+1', '2d8-3', 'd10', etc.
    Returns (num_dice, die, bonus).
    """
    text = str(s or "").strip()
    m = re.match(r"^(\d*)d(\d+)(?:\s*([+-])\s*(\d+))?$", text, re.IGNORECASE)
    if not m:
        return (1, "d6", 0)

    diceNumber = int(m.group(1)) if m.group(1) else 1
    die = f"d{m.group(2)}"
    bonus = 0
    if m.group(3) and m.group(4):
        sign = -1 if m.group(3) == "-" else 1
        bonus = sign * int(m.group(4))

    return (diceNumber, die, bonus)


def _parse_cost(s: Any) -> List[Dict[str, Any]]:
    if isinstance(s, list):
        return s
    if isinstance(s, dict):
        return [
            {"key": k, "value": v, "keyIsID":  False, "scalable":  False, "step": None, "consumeOnSuccess":  False}
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
                "keyIsID":  False,
                "scalable":  False,
                "step": None,
                "consumeOnSuccess":  False,
            }
        )
    return out


def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w.\- ]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s or "unnamed"


# ---------------- Row -> Actor ----------------

def _parse_int(val: Any, default: int) -> int:
    try:
        if val is None or val == "":
            return default
        return int(val)
    except Exception:
        return default


def build_actor_from_row(row: Dict[str, Any]) -> Dict[str, Any]:

    # 	attack attack-name	attack-description	attack-damage	attack-range	attack-img	experience-name	experience-bonus

    name = _get(row, "name") or ""
    img = _get(row, "img") or ""
    systemType = _get(row, "systemType") or "standard"
    notes = _get(row, "notes") or ""
    description = _get(row, "description") or ""
    motivesAndTactics = _get(row, "motivesAndTactics") or ""
    attackName = _get(row, "attackName") or ""
    attackDamage = _get(row, "attackDamage") or "d6"
    (attackDamageDieNumber, attackDamageDie, attackDamageBonus) = _parse_damage_str(attackDamage)
    attackRange = _get(row, "attackRange") or "melee"
    attackImg = _get(row, "attackImg") or ""
    experienceName = _get(row, "experienceName") or ""
    attackDescription = _get(row, "attackDescription") or ""

    hitPoints = _parse_int(_get(row, "hp", "hitPoints"), 1)
    stress = _parse_int(_get(row, "stress"), 1)
    tier = _parse_int(_get(row, "tier"), 1)
    difficulty = _parse_int(_get(row, "difficulty"), 8)
    majorThreshold = _parse_int(_get(row, "majorThreshold"), 2)
    severeThreshold = _parse_int(_get(row, "severeThreshold"), 4)
    attackBonus = _parse_int(_get(row, "attackBonus"), 0)
    experienceBonus = _parse_int(_get(row, "experienceBonus"), 2)
    experiences = {}
    if experienceName:
        experiences[experienceName] = {
            "name": experienceName,
            "value": experienceBonus,
            "description": ""
        }

    actor: Dict[str, Any] = {
      "name": name,
      "type": "adversary",
      "img": f"modules/cybermancy/assets/icons/adversaries/{img}.webp",
      "system": {
        "description": description,
        "resistance": {
          "physical": {
            "resistance":  False,
            "immunity":  False,
            "reduction": 0
          },
          "magical": {
            "resistance":  False,
            "immunity":  False,
            "reduction": 0
          }
        },
        "tier": tier,
        "type": systemType,
        "notes": notes,
        "difficulty": difficulty,
        "hordeHp": 1,
        "damageThresholds": {
          "major": majorThreshold,
          "severe": severeThreshold,
        },
        "resources": {
          "hitPoints": {
            "value": 0,
            "max": hitPoints,
            "isReversed": True
          },
          "stress": {
            "value": 0,
            "max": stress,
            "isReversed": True
          }
        },
        "attack": {
          "name": attackName,
          "img": f"modules/cybermancy/assets/icons/attacks/{attackImg}.webp",
          "systemPath": "attack",
          "chatDisplay":  False,
          "type": "attack",
          "range": attackRange,
          "target": {
            "type": "any",
            "amount": 1
          },
          "roll": {
            "type": "attack",
            "trait": None,
            "difficulty": None,
            "bonus": attackBonus,
            "advState": "neutral",
            "diceRolling": {
              "multiplier": "prof",
              "flatMultiplier": 1,
              "dice": attackDamageDie,
              "compare":  None,
              "treshold":  None
            },
            "useDefault":  False
          },
          "damage": {
            "parts": [
              {
                "value": {
                  "custom": {
                    "enabled":  False,
                    "formula": ""
                  },
                  "flatMultiplier": attackDamageDieNumber,
                  "dice": attackDamageDie,
                  "bonus": attackDamageBonus,
                  "multiplier": "flat"
                },
                "applyTo": "hitPoints",
                "type": [
                  "physical"
                ],
                "resultBased":  False,
                "valueAlt": {
                  "multiplier": "prof",
                  "flatMultiplier": attackDamageDieNumber,
                  "dice": attackDamageDie,
                  "bonus":  attackDamageBonus,
                  "custom": {
                    "enabled":  False,
                    "formula": ""
                  }
                },
                "base":  False
              }
            ],
            "includeBase":  False
          },
          "description": attackDescription,
          "actionType": "action",
          "cost": [],
          "uses": {
            "value":  None,
            "max":  None,
            "recovery":  None,
            "consumeOnSuccess":  False
          },
          "effects": [],
          "save": {
            "trait":  None,
            "difficulty":  None,
            "damageMod": "none"
          }
        },
        "experiences": experiences,
        "bonuses": {
          "roll": {
            "attack": {
              "bonus": 0,
              "dice": []
            },
            "action": {
              "bonus": 0,
              "dice": []
            },
            "reaction": {
              "bonus": 0,
              "dice": []
            }
          },
          "damage": {
            "physical": {
              "bonus": 0,
              "dice": []
            },
            "magical": {
              "bonus": 0,
              "dice": []
            }
          }
        },
        "motivesAndTactics": motivesAndTactics,
      },
      "prototypeToken": {
        "name": name,
        "displayName": 30,
        "actorLink":  False,
        "width": 1,
        "height": 1,
        "texture": {
          "src": f"modules/cybermancy/assets/icons/adversaries/{img}.webp",
          "anchorX": 0.5,
          "anchorY": 0.5,
          "offsetX": 0,
          "offsetY": 0,
          "fit": "contain",
          "scaleX": 1,
          "scaleY": 1,
          "rotation": 0,
          "tint": "#ffffff",
          "alphaThreshold": 0.75
        },
        "lockRotation":  False,
        "rotation": 0,
        "alpha": 1,
        "disposition": -1,
        "displayBars": 20,
        "bar1": {
          "attribute": "resources.hitPoints"
        },
        "bar2": {
          "attribute": "resources.stress"
        },
        "light": {
          "negative":  False,
          "priority": 0,
          "alpha": 0.5,
          "angle": 360,
          "bright": 0,
          "color":  None,
          "coloration": 1,
          "dim": 0,
          "attenuation": 0.5,
          "luminosity": 0.5,
          "saturation": 0,
          "contrast": 0,
          "shadows": 0,
          "animation": {
            "type":  None,
            "speed": 5,
            "intensity": 5,
            "reverse":  False
          },
          "darkness": {
            "min": 0,
            "max": 1
          }
        },
        "sight": {
          "enabled":  False,
          "range": 0,
          "angle": 360,
          "visionMode": "basic",
          "color":  None,
          "attenuation": 0.1,
          "brightness": 0,
          "saturation": 0,
          "contrast": 0
        },
        "detectionModes": [],
        "occludable": {
          "radius": 0
        },
        "ring": {
          "enabled":  False,
          "colors": {
            "ring":  None,
            "background":  None
          },
          "effects": 1,
          "subject": {
            "scale": 1,
            "texture":  None
          }
        },
        "turnMarker": {
          "mode": 1,
          "animation":  None,
          "src":  None,
          "disposition":  False
        },
        "movementAction":  None,
        "flags": {},
        "randomImg":  False,
        "appendNumber":  False,
        "prependAdjective":  False
      },
      "effects": [],
      "flags": {}
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

        out_path.write_text(json.dumps(actor, indent=2, ensure_ascii= False), encoding="utf-8")
        written += 1

    print(f"Wrote {written} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
