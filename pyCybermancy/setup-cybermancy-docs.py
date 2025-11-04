#!/usr/bin/env python3
"""
Create the Cybermancy docs-friendly repo skeleton with player-facing and GM-facing docs.

Usage:
  python setup_cybermancy_docs.py
  python setup_cybermancy_docs.py --project-name cybermancy --base-dir "D:/Projects"
"""

from pathlib import Path
import argparse
from typing import Iterable, Tuple

PLAYER_ITEMS = [
    "ammo", "armors", "consumables", "cybernetics", "drones-devices",
    "loot", "mods", "weapons"
]
SYSTEM_SECTIONS = ["classes", "domains", "features", "subclasses"]
ADVENTURE_SECTIONS = ["adversaries", "environments"]

def mkd(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def mkmd(p: Path, title: str) -> None:
    if not p.exists():
        p.write_text(f"# {title}\n", encoding="utf-8")

def create_tree(base: Path) -> None:
    # core
    mkd(base)
    mkd(base / "src" / "packs")
    mkd(base / "assets")
    mkd(base / "docs")

    # src/packs/items/*
    for d in PLAYER_ITEMS:
        mkd(base / "src" / "packs" / "items" / d)

    # src/packs/system/*
    for d in SYSTEM_SECTIONS:
        mkd(base / "src" / "packs" / "system" / d)

    # src/packs/adventure/*
    for d in ADVENTURE_SECTIONS:
        mkd(base / "src" / "packs" / "adventure" / d)

    # docs/player-facing
    mkd(base / "docs" / "player-facing")
    mkmd(base / "docs" / "player-facing" / "index.md", "Cybermancy — Player Guide")

    mkd(base / "docs" / "player-facing" / "world")
    mkmd(base / "docs" / "player-facing" / "world" / "player-visible-info-on-the-council.md",
         "The Council (Player-visible)")
    mkmd(base / "docs" / "player-facing" / "world" / "player-visible-info-on-the-cabal.md",
         "The Cabal (Player-visible)")
    mkmd(base / "docs" / "player-facing" / "world" / "player-visible-info-on-timeline.md",
         "Timeline (Player-visible)")

    mkd(base / "docs" / "player-facing" / "items")
    for name in PLAYER_ITEMS:
        mkmd(base / "docs" / "player-facing" / "items" / f"{name}.md", name)

    mkd(base / "docs" / "player-facing" / "system")
    for name in SYSTEM_SECTIONS:
        mkmd(base / "docs" / "player-facing" / "system" / f"{name}.md", name)

    # docs/gm-facing
    mkd(base / "docs" / "gm-facing")
    mkmd(base / "docs" / "gm-facing" / "index.md", "Cybermancy — GM Guide")

    mkd(base / "docs" / "gm-facing" / "world")
    mkmd(base / "docs" / "gm-facing" / "world" / "the-council.md", "The Council")
    mkmd(base / "docs" / "gm-facing" / "world" / "the-council-projects.md", "The Council — Projects")
    mkmd(base / "docs" / "gm-facing" / "world" / "the-cabal.md", "The Cabal")
    mkmd(base / "docs" / "gm-facing" / "world" / "the-cabal-projects.md", "The Cabal — Projects")
    mkmd(base / "docs" / "gm-facing" / "world" / "timeline.md", "Timeline")

    mkd(base / "docs" / "gm-facing" / "items")
    for name in PLAYER_ITEMS:
        mkmd(base / "docs" / "gm-facing" / "items" / f"{name}.md", name)

    mkd(base / "docs" / "gm-facing" / "adventures")
    mkmd(base / "docs" / "gm-facing" / "adventures" / "adversaries.md", "Adversaries")
    mkmd(base / "docs" / "gm-facing" / "adventures" / "npc-actors.md", "NPC Actors")
    mkmd(base / "docs" / "gm-facing" / "adventures" / "environments.md", "Environments")

    mkd(base / "docs" / "gm-facing" / "meta")
    mkmd(base / "docs" / "gm-facing" / "meta" / "etl-pipeline.md", "ETL Pipeline")
    mkmd(base / "docs" / "gm-facing" / "meta" / "visual-canon.md", "Visual Canon")

def main() -> None:
    ap = argparse.ArgumentParser(description="Create Cybermancy docs folder/file structure.")
    ap.add_argument("--project-name", default="cybermancy",
                    help="Top-level project folder name to create (default: cybermancy)")
    ap.add_argument("--base-dir", default=".", help="Directory in which to create the project folder")
    args = ap.parse_args()

    target = Path(args.base_dir).expanduser().resolve() / args.project_name
    create_tree(target)

    print(f"✅ Created/updated structure at: {target}")
    print("Next:")
    print(" - Add mkdocs.player.yml and mkdocs.gm.yml at repo root")
    print(" - Add GitHub Actions workflow to publish /player and /gm")

if __name__ == "__main__":
    main()
