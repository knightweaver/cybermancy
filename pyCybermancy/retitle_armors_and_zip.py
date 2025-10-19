#!/usr/bin/env python3
import json, sys, zipfile, argparse
from pathlib import Path
import csv

def load_mapping(path: Path):
    mapping = {}
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["old_name"]] = {
                "name": row["new_name"],
                "description": row["new_description"]
            }
    return mapping

def transform_file(p: Path, mapping: dict):
    data = json.loads(p.read_text(encoding="utf-8"))
    old_name = data.get("name", "")
    if old_name in mapping:
        data["name"] = mapping[old_name]["name"]
        sysnode = data.setdefault("system", {})
        sysnode["description"] = mapping[old_name]["description"]
    return json.dumps(data, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="Retitle Daggerheart armors for Cybermancy and zip them.")
    ap.add_argument("input_dir", help="Folder containing original armor JSON files (from Foundryborne repo).")
    ap.add_argument("mapping_csv", help="CSV mapping file (old_name,new_name,new_description).")
    ap.add_argument("-o", "--output", default="armors_cybermancy.zip", help="Output zip filename.")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    mapping = load_mapping(Path(args.mapping_csv))
    out_zip = Path(args.output)

    with zipfile.ZipFile(out_zip, "w") as zf:
        for p in input_dir.glob("*.json"):
            try:
                new_text = transform_file(p, mapping)
                zf.writestr(p.name, new_text)
            except Exception as e:
                zf.write(p, arcname=p.name)
                print(f"WARNING: Passed through unchanged: {p.name}: {e}", file=sys.stderr)

    print(f"Created: {out_zip}")

if __name__ == "__main__":
    main()
