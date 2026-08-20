#!/usr/bin/env python3
"""
Generate CSV indexes and Markdown detail pages for Cybermancy.

Supported publication families:
- Player-facing items: weapons, armors, ammo, consumables, cybernetics,
  drones-devices, mods, loot.
- Player-facing system content: classes, subclasses, domains, features.
- GM-facing system content: adversary feature library.
- GM-facing Actor content: adversaries and environments.

Default source layout:
- items:        <repo-root>/src/packs/items/<type>/**/*.json
- system:       <repo-root>/src/packs/system/<type>/**/*.json
- adversaries:  <repo-root>/src/packs/adversaries/**/*.json
- environments: <repo-root>/src/packs/environments/**/*.json

Outputs:
- CSV indexes: <repo-root>/docs/data/<type>.csv
- Detail pages: paths are controlled per family by CONFIG.

Usage:
  python generate-docs.py --audience player-facing
  python generate-docs.py --audience gm-facing
  python generate-docs.py --audience gm-facing --types adversaries,environments
  python generate-docs.py --repo-root .
"""

from pathlib import Path
import argparse
import csv
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------- Utilities --------------------------------------

def get_in(obj: Dict[str, Any], dotted: str, default: Any = "") -> Any:
    cur: Any = obj
    if not dotted:
        return default
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


def md_escape(s: Any) -> str:
    return (str(s) if s is not None else "").replace("<", "&lt;").replace(">", "&gt;")


def titleize(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s


def _fmt_number(n: Any) -> str:
    """Format numeric bonus cleanly (8.0 -> 8)."""
    if n is None:
        return ""
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        return str(int(n)) if n.is_integer() else str(n)
    return str(n)


def _signed_number(n: Any, zero_as: str = "+0") -> str:
    if n in (None, ""):
        return "—"
    try:
        f = float(n)
        if f == 0:
            return zero_as
        return f"{'+' if f > 0 else '-'}{_fmt_number(abs(f))}"
    except (TypeError, ValueError):
        s = str(n)
        return s if s.startswith(("+", "-")) else f"+{s}"


def prettify_camel(s: Any) -> str:
    """Convert camelCase or PascalCase into spaced title case."""
    if s is None:
        return ""
    s = str(s)
    if not s:
        return ""
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return s.strip().title()


def strip_html(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def is_foundry_folder(obj: Dict[str, Any]) -> bool:
    """Return True for Foundry folder records rather than document records."""
    key = str(obj.get("_key") or "")
    return key.startswith("!folders!") or "!folders!" in key


def foundry_document_id(obj: Dict[str, Any]) -> str:
    """Resolve the document/folder id from _id or the trailing segment of _key."""
    direct = obj.get("_id")
    if direct:
        return str(direct)
    key = str(obj.get("_key") or "")
    return key.rsplit("!", 1)[-1] if "!" in key else ""


def source_dir_for(root: Path, cfg: Dict[str, Any]) -> Path:
    """Resolve CONFIG source path while preserving the legacy kind/src_subdir convention."""
    explicit = cfg.get("src_path")
    if explicit:
        return root / explicit
    return root / "src" / "packs" / cfg["kind"] / cfg["src_subdir"]


def _coalesce(*vals: Any) -> Any:
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return None


def _join_nonempty(parts: List[str], sep: str = " ") -> str:
    return sep.join([p for p in parts if p and str(p).strip()])


# ---------------------------- Actions / effects ------------------------------

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
    rtype = roll.get("type") or "—"
    adv = roll.get("advState") or "neutral"
    dr = roll.get("diceRolling") or {}
    dice = dr.get("dice") or "—"
    mult = dr.get("multiplier") or None
    fmult = dr.get("flatMultiplier") or None
    mult_str = ""
    if mult and fmult not in (None, 1):
        mult_str = f"{mult}×{_fmt_number(fmult)}"
    elif mult:
        mult_str = str(mult)
    dice_part = _join_nonempty([str(dice), mult_str], sep="·") if (dice != "—" or mult_str) else "—"
    return f"{trait} {rtype}; dice {dice_part}; adv {adv}"


def _fmt_damage_block(damage: Optional[Dict[str, Any]]) -> str:
    if not isinstance(damage, dict):
        return "—"
    parts = damage.get("parts") or []
    if not parts:
        return "—"

    out: List[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        val = p.get("value") or {}
        dice = val.get("dice")
        bonus = val.get("bonus")
        seg: List[str] = []
        if dice:
            seg.append(str(dice))
        if bonus not in (None, 0, "0"):
            try:
                b = float(bonus)
                sign = "+" if b >= 0 else "-"
                seg.append(f"{sign}{_fmt_number(abs(b))}")
            except (TypeError, ValueError):
                seg.append(str(bonus))
        seg_txt = "".join(seg) if seg else "—"
        t_list = p.get("type") or []
        dtype = t_list[0] if isinstance(t_list, list) and t_list else None
        out.append(_join_nonempty([seg_txt, str(dtype or "")], sep=" "))
    return ", ".join(out) if out else "—"


def _fmt_uses(uses: Optional[Dict[str, Any]]) -> str:
    if not isinstance(uses, dict):
        return "—"
    val = uses.get("value")
    mx = uses.get("max")
    rec = uses.get("recovery")
    cos = "consumeOnSuccess" in uses and bool(uses.get("consumeOnSuccess"))
    pieces: List[str] = []
    if mx not in (None, ""):
        pieces.append(f"{_fmt_number(val)}/{_fmt_number(mx)}")
    elif val not in (None, ""):
        pieces.append(_fmt_number(val))
    if rec:
        pieces.append(f"recovers: {rec}")
    if cos:
        pieces.append("consume on success")
    return _join_nonempty(pieces, sep="; ") or "—"


def _fmt_cost(cost: Any) -> str:
    if isinstance(cost, list) and cost:
        parts: List[str] = []
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


def summarize_attack(attack: Dict[str, Any]) -> Dict[str, str]:
    """Normalize a Foundry/Daggerheart attack node for item or Actor display."""
    if not isinstance(attack, dict):
        return {
            "name": "—", "bonus": "—", "damage": "—", "damageType": "—",
            "range": "—", "trait": "—"
        }

    rng = prettify_camel(attack.get("range")) or "—"
    roll = attack.get("roll") if isinstance(attack.get("roll"), dict) else {}
    trait = roll.get("trait") or "—"
    bonus = _signed_number(roll.get("bonus"))

    parts = (attack.get("damage") or {}).get("parts") or []
    damage = "—"
    damage_type = "—"
    if isinstance(parts, list) and parts:
        p0 = parts[0] or {}
        val = p0.get("value") or {}
        dice = val.get("dice")
        dmg_bonus = val.get("bonus")
        bits: List[str] = []
        if dice:
            bits.append(str(dice))
        if dmg_bonus not in (None, 0, "0"):
            try:
                b = float(dmg_bonus)
                bits.append(f"{'+' if b >= 0 else '-'}{_fmt_number(abs(b))}")
            except (TypeError, ValueError):
                bits.append(str(dmg_bonus))
        damage = "".join(bits) if bits else "—"
        type_list = p0.get("type") or []
        damage_type = type_list[0] if isinstance(type_list, list) and type_list else "—"

    return {
        "name": str(attack.get("name") or "—"),
        "bonus": bonus,
        "damage": damage,
        "damageType": str(damage_type),
        "range": rng,
        "trait": str(trait),
    }


def summarize_actions(actions_node: Any) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    if not actions_node:
        return results

    if isinstance(actions_node, dict):
        iterable = actions_node.values()
    elif isinstance(actions_node, list):
        iterable = actions_node
    else:
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
            sv_mod = sv.get("damageMod") or "none"
            save = _join_nonempty([
                sv_trait or "—",
                f"DC {sv_diff}" if sv_diff not in (None, "") else None,
                f"mod {sv_mod}",
            ], sep="; ")

        desc = strip_html(a.get("description") or "").strip().split(":")
        desc = desc[-1] if len(desc) > 1 else desc[0]

        summary = _join_nonempty([
            f"{name} [{a_type}]",
            f"range {rng}",
            f"target {target}",
            f"roll {roll}",
            f"damage {damage}" if damage != "—" else None,
            f"save {save}" if save != "—" else None,
            f"cost {cost}" if cost != "—" else None,
            f"uses {uses}" if uses != "—" else None,
        ], sep=" — ")

        results.append({
            "name": str(name),
            "type": str(a_type),
            "range": rng,
            "target": target,
            "roll": roll,
            "damage": damage,
            "cost": cost,
            "uses": uses,
            "save": save,
            "description": desc,
            "summary": summary,
        })
    return results


def _fmt_effect_duration(dur: Any) -> str:
    if not isinstance(dur, dict):
        return "—"
    parts: List[str] = []
    if dur.get("seconds"):
        parts.append(f"{_fmt_number(dur['seconds'])}s")
    if dur.get("rounds"):
        parts.append(f"{_fmt_number(dur['rounds'])} rounds")
    if dur.get("turns"):
        parts.append(f"{_fmt_number(dur['turns'])} turns")
    if dur.get("sustained"):
        parts.append("sustained")
    anchors: List[str] = []
    if dur.get("startRound") not in (None, ""):
        anchors.append(f"startR {dur['startRound']}")
    if dur.get("startTurn") not in (None, ""):
        anchors.append(f"startT {dur['startTurn']}")
    if anchors:
        parts.append(f"({', '.join(anchors)})")
    return _join_nonempty(parts, sep=", ") or "—"


def _fmt_effect_changes(changes: Any) -> str:
    if not isinstance(changes, list) or not changes:
        return "—"
    out: List[str] = []
    for ch in changes:
        if not isinstance(ch, dict):
            continue
        key = ch.get("key") or "—"
        mode = ch.get("mode")
        val = ch.get("value")
        out.append(f"{key} ({mode}) = {val}" if mode not in (None, "") else f"{key} = {val}")
    return "; ".join(out) if out else "—"


def summarize_effects(effects_node: Any) -> List[Dict[str, str]]:
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
        changes = _fmt_effect_changes(_coalesce(eff.get("changes"), eff.get("system", {}).get("changes")))
        duration = _fmt_effect_duration(eff.get("duration"))
        transfer = "yes" if bool(eff.get("transfer")) else "no" if eff.get("transfer") is not None else "—"
        disabled = "yes" if bool(eff.get("disabled")) else "no" if eff.get("disabled") is not None else "—"
        summary = _join_nonempty([
            str(name),
            f"changes: {changes}" if changes != "—" else None,
            f"duration: {duration}" if duration != "—" else None,
            f"transfer: {transfer}" if transfer != "—" else None,
            f"disabled: {disabled}" if disabled != "—" else None,
        ], sep=" — ")
        results.append({
            "name": str(name), "changes": changes, "duration": duration,
            "transfer": transfer, "disabled": disabled,
            "description": desc, "summary": summary,
        })
    return results


# ---------------------------- Feature summarizers ----------------------------

def _summarize_features_generic(features_node: Any, default_kind: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not isinstance(features_node, list):
        return out
    for f in features_node:
        if not isinstance(f, dict):
            continue
        name = _coalesce(f.get("name"), f.get("value")) or "Unnamed Feature"
        kind = _coalesce(f.get("type"), f.get("kind"), default_kind)
        desc = _coalesce(f.get("description"), "")
        summary_bits = [f"{name} [{kind}]", f"{desc}"]
        summary = " — ".join([b for b in summary_bits if b])
        out.append({
            "name": prettify_camel(name),
            "kind": str(kind),
            "description": str(desc),
            "summary": summary or str(name),
        })
    return out


def summarize_weapon_features(node: Any) -> List[Dict[str, str]]:
    return _summarize_features_generic(node, default_kind="weapon-feature")


def summarize_armor_features(node: Any) -> List[Dict[str, str]]:
    return _summarize_features_generic(node, default_kind="armor-feature")


def summarize_embedded_actor_features(items_node: Any) -> List[Dict[str, Any]]:
    """Normalize embedded Actor feature Items without duplicating identical action text."""
    out: List[Dict[str, Any]] = []
    if not isinstance(items_node, list):
        return out
    for item in items_node:
        if not isinstance(item, dict) or item.get("type") != "feature":
            continue
        system = item.get("system") if isinstance(item.get("system"), dict) else {}
        desc = strip_html(system.get("description") or "")
        actions = summarize_actions(system.get("actions") or {})
        distinct_actions: List[Dict[str, str]] = []
        norm_desc = re.sub(r"\s+", " ", desc).strip().lower()
        for action in actions:
            action_desc = re.sub(r"\s+", " ", action.get("description", "")).strip().lower()
            if not action_desc or action_desc == norm_desc:
                continue
            distinct_actions.append(action)
        out.append({
            "name": str(item.get("name") or "Unnamed Feature"),
            "description": desc,
            "actions": distinct_actions,
        })
    return out


def embedded_features_to_md(features: List[Dict[str, Any]]) -> str:
    if not features:
        return "—"
    blocks: List[str] = []
    for feature in features:
        name = md_escape(feature.get("name") or "Unnamed Feature")
        desc = feature.get("description") or ""
        block = f"### {name}\n\n{desc or '—'}"
        action_lines: List[str] = []
        for action in feature.get("actions") or []:
            label = md_escape(action.get("name") or "Action")
            atype = prettify_camel(action.get("type") or "action")
            adesc = action.get("description") or action.get("summary") or ""
            action_lines.append(f"- **{label}** (*{atype}*) — {adesc}")
        if action_lines:
            block += "\n\n" + "\n".join(action_lines)
        blocks.append(block)
    return "\n\n".join(blocks)


# ---------------------------- Actor helpers ----------------------------------

def experiences_to_md(experiences: Any) -> str:
    if not experiences:
        return "—"
    lines: List[str] = []
    vals = experiences.values() if isinstance(experiences, dict) else experiences if isinstance(experiences, list) else []
    for exp in vals:
        if isinstance(exp, dict):
            name = exp.get("name") or "Experience"
            value = exp.get("value")
            suffix = f" {_signed_number(value)}" if value not in (None, "") else ""
            lines.append(f"- **{md_escape(name)}{suffix}**")
        elif exp not in (None, ""):
            lines.append(f"- {md_escape(exp)}")
    return "\n".join(lines) or "—"


def impulses_to_md(impulses: Any) -> str:
    if not impulses:
        return "—"
    if isinstance(impulses, list):
        vals = [str(x).strip() for x in impulses if str(x).strip()]
    else:
        vals = [x.strip() for x in re.split(r"[,\n;]+", str(impulses)) if x.strip()]
    return "\n".join(f"- {md_escape(x)}" for x in vals) or "—"


def potential_adversaries_to_md(value: Any) -> str:
    if not value:
        return "—"
    entries: List[str] = []
    if isinstance(value, dict):
        iterable = value.items()
        for k, v in iterable:
            if isinstance(v, dict):
                name = v.get("name") or v.get("label") or k
                entries.append(str(name))
            elif isinstance(v, str) and v:
                entries.append(v)
            elif k:
                entries.append(str(k))
    elif isinstance(value, list):
        for v in value:
            if isinstance(v, dict):
                entries.append(str(v.get("name") or v.get("label") or v.get("id") or "Adversary"))
            elif v not in (None, ""):
                entries.append(str(v))
    else:
        entries.append(str(value))
    return "\n".join(f"- {md_escape(x)}" for x in entries) or "—"


def resistances_to_md(resistance: Any) -> str:
    if not isinstance(resistance, dict):
        return ""
    lines: List[str] = []
    for damage_type, data in resistance.items():
        if not isinstance(data, dict):
            continue
        flags: List[str] = []
        if data.get("immunity"):
            flags.append("Immune")
        elif data.get("resistance"):
            flags.append("Resistant")
        reduction = data.get("reduction")
        if reduction not in (None, 0, "0", ""):
            flags.append(f"Reduction {_fmt_number(reduction)}")
        if flags:
            lines.append(f"- **{prettify_camel(damage_type)}:** {', '.join(flags)}")
    return "\n".join(lines)


def resolve_folder_path(folder_id: str, folder_map: Dict[str, Dict[str, Any]], type_key: str, sep: str = "/") -> str:
    if not folder_id:
        return type_key
    parts: List[str] = []
    seen = set()
    current = folder_id
    while current:
        if current in seen:
            break
        seen.add(current)
        meta = folder_map.get(current)
        if not meta:
            parts.append(type_key)
            break
        name = meta.get("name")
        if name:
            parts.append(str(name))
        parent = meta.get("parent_folder")
        if not parent or parent == current:
            parts.append(type_key)
            break
        current = parent
    if not parts:
        return type_key
    return sep.join(reversed(parts))


def resolve_publication_image(
    docs_root: Path,
    detail_dir: Path,
    audience: str,
    type_key: str,
    slug: str,
    obj: Dict[str, Any],
) -> str:
    """Return an existing MkDocs-local image path, or an empty string if none is staged."""
    audience_root = docs_root / audience
    source_name = Path(str(obj.get("img") or "")).name
    stem_variants = [slug, slug.replace("-", "_"), Path(source_name).stem] if source_name else [slug, slug.replace("-", "_")]
    stem_variants = list(dict.fromkeys([x for x in stem_variants if x]))

    candidates: List[Path] = []
    if type_key == "adversaries":
        for stem in stem_variants:
            for ext in (".webp", ".png", ".jpg", ".jpeg"):
                candidates.extend([
                    audience_root / "assets" / "icons" / "adversaries" / f"{stem}{ext}",
                    audience_root / "assets" / "images" / "adversaries" / f"{stem}{ext}",
                ])
    elif type_key == "environments":
        for stem in stem_variants:
            for ext in (".png", ".webp", ".jpg", ".jpeg"):
                candidates.append(audience_root / "assets" / "images" / "environments" / f"{stem}{ext}")

    for candidate in candidates:
        if candidate.exists():
            rel = os.path.relpath(candidate, detail_dir).replace(os.sep, "/")
            return rel
    return ""


def optional_image_markup(image_rel: str, name: str) -> str:
    if not image_rel:
        return ""
    return f'<img src="{md_escape(image_rel)}" alt="{md_escape(name)}" class="item-image" style="width:300px; height:auto;">'


# ---------------------------- Templates --------------------------------------

TEMPLATES: Dict[str, str] = {
    "item_default": """<div class="default" markdown="1">
# {name}
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">

*{description}*

### **Tier: {tier}**

#### Actions
{actions_flat}

#### Effects
{effects_flat}

<div class="meta" markdown="1">
{folder_path}
<br>
**UUID:** `Compendium.cybermancy.{comp_key}.{slug}`
</div>
</div>
""",

    "weapon": """<div class="item" markdown="1">
<div class="grid item-grid" markdown="1">
<div markdown="1">
# {name}

<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">

<div class="item-flavor">
{description}
</div>
</div>

<div markdown="1">
#### Stats
<table class="stat-table">
  <thead><tr><th align="left">Attribute</th><th align="right">Value</th></tr></thead>
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
{folder_path}
<br>
</div>
</div>
""",

    "armor": """<div class="item" markdown="1">
<div class="grid item-grid" markdown="1">
<div markdown="1">
# {name}
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">
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
{folder_path}
<br>
**UUID:** `Compendium.cybermancy.{comp_key}.{slug}`
</div>
</div>
""",

    "class": """<div class="class" markdown="1">
# {name}
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">

## Description
*{description}*

## At a Glance
- **Domains:** {domains_list}
- **Hit Points:** {hitPoints}
- **Evasion:** {evasion}

## Subclasses
{subclasses_md}

## Features
{features_md}

---

<div class="meta" markdown="1">
**UUID:** `Compendium.cybermancy.system.{slug}`
{folder_path}
<br>
</div>
</div>
""",

    "subclass": """<div class="subclass" markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">
# {name}

## Description
*{description}*

<div class="item-subtitle">Subclass</div>

## Features
{features_md}

---

<div class="meta" markdown="1">
**UUID:** `Compendium.cybermancy.system.{slug}`
{folder_path}
<br>
</div>
</div>
""",

    "domain": """<div class="domain" markdown="1">
# {name}
## {domain}
<div class="grid item-grid" markdown="1">
<div markdown="1">
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">
## Description
{description}
</div>
<div markdown="1">
<table class="stat-table">
  <thead><tr><th>Attribute</th><th align="right">Value</th></tr></thead>
  <tbody>
    <tr><td>Type</td><td align="right">{type}</td></tr>
    <tr><td>Level</td><td align="right">{level}</td></tr>
    <tr><td>Recall Cost</td><td align="right">{recallCost}</td></tr>
  </tbody>
</table>
</div>
</div>
## Actions
{actions_flat}

---

<div class="meta" markdown="1">
{folder_path}
<br>
**UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
""",

    "feature": """<div class="feature" markdown="1">
# {name}
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">
## Description
*{description}*

## Actions
{actions_flat}

---

<div class="meta" markdown="1">
{folder_path}
<br>
**UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
""",

    "adversaries-features": """<div class="feature" markdown="1">
# {name}
<img src="{image_rel}" alt="{name}" class="item-image" style="width:300px; height:auto;">
## Description
*{description}*

## Actions
{actions_flat}

---

<div class="meta" markdown="1">
{folder_path}
<br>
**UUID:** `Compendium.cybermancy.system.{slug}`
</div>
</div>
""",

    "adversary": """<div class="adversary" markdown="1">
# {name}
{image_markup}

<div class="item-flavor" markdown="1">
{description}
</div>

<table class="stat-table">
  <thead><tr><th>Attribute</th><th align="right">Value</th></tr></thead>
  <tbody>
    <tr><td>Tier</td><td align="right">{tier}</td></tr>
    <tr><td>Role</td><td align="right">{role}</td></tr>
    <tr><td>Difficulty</td><td align="right">{difficulty}</td></tr>
    <tr><td>Damage Thresholds</td><td align="right">{majorThreshold} / {severeThreshold}</td></tr>
    <tr><td>Hit Points</td><td align="right">{hitPoints}</td></tr>
    <tr><td>Stress</td><td align="right">{stress}</td></tr>
  </tbody>
</table>

## Attack

| Attack | Modifier | Range | Damage |
|---|---:|---|---|
| {attackName} | {attackBonus} | {attackRange} | {attackDamage} {attackDamageType} |

## Experiences
{experiences_md}

## Motives & Tactics
{motivesAndTactics}

## Features
{embedded_features_md}

{resistances_section}
{notes_section}

---

<div class="meta" markdown="1">
{folder_path}
</div>
</div>
""",

    "environment": """<div class="environment" markdown="1">
# {name}
{image_markup}

<div class="item-flavor" markdown="1">
{description}
</div>

<table class="stat-table">
  <thead><tr><th>Attribute</th><th align="right">Value</th></tr></thead>
  <tbody>
    <tr><td>Tier</td><td align="right">{tier}</td></tr>
    <tr><td>Type</td><td align="right">{environmentType}</td></tr>
    <tr><td>Difficulty</td><td align="right">{difficulty}</td></tr>
  </tbody>
</table>

## Impulses
{impulses_md}

## Features
{embedded_features_md}

## Potential Adversaries
{potential_adversaries_md}

{notes_section}

---

<div class="meta" markdown="1">
{folder_path}
</div>
</div>
""",
}


# ---------------------------- Configuration ----------------------------------

DEFAULT_ITEM_FIELD_MAP = {
    "name": "name",
    "id": "_id",
    "key": "_key",
    "folder": "folder",
    "type": "type",
    "description": "system.description",
    "tier": "system.tier",
    "actions": "system.actions",
    "effects": "effects",
    "img": "img",
}

ACTOR_FIELD_MAP = {
    "name": "name",
    "id": "_id",
    "key": "_key",
    "folder": "folder",
    "type": "type",
    "description": "system.description",
    "tier": "system.tier",
    "img": "img",
}

CONFIG: Dict[str, Dict[str, Any]] = {
    # Features first: classes/subclasses can resolve references from feature_map.
    "features": {
        "kind": "system", "audiences": ["player-facing"], "src_subdir": "features",
        "csv_fields": ["name", "slug", "description"],
        "field_map": {
            "name": "name", "id": "_id", "key": "_key", "folder": "folder",
            "actions": "system.actions", "description": "system.description", "img": "img",
        },
        "template": "feature",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/system/{key}",
    },
    "adversaries-features": {
        "kind": "system", "audiences": ["gm-facing"], "src_subdir": "adversaries-features",
        "csv_fields": ["name", "slug", "tier", "description"],
        "field_map": {
            "name": "name", "id": "_id", "key": "_key", "folder": "folder",
            "actions": "system.actions", "description": "system.description", "img": "img",
        },
        "template": "adversaries-features",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/system/{key}",
    },

    # GM Actor packs. These use explicit source paths because they live directly
    # below src/packs rather than under src/packs/items or src/packs/system.
    "adversaries": {
        "kind": "actors", "audiences": ["gm-facing"],
        "src_path": "src/packs/adversaries", "actor_type": "adversary",
        "csv_fields": ["name", "slug", "tier", "role", "difficulty", "description"],
        "field_map": ACTOR_FIELD_MAP | {
            "role": "system.type", "difficulty": "system.difficulty",
        },
        "template": "adversary",
        "comp_key": "adversaries",
        "out_dir_name": lambda audience, key: f"{audience}/adventures/{key}",
        "sort_fields": ["tier", "role", "name"],
    },
    "environments": {
        "kind": "actors", "audiences": ["gm-facing"],
        "src_path": "src/packs/environments", "actor_type": "environment",
        "csv_fields": ["name", "slug", "tier", "type", "difficulty", "description"],
        "field_map": ACTOR_FIELD_MAP | {
            "difficulty": "system.difficulty",
        },
        "template": "environment",
        "comp_key": "environments",
        "out_dir_name": lambda audience, key: f"{audience}/adventures/{key}",
        "sort_fields": ["tier", "type", "name"],
    },

    # Player items.
    "weapons": {
        "kind": "items", "audiences": ["player-facing"], "src_subdir": "weapons",
        "csv_fields": ["name", "slug", "description", "tier", "trait", "range", "burden", "damage", "weapon_feats", "actions_flat"],
        "field_map": DEFAULT_ITEM_FIELD_MAP | {
            "attack": "system.attack", "burden": "system.burden",
            "weaponFeatures": "system.weaponFeatures", "trait": "system.attack.roll.trait",
            "range": "system.attack.range",
        },
        "template": "weapon",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "weapons",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}",
    },
    "armors": {
        "kind": "items", "audiences": ["player-facing"], "src_subdir": "armors",
        "csv_fields": ["name", "slug", "description", "tier", "baseScore", "majorThreshold", "severeThreshold", "armor_features_flat"],
        "field_map": DEFAULT_ITEM_FIELD_MAP | {
            "baseScore": "system.baseScore", "armorFeatures": "system.armorFeatures",
            "baseThresholds": "system.baseThresholds",
        },
        "template": "armor",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "armors",
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}",
    },
}

for _key in ("ammo", "consumables", "cybernetics", "drones-devices", "mods", "loot"):
    CONFIG[_key] = {
        "kind": "items", "audiences": ["player-facing"], "src_subdir": _key,
        "csv_fields": ["name", "slug", "description", "tier", "actions"],
        "field_map": DEFAULT_ITEM_FIELD_MAP,
        "template": "item_default",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": _key,
        "out_dir_name": lambda audience, key: f"{audience}/items/{key}",
    }

CONFIG.update({
    "domains": {
        "kind": "system", "audiences": ["player-facing"], "src_subdir": "domains",
        "csv_fields": ["name", "slug", "domain", "description", "level", "recallCost"],
        "field_map": {
            "name": "name", "id": "_id", "key": "_key", "folder": "folder",
            "type": "system.type", "level": "system.level", "domain": "system.domain",
            "recallCost": "system.recallCost", "actions": "system.actions",
            "description": "system.description", "img": "img",
        },
        "template": "domain",
        "image_rel": lambda audience, key, slug, domain="": f"../../../assets/icons/{key}/{domain}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/system/{key}",
    },
    "subclasses": {
        "kind": "system", "audiences": ["player-facing"], "src_subdir": "subclasses",
        "csv_fields": ["name", "slug", "description", "spellcastingTrait"],
        "field_map": {
            "name": "name", "id": "_id", "key": "_key", "folder": "folder",
            "spellcastingTrait": "system.spellcastingTrait", "features": "system.features",
            "description": "system.description", "img": "img",
        },
        "template": "subclass",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/system/{key}",
    },
    "classes": {
        "kind": "system", "audiences": ["player-facing"], "src_subdir": "classes",
        "csv_fields": ["name", "slug", "description"],
        "field_map": {
            "name": "name", "id": "_id", "key": "_key", "folder": "folder",
            "type": "type", "domains": "system.domains", "hitPoints": "system.hitPoints",
            "evasion": "system.evasion", "features": "system.features",
            "subclasses": "system.subclasses", "description": "system.description", "img": "img",
        },
        "template": "class",
        "image_rel": lambda audience, key, slug: f"../../../assets/icons/{key}/{slug}.webp",
        "comp_key": "system",
        "out_dir_name": lambda audience, key: f"{audience}/system/{key}",
    },
})


# ---------------------------- Rendering helpers ------------------------------

def render_template(tmpl_key: str, ctx: Dict[str, Any]) -> str:
    return TEMPLATES[tmpl_key].format(**ctx)


def list_to_md_bullets(val: Any) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return "\n".join(f"- {md_escape(str(x))}" for x in val)
    return f"- {md_escape(str(val))}"


def features_to_md(val: Any, feature_map: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    if not val:
        return ""
    feature_map = feature_map or {}
    lines: List[str] = []

    if isinstance(val, list):
        for x in val:
            if isinstance(x, str):
                feature_id = x.split(".")[-1]
                meta = feature_map.get(feature_id)
                if meta:
                    fname = meta.get("name", "")
                    fdesc = meta.get("description", "")
                    ftype = meta.get("type") or ""
                    fimg = meta.get("feature_image_rel") or ""
                    href = meta.get("feature_href_rel", f"../features/{slugify(fname)}/")
                    type_prefix = f"_{md_escape(str(ftype).title())}_: " if ftype else ""
                    lines.append(
                        "- "
                        f"<a href='{href}'><img src='{fimg}' alt='{md_escape(fname)}' "
                        f"class='item-image' style='width:120px; height:auto;'></a><br> "
                        f"<a href='{href}'><strong>{md_escape(fname)}</strong></a> — {type_prefix}{fdesc}"
                    )
                else:
                    lines.append(f"- {md_escape(x)}")
                continue

            if isinstance(x, dict) and "item" in x:
                uuid = str(x.get("item", ""))
                feature_id = uuid.split(".")[-1]
                meta = feature_map.get(feature_id)
                if meta:
                    fname = meta.get("name", "")
                    fdesc = meta.get("description", "")
                    ftype = x.get("type") or meta.get("type") or ""
                    fimg = meta.get("feature_image_rel") or ""
                    href = meta.get("feature_href_rel", f"../features/{slugify(fname)}/")
                    type_prefix = f"_{md_escape(str(ftype).title())}_: " if ftype else ""
                    lines.append(
                        "- "
                        f"<a href='{href}'><img src='{fimg}' alt='{md_escape(fname)}' "
                        f"class='item-image' style='width:120px; height:auto;'></a><br> "
                        f"<a href='{href}'><strong>{md_escape(fname)}</strong></a> — {type_prefix}{fdesc}"
                    )
                    continue

            if isinstance(x, dict):
                name = x.get("name") or ""
                desc = x.get("description") or x.get("text") or ""
                if name or desc:
                    lines.append(f"- **{md_escape(name)}** — {desc}" if desc else f"- {md_escape(name)}")
                    continue

            lines.append(f"- {md_escape(x)}")
        return "\n".join(lines)

    if isinstance(val, dict):
        for k, v in val.items():
            if isinstance(v, dict):
                name = v.get("name", k)
                desc = v.get("description", v.get("text", ""))
                lines.append(f"- **{md_escape(name)}** — {desc}" if desc else f"- {md_escape(name)}")
            else:
                lines.append(f"- **{md_escape(k)}** — {v}")
        return "\n".join(lines)

    return md_escape(val)


def _sort_component(value: Any) -> Tuple[int, Any]:
    if value in (None, ""):
        return (2, "")
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value).lower())


def sort_rows(rows: List[Dict[str, Any]], cfg: Dict[str, Any]) -> None:
    fields = cfg.get("sort_fields")
    if fields:
        rows.sort(key=lambda r: tuple(_sort_component(r.get(field)) for field in fields))
        return

    tier_present = "tier" in cfg["csv_fields"]
    domain_present = "domain" in cfg["csv_fields"]
    if tier_present:
        rows.sort(key=lambda r: (str(r.get("tier", "")).lower(), str(r.get("name", "")).lower()))
    elif domain_present:
        def level_sort_value(v: Dict[str, Any]) -> int:
            try:
                return int(v.get("level"))
            except (TypeError, ValueError):
                return 9999
        rows.sort(key=lambda r: (str(r.get("domain", "")).lower(), level_sort_value(r)))
    else:
        rows.sort(key=lambda r: str(r.get("name", "")).lower())


# ---------------------------- Main processor ---------------------------------

def process_type(
    root: Path,
    docs_root: Path,
    data_root: Path,
    audience: str,
    type_key: str,
    feature_map: Dict[str, Dict[str, Any]],
    folder_map: Dict[str, Dict[str, Any]],
) -> Tuple[int, Optional[Path]]:
    cfg = CONFIG[type_key]
    kind = cfg["kind"]
    src_dir = source_dir_for(root, cfg)
    if not src_dir.exists():
        return 0, None

    rows: List[Dict[str, Any]] = []
    field_map = cfg["field_map"]
    template_key = cfg["template"]
    out_dir_rel = cfg["out_dir_name"](audience, type_key)
    out_dir = docs_root / out_dir_rel
    ensure_dir(out_dir)

    # First pass: gather organizational folders.
    for p in sorted(src_dir.rglob("*.json")):
        obj = read_json(p)
        if not obj or not is_foundry_folder(obj):
            continue
        name = get_in(obj, field_map.get("name", "name"))
        if not name:
            continue
        folder_id = foundry_document_id(obj)
        parent = get_in(obj, field_map.get("folder", "folder"))
        if folder_id:
            folder_map[folder_id] = {"name": name, "parent_folder": parent}

    count = 0
    for p in sorted(src_dir.rglob("*.json")):
        obj = read_json(p)
        if not obj or is_foundry_folder(obj):
            continue

        expected_actor_type = cfg.get("actor_type")
        if expected_actor_type and str(obj.get("type") or "").lower() != str(expected_actor_type).lower():
            continue

        name = get_in(obj, field_map.get("name", "name"))
        if not name:
            continue
        slug = slugify(str(name))
        description = get_in(obj, field_map.get("description", "system.description"))
        document_type = get_in(obj, field_map.get("type", "type"))
        doc_id = foundry_document_id(obj)
        tier = get_in(obj, field_map.get("tier", "system.tier"))
        folder = get_in(obj, field_map.get("folder", "folder"))

        if tier in (None, "") and isinstance(folder, str) and folder and folder in folder_map:
            tier = folder_map[folder]["name"]

        # Preserve existing feature-reference behavior for item/system families.
        if kind != "actors" and doc_id:
            image_rel_fn = cfg.get("image_rel")
            try:
                feature_image_rel = md_escape(image_rel_fn(audience, type_key, slug)) if image_rel_fn else ""
            except TypeError:
                feature_image_rel = ""
            feature_map[doc_id] = {
                "name": name,
                "description": description,
                "type": document_type,
                "feature_image_rel": feature_image_rel,
                "feature_href_rel": f"../../{type_key}/{slug}/",
            }

        actions_node = get_in(obj, field_map.get("actions", "system.actions"), [])
        effects_node = get_in(obj, field_map.get("effects", "system.effects"), [])
        action_summaries = summarize_actions(actions_node)
        effect_summaries = summarize_effects(effects_node)
        folder_path = resolve_folder_path(folder, folder_map, type_key)

        csv_row: Dict[str, Any] = {"name": name, "slug": slug}
        for col in cfg["csv_fields"]:
            if col in ("name", "slug"):
                continue
            src = field_map.get(col, col)
            csv_row[col] = get_in(obj, src, "")
        if "tier" in cfg["csv_fields"]:
            csv_row["tier"] = tier
        rows.append(csv_row)

        detail_dir = docs_root / out_dir_rel / slug
        ensure_dir(detail_dir)

        static_image_rel = ""
        if kind != "actors" and cfg.get("image_rel"):
            try:
                static_image_rel = cfg["image_rel"](audience, type_key, slug)
            except TypeError:
                static_image_rel = ""

        ctx: Dict[str, Any] = {
            "name": md_escape(name),
            "image_rel": md_escape(static_image_rel),
            "image_markup": "",
            "slug": slug,
            "type": prettify_camel(document_type or "Common"),
            "tier": md_escape(str(tier) if tier not in (None, "") else "—"),
            "description": description or "(No description yet.)",
            "comp_key": cfg.get("comp_key", type_key),
            "type_title": titleize(type_key[:-1]) if type_key.endswith("s") else titleize(type_key),
            "actions": action_summaries,
            "effects": effect_summaries,
            "actions_flat": "\n\n".join(
                f"- <div markdown='1'>**{a['name']}**<br>*{a['description']}*</div>" for a in action_summaries
            ) or "—",
            "effects_flat": "\n\n".join(
                f"- <div markdown='1'>**{e['name']}**<br>*{e['description']}*</div>" for e in effect_summaries
            ) or "—",
            "folder_path": folder_path,
        }

        if kind == "items":
            attack_node = get_in(obj, field_map.get("attack", "system.attack"), {})
            atk = summarize_attack(attack_node) if attack_node else {
                "damage": "—", "damageType": "—", "range": "—", "trait": "—",
            }
            damage = atk["damage"]
            rng = atk["range"]
            trait = prettify_camel(atk.get("trait") or "—")
            weapon_feats = summarize_weapon_features(get_in(obj, field_map.get("weaponFeatures", "system.weaponFeatures"), []))
            armor_feats = summarize_armor_features(get_in(obj, field_map.get("armorFeatures", "system.armorFeatures"), []))
            burden = prettify_camel(get_in(obj, field_map.get("burden", "")))
            base_score = get_in(obj, field_map.get("baseScore", ""))
            base_thresholds = get_in(obj, field_map.get("baseThresholds", ""))
            if not isinstance(base_thresholds, dict):
                base_thresholds = {}

            for key_name, value in {
                "damage": damage, "range": rng, "trait": trait, "burden": burden,
                "majorThreshold": base_thresholds.get("major", "—"),
                "severeThreshold": base_thresholds.get("severe", "—"),
            }.items():
                if key_name in cfg["csv_fields"]:
                    rows[-1][key_name] = value

            ctx.update({
                "damage": md_escape(damage or "—"),
                "range": md_escape(rng or "—"),
                "trait": md_escape(trait or "—"),
                "burden": md_escape(burden or "—"),
                "baseScore": md_escape(base_score or "—"),
                "baseThresholds": md_escape(base_thresholds or "—"),
                "majorThreshold": md_escape(base_thresholds.get("major", "—")),
                "severeThreshold": md_escape(base_thresholds.get("severe", "—")),
                "weapon_features_list": weapon_feats,
                "armor_features_list": armor_feats,
                "weapon_features_flat": "\n".join(
                    f"- <div markdown='1'>**{x['name']}**<br>*{x['description']}*</div>" for x in weapon_feats
                ) or "—",
                "armor_features_flat": "\n".join(
                    f"- <div markdown='1'>**{x['name']}**<br>*{x['description']}*</div>" for x in armor_feats
                ) or "—",
            })

        elif kind == "actors":
            system = obj.get("system") if isinstance(obj.get("system"), dict) else {}
            pub_image = resolve_publication_image(docs_root, detail_dir, audience, type_key, slug, obj)
            ctx["image_markup"] = optional_image_markup(pub_image, str(name))
            ctx["description"] = strip_html(description) or "(No description yet.)"

            embedded = summarize_embedded_actor_features(obj.get("items") or [])
            ctx["embedded_features_md"] = embedded_features_to_md(embedded)
            ctx["difficulty"] = md_escape(system.get("difficulty") if system.get("difficulty") not in (None, "") else "—")
            notes = strip_html(system.get("notes") or "")
            ctx["notes_section"] = f"## Notes\n{notes}\n" if notes else ""

            if type_key == "adversaries":
                role = prettify_camel(system.get("type") or "—")
                thresholds = system.get("damageThresholds") if isinstance(system.get("damageThresholds"), dict) else {}
                resources = system.get("resources") if isinstance(system.get("resources"), dict) else {}
                hp = get_in(resources, "hitPoints.max", "—")
                stress = get_in(resources, "stress.max", "—")
                attack = summarize_attack(system.get("attack") or {})
                resistances_md = resistances_to_md(system.get("resistance"))

                rows[-1]["role"] = role
                rows[-1]["difficulty"] = system.get("difficulty", "")
                rows[-1]["description"] = strip_html(description)

                ctx.update({
                    "role": md_escape(role),
                    "majorThreshold": md_escape(thresholds.get("major", "—")),
                    "severeThreshold": md_escape(thresholds.get("severe", "—")),
                    "hitPoints": md_escape(hp),
                    "stress": md_escape(stress),
                    "attackName": md_escape(attack["name"]),
                    "attackBonus": md_escape(attack["bonus"]),
                    "attackRange": md_escape(attack["range"]),
                    "attackDamage": md_escape(attack["damage"]),
                    "attackDamageType": md_escape(prettify_camel(attack["damageType"])),
                    "experiences_md": experiences_to_md(system.get("experiences")),
                    "motivesAndTactics": strip_html(system.get("motivesAndTactics") or "") or "—",
                    "resistances_section": f"## Resistances & Immunities\n{resistances_md}\n" if resistances_md else "",
                })

            elif type_key == "environments":
                environment_type = prettify_camel(system.get("type") or "—")
                rows[-1]["type"] = environment_type
                rows[-1]["difficulty"] = system.get("difficulty", "")
                rows[-1]["description"] = strip_html(description)
                ctx.update({
                    "environmentType": md_escape(environment_type),
                    "impulses_md": impulses_to_md(system.get("impulses")),
                    "potential_adversaries_md": potential_adversaries_to_md(system.get("potentialAdversaries")),
                })

        else:  # system
            domain = ""
            if type_key == "classes":
                domains = get_in(obj, field_map["domains"], [])
                ctx["domains_list"] = prettify_camel(", ".join(domains) if isinstance(domains, list) else domains)
                ctx["hitPoints"] = md_escape(get_in(obj, field_map["hitPoints"], ""))
                ctx["evasion"] = md_escape(get_in(obj, field_map["evasion"], ""))
                ctx["features_md"] = features_to_md(get_in(obj, field_map["features"], []), feature_map)
                ctx["subclasses_md"] = features_to_md(get_in(obj, field_map["subclasses"], []), feature_map)
            elif type_key == "subclasses":
                ctx["features_md"] = features_to_md(get_in(obj, field_map["features"], []), feature_map)
            elif type_key == "domains":
                domain = get_in(obj, field_map.get("domain", "system.domain"))
                ctx["level"] = md_escape(get_in(obj, field_map["level"], ""))
                ctx["domain"] = prettify_camel(get_in(obj, field_map["domain"], []))
                ctx["recallCost"] = md_escape(get_in(obj, field_map["recallCost"], ""))
                if "domain" in cfg["csv_fields"]:
                    rows[-1]["domain"] = prettify_camel(domain)

            if type_key == "domains":
                ctx["image_rel"] = cfg["image_rel"](audience, type_key, slug, domain)
            else:
                ctx["image_rel"] = cfg["image_rel"](audience, type_key, slug)

        page_md = render_template(template_key, ctx)
        (detail_dir / "index.md").write_text(page_md, encoding="utf-8")
        count += 1

    if rows:
        sort_rows(rows, cfg)
        csv_path = data_root / f"{type_key}.csv"
        ensure_dir(csv_path.parent)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cfg["csv_fields"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {csv_path} ({len(rows)} rows)")

    return count, out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument("--audience", default="player-facing", choices=["player-facing", "gm-facing"])
    ap.add_argument(
        "--types", default="",
        help=("Comma-separated type keys to build (default: all). "
              "Examples: weapons,armors,classes,domains or adversaries,environments"),
    )
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    docs_root = root / "docs"
    data_root = docs_root / "data"
    ensure_dir(docs_root)
    ensure_dir(data_root)
    feature_map: Dict[str, Dict[str, Any]] = {}
    folder_map: Dict[str, Dict[str, Any]] = {}

    all_types = list(CONFIG.keys())
    selected = [t.strip() for t in args.types.split(",") if t.strip()] if args.types else all_types

    total = 0
    for type_key in selected:
        if type_key not in CONFIG:
            print(f"[skip] Unknown type: {type_key}")
            continue
        if args.audience not in CONFIG[type_key]["audiences"]:
            print(f"[skip] {type_key}: not published to {args.audience}")
            continue

        n, out_dir = process_type(
            root, docs_root, data_root, args.audience, type_key, feature_map, folder_map
        )
        if n:
            print(f"[ok] {type_key}: {n} pages -> {out_dir}")
            total += n
        else:
            print(f"[warn] {type_key}: no JSON found")

    print(f"Done. Wrote {total} pages total.")


if __name__ == "__main__":
    main()
