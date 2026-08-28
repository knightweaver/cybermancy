#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.encounters import load_json, render_package, validate_sidecar

DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "build/rulebook/source"
DEFAULT_CONFIG_ROOT = REPO_ROOT / "build/rulebook/layout/encounters"
DEFAULT_OUTPUT = REPO_ROOT / "build/rulebook/layout/encounters/proof-output"
CONFIGS = {
    "adversary": "adversary-package-v1.json",
    "environment": "environment-package-v1.json",
    "feature-reference": "adversary-feature-reference-v1.json",
}


def _resolve(value: str | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _compile(tex: Path) -> tuple[bool, str]:
    exe = shutil.which("lualatex")
    if not exe:
        return False, "LuaLaTeX not found on PATH"
    logs = []
    for _ in range(2):
        proc = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", tex.name], cwd=tex.parent,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace")
        logs.append(proc.stdout or "")
        if proc.returncode:
            return False, "\n".join(logs)
    return True, "\n".join(logs)


def build_one(kind: str, sidecar_path: Path, source_root: Path, config_root: Path, output: Path, tex_only: bool) -> dict:
    sidecar = load_json(sidecar_path)
    errors = validate_sidecar(sidecar)
    if errors:
        return {"status": "FAIL", "kind": kind, "errors": errors}
    config_path = config_root / CONFIGS[kind]
    config = load_json(config_path)
    tex_text, report = render_package(sidecar, config, source_root)
    output.mkdir(parents=True, exist_ok=True)
    stem = {
        "adversary": "Cybermancy_Chapter30_Adversaries_PhaseC_Proof",
        "environment": "Cybermancy_Chapter31_Environments_PhaseC_Proof",
        "feature-reference": "Cybermancy_Chapter32_Adversary_Feature_Reference_PhaseC_Proof",
    }[kind]
    tex_path = output / f"{stem}.tex"
    tex_path.write_text(tex_text, encoding="utf-8")
    report["config"] = str(config_path)
    report["sidecar"] = str(sidecar_path)
    report["tex"] = str(tex_path)
    if not tex_only:
        ok, log = _compile(tex_path)
        report["status"] = "PASS" if ok and report.get("status") == "PASS" else "FAIL"
        report["pdf"] = str(tex_path.with_suffix(".pdf")) if ok else None
        if not ok:
            report["compileLogTail"] = "\n".join(log.splitlines()[-50:])
    report_path = output / f"{stem}.report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Build Cybermancy Part VI Encounter Toolkit proof packages from Step 4 structured semantics.")
    p.add_argument("command", choices=["proof", "build"])
    p.add_argument("--family", choices=["adversary", "environment", "feature-reference", "all"], default="all")
    p.add_argument("--sidecar")
    p.add_argument("--source-root")
    p.add_argument("--config-root")
    p.add_argument("--output-dir")
    p.add_argument("--tex-only", action="store_true")
    args = p.parse_args()

    sidecar = _resolve(args.sidecar, DEFAULT_SIDECAR)
    source_root = _resolve(args.source_root, DEFAULT_SOURCE_ROOT)
    config_root = _resolve(args.config_root, DEFAULT_CONFIG_ROOT)
    output = _resolve(args.output_dir, DEFAULT_OUTPUT)
    kinds = list(CONFIGS) if args.family == "all" else [args.family]
    reports = [build_one(k, sidecar, source_root, config_root, output, args.tex_only) for k in kinds]
    failed = [r for r in reports if r.get("status") != "PASS"]
    print(json.dumps({"status": "FAIL" if failed else "PASS", "packages": reports}, indent=2, ensure_ascii=False))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
