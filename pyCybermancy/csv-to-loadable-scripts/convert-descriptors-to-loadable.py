#!/usr/bin/env python3
"""
convert-descriptors-to-loadable.py
Batch-build Foundry/Daggerheart loadable JSONs by applying a CSV (or JSON array)
of flat descriptors onto a provided template JSON file.

Key features
- --template <file>: base JSON to clone for each row.
- CSV/JSON values are coerced (bool/num/JSON) and written into the clone.
- Column headers can be JSON paths (e.g., system.description, system.level).
- Bare headers map to:
    - Top-level for: name, img, type
    - Otherwise to system.<header>
- String interpolation: any string in the template containing {{ColumnName}}
  is expanded per-row (after coercion). Example: "name": "{{card_name}}".
- Output file name defaults to <name>.json or <row-<n>> if missing.

Usage
  python convert-descriptors-to-loadable.py descriptors.csv --template domain-card-template.json -o out/
  python convert-descriptors-to-loadable.py descriptors.json --template domain-card-template.json -o out/
"""

from __future__ import annotations
import argparse, csv, json, re, sys, copy
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

# ---------------- Utils ----------------
TOP_LEVEL_FIELDS = {"name", "img", "type"}

def _coerce_scalar(x: Any) -> Any:
    if x is None: return None
    if isinstance(x, (bool, int, float, dict, list)): return x
    s = str(x).strip()
    if s == "": return ""
    low = s.lower()
    if low == "true": return True
    if low == "false": return False
    if low in {"null","none"}: return None
    # JSON object/array/quoted?
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")) or (s.startswith('"') and s.endswith('"')):
        try: return json.loads(s)
        except Exception: pass
    # number?
    if re.fullmatch(r"[+-]?\d+", s): return int(s)
    if re.fullmatch(r"[+-]?\d+\.\d+", s): return float(s)
    return s

def _read_records(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                rows.append({k: _coerce_scalar(v) for k, v in row.items()})
        if not rows:
            raise SystemExit("CSV has no rows.")
        return rows
    # JSON (object or array)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict): return [data]
    if isinstance(data, list): return [dict(m) for m in data]
    raise SystemExit("Descriptor JSON must be an object or an array of objects.")

def _get_in(obj: Any, path: List[str]) -> Any:
    cur = obj
    for p in path:
        if not isinstance(cur, dict): return None
        cur = cur.get(p)
    return cur

def _set_in(obj: Dict[str, Any], path: List[str], value: Any) -> None:
    cur = obj
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value

def _path_for_header(h: str) -> List[str]:
    # If header is explicit JSON path, honor it.
    if "." in h:
        return [p for p in h.split(".") if p]
    # Otherwise, route name/img/type to top-level; rest to system.<header>
    if h in TOP_LEVEL_FIELDS:
        return [h]
    return ["system", h]

_INTERP_RE = re.compile(r"\{\{([^{}]+)\}\}")

def _interpolate_strings(node: Any, row: Dict[str, Any]) -> Any:
    # Recursively replace {{Column}} tokens in strings with row values coerced to str.
    if isinstance(node, dict):
        return {k: _interpolate_strings(v, row) for k, v in node.items()}
    if isinstance(node, list):
        return [_interpolate_strings(v, row) for v in node]
    if isinstance(node, str):
        def repl(m):
            key = m.group(1)
            val = row.get(key)
            if val is None: return ""
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)
        return _INTERP_RE.sub(repl, node)
    return node

# ---------------- Main build ----------------
def build_from_row(template: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(template)

    # 1) Interpolate any {{Column}} placeholders in the template.
    out = _interpolate_strings(out, row)

    # 2) Apply row fields as assignments (path-aware).
    for hdr, raw_val in row.items():
        if hdr is None or hdr == "": continue
        path = _path_for_header(hdr)
        _set_in(out, path, raw_val)

    # 3) Fallbacks: ensure minimally required structure is present.
    # If "system" missing, create it.
    if "system" not in out or not isinstance(out["system"], dict):
        out["system"] = {}

    return out

# ---------------- CLI ----------------
def main():
    ap = argparse.ArgumentParser(description="Map descriptor rows to a template JSON and emit loadable files.")
    ap.add_argument("descriptor", help="CSV or JSON (array/object) of flat descriptors")
    ap.add_argument("--template", required=True, help="Template JSON to clone per row")
    ap.add_argument("-o", "--out", required=True, help="Output directory")
    ap.add_argument("--name-field", default="name", help="Column to use for output filename (default: name)")
    args = ap.parse_args()

    desc_path = Path(args.descriptor)
    tmpl_path = Path(args.template)
    out_dir  = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        template = json.loads(tmpl_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read template: {e}")

    records = _read_records(desc_path)

    written = 0
    for idx, row in enumerate(records, start=1):
        built = build_from_row(template, row)

        # Choose filename
        fname_base = row.get(args.name_field)
        if not fname_base or str(fname_base).strip() == "":
            fname_base = f"row-{idx}"
        fname = re.sub(r"[^\w.\- ]+", "_", str(fname_base)).strip().replace(" ", "_") or f"row-{idx}"
        out_path = out_dir / f"{fname}.json"

        # Ensure pretty JSON
        out_path.write_text(json.dumps(built, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1

    print(f"Wrote {written} file(s) to {out_dir}")

if __name__ == "__main__":
    main()
