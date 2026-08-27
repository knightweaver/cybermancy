from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import rulebook_normalize
from rulebook_normalize.markdown import ensure_image_heading_block_boundaries


_IMAGE_LINE_RE = re.compile(
    r'^[ \t]*!\[[^\]\n]*\]\([^\n]+\)(?:\{[^\n}]*\})?[ \t]*$'
)
_HEADING_LINE_RE = re.compile(r'^[ \t]*#{1,6}[ \t]+.+$')


def _package_origin() -> tuple[Path, Path]:
    scripts_dir = Path(__file__).resolve().parent
    expected = (scripts_dir / "rulebook_normalize").resolve()
    package_file = getattr(rulebook_normalize, "__file__", None)
    if not package_file:
        raise RuntimeError("Loaded rulebook_normalize package has no __file__; origin cannot be verified.")
    loaded = Path(package_file).resolve().parent
    return expected, loaded


def _assert_authoritative_package() -> dict[str, str]:
    expected, loaded = _package_origin()
    if loaded != expected:
        raise RuntimeError(
            "Step 4 loaded rulebook_normalize from a non-authoritative location. "
            f"Expected {expected}; loaded {loaded}. The legacy pyCybermancy copy "
            "is not a valid Step 4 runtime fallback."
        )
    return {
        "expectedPackageDirectory": str(expected),
        "loadedPackageDirectory": str(loaded),
        "packageFile": str(Path(rulebook_normalize.__file__).resolve()),
    }


def _adjacent_image_heading_defects(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    defects: list[dict[str, Any]] = []
    for index in range(len(lines) - 1):
        image = lines[index]
        heading = lines[index + 1]
        if _IMAGE_LINE_RE.fullmatch(image) and _HEADING_LINE_RE.fullmatch(heading):
            defects.append(
                {
                    "line": index + 1,
                    "image": image.strip(),
                    "heading": heading.strip(),
                }
            )
    return defects


def _write_validation(outroot: Path, report: dict[str, Any]) -> None:
    path = outroot / "source" / "metadata" / "validation.json"
    if not path.parent.is_dir():
        return
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _normalize_and_validate_assembled_profiles(
    outroot: Path,
    report: dict[str, Any],
    *,
    add_check,
) -> None:
    """Normalize and validate the actual Step 4 assembled publication artifacts.

    Per-fragment normalization remains useful, but the publication contract is
    the materialized files consumed by downstream steps. This pass therefore
    enforces the image -> ATX-heading block boundary on those final artifacts
    and then validates the exact bytes Step 5/6 will read.
    """
    assembled_root = outroot / "source" / "assembled"
    profile_paths = sorted(assembled_root.glob("*.md")) if assembled_root.is_dir() else []
    if not profile_paths:
        add_check(
            report,
            "ASSEMBLED_IMAGE_HEADING_BOUNDARIES",
            "ERROR",
            "Step 4 assembled profile directory is missing or contains no Markdown profiles.",
        )
        _write_validation(outroot, report)
        return

    repaired: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []

    for path in profile_paths:
        original = path.read_text(encoding="utf-8")
        before = _adjacent_image_heading_defects(original)
        normalized = ensure_image_heading_block_boundaries(original)
        if normalized != original:
            path.write_text(normalized, encoding="utf-8")
        after = _adjacent_image_heading_defects(normalized)

        for defect in before:
            repaired.append({"profile": path.stem, **defect})
        for defect in after:
            remaining.append({"profile": path.stem, **defect})

    if remaining:
        add_check(
            report,
            "ASSEMBLED_IMAGE_HEADING_BOUNDARIES",
            "ERROR",
            (
                f"Step 4 assembled profiles still contain {len(remaining)} image/heading "
                "block-boundary defect(s) after normalization."
            ),
            remaining[:200],
        )
    else:
        add_check(
            report,
            "ASSEMBLED_IMAGE_HEADING_BOUNDARIES",
            "PASS",
            (
                "Actual Step 4 assembled profiles contain explicit Markdown block boundaries "
                f"between standalone images and following headings; normalized {len(repaired)} "
                "boundary occurrence(s) at the publication-output boundary."
            ),
            {
                "profileCount": len(profile_paths),
                "normalizedBoundaryCount": len(repaired),
                "remainingDefectCount": 0,
            },
        )

    _write_validation(outroot, report)


def configure_step4_prose_boundaries(namespace: dict[str, Any]) -> None:
    """Install authoritative-package and assembled-output prose invariants."""
    origin = _assert_authoritative_package()
    add_check = namespace.get("add_check")
    if not callable(add_check):
        raise RuntimeError("Step 4 namespace does not expose add_check().")

    # Validate/report package origin for both `validate` and `build` commands.
    if not namespace.get("_prose_boundary_preflight_patch"):
        original_preflight = namespace.get("preflight")
        if not callable(original_preflight):
            raise RuntimeError("Step 4 namespace does not expose preflight().")

        def preflight(*args, **kwargs):
            report, pub, asm, config = original_preflight(*args, **kwargs)
            add_check(
                report,
                "NORMALIZATION_PACKAGE_ORIGIN",
                "PASS",
                "Step 4 is using the authoritative build/rulebook/scripts/rulebook_normalize package.",
                origin,
            )
            return report, pub, asm, config

        namespace["preflight"] = preflight
        namespace["_prose_boundary_preflight_patch"] = True

    # Patch materialize at the same extension point used by the accepted Step 4
    # class/domain semantic passes. deterministic_build invokes this function
    # twice, so the output-boundary normalization is covered by the existing
    # byte-for-byte determinism check.
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_prose_boundaries_patch", False):
        return

    original_materialize = pipeline.materialize

    def materialize(
        repo_root: Path,
        outroot: Path,
        pub: dict,
        asm: dict,
        config: dict,
        base_report: dict | None = None,
    ) -> dict:
        report = original_materialize(repo_root, outroot, pub, asm, config, base_report)
        _normalize_and_validate_assembled_profiles(
            outroot,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._prose_boundaries_patch = True
