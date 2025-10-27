#!/usr/bin/env python3
"""
Batch Cybermancy icon generator (CLI)
- Reads items from a JSON file (expects keys: name, description, effect, img).
- Generates one .webp per item via OpenAI Images API.
- Outputs individual .webp files (no zipping).

Dependencies:
  pip install openai pillow python-slugify python-dotenv
Env:
  OPENAI_API_KEY in .env or environment
"""

import os, json, base64, time, argparse, logging
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List
from PIL import Image
from slugify import slugify
from dotenv import load_dotenv
from openai import OpenAI
import csv

# Color scheme mapping from your spec
EFFECT_PALETTE = {
    "healing": "warm red–orange to amber",
    "stress": "soft violet-blue to lavender",
    "physical": "cyan–teal to electric blue",
    "strength": "amber-gold to bronze",
    "cognitive": "neon green to lime-white",
    "charisma": "neon green to lime-white",
    "armor": "any colors that articles of clothing might have, but tending toward steel grey to leather brown",
    "loot": "use the description field to infer a color scheme for the item",
    "circuit": "glowing circuitry motif, light grey background, neon blue and green accents",
    "weapons": "gunmetal grey with accents of electric cyan and molten red-orange",
    "corporate": "gunmetal and chrome with cold blue-white highlights",
    "military": "matte steel with amber-orange tracer glows",
    "prototype": "graphite and silver with lime-green or violet plasma lines",
    "street": "scratched chrome with graffiti teal and orange",
    "antique": "aged bronze and iron with faint amber and smoke-blue glow",
    "stealth": "matte black and charcoal with subtle purple or cyan pulse lines",
    "domain-bullet": "gunmetal and graphite base with fiery orange to ember-red glow and cyan tracer accents",
    "domain-maker": "titanium grey and steel blue base with amber-gold and teal glows, accented by warm white plasma highlights",
    # Classes
    "class-netrunner": "graphite base with cyan/teal code glow and subtle violet accents",
    "class-rigger": "steel/titanium base with teal (control links) and amber (power) highlights",
    "class-streetsamurai": "gunmetal and black carbon fiber base with crimson and steel-blue accents, faint amber weapon glow",

    # Netrunner Subclasses
    "subclass-ghost-in-the-machine": "cool cyan/teal and violet; human silhouette dissolving into circuits/data",
    "subclass-wrecking-ball": "gunmetal with high-contrast red-orange + electric blue ‘breach’ energy",

    # Rigger Subclasses
    "subclass-jack-of-all-trades": "titanium/steel-blue with balanced teal/amber utility glows (multi-drone toolkit)",
    "subclass-speed-racer": "graphite/carbon with teal/amber speed trails; hints of magenta for motion blur",

    # Street Samurai Subclasses
    "subclass-bodyguard": "matte black and brushed silver with crimson-gold defensive highlights; strong, grounded presence",
    "subclass-mercenary": "dark steel with burnt orange and neon red combat glows; tactical, ruthless, efficient",

    # Domains
    "domain-bullet": "gunmetal/graphite base with fiery orange→ember red glow and cyan tracer streaks",
    "domain-make": "titanium grey + steel blue with amber-gold forge glow and teal circuitry accents",
    "domain-circuit": "black/graphite vector iconography with cyan circuit lines (for SVG glyphs)"

}
# map common aliases (case/space-insensitive)
NAME_ALIASES = {"name","card_name","title","item","card"}
DESC_ALIASES = {"description","card_description","card_effect","effect_text","text","blurb"}
EFFECT_ALIASES = {"effect","domain","type","category"}
IMG_ALIASES = {"img","image","filename","file","icon"}

STYLE = (
    "Semi-realistic cyberpunk character emblem.",
    "Subclass images should borrow motifs from their class images.",
    "If the primary entity in the image is a character (netrunner, rigger, or street-samuri),The resulting image should not look like a robot, but should clearly be human, or at least human adjacent",
    "If the primary entity in the image is a drone, can look like a typical drone",
    "Larger canvas for detail (e.g. 800×800 px).",
    "High-fidelity materials: carbon fiber, alloy plating, glass, neon.",
    "Dynamic lighting: key + rim, warm/cool color contrast.",
    "Minimal background: soft vignette, light grey field.",
    "Readable at reduced scale, but richer detail than item icons.",
    "No text, no lettering, no UI framing.",
    "Clean edge discipline: no clutter beyond silhouette."
)
#STYLE = (
#    "cyberpunk item icon, semi-realistic rendering, metallic/glass materials, "
#    "clean silhouette, soft reflections, subtle vignette, NO text or labels, "
#    "light grey background, consistent luminance"
#)
#STYLE = (
#    "cyberpunk weapon icon, semi-realistic rendering, gunmetal and graphite materials,"
#    "clean silhouette, subtle reflections, light grey background, consistent luminance,"
#    "with glowing accents of electric cyan and molten red-orange to imply energy and power."
#)

def norm(s): return s.strip().lower().replace(" ", "") if isinstance(s, str) else ""

def build_prompt(name: str, description: str, effect: str) -> str:
    palette = EFFECT_PALETTE.get((effect or "").lower().strip(), "cyan–teal to electric blue")
    return f"{name}: {description}. Color scheme: {palette}. Style: {STYLE}."


def b64png_to_webp(b64_png: str, out_path: Path) -> None:
    img = Image.open(BytesIO(base64.b64decode(b64_png))).convert("RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", method=6, quality=95)

def find_col(columns, preferred, aliases):
    """Return the column name to use: prefer --*-key, else best alias match."""
    cols_norm = {norm(c): c for c in columns}
    # prefer the exact provided key
    if preferred and norm(preferred) in cols_norm:
        return cols_norm[norm(preferred)]
    # try aliases
    for a in aliases:
        if a in cols_norm:
            return cols_norm[a]
    return None

def load_items(path: Path, name_key: str, desc_key: str, effect_key: str, img_key: str):
    # JSON path?
    if path.suffix.lower() in {".json"}:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            data = data["items"]
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list or an object with an 'items' list.")
        # ensure fields exist (empty if missing)
        items = []
        for obj in data:
            if isinstance(obj, dict):
                items.append({
                    name_key: str(obj.get(name_key, "")).strip(),
                    desc_key: str(obj.get(desc_key, "")).strip(),
                    effect_key: str(obj.get(effect_key, "")).strip(),
                    img_key: str(obj.get(img_key, "")).strip(),
                })
        return items

    # CSV path?
    if path.suffix.lower() in {".csv"}:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            # resolve columns (prefer explicit keys passed on CLI; else aliases)
            name_col   = find_col(cols, name_key,   NAME_ALIASES)
            desc_col   = find_col(cols, desc_key,   DESC_ALIASES)
            effect_col = find_col(cols, effect_key, EFFECT_ALIASES)
            img_col    = find_col(cols, img_key,    IMG_ALIASES)

            if not name_col:
                raise ValueError(f"Could not resolve name column. Passed '{name_key}', available: {cols}")
            if not desc_col:
                raise ValueError(f"Could not resolve description column. Passed '{desc_key}', available: {cols}")
            if not effect_col:
                raise ValueError(f"Could not resolve effect column. Passed '{effect_key}', available: {cols}")
            # img is optional; if missing, we'll slugify the name later
            items = []
            for row in reader:
                items.append({
                    name_key:   str(row.get(name_col, "")).strip(),
                    desc_key:   str(row.get(desc_col, "")).strip(),
                    effect_key: str(row.get(effect_col, "")).strip(),
                    img_key:    str(row.get(img_col, "")).strip() if img_col else "",
                })
            return items

    raise ValueError(f"Unsupported input type: {path.suffix} (use .json or .csv)")

def main():
    parser = argparse.ArgumentParser(description="Batch-generate Cybermancy item icons via OpenAI Images API.")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Path to input JSON file.")
    parser.add_argument("--outdir", "-o", required=True, type=Path, help="Output directory for .webp files.")
    parser.add_argument("--model", default="gpt-image-1-mini", help="OpenAI image model (e.g., gpt-image-1 or gpt-image-1-mini).")
    parser.add_argument("--size", default="1024x1024", help="Image size, e.g., Supported values are: '1024x1024', '1024x1536', '1536x1024', and 'auto'.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay (s) between requests to avoid rate limits.")
    parser.add_argument("--max-items", type=int, default=0, help="Optional cap on number of items to render (0 = all).")
    parser.add_argument("--seed", type=int, default=None, help="Optional generation seed if supported.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument("--name-key", default="name", help="Key for item name in JSON.")
    parser.add_argument("--desc-key", default="description", help="Key for item description in JSON.")
    parser.add_argument("--effect-key", default="effect", help="Key for item effect in JSON.")
    parser.add_argument("--img-key", default="img", help="Key for image filename in JSON.")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR).")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY (set in environment or .env)")

    client = OpenAI(api_key=api_key)

    items = load_items(args.input, args.name_key, args.desc_key, args.effect_key, args.img_key)
    if args.max_items and args.max_items > 0:
        items = items[:args.max_items]

    logging.info(f"Loaded {len(items)} items from {args.input}")
    args.outdir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for idx, item in enumerate(items, 1):
        name = item[args.name_key]
        desc = item[args.desc_key]
        effect = item[args.effect_key]
        img_name = item.get(args.img_key, "").strip()

        prompt = build_prompt(name, desc, effect)

        # use img field if present, otherwise slugify name
        fname = slugify(img_name) if img_name else slugify(name)
        if not fname.lower().endswith(".webp"):
            fname += ".webp"
        out_path = args.outdir / fname

        if out_path.exists() and not args.overwrite:
            logging.info(f"[{idx}/{len(items)}] SKIP exists: {fname}")
            continue

        try:
            kwargs = dict(model=args.model, prompt=prompt, size=args.size)
            if args.seed is not None:
                kwargs["seed"] = args.seed

            resp = client.images.generate(**kwargs)
            b64 = resp.data[0].b64_json
            b64png_to_webp(b64, out_path)
            logging.info(f"[{idx}/{len(items)}] WROTE {out_path.name}")
            generated += 1
            time.sleep(args.delay)
        except Exception as e:
            logging.error(f"[{idx}/{len(items)}] FAILED {name}: {e}")

    logging.info(f"Done. Generated {generated} file(s) into: {args.outdir}")


if __name__ == "__main__":
    main()
