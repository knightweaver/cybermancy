#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_step4_feature_equivalence import write_feature_equivalence_artifacts

DEFAULT_SIDECAR = REPO_ROOT / "build/rulebook/source/metadata/structured-entities.json"
DEFAULT_AUDIT = REPO_ROOT / "build/rulebook/source/metadata/adversary-feature-equivalence-audit.json"
DEFAULT_REVIEW = REPO_ROOT / "build/rulebook/source/metadata/adversary-feature-equivalence-review.md"


def _resolve(value: str | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Step 4 standalone Adversary Features for publication equivalence. "
            "This command produces review artifacts only; it never alters canonical Feature entities "
            "or Chapter 32 selection."
        )
    )
    parser.add_argument("--sidecar")
    parser.add_argument("--audit-output")
    parser.add_argument("--review-output")
    args = parser.parse_args()

    sidecar_path = _resolve(args.sidecar, DEFAULT_SIDECAR)
    audit_path = _resolve(args.audit_output, DEFAULT_AUDIT)
    review_path = _resolve(args.review_output, DEFAULT_REVIEW)

    if not sidecar_path.is_file():
        print(json.dumps({"status": "FAIL", "error": f"Missing sidecar: {sidecar_path}"}, indent=2))
        return 2

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    audit = write_feature_equivalence_artifacts(sidecar, audit_path, review_path)
    print(
        json.dumps(
            {
                "status": "PASS",
                "sidecar": str(sidecar_path),
                "audit": str(audit_path),
                "review": str(review_path),
                "summary": audit.get("summary"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
