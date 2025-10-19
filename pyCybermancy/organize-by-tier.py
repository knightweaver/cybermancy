#!/usr/bin/env python3
"""
organize_by_tier.py
Move Cybermancy item JSON files into subfolders by tier.

- Reads "tier" from either item["system"]["tier"] (preferred) or item["tier"].
- Creates subfolders like: <root>/tier-1/, <root>/tier-2/, ... (customizable with --format).
- Skips files missing a numeric tier (unless --unknown-dir is provided).
- Safe by default: errors are reported and the script continues.

Usage:
  python organize_by_tier.py /path/to/items
  python organize_by_tier.py /path/to/items --format "Tier-{tier}" --unknown-dir "_unknown" --dry-run
"""

from __future__ import annotations
import argparse, json, sys, shutil
from pathlib import Path
from typing import Optional

def get_tier(p: Path) -> Optional[int]:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    # Prefer system.tier, fall back to top-level tier
    tier = None
    if isinstance(data, dict):
        sysobj = data.get("system") or {}
        tier = sysobj.get("tier", data.get("tier"))
    # Coerce to int if possible
    try:
        return int(tier)
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser(description="Organize Cybermancy JSON items by tier.")
    ap.add_argument("root", help="Folder containing JSON item files")
    ap.add_argument("--glob", default="*.json", help="Glob for item files relative to root (default: *.json)")
    ap.add_argument("--format", default="tier-{tier}", help='Subfolder naming format (default: "tier-{tier}")')
    ap.add_argument("--unknown-dir", default=None, help="If set, files without a numeric tier go here (subfolder name)")
    ap.add_argument("--dry-run", action="store_true", help="Show planned moves without changing files")
    ap.add_argument("--verbose", action="store_true", help="Print each move")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    files = sorted(root.glob(args.glob))
    if not files:
        print("No files matched.", file=sys.stderr)
        return

    moved, skipped, errors = 0, 0, 0
    for f in files:
        if not f.is_file():
            continue
        tier = get_tier(f)
        if tier is None:
            if args.unknown_dir:
                sub = root / args.unknown_dir
            else:
                skipped += 1
                if args.verbose:
                    print(f"skip (no tier): {f.name}")
                continue
        else:
            sub = root / args.format.format(tier=tier)

        try:
            sub.mkdir(parents=True, exist_ok=True)
            dest = sub / f.name
            if args.dry_run:
                if args.verbose:
                    print(f"would move: {f} -> {dest}")
            else:
                shutil.move(str(f), str(dest))
                if args.verbose:
                    print(f"moved: {f.name} -> {sub.name}/")
                moved += 1
        except Exception as e:
            errors += 1
            print(f"error moving {f}: {e}", file=sys.stderr)

    print(f"Done. moved={moved} skipped={skipped} errors={errors}")

if __name__ == "__main__":
    main()
