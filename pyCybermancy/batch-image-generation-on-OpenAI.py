#!/usr/bin/env python3
"""
Batch Cybermancy icon generator (CLI)
- Reads items from JSON or CSV.
- CSV should include: name, description, effect, img (optional), style (new), organ (for cybernetics).
- Per-row 'style' selects a visual style preset; 'effect' still maps to EFFECT_PALETTE.

Dependencies:
  pip install openai pillow python-slugify python-dotenv
Env:
  OPENAI_API_KEY in .env or environment
"""

import os, json, base64, time, argparse, logging, csv, re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any
from PIL import Image
from slugify import slugify
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# Color scheme / effect palette
# -----------------------------
EFFECT_PALETTE: Dict[str, str] = {
    "healing": "warm red–orange to amber",
    "stress": "soft violet-blue to lavender",
    "physical": "cyan–teal to electric blue",
    "strength": "amber-gold to bronze",
    "cognitive": "neon green to lime-white",
    "charisma": "neon green to lime-white",
    "armor": "steel grey to leather brown (realistic textile/leather tones)",
    "loot": "infer from description; accent with metallics appropriate to the object",
    "circuit": "glowing circuitry motif, light grey background, neon blue and green accents",
    "weapons": "gunmetal grey with accents of electric cyan and molten red-orange",
    "corporate": "gunmetal and chrome with cold blue-white highlights",
    "military": "matte steel with amber-orange tracer glows",
    "prototype": "graphite and silver with lime-green or violet plasma lines",
    "street": "scratched chrome with graffiti teal and orange",
    "antique": "aged bronze and iron with faint amber and smoke-blue glow",
    "stealth": "matte black and charcoal with subtle purple or cyan pulse lines",
    "cybernetic": "metallic organ implants integrated into skin; accent glow matches enhancement type",
    "programs": "graphite/black vector iconography with cyan circuit lines (glyph-like, minimal)",
    # Domains / classes (optional, use as styles or effects)
    "domain-bullet": "gunmetal & graphite base, ember-red glow with cyan tracer accents",
    "domain-maker": "titanium grey & steel blue, amber-gold + teal forge/circuit accents",
    "domain-circuit": "graphite + cyan/teal circuitry on light grey",
    "class-netrunner": "graphite base with cyan/teal code glow and subtle violet accents",
    "class-rigger": "steel/titanium with teal (control links) and amber (power) highlights",
    "class-streetsamurai": "gunmetal & carbon fiber with crimson and steel-blue accents",
}

# -----------------------------
# Style presets (chosen by CSV 'style' column)
# -----------------------------
STYLE_PRESETS: Dict[str, str] = {
    # Generic buckets
    "item": (
        "cyberpunk item icon, semi-realistic rendering, metallic/glass materials, "
        "clean silhouette, soft reflections, subtle vignette, NO text or labels, "
        "light grey background, consistent luminance"
    ),
    "weapon": (
        "cyberpunk weapon icon, semi-realistic rendering, gunmetal/graphite materials, "
        "clean silhouette, subtle reflections, medium grey background, consistent luminance; "
        "imply energy/power with restrained glows"
    ),
    "program": (
        "minimalist glyph-like icon (software/program), vector feel, crisp edges, "
        "graphite/black base with neon circuitry accents, light grey background, no text"
    ),
    "cybernetic": (
        "graphic, semi-abstract cybernetics panel; minimal human depiction (silhouette or partial overlay), "
        "clean light-grey background, crisp edges, layered shapes, glowing accent lines, vector-like clarity; "
        "no photoreal face, no busy HUD/text"
    ),
    "ice": (
        "Cybermancy style: semi-abstract cyberpunk concept art of Intrusion Countermeasures Electronics (ICE). "
        "minimalist glyph-like icon (software/program), vector feel, crisp edges, "
        "pulses of neon blue and white light, and fractal lattice patterns implying code and control. "
        "black/graphite with cyan/teal circuits; clean vector on a dark background"
        "Rendered as a semi-abstract icon on a dark background, metallic and glasslike materials, consistent with Cybermancy item icons. "
        "Do not include text, borders, or characters—focus on abstract technological form and energy."
    ),
    # Optional specific “tones” you can use directly in CSV
    "class-netrunner": "netrunner emblem; graphite base, cyan/teal code glow, subtle violet; clean, iconic on light grey",
    "class-rigger": "rigger emblem; steel/titanium, teal control links + amber power highlights; iconic on light grey",
    "class-streetsamurai": "street samurai emblem; carbon fiber + gunmetal, crimson/steel-blue accents; iconic on light grey",
    "domain-circuit": "domain icon; black/graphite with cyan/teal circuits; clean vector on light grey",
    "domain-bullet": "domain icon; gunmetal/graphite with ember red + cyan tracers; clean vector on light grey",
    "domain-maker": "domain icon; titanium/steel-blue with amber/teal forge/circuit glows; light grey"
}

# Column aliases (CSV headers can vary)
NAME_ALIASES = {"name","card_name","title","item","card"}
DESC_ALIASES = {"description","card_description","card_effect","effect_text","text","blurb"}
EFFECT_ALIASES = {"effect","domain","type","category"}
IMG_ALIASES = {"img","image","filename","file","icon"}
STYLE_ALIASES = {"style","visual_style","art_style"}
ORGAN_ALIASES = {"organ","body_part","cyber_organ"}

# Organ → prompt focus (cybernetics only)
ORGAN_FOCUS = {
    "eye": "close-up portrait; one cybernetic eye prominently integrated",
    "arm": "upper torso with cybernetic arm extended in a dynamic pose",
    "hand": "close-up of cybernetic hand with splayed fingers",
    "legs": "mid or full-body with cybernetic legs visible",
    "spinal": "rear three-quarter angle showing spinal interface plating",
    "skin": "mid-torso showing synthetic skin seams and glow-lines",
    "vocal chords": "neck/throat close-up with visible vocal emitters",
    "bones": "cutaway showing reinforced skeletal elements",
    "nervous system": "cutaway with neural pathways illuminated",
    "brain": "skull close-up with cross-section of implanted cortex hardware"
}

def norm(s:str) -> str:
    return s.strip().lower().replace(" ","") if isinstance(s,str) else ""

def find_col(columns: List[str], preferred: str, aliases: set) -> str:
    cols_norm = {norm(c): c for c in columns}
    if preferred and norm(preferred) in cols_norm:
        return cols_norm[norm(preferred)]
    for a in aliases:
        if a in cols_norm:
            return cols_norm[a]
    return ""

def slugify_safe(s: str) -> str:
    return slugify(s or "").strip("-") or "untitled"

def select_style_text(style_token: str) -> str:
    token = (style_token or "").strip().lower()
    if token in STYLE_PRESETS:
        return STYLE_PRESETS[token]
    # allow passing effect-like keys as styles too (e.g., "class-netrunner", "domain-circuit")
    if token in EFFECT_PALETTE:
        return f"icon styled for '{token}'; " + EFFECT_PALETTE[token] + "; light grey background; clean silhouette"
    # fallback
    return STYLE_PRESETS["item"]

def select_palette_text(effect_token: str) -> str:
    key = (effect_token or "").strip().lower()
    return EFFECT_PALETTE.get(key, "cyan–teal to electric blue accents on a light grey background")

def build_prompt(name: str, description: str, effect: str, organ: str, style_token: str) -> str:
    """Compose the final prompt using row style + effect palette. Cybernetics get organ focus."""
    style_text = select_style_text(style_token)
    palette = select_palette_text(effect)
    organ_key = (organ or "").strip().lower()
    organ_focus = ORGAN_FOCUS.get(organ_key, "Depict the subject in isolation as a product render.")

    # Cybernetics use different guidance
    if (style_token or "").strip().lower() == "cybernetic" or (effect or "").strip().lower() == "cybernetic":
        focus_phrase = (
            "Depict the augmentation on a human subject (silhouette/partial overlay), "
            "with realistic anatomical integration: seams, cabling, alloy under skin. "
            f"Focal guidance: {organ_focus}."
        )
    else:
        focus_phrase = "Depict the subject in isolation as a premium product render."

    return (
        f"Generate an image for '{name}'. "
        f"Description: {description} "
        f"Style: {style_text}. "
        f"Color & glow accents guided by palette: {palette}. "
        f"{focus_phrase} "
        "Readable at 400×400 icon scale; high-fidelity materials and edges."
    )

def b64png_to_webp(b64_png: str, out_path: Path) -> None:
    img = Image.open(BytesIO(base64.b64decode(b64_png))).convert("RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", method=6, quality=95)

def load_items(path: Path, name_key: str, desc_key: str, effect_key: str, img_key: str, style_key: str, organ_key: str) -> List[Dict[str,str]]:
    # JSON input
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            data = data["items"]
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list or an object with an 'items' list.")
        items = []
        for obj in data:
            if isinstance(obj, dict):
                items.append({
                    name_key:   str(obj.get(name_key, "")).strip(),
                    desc_key:   str(obj.get(desc_key, "")).strip(),
                    effect_key: str(obj.get(effect_key, "")).strip(),
                    img_key:    str(obj.get(img_key, "")).strip(),
                    style_key:  str(obj.get(style_key, "")).strip(),
                    organ_key:  str(obj.get(organ_key, "")).strip(),
                })
        return items

    # CSV input
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            name_col   = find_col(cols, name_key,   NAME_ALIASES)
            desc_col   = find_col(cols, desc_key,   DESC_ALIASES)
            effect_col = find_col(cols, effect_key, EFFECT_ALIASES)
            img_col    = find_col(cols, img_key,    IMG_ALIASES)
            style_col  = find_col(cols, style_key,  STYLE_ALIASES)
            organ_col  = find_col(cols, organ_key,  ORGAN_ALIASES)
            if not name_col or not desc_col or not effect_col:
                raise ValueError(f"Missing required columns. Found: {cols}")
            items = []
            for row in reader:
                items.append({
                    name_key:   str(row.get(name_col, "")).strip(),
                    desc_key:   str(row.get(desc_col, "")).strip(),
                    effect_key: str(row.get(effect_col, "")).strip(),
                    img_key:    str(row.get(img_col, "")).strip() if img_col else "",
                    style_key:  str(row.get(style_col, "")).strip(),
                    organ_key:  str(row.get(organ_col, "")).strip(),
                })
            return items

    raise ValueError(f"Unsupported input: {path.suffix} (use .json or .csv)")

def main():
    parser = argparse.ArgumentParser(description="Batch-generate Cybermancy icons via OpenAI Images API (per-row styles).")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Path to input CSV or JSON.")
    parser.add_argument("--outdir", "-o", required=True, type=Path, help="Output directory for .webp files.")
    parser.add_argument("--model", default="gpt-image-1-mini", help="Image model.")
    parser.add_argument("--size", default="1024x1024", help="Image size (e.g., 1024x1024).")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests.")
    parser.add_argument("--max-items", type=int, default=0, help="0 = all.")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    # column keys
    parser.add_argument("--name-key",  default="name")
    parser.add_argument("--desc-key",  default="description")
    parser.add_argument("--effect-key",default="effect")
    parser.add_argument("--img-key",   default="img")
    parser.add_argument("--style-key", default="style")
    parser.add_argument("--organ-key", default="organ")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)

    items = load_items(args.input, args.name_key, args.desc_key, args.effect_key, args.img_key, args.style_key, args.organ_key)
    if args.max_items and args.max_items > 0:
        items = items[:args.max_items]

    logging.info(f"Loaded {len(items)} items from {args.input}")
    args.outdir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for idx, item in enumerate(items, 1):
        name   = item.get(args.name_key, "")
        desc   = item.get(args.desc_key, "")
        effect = item.get(args.effect_key, "")
        style  = item.get(args.style_key, "")
        organ  = item.get(args.organ_key, "")
        img_in = (item.get(args.img_key, "") or "").strip()

        prompt = build_prompt(name, desc, effect, organ, style)

        fname = slugify_safe(img_in or name)
        if not fname.lower().endswith(".webp"): fname += ".webp"
        out_path = args.outdir / fname

        if out_path.exists() and not args.overwrite:
            logging.info(f"[{idx}/{len(items)}] SKIP exists: {out_path.name}")
            continue

        try:
            req = dict(model=args.model, prompt=prompt, size=args.size)
            if args.seed is not None: req["seed"] = args.seed
            resp = client.images.generate(**req)
            b64 = resp.data[0].b64_json
            b64png_to_webp(b64, out_path)
            logging.info(f"[{idx}/{len(items)}] WROTE {out_path.name}")
            generated += 1
            time.sleep(args.delay)
        except Exception as e:
            logging.error(f"[{idx}/{len(items)}] FAILED {name}: {e}")

    logging.info(f"Done. Generated {generated} files into: {args.outdir}")

if __name__ == "__main__":
    main()
