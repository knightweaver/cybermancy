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
    return (str(s) or "").replace("<", "&lt;").replace(">", "&gt;")

def titleize(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s

def _fmt_number(n) -> str:
    """Format numeric bonus cleanly (8.0 -> 8)."""
    if n is None:
        return ""
    if isinstance(n, (int,)):
        return str(n)
    if isinstance(n, float):
        return str(int(n)) if n.is_integer() else str(n)
    return str(n)

def prettify_camel(s: str) -> str:
    """
    Convert camelCase or PascalCase into spaced, title-cased words.
    Examples:
        "oneHanded"  -> "One Handed"
        "strength"   -> "Strength"
        "UltraHeavyArmor" -> "Ultra Heavy Armor"
    """
    if not s:
        return ""
    # Insert a space before any capital letter preceded by a lowercase letter or number
    s = re.sub(r'(?<=[a-z0-9])([A-Z])', r' \1', s)
    # Handle acronyms or all-caps chunks more gracefully
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)
    return s.strip().title()

def summarize_attack(attack: Dict[str, Any]) -> Dict[str, str]:
    """
    Turn a Foundry/Daggerheart attack node into a concise summary.
    Returns dict with keys: damage, damageType, range.
    """
    if not isinstance(attack, dict):
        return {"damage": "—", "damageType": "—", "range": "—"}

    rng = prettify_camel(attack.get("range")) or "—"

    roll = attack.get("roll")
    trait = roll.get("trait")

    parts = (attack.get("damage") or {}).get("parts") or []
    if not parts or not isinstance(parts, list):
        return {"damage": "—", "damageType": "—", "range": rng, "trait": trait}

    p0 = parts[0] or {}
    val = p0.get("value") or {}
    dice = val.get("dice")  # e.g., "d10"
    bonus = val.get("bonus")  # e.g., 8 (may be None)

    # Build "d10+8", "d6", "+2", or "—" if empty
    damage_bits = []
    if dice:
        damage_bits.append(str(dice))
    if bonus is not None and bonus != 0:
        # add + or - appropriately
        sign = "+" if float(bonus) >= 0 else "-"
        damage_bits.append(f"{sign}{_fmt_number(abs(float(bonus)))}")

    damage = "".join(damage_bits) if damage_bits else "—"

    type_list = p0.get("type") or []
    damage_type = type_list[0] if isinstance(type_list, list) and type_list else "—"

    return {"damage": damage, "damageType": str(damage_type), "range": rng, "trait": trait}

from typing import Any, Dict, List, Optional

# ---------- tiny utils ----------
def _coalesce(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return None

def _join_nonempty(parts: List[str], sep: str = " "):
    return sep.join([p for p in parts if p and str(p).strip()])

def _fmt_number(n) -> str:
    if n is None:
        return ""
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        return str(int(n)) if n.is_integer() else str(n)
    return str(n)

def _fmt_target(target: Optional[Dict[str, Any]]) -> str:
    if not isinstance(target, dict):
        return "—"
    ttype = target.get("type") or "—"
    amt = target.get("amount")
    return f"{ttype}{f' ({amt})' if amt not in (None, '') else ''}"

def _fmt_roll(roll: Optional[Dict[str, Any]]) -> str:
    if not isinstance(roll, dict):
        return "—"
    trait = roll.get("trait") or "—"
    rtype  = roll.get("type") or "—"
    adv = roll.get("advState") or "neutral"
    dr = roll.get("diceRolling") or {}
    dice  = dr.get("dice") or "—"
    mult  = dr.get("multiplier") or None   # e.g., "prof"
    fmult = dr.get("flatMultiplier") or None
    mult_str = ""
    if mult and fmult not in (None, 1):
        mult_str = f"{mult}×{_fmt_number(fmult)}"
    elif mult:
        mult_str = f"{mult}"

    dice_part = _join_nonempty([dice, mult_str], sep="·") if (dice != "—" or mult_str) else "—"
    return f"{trait} {rtype}; dice {dice_part}; adv {adv}"

def _fmt_damage_block(damage: Optional[Dict[str, Any]]) -> str:
    """
    Summarize a Daggerheart-like damage node with 'parts' as in your attack.
    Returns e.g. 'd10+8 physical' or '—'.
    """
    if not isinstance(damage, dict):
        return "—"
    parts = damage.get("parts") or []
    if not parts:
        return "—"

    out = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        val = p.get("value") or {}
        dice = val.get("dice")
        bonus = val.get("bonus")
        seg = []
        if dice:
            seg.append(str(dice))
        if bonus not in (None, 0, "0"):
            sign = "+" if float(bonus) >= 0 else "-"
            seg.append(f"{sign}{_fmt_number(abs(float(bonus)))}")
        seg_txt = "".join(seg) if seg else "—"

        t_list = p.get("type") or []
        dtype = t_list[0] if isinstance(t_list, list) and t_list else None
        out.append(_join_nonempty([seg_txt, dtype or ""], sep=" "))
    return ", ".join(out) if out else "—"

def _fmt_uses(uses: Optional[Dict[str, Any]]) -> str:
    if not isinstance(uses, dict):
        return "—"
    val = uses.get("value")
    mx = uses.get("max")
    rec = uses.get("recovery")
    cos = "consumeOnSuccess" in uses and bool(uses.get("consumeOnSuccess"))
    pieces = []
    if mx is not None:
        pieces.append(f"{_fmt_number(val)}/{_fmt_number(mx)}")
    elif val is not None:
        pieces.append(_fmt_number(val))
    if rec:
        pieces.append(f"recovers: {rec}")
    if cos:
        pieces.append("consume on success")
    return _join_nonempty(pieces, sep="; ") or "—"

def _fmt_cost(cost: Any) -> str:
    """
    Cost is often a list of objects; try to render something readable.
    Fallbacks to '—' if nothing sensible is present.
    """
    if isinstance(cost, list) and cost:
        parts = []
        for c in cost:
            if not isinstance(c, dict):
                continue
            ctype = c.get("type") or c.get("name") or "cost"
            amt = c.get("amount") or c.get("value")
            parts.append(f"{ctype}{f' {_fmt_number(amt)}' if amt not in (None, '') else ''}")
        return ", ".join([p for p in parts if p]) or "—"
    if isinstance(cost, dict) and cost:
        return ", ".join([f"{k}:{v}" for k, v in cost.items()])
    return "—"

# ---------- ACTIONS ----------
def summarize_actions(actions_node: Any) -> List[Dict[str, str]]:
    """
    Turn system.actions into a list of normalized dicts.
    Accepts either:
      - array of action objects, or
      - object map: { "Action Name": { ...action... }, ... }
    Returns list with keys:
      name, type, range, target, roll, damage, cost, uses, save, description, summary
    """
    results: List[Dict[str, str]] = []
    if not actions_node:
        return results

    # Normalize shape
    if isinstance(actions_node, dict):
        iterable = actions_node.values()
    elif isinstance(actions_node, list):
        iterable = actions_node
    else:
        # Unknown format, fail soft
        return results

    for a in iterable:
        if not isinstance(a, dict):
            continue

        name = a.get("name") or "Unnamed Action"
        a_type = _coalesce(a.get("actionType"), a.get("type"), "action")

        rng = prettify_camel(a.get("range")) or "—"
        target = _fmt_target(a.get("target"))
        roll = _fmt_roll(a.get("roll"))
        damage = _fmt_damage_block(a.get("damage"))
        cost = _fmt_cost(a.get("cost"))
        uses = _fmt_uses(a.get("uses"))

        save = "—"
        if isinstance(a.get("save"), dict):
            sv = a["save"]
            sv_trait = sv.get("trait")
            sv_diff = sv.get("difficulty")
            sv_mod  = sv.get("damageMod") or "none"
            save = _join_nonempty(
                [
                    sv_trait or "—",
                    f"DC {sv_diff}" if sv_diff not in (None, "") else None,
                    f"mod {sv_mod}",
                ],
                sep="; ",
            )

        desc = strip_html(a.get("description") or "").strip().split(":")
        desc = desc[len(desc) - 1] if len(desc) > 1 else desc[0]

        summary = _join_nonempty(
            [
                f"{name} [{a_type}]",
                f"range {rng}",
                f"target {target}",
                f"roll {roll}",
                f"damage {damage}" if damage != "—" else None,
                f"save {save}" if save != "—" else None,
                f"cost {cost}" if cost != "—" else None,
                f"uses {uses}" if uses != "—" else None,
            ],
            sep=" — ",
        )

        results.append(
            {
                "name": name,
                "type": a_type,
                "range": rng,
                "target": target,
                "roll": roll,
                "damage": damage,
                "cost": cost,
                "uses": uses,
                "save": save,
                "description": desc,
                "summary": summary,
            }
        )

    return results

def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)

# ---------- EFFECTS ----------
def _fmt_effect_duration(dur: Any) -> str:
    """
    Foundry ActiveEffect-like durations vary; try several common patterns.
    """
    if not isinstance(dur, dict):
        return "—"
    # Foundry style fields
    seconds = dur.get("seconds")
    rounds  = dur.get("rounds")
    turns   = dur.get("turns")
    start_round = dur.get("startRound")
    start_turn  = dur.get("startTurn")
    sustained   = dur.get("sustained")  # custom, if present

    parts = []
    if seconds:
        parts.append(f"{_fmt_number(seconds)}s")
    if rounds:
        parts.append(f"{_fmt_number(rounds)} rounds")
    if turns:
        parts.append(f"{_fmt_number(turns)} turns")
    if sustained:
        parts.append("sustained")

    # add anchors if available
    anchors = []
    if start_round not in (None, ""):
        anchors.append(f"startR {start_round}")
    if start_turn not in (None, ""):
        anchors.append(f"startT {start_turn}")
    if anchors:
        parts.append(f"({', '.join(anchors)})")

    return _join_nonempty(parts, sep=", ") or "—"

def _fmt_effect_changes(changes: Any) -> str:
    """
    Compact renderer for ActiveEffect-style changes: {key, mode, value}
    """
    if not isinstance(changes, list) or not changes:
        return "—"
    out = []
    for ch in changes:
        if not isinstance(ch, dict):
            continue
        key = ch.get("key") or "—"
        mode = ch.get("mode")
        val = ch.get("value")
        # Show mode if present; many Daggerheart mods only need key/value
        if mode not in (None, ""):
            out.append(f"{key} ({mode}) = {val}")
        else:
            out.append(f"{key} = {val}")
    return "; ".join(out) if out else "—"

def summarize_effects(effects_node: Any) -> List[Dict[str, str]]:
    """
    Turn system.effects (array) into a list of normalized dicts:
    keys: name, changes, duration, transfer, disabled, description, summary
    """
    results: List[Dict[str, str]] = []
    if not isinstance(effects_node, list):
        return results

    for eff in effects_node:
        if not isinstance(eff, dict):
            continue

        name = eff.get("name") or "Unnamed Effect"
        desc = (eff.get("description") or eff.get("flags", {}).get("core", {}).get("statusId") or "").strip()
        if len(desc) > 180:
            desc = desc[:177].rstrip() + "…"

        changes = _fmt_effect_changes(_coalesce(eff.get("changes"),
                                               eff.get("system", {}).get("changes")))
        duration = _fmt_effect_duration(eff.get("duration"))
        transfer = "yes" if bool(eff.get("transfer")) else "no" if eff.get("transfer") is not None else "—"
        disabled = "yes" if bool(eff.get("disabled")) else "no" if eff.get("disabled") is not None else "—"

        summary = _join_nonempty([
            name,
            f"changes: {changes}" if changes != "—" else None,
            f"duration: {duration}" if duration != "—" else None,
            f"transfer: {transfer}" if transfer != "—" else None,
            f"disabled: {disabled}" if disabled != "—" else None
        ], sep=" — ")

        results.append({
            "name": name,
            "changes": changes,
            "duration": duration,
            "transfer": transfer,
            "disabled": disabled,
            "description": desc,
            "summary": summary
        })
    return results

# ---------- tiny extras ----------
def _fmt_tags(tags: Any) -> str:
    if isinstance(tags, (list, tuple)):
        return ", ".join(str(t) for t in tags if t not in (None, "", [])) or "—"
    if isinstance(tags, str) and tags.strip():
        return tags
    return "—"

def _shorten(text: str, n: int = 2000) -> str:
    text = (text or "").strip()
    return (text[: n-3].rstrip() + "…") if len(text) > n else text

def _fmt_requires(req: Any) -> str:
    """Render a variety of 'requires' shapes."""
    if not req:
        return "—"
    if isinstance(req, str):
        return req
    if isinstance(req, dict):
        bits = []
        for k in ("trait", "skill", "feature", "domain", "level", "tier", "burden", "proficiency"):
            v = req.get(k)
            if v not in (None, "", []):
                bits.append(f"{k}: {v}")
        return ", ".join(bits) if bits else "—"
    if isinstance(req, list):
        return "; ".join(_fmt_requires(x) for x in req if x) or "—"
    return str(req)

def _fmt_state(flags: Dict[str, Any]) -> str:
    """Common boolean flags → compact badges."""
    if not isinstance(flags, dict):
        return "—"
    badges = []
    if flags.get("passive") is True:
        badges.append("passive")
    if flags.get("active") is True:
        badges.append("active")
    if flags.get("stacking") is True:
        badges.append("stacking")
    if flags.get("inherent") is True:
        badges.append("inherent")
    if flags.get("unique") is True:
        badges.append("unique")
    return ", ".join(badges) if badges else "—"

# ---------- FEATURE SUMMARIZERS ----------
def _summarize_features_generic(features_node: Any, default_kind: str) -> List[Dict[str, str]]:
    """
    Normalize weapon/armor feature arrays into:
    name, kind, tags, changes, uses, cost, requires, state, description, summary
    """
    out: List[Dict[str, str]] = []
    if not isinstance(features_node, list):
        return out

    for f in features_node:
        if not isinstance(f, dict):
            continue

        name = _coalesce(f.get("name"), f.get("value")) or "Unnamed Feature"
        kind = _coalesce(f.get("type"), f.get("kind"), default_kind)
        desc = _coalesce(f.get("description"), "")
        #uses = _fmt_uses(f.get("uses"))
        #cost = _fmt_cost(f.get("cost"))

        summary_bits = [
            f"{name} [{kind}]",
            f"{desc}"
        ]
        summary = " — ".join([b for b in summary_bits if b])

        out.append({
            "name": prettify_camel(name),
            "kind": str(kind),
            "description": desc,
            "summary": summary or name
        })
    return out

def summarize_weapon_features(weapon_features_node: Any) -> List[Dict[str, str]]:
    """Wrapper specialized for weapon features."""
    return _summarize_features_generic(weapon_features_node, default_kind="weapon-feature")

def summarize_armor_features(armor_features_node: Any) -> List[Dict[str, str]]:
    """Wrapper specialized for armor features."""
    return _summarize_features_generic(armor_features_node, default_kind="armor-feature")

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
    <div class="item-flavor">
    *{description}*
    </div>
    </div>

    <div markdown="1">
    #### Actions
    {actions_flat}

    #### Effects
    {effects_flat}
    </div>

    </div>

    <div class="meta" markdown="1">
    **UUID:** `Compendium.cybermancy.{comp_key}.{slug}`
    </div>
    </div>
    """,

    # Weapon (item) --------------------------------------------------------
    "weapon": """<div class="item" markdown="1">
    
<div class="grid item-grid" markdown="1">
<div markdown="1">
### {name}

<img src="{image_rel}" alt="{name}" class="item-image">

<div class="item-flavor">
{description}
</div>
</div>

<div markdown="1">

#### Stats
<table class="stat-table">
  <thead><tr><th>Attribute</th><th align="right">Value</th></tr></thead>
  <tbody>
    <tr><td>Tier</td><td align="right">{tier}</td></tr>
    <tr><td>Trait</td><td align="right">{trait}</td></tr>
    <tr><td>Range</td><td align="right">{range}</td></tr>
    <tr><td>Burden</td><td align="right">{burden}</td></tr>
    <tr><td>Damage</td><td align="right">{damage}</td></tr>
  </tbody>
</table>

</div>
</div>
#### Actions
{actions_flat}

#### Effects
{effects_flat}

#### Weapon Features
{weapon_features_flat}
{weapon_features_list}


---

<div class="meta" markdown="1">
**UUID:** `Compendium.cybermancy.{comp_key}.{slug}`
</div>
</div>
""",

    # Armor (item) --------------------------------------------------------
    "armor": """<div class="item" markdown="1">
<div class="grid item-grid" markdown="1">

<div markdown="1">
### {name}
<img src="{image_rel}" alt="{name}" class="item-image">

<div class="item-flavor">
*{description}*
</div>
</div>

<div markdown="1">

#### Stats
<table class="stat-table">
  <thead><tr><th>Attribute</th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Tier</td><td align="right">{tier}</td></tr>
    <tr><td>Base Score</td><td align="right">{baseScore}</td></tr>
    <tr><td>Thresholds</td><td align="right">{majorThreshold} / {severeThreshold}</td></tr>
  </tbody>
</table>

</div>
</div>

#### Actions
{actions_flat}

#### Effects
{effects_flat}

#### Armor Features
{armor_features_flat}

---

<div class="meta" markdown="1">
**UUID:** `Compendium.cybermancy.{comp_key}.{slug}`
</div>
</div>
""",

    # Classes (system) --------------------------------------------------------
    "class": """<div class="class" markdown="1">
    <img src="{image_rel}" alt="{name}" class="item-image">

    # {name}

    ## At a Glance
    - **Domains:** {domains_list}
    - **Hit Points:** {hitPoints}
    - **Evasion:** {evasion}

    ## Features
    {features_md}

    ---

    ## Description
    {description}

    <div class="meta" markdown="1">
    **UUID:** `Compendium.cybermancy.system.{slug}`
    </div>
    </div>
    """,

    # Subclasses (system) -----------------------------------------------------
    "subclass": """<div class="subclass" markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image">

# {name}
<div class="item-subtitle">Subclass</div>

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

    # {name}
    - **Type:** {type}
    - **Level:** {level}
    - **Domain:** {domain}
    - **Recall Cost:** {recallCost}

    ## Actions
    {actions_flat}

    ---

    ## Description
    {description}

    <div class="meta" markdown="1">
    **UUID:** `Compendium.cybermancy.system.{slug}`
    </div>
    </div>
    """,

    # Features (system) -------------------------------------------------------
    "feature": """<div class="feature" markdown="1">
    <img src="{image_rel}" alt="{name}" class="item-image">

    # {name}

    ## Actions
    {actions_flat}

    ---

    ## Description
    {description}

    <div class="meta" markdown="1">
    **UUID:** `Compendium.cybermancy.system.{slug}`
    </div>
    </div>
    """,
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
    "type": "type",
    "description": "system.description",
    "tier": "system.tier",
    "actions": "system.actions",
    "effects": "effects",
    "img": "img"
}

CONFIG: Dict[str, Dict[str, Any]] = {
    # ---------------- Items ----------------
    "weapons": {
        "kind": "items",
        "src_subdir": "weapons",
        "csv_fields": ["name","slug","description","tier","trait","range","burden","damage","weapon_feats","actions_flat"],
        "field_map": DEFAULT_ITEM_FIELD_MAP | {
            # example extra fields you might have in cyberware
            "attack": "system.attack",
            "burden": "system.burden",
            "weaponFeatures": "system.weaponFeatures",
            "trait": "system.attack.roll.trait",
            "range": "system.attack.range"
        },
        "template": "weapon",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "weapons",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "armors": {
        "kind": "items",
        "src_subdir": "armors",
        "csv_fields": ["name","slug","description","tier","baseScore","majorThreshold","severeThreshold","armor_features_flat"],
        "field_map": DEFAULT_ITEM_FIELD_MAP | {
            # example extra fields you might have in cyberware
            "baseScore": "system.baseScore",
            "armorFeatures": "system.armorFeatures",
            "baseThresholds": "system.baseThresholds"
        },
        "template": "armor",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "armors",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "ammo": {
        "kind": "items",
        "src_subdir": "ammo",
        "csv_fields": ["name","slug","description","tier","actions"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "ammo",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "consumables": {
        "kind": "items",
        "src_subdir": "consumables",
        "csv_fields": ["name","slug","description","tier","actions"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "consumables",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "cybernetics": {
        "kind": "items",
        "src_subdir": "cybernetics",
        "csv_fields": ["name","slug","description","tier","actions"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "cybernetics",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "drones-devices": {
        "kind": "items",
        "src_subdir": "drones-devices",
        "csv_fields": ["name","slug","description","tier","actions"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "drones-devices",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "mods": {
        "kind": "items",
        "src_subdir": "mods",
        "csv_fields": ["name","slug","description","tier","actions"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "mods",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}"
    },
    "loot": {
        "kind": "items",
        "src_subdir": "loot",
        "csv_fields": ["name","slug","description","tier","actions"],
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
        "csv_fields": ["name","slug","domains","hitPoints","evasion", "features", "subclasses"],
        "field_map": {
            "name": "name",
            "type": "type",
            "domains": "system.domains",
            "hitPoints": "system.hitPoints",
            "evasion": "system.evasion",
            "features": "system.features",
            "subclasses": "system.subclasses",
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
        "csv_fields": ["name","slug","description","spellcastingTrait","features"],
        "field_map": {
            "name": "name",
            "spellcastingTrait": "system.spellcastingTrait",
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
        "csv_fields": ["name","slug","domain","type","description","level","recallCost","actions"],
        "field_map": {
            "name": "name",
            "type": "system.type",
            "level": "system.level",
            "domain": "system.domain",
            "recallCost": "system.recallCost",
            "actions": "system.actions",
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
        "csv_fields": ["name","slug","description","actions"],
        "field_map": {
            "name": "name",
            "actions": "system.actions",
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

    detail_dir = ""

    count = 0
    for p in sorted(src_dir.rglob("*.json")):
        obj = read_json(p)
        name = get_in(obj, field_map.get("name", "name"))
        if not name:
            continue
        slug = slugify(name)

        # Common basics
        img_ref = get_in(obj, field_map.get("img", "img"))
        description = get_in(obj, field_map.get("description", "system.description"))
        type = get_in(obj, field_map.get("type", "type"))
        tier = get_in(obj, field_map.get("tier", "system.tier"))

        actions_node = get_in(obj, field_map.get("actions", "system.actions"), [])
        effects_node = get_in(obj, field_map.get("effects", "system.effects"), [])

        action_summaries = summarize_actions(actions_node)  # List[dict]
        effect_summaries = summarize_effects(effects_node)  # List[dict]

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
            #"image_rel": md_escape(img_ref),
            "image_rel": md_escape(cfg["image_rel"](audience, type_key, slug)),
            "slug": slug,
            "type": md_escape(type or "Common"),
            "tier": md_escape(str(tier) or "—"),
            "description": md_escape(description or "(No description yet.)"),
            "comp_key": cfg.get("comp_key", type_key),
            "type_title": titleize(type_key[:-1]) if type_key.endswith("s") else titleize(type_key),
            "actions": action_summaries,
            "effects": effect_summaries,
            "actions_flat": "\n\n".join(f"- <div markdown='1'>**{a['name']}**<br>*{a['description']}*</div>" for a in action_summaries) or "—",
            "effects_flat": "\n\n".join(f"- <div markdown='1'>**{e['name']}**<br>*{e['description']}*</div>" for e in effect_summaries) or "—"
        }

        detail_dir = docs_root / out_dir_rel / slug
        ensure_dir(detail_dir)

        # Item-specific enrichments
        if kind == "items":
            # Prefer computed values from the attack node when present.
            attack_node = get_in(obj, field_map.get("attack", "system.attack"), {})
            atk_summary = summarize_attack(attack_node) if attack_node else {"damage": "—", "damageType": "—",
                                                                             "range": "—", "trait": "—"}

            damage = atk_summary["damage"]
            rng = atk_summary["range"]
            damage_type = prettify_camel(atk_summary["damageType"])
            trait = prettify_camel(atk_summary["trait"]) # available for future use

            weapon_features_node = get_in(obj, field_map.get("weaponFeatures", "system.weaponFeatures"), [])
            armor_features_node = get_in(obj, field_map.get("armorFeatures", "system.armorFeatures"), [])

            weapon_feats = summarize_weapon_features(weapon_features_node)
            armor_feats = summarize_armor_features(armor_features_node)
            burden = prettify_camel(get_in(obj, field_map.get("burden", "")))
            baseScore = get_in(obj, field_map.get("baseScore", ""))
            baseThresholds = get_in(obj, field_map.get("baseThresholds", ""))

            # If this type’s CSV schema expects damage/range, put the computed values in the row
            if "damage" in cfg["csv_fields"]:
                rows[-1]["damage"] = damage
            if "range" in cfg["csv_fields"]:
                rows[-1]["range"] = rng
            if "trait" in cfg["csv_fields"]:
                rows[-1]["trait"] = trait
            if "majorThreshold" in cfg["csv_fields"]:
                rows[-1]["majorThreshold"] = baseThresholds.get("major", "—") if baseThresholds else "—"
            if "severeThreshold" in cfg["csv_fields"]:
                rows[-1]["severeThreshold"] = baseThresholds.get("severe", "—") if baseThresholds else "—"

            ctx.update({
                "damage": md_escape(damage or "—"),
                "range": md_escape(rng or "—"),
                "trait": md_escape(trait or "—"),
                "burden": md_escape(burden or "—"),
                "baseScore": md_escape(baseScore or "—"),
                "baseThresholds": md_escape(baseThresholds or "—"),
                "majorThreshold": md_escape(baseThresholds.get("major", "—") if baseThresholds else "—"),
                "severeThreshold": md_escape(baseThresholds.get("severe", "—") if baseThresholds else "—"),
                "weapon_features_list": weapon_feats,
                "armor_features_list": armor_feats,
                "weapon_features_flat": "\n".join(f"- <div markdown='1'>**{x['name']}**<br>*{x['description']}*</div>" for x in weapon_feats) or "—",
                "armor_features_flat": "\n".join(f"- <div markdown='1'>**{x['name']}**<br>*{x['description']}*</div>" for x in armor_feats) or "—"
            })

        # System types enrichments
        else:
            # All system types write to docs/<audience>/<type>/<slug>/index.md
            image_rel = cfg["image_rel"](audience, type_key, slug)
            detail_dir = docs_root / out_dir_rel / slug
            ensure_dir(detail_dir)
            ctx["image_rel"] = image_rel

            if type_key == "classes":
                ctx["domains_list"] = ", ".join(get_in(obj, field_map["domains"], []) or [])
                ctx["hitPoints"] = md_escape(get_in(obj, field_map["hitPoints"], ""))
                ctx["evasion"] = md_escape(get_in(obj, field_map["evasion"], ""))
                features = get_in(obj, field_map["features"], [])
                ctx["features_md"] = features_to_md(features)
            elif type_key == "subclasses":
                features = get_in(obj, field_map["features"], [])
                ctx["features_md"] = features_to_md(features)
            elif type_key == "domains":
                ctx["level"] = md_escape(get_in(obj, field_map["level"], ""))
                ctx["domain"] = list_to_md_bullets(get_in(obj, field_map["domain"], []))
                ctx["recallCost"]  = features_to_md(get_in(obj, field_map["recallCost"], []))
            # elif type_key == "features":

        # Render and write
        page_md = render_template(template_key, ctx)
        (detail_dir / "index.md").write_text(page_md, encoding="utf-8")
        count += 1

    # CSV index
    if rows:
        # --- Sort rows by Tier (if present) then by Name ---
        tier_present = "tier" in CONFIG[type_key]["csv_fields"]
        if tier_present:
            def tier_sort_value(v):
                t = v.get("tier")
                try:
                    # Handle numeric tiers if they are strings
                    return int(t)
                except (TypeError, ValueError):
                    # None or non-numeric values sort last
                    return 9999
            rows.sort(key=lambda r: (tier_sort_value(r), str(r.get("name", "")).lower()))
        else:
            rows.sort(key=lambda r: str(r.get("name", "")).lower())
        # ---------------------------------------------------

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
