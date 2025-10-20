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

# Color scheme mapping from your spec
EFFECT_PALETTE = {
    "healing": "warm red–orange to amber",
    "stress": "soft violet-blue to lavender",
    "physical": "cyan–teal to electric blue",
    "strength": "amber-gold to bronze",
    "cognitive": "neon green to lime-white",
    "charisma": "neon green to lime-white",
    "armor": "any colors that articles of clothing might have, but tending toward steel grey to leather brown",
    "loot": "use the description field to infer a color scheme for the item"

}

STYLE = (
    "cyberpunk item icon, semi-realistic rendering, metallic/glass materials, "
    "clean silhouette, soft reflections, subtle vignette, NO text or labels, "
    "light grey background, consistent luminance"
)


def build_prompt(name: str, description: str, effect: str) -> str:
    palette = EFFECT_PALETTE.get((effect or "").lower().strip(), "cyan–teal to electric blue")
    return f"{name}: {description}. Color scheme: {palette}. Style: {STYLE}."


def b64png_to_webp(b64_png: str, out_path: Path) -> None:
    img = Image.open(BytesIO(base64.b64decode(b64_png))).convert("RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", method=6, quality=95)


def load_items(json_path: Path, name_key: str, desc_key: str, effect_key: str, img_key: str) -> List[Dict[str, Any]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of objects or an object with an 'items' list.")

    items = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        name = str(obj.get(name_key, "")).strip()
        if not name:
            continue
        desc = str(obj.get(desc_key, "")).strip()
        eff = str(obj.get(effect_key, "")).strip()
        img = str(obj.get(img_key, "")).strip()
        items.append({name_key: name, desc_key: desc, effect_key: eff, img_key: img})
    return items


def main():
    parser = argparse.ArgumentParser(description="Batch-generate Cybermancy item icons via OpenAI Images API.")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Path to input JSON file.")
    parser.add_argument("--outdir", "-o", required=True, type=Path, help="Output directory for .webp files.")
    parser.add_argument("--model", default="gpt-image-1", help="OpenAI image model (e.g., gpt-image-1 or gpt-image-1-mini).")
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
