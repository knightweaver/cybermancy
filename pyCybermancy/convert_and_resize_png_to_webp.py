# convert_png_folder_to_webp.py
# Usage:
#   python convert_png_folder_to_webp.py "E:\path\to\folder" --width 400 --height 400 --dpi 96
#   (add --recursive to include subfolders)
#
# Notes:
# - Files are overwritten in-place: each *.png becomes <same name>.webp and the PNG is deleted.
# - WebP doesn’t have a universal DPI tag; Pillow accepts `dpi=(x,y)`, but many tools ignore it.
# - Requires: pip install pillow

import argparse
from pathlib import Path
from PIL import Image
import os
import sys

def convert_one(png_path: Path, out_w: int, out_h: int, dpi: int, quality: int, lossless: bool):
    # Open and ensure an RGB(A) mode that WebP supports
    with Image.open(png_path) as im:
        # Convert paletted/LA/etc. to RGBA to preserve transparency cleanly
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")

        # Resize to exact target size (no aspect preservation by design)
        im = im.resize((out_w, out_h), Image.LANCZOS)

        webp_path = png_path.with_suffix(".webp")
        params = {
            "format": "WEBP",
            "quality": quality,
            "method": 6,           # better compression effort
            "lossless": lossless,
            "dpi": (dpi, dpi),     # may be ignored by some readers
        }

        im.save(webp_path, **params)

    # Remove original PNG only after successful save
    try:
        os.remove(png_path)
    except OSError as e:
        print(f"Warning: could not delete {png_path}: {e}", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description="Resize all PNGs in a folder and convert to .webp (replacing originals).")
    ap.add_argument("folder", type=Path, help="Folder containing PNG images")
    ap.add_argument("--width", "-W", type=int, required=True, help="Target width in pixels")
    ap.add_argument("--height", "-H", type=int, required=True, help="Target height in pixels")
    ap.add_argument("--dpi", type=int, default=96, help="Target DPI metadata (may be ignored by some tools)")
    ap.add_argument("--recursive", "-r", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--quality", "-q", type=int, default=90, help="WEBP quality (0-100, ignored if --lossless)")
    ap.add_argument("--lossless", action="store_true", help="Use lossless WebP")
    args = ap.parse_args()

    if not args.folder.exists() or not args.folder.is_dir():
        ap.error(f"Folder not found: {args.folder}")

    pattern = "**/*.png" if args.recursive else "*.png"
    pngs = list(args.folder.glob(pattern))
    if not pngs:
        print("No PNG files found.")
        return

    for p in pngs:
        try:
            convert_one(p, args.width, args.height, args.dpi, args.quality, args.lossless)
            print(f"Converted: {p}")
        except Exception as e:
            print(f"Error converting {p}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
