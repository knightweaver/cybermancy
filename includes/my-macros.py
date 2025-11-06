# my-macromy-macros.py
from csv import DictReader
from pathlib import Path

def define_env(env):

    @env.macro
    def load_csv(rel_path):
        # rel_path like "data/weapons.csv" under docs/
        p = Path(env.project_dir) / "docs" / rel_path
        with p.open(encoding="utf-8") as f:
            return list(DictReader(f))