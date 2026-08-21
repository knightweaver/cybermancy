#!/usr/bin/env python3
"""
Simple batch logo generator for Cybermancy corporations.

Expected CSV columns:
- name   : used for filename
- style  : optional, appended to prompt context
- prompt : full base prompt text

Usage examples:
  python3 batch-logo-gen.py -i corp_logos.csv -o out/
  python3 batch-logo-gen.py -i corp_logos.csv -o out/ --model gpt-image-1-mini --size 1024x1024 --format webp

Env:
  OPENAI_API_KEY must be set.
Deps:
  pip install openai pillow python-slugify python-dotenv
"""

import os
import csv
import base64
import argparse
import logging
from io import BytesIO
from pathlib import Path

from PIL import Image
from slugify import slugify
from dotenv import load_dotenv
from openai import OpenAI


def slugify_safe(s: str) -> str:
    s = slugify(s or "").strip("-")
    return s or "logo"


def save_image(b64_data: str, out_path: Path, fmt: str) -> None:
    img = Image.open(BytesIO(base64.b64decode(b64_data))).convert("RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fmt_upper = fmt.upper()
    if fmt_upper == "WEBP":
        img.save(out_path, "WEBP", method=6, quality=95)
    elif fmt_upper in ("PNG", "JPG", "JPEG"):
        if fmt_upper in ("JPG", "JPEG"):
            img = img.convert("RGB")
            img.save(out_path, "JPEG", quality=95)
        else:
            img.save(out_path, fmt_upper)
    else:
        raise ValueError(f"Unsupported output format: {fmt}")


def build_prompt(row: dict) -> str:
    name = (row.get("name") or "").strip()
    style = (row.get("style") or "").strip()
    base_prompt = (row.get("prompt") or "").strip()

    # Minimal composition: CSV prompt is authoritative; style is optional flavor.
    if style:
        return f"{base_prompt} Style hint: {style}."
    if name and base_prompt:
        return f"{base_prompt} This is the logo for {name}."
    return base_prompt or f"corporate logo for {name} on a light grey background."


def main():
    parser = argparse.ArgumentParser(description="Simple batch logo generator for Cybermancy corporations.")
    parser.add_argument("-i", "--input", required=True, type=Path, help="Input CSV file.")
    parser.add_argument("-o", "--outdir", required=True, type=Path, help="Output directory.")
    parser.add_argument("--model", default="gpt-image-1-mini", help="OpenAI image model to use.")
    parser.add_argument("--size", default="1024x1024", help="Image size, e.g. 512x512 or 1024x1024.")
    parser.add_argument(
        "--format",
        default="webp",
        choices=["webp", "png", "jpg", "jpeg"],
        help="Output image format.",
    )
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between requests in seconds.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--max-items", type=int, default=0, help="Limit number of rows processed (0 = all).")
    parser.add_argument("--log-level", default="INFO", help="Logging level.")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    with args.input.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if args.max_items and args.max_items > 0:
        rows = rows[: args.max_items]

    args.outdir.mkdir(parents=True, exist_ok=True)
    fmt = args.format.lower()
    generated = 0

    for idx, row in enumerate(rows, start=1):
        name = (row.get("name") or f"row-{idx}").strip()
        prompt = build_prompt(row)

        fname_base = slugify_safe(name)
        out_path = args.outdir / f"{fname_base}.{fmt}"

        if out_path.exists() and not args.overwrite:
            logging.info(f"[{idx}/{len(rows)}] SKIP exists: {out_path.name}")
            continue

        try:
            req = {
                "model": args.model,
                "prompt": prompt,
                "size": args.size,
            }
            resp = client.images.generate(**req)
            b64 = resp.data[0].b64_json
            save_image(b64, out_path, fmt)
            logging.info(f"[{idx}/{len(rows)}] WROTE {out_path.name}")
            generated += 1
        except Exception as e:
            logging.error(f"[{idx}/{len(rows)}] FAILED {name}: {e}")

    logging.info(f"Done. Generated {generated} logo(s) into {args.outdir}")


if __name__ == "__main__":
    main()
