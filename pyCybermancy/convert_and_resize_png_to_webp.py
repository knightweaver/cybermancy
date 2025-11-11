#!/usr/bin/env python3
# convert_and_resize_images.py
#
# Usage:
#   python convert_and_resize_images.py "E:\path\to\folder" --width 400 --height 400 --dpi 96 --input-type webp
#   (add --recursive to include subfolders)
#
# Notes:
# - Files are overwritten in-place: each *.png or *.webp is re-saved to <same name>.webp after resizing.
# - WebP doesn’t have a universal DPI tag; Pillow accepts `dpi=(x,y)`, but many tools ignore it.
# - Requires: pip install pillow

import argparse
from pathlib import Path
from PIL import Image
import os
import sys


def convert_one(img_path: Path, out_w: int, out_h: int, dpi: int, quality: int, lossless: bool):
    """Resize and (re)save a PNG or WEBP image to WebP format."""
    with Image.open(img_path) as im:
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")

        im = im.resize((out_w, out_h), Image.LANCZOS)
        webp_path = img_path.with_suffix(".webp")

        params = {
            "format": "WEBP",
            "quality": quality,
            "method": 6,
            "lossless": lossless,
            "dpi": (dpi, dpi),
        }
        im.save(webp_path, **params)

    # remove original if different extension
    if img_path.suffix.lower() != ".webp":
        try:
            os.remove(img_path)
        except OSError as e:
            print(f"Warning: could not delete {img_path}: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(
        description="Resize all PNG or WEBP images in a folder and convert to .webp (replacing originals)."
    )
    ap.add_argument("folder", type=Path, help="Folder containing images")
    ap.add_argument("--width", "-W", type=int, required=True, help="Target width in pixels")
    ap.add_argument("--height", "-H", type=int, required=True, help="Target height in pixels")
    ap.add_argument("--dpi", type=int, default=96, help="Target DPI metadata (may be ignored by some tools)")
    ap.add_argument("--recursive", "-r", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--quality", "-q", type=int, default=90, help="WEBP quality (0-100, ignored if --lossless)")
    ap.add_argument("--lossless", action="store_true", help="Use lossless WebP output")
    ap.add_argument(
        "--input-type",
        choices=["png", "webp"],
        default="png",
        help="Specify which image type to process (default: png)",
    )
    args = ap.parse_args()

    if not args.folder.exists() or not args.folder.is_dir():
        ap.error(f"Folder not found: {args.folder}")

    pattern = f"**/*.{args.input_type}" if args.recursive else f"*.{args.input_type}"
    images = list(args.folder.glob(pattern))
    if not images:
        print(f"No {args.input_type.upper()} files found.")
        return

    for img_path in images:
        try:
            convert_one(img_path, args.width, args.height, args.dpi, args.quality, args.lossless)
            print(f"Resized: {img_path}")
        except Exception as e:
            print(f"Error processing {img_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
