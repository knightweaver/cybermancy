from pathlib import Path
import csv

def define_env(env):
    """MkDocs Macros hook."""

    @env.macro
    def load_csv(rel_path):
        """
        Load a CSV from docs/ and return a list of dict rows.
        Usage: {{ load_csv('data/weapons.csv') }}
        """
        docs_dir = Path(env.conf['docs_dir'])
        p = (docs_dir / rel_path).resolve()
        rows = []
        with p.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                rows.append({k: v.strip() for k, v in row.items()})
        return rows
