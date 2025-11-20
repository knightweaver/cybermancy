import json
import os
import re
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def first_or_none(items):
    return items[0] if items else None


# ---------------------------------------------------------------------------
# Extractor Functions (unchanged)
# ---------------------------------------------------------------------------

def extract_traits(system):
    t = system["traits"]
    return {
        "strength": t["strength"]["value"],
        "agility":  t["agility"]["value"],
        "finesse":  t["finesse"]["value"],
        "instinct": t["instinct"]["value"],
        "presence": t["presence"]["value"],
        "knowledge":t["knowledge"]["value"]
    }


def extract_experiences(system):
    ex = system.get("experiences", {})
    out = []
    for obj in ex.values():
        out.append({
            "name": obj.get("name",""),
            "value": obj.get("value",""),
            "description": obj.get("description","")
        })
    return out


def extract_features(items):
    groups = {
        "ancestry": [],
        "community": [],
        "class": [],
        "subclass": []
    }
    for it in items:
        if it["type"] != "feature":
            continue
        origin = it["system"].get("originItemType")
        if origin in groups:
            groups[origin].append({
                "name": it["name"],
                "description": it["system"].get("description","")
            })
    return groups


def extract_domain_cards(items):
    out = []
    for it in items:
        if it["type"] != "domainCard":
            continue
        sys = it["system"]
        out.append({
            "name": it["name"],
            "domain": sys.get("domain",""),
            "level": sys.get("level",""),
            "description": sys.get("description","")
        })
    return out


def extract_weapons(items):
    out = []
    for it in items:
        if it["type"] != "weapon":
            continue
        sys = it["system"]
        atk = sys.get("attack", {})
        dmg = ""
        parts = atk.get("damage",{}).get("parts",[])
        if parts:
            val = parts[0].get("value",{})
            dice = val.get("dice","")
            bonus = val.get("bonus")
            dmg_type = ", ".join(parts[0].get("type",[]))
            if bonus:
                dmg = f"{dice}+{bonus} ({dmg_type})"
            else:
                dmg = f"{dice} ({dmg_type})"

        actions = []
        for a in sys.get("actions",{}).values():
            actions.append({
                "name": a.get("name",""),
                "description": a.get("description","")
            })

        out.append({
            "name": it["name"],
            "equipped": sys.get("equipped", False),
            "trait": atk.get("roll",{}).get("trait",""),
            "range": atk.get("range",""),
            "damage": dmg,
            "actions": actions
        })
    return out


def extract_armor(items):
    out = []
    for it in items:
        if it["type"] != "armor":
            continue
        sys = it["system"]
        out.append({
            "name": it["name"],
            "equipped": sys.get("equipped", False),
            "base": sys.get("baseScore",""),
            "major": sys.get("baseThresholds",{}).get("major",""),
            "severe": sys.get("baseThresholds",{}).get("severe",""),
            "description": sys.get("description","")
        })
    return out


def extract_consumables(items):
    out = []
    for it in items:
        if it["type"] != "consumable":
            continue
        sys = it["system"]
        out.append({
            "name": it["name"],
            "qty": sys.get("quantity",1),
            "description": sys.get("description","")
        })
    return out


def extract_gear(items):
    out = []
    for it in items:
        if it["type"] != "loot":
            continue
        sys = it["system"]
        out.append({
            "name": it["name"],
            "qty": sys.get("quantity",1),
            "description": sys.get("description","")
        })
    return out


def find_item_name(items, type_name):
    for it in items:
        if it["type"] == type_name:
            return it["name"]
    return ""


# ---------------------------------------------------------------------------
# Character Context
# ---------------------------------------------------------------------------

def extract_character_context(actor_json):
    name = actor_json["name"]
    system = actor_json["system"]
    items = actor_json["items"]

    ancestry_name = find_item_name(items, "ancestry")
    community_name = find_item_name(items, "community")
    class_name = find_item_name(items, "class")
    subclass_name = find_item_name(items, "subclass")

    return {
        "name": name,
        "img": actor_json.get("img",""),
        "heritage_name": ancestry_name,
        "community_name": community_name,
        "class_name": class_name,
        "subclass_name": subclass_name,

        "level": system["levelData"]["level"]["current"],
        "proficiency": system.get("proficiency",0),
        "evasion": system.get("evasion",0),
        "armor": system.get("armorScore",0),

        "hp_current": system["resources"]["hitPoints"]["value"],
        "hp_max": system["resources"]["hitPoints"]["max"],
        "stress_current": system["resources"]["stress"]["value"],
        "stress_max": system["resources"]["stress"]["max"],
        "hope_current": system["resources"]["hope"]["value"],
        "hope_max": system["resources"]["hope"]["max"],

        "traits": extract_traits(system),
        "thresholds": {
            "major": system["damageThresholds"]["major"],
            "severe": system["damageThresholds"]["severe"]
        },
        "resistances": {
            "physical": "Resist" if system["resistance"]["physical"]["resistance"] else "—",
            "magical": "Resist" if system["resistance"]["magical"]["resistance"] else "—"
        },
        "gold": system["gold"],

        "experiences": extract_experiences(system),
        "features": extract_features(items),
        "domain_cards": extract_domain_cards(items),
        "weapons": extract_weapons(items),
        "armor_items": extract_armor(items),
        "consumables": extract_consumables(items),
        "gear": extract_gear(items),

        "biography": system["biography"].get("background","")
    }


# ---------------------------------------------------------------------------
# Render One File
# ---------------------------------------------------------------------------

def render_character_html(actor_path, template, output_dir):
    with open(actor_path, "r", encoding="utf-8") as f:
        actor = json.load(f)

    ctx = extract_character_context(actor)
    slug = slugify(ctx["name"])

    html = template.render(**ctx)

    out_path = Path(output_dir) / f"{slug}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"[OK] {actor_path} → {out_path}")


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate character HTML pages from Foundry JSON exports.")
    parser.add_argument("input", help="JSON file or folder containing JSON files")

    parser.add_argument("--template-dir", default="templates", help="Directory containing Jinja2 templates")
    parser.add_argument("--template", default="character_sheet.html.j2", help="Template file name or full template path")
    parser.add_argument("--output-dir", default="docs/characters", help="Output directory")

    args = parser.parse_args()

    # ----------------------------------------------------------------------
    # Improved template resolution (supports full paths)
    # ----------------------------------------------------------------------
    template_path = Path(args.template)

    if template_path.is_file():
        # Full path provided → override template_dir
        template_dir = template_path.parent
        template_name = template_path.name
    else:
        # Use template_dir + template_name
        template_dir = Path(args.template_dir)
        template_name = args.template

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template(template_name)

    # ----------------------------------------------------------------------
    # Input: single file or folder
    # ----------------------------------------------------------------------
    input_path = Path(args.input)

    if input_path.is_file():
        render_character_html(input_path, template, args.output_dir)

    elif input_path.is_dir():
        files = sorted(list(input_path.glob("*.json")))
        if not files:
            print(f"No JSON files found in {input_path}")
            return
        for f in files:
            render_character_html(f, template, args.output_dir)

    else:
        print(f"Input path does not exist: {input_path}")


if __name__ == "__main__":
    main()
