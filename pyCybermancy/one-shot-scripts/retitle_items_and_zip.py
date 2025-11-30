#!/usr/bin/env python3
import json, sys, argparse, csv, re
from pathlib import Path

def load_mapping(path: Path):
    """Load CSV mapping of old_name → new_name, new_description, img-path."""
    mapping = {}
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["old_name"]] = {
                "name": row["new_name"],
                "description": row["new_description"],
                "img-path": row["img-path"],
            }
    return mapping


def safe_filename(name: str) -> str:
    """Generate a filesystem-safe filename based on new_name."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "unnamed"


def transform_file(p: Path, mapping: dict):
    """Transform one JSON file according to the mapping."""
    data = json.loads(p.read_text(encoding="utf-8"))
    old_name = data.get("name", "")
    if old_name in mapping:
        m = mapping[old_name]
        data["name"] = m["name"]
        data["img"] = m["img-path"]
        sysnode = data.setdefault("system", {})
        sysnode["description"] = m["description"]
        sysnode["img"] = m["img-path"]
        new_name = m["name"]
    else:
        new_name = old_name
    return json.dumps(data, ensure_ascii=False, indent=2), new_name


def main():
    ap = argparse.ArgumentParser(description="Retitle Daggerheart armor items for Cybermancy.")
    ap.add_argument("input_dir", help="Folder containing original armor JSON files.")
    ap.add_argument("mapping_csv", help="CSV mapping file (old_name,new_name,new_description,img-path).")
    ap.add_argument("-o", "--output-dir", default="armors_cybermancy", help="Output folder for transformed JSON files.")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    mapping = load_mapping(Path(args.mapping_csv))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for p in input_dir.glob("*.json"):
        try:
            new_text, new_name = transform_file(p, mapping)
            safe_name = safe_filename(new_name)
            out_path = out_dir / f"{safe_name}.json"
            out_path.write_text(new_text, encoding="utf-8")
            count += 1
            print(f"✓ Wrote {out_path.name}")
        except Exception as e:
            print(f"⚠️  WARNING: Failed to process {p.name}: {e}", file=sys.stderr)

    print(f"Completed: {count} files written to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
