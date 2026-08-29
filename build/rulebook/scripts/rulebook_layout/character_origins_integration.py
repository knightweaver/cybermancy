from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED = {
    10: {
        "chapterId": "ch10-ancestories",
        "entryKind": "ancestory",
        "entryCount": 18,
        "featuresPerEntry": 2,
    },
    11: {
        "chapterId": "ch11-communities",
        "entryKind": "community",
        "entryCount": 9,
        "featuresPerEntry": 1,
    },
}


@dataclass(frozen=True)
class CharacterOriginsPayload:
    chapter10_latex: str
    chapter11_latex: str
    ancestories: int
    communities: int
    artwork: int
    source_sha256: str

    def summary(self) -> dict[str, Any]:
        return {
            "order": 40,
            "chapters": [10, 11],
            "ancestories": self.ancestories,
            "communities": self.communities,
            "artwork": self.artwork,
            "sourceSha256": self.source_sha256,
        }


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Python module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stage_spec(contract: dict[str, Any]) -> dict[str, Any] | None:
    for item in contract.get("transformationOrder") or []:
        if isinstance(item, dict) and item.get("stage") == "character-origins":
            return item
    return None


def _pandoc_latex(
    markdown: str,
    pandoc: str,
    markdown_from: str,
    lua_filter: Path,
) -> str:
    proc = subprocess.run(
        [
            pandoc,
            "--from",
            markdown_from,
            "--to=latex",
            "--wrap=none",
            "--lua-filter",
            str(lua_filter),
        ],
        input=markdown,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        tail = "\n".join(
            ((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines()[-80:]
        )
        raise RuntimeError(
            f"Character Origins Pandoc fragment generation failed:\n{tail}"
        )
    latex = (proc.stdout or "").strip() + "\n"
    forbidden = (
        r"\documentclass",
        r"\usepackage",
        r"\begin{document}",
        r"\end{document}",
    )
    leaked = [token for token in forbidden if token in latex]
    if leaked:
        raise RuntimeError(
            f"Standalone publication shell leaked into Character Origins fragment: {leaked}"
        )
    if not latex.strip():
        raise RuntimeError("Character Origins Pandoc fragment is empty.")
    return latex


def _stage_assets(
    prose: Any,
    annotated: str,
    chapter: int,
    asset_root: Path,
    asset_cache: Path,
    missing: list[dict[str, Any]],
) -> tuple[str, int]:
    """Use the frozen Long-Form Prose asset-staging runtime.

    Character Origins intentionally inherits the Prose v1 asset resolver/stager;
    the Character Origins builder owns entry annotation, not generic asset staging.
    """
    stage = getattr(prose, "stage_markdown_assets", None)
    if not callable(stage):
        raise RuntimeError(
            "Accepted Long-Form Prose runtime does not expose stage_markdown_assets."
        )
    return stage(annotated, chapter, asset_root, asset_cache, missing)


def compose_character_origins_stage(
    builder_script: Path,
    prose_builder_script: Path,
    config_path: Path,
    lua_filter: Path,
    complete_source: Path,
    player_source: Path,
    asset_root: Path,
    work_dir: Path,
    contract: dict[str, Any],
    pandoc: str,
    markdown_from: str,
) -> tuple[CharacterOriginsPayload | None, dict[str, Any]]:
    """Compose frozen Chapters 10-11 from the accepted Character Origins producer."""
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-character-origins-integration-composition-v1",
        "status": "PASS",
        "checks": [],
        "errors": [],
        "chapters": [],
        "assetStagingOwner": "long-form-prose-v1",
    }

    for label, path, is_dir in (
        ("builder", builder_script, False),
        ("proseBuilder", prose_builder_script, False),
        ("config", config_path, False),
        ("luaFilter", lua_filter, False),
        ("completeSource", complete_source, False),
        ("playerSource", player_source, False),
        ("assetRoot", asset_root, True),
    ):
        exists = path.is_dir() if is_dir else path.is_file()
        if not exists:
            report["status"] = "FAIL"
            report["errors"].append(
                f"Required Character Origins integration input is missing: {label}={path}"
            )
    if report["status"] != "PASS":
        return None, report

    stage = _stage_spec(contract)
    if (
        not isinstance(stage, dict)
        or int(stage.get("order") or -1) != 40
        or stage.get("chapters") != [10, 11]
    ):
        report["status"] = "FAIL"
        report["errors"].append(
            "Integration contract does not define Character Origins as order 40 for Chapters 10-11."
        )
        return None, report

    config = _load_json(config_path)
    frozen = config.get("freeze") if isinstance(config.get("freeze"), dict) else {}
    acceptance = (
        frozen.get("acceptanceCorpus")
        if isinstance(frozen.get("acceptanceCorpus"), dict)
        else {}
    )
    if (
        config.get("schema") != "cybermancy-rulebook-character-origins-layout-v1"
        or config.get("version") != "1.0"
        or config.get("status") != "ACCEPTED"
        or frozen.get("status") != "frozen"
        or frozen.get("version") != "v1.0"
    ):
        report["status"] = "FAIL"
        report["errors"].append(
            "Character Origins layout contract is not the accepted frozen v1.0 contract."
        )
        return None, report

    regression = (
        contract.get("regressionExpectations")
        if isinstance(contract.get("regressionExpectations"), dict)
        else {}
    )
    origin_regression = (
        regression.get("characterOrigins")
        if isinstance(regression.get("characterOrigins"), dict)
        else {}
    )
    anchors = {
        "ancestories": int(origin_regression.get("ancestories") or 0),
        "communities": int(origin_regression.get("communities") or 0),
        "artwork": int(origin_regression.get("artwork") or 0),
    }
    frozen_anchors = {
        "ancestories": int(acceptance.get("ancestories") or 0),
        "communities": int(acceptance.get("communities") or 0),
        "artwork": int(acceptance.get("stagedArtwork") or 0),
    }
    if anchors != frozen_anchors or anchors != {
        "ancestories": 18,
        "communities": 9,
        "artwork": 27,
    }:
        report["status"] = "FAIL"
        report["errors"].append(
            f"Character Origins regression anchors drifted: integration={anchors}, frozen={frozen_anchors}."
        )
        return None, report

    origin = _load_module(
        builder_script, "cybermancy_character_origins_integration_source"
    )
    prose = _load_module(prose_builder_script, "cybermancy_prose_integration_source")

    complete = origin.extract_target_chapters(
        prose, complete_source.read_text(encoding="utf-8")
    )
    player = origin.extract_target_chapters(
        prose, player_source.read_text(encoding="utf-8")
    )
    if sorted(complete) != [10, 11] or sorted(player) != [10, 11]:
        report["status"] = "FAIL"
        report["errors"].append(
            "Complete Rulebook and Player Guide must each contain exactly Chapters 10 and 11 for this stage."
        )
        return None, report

    work_dir.mkdir(parents=True, exist_ok=True)
    asset_cache = work_dir / "assets"
    fragments: dict[int, str] = {}
    all_source: list[str] = []
    artwork_count = 0

    for chapter in (10, 11):
        spec = EXPECTED[chapter]
        complete_row = complete[chapter]
        player_row = player[chapter]
        complete_md = str(complete_row.get("markdown") or "")
        player_md = str(player_row.get("markdown") or "")
        row: dict[str, Any] = {
            "chapter": chapter,
            "chapterId": spec["chapterId"],
            "status": "PASS",
        }
        errors: list[str] = []

        if complete_md != player_md:
            errors.append(
                "Complete Rulebook and Player Guide normalized chapter fragments are not byte-equivalent."
            )
        if origin.RAW_MKDOCS_RE.search(complete_md):
            errors.append(
                "Raw MkDocs wrapper reached Character Origins integration input."
            )

        try:
            annotated, entries = origin.annotate_chapter(
                complete_md, chapter, str(spec["entryKind"])
            )
        except Exception as exc:
            annotated, entries = "", []
            errors.append(f"Frozen Character Origins annotation failed: {exc}")

        expected_config = (config.get("expectedCorpus") or {}).get(str(chapter)) or {}
        titles = [str(entry.get("title") or "") for entry in entries]
        expected_titles = [str(value) for value in expected_config.get("entries") or []]
        if len(entries) != int(spec["entryCount"]):
            errors.append(
                f"Chapter {chapter} contains {len(entries)} entries; expected {spec['entryCount']}."
            )
        if titles != expected_titles:
            errors.append(
                f"Chapter {chapter} entry identity/order differs from the frozen v1.0 corpus."
            )
        wrong_features = [
            str(entry.get("title") or "")
            for entry in entries
            if len(entry.get("features") or []) != int(spec["featuresPerEntry"])
        ]
        if wrong_features:
            errors.append(
                f"Chapter {chapter} entries do not all contain exactly {spec['featuresPerEntry']} Feature(s): {wrong_features}"
            )

        missing: list[dict[str, Any]] = []
        try:
            staged, resolved = _stage_assets(
                prose,
                annotated,
                chapter,
                asset_root,
                asset_cache,
                missing,
            )
        except Exception as exc:
            staged, resolved = "", 0
            errors.append(f"Character Origins asset staging failed: {exc}")

        if missing:
            errors.append(
                f"Chapter {chapter} has missing staged publication artwork: {missing}"
            )
        if resolved != len(entries):
            errors.append(
                f"Chapter {chapter} resolved {resolved} artwork item(s); expected one for each of {len(entries)} entries."
            )

        if not errors:
            try:
                fragments[chapter] = _pandoc_latex(
                    staged, pandoc, markdown_from, lua_filter
                )
            except Exception as exc:
                errors.append(str(exc))

        artwork_count += resolved
        row.update(
            {
                "entryCount": len(entries),
                "featureCount": sum(
                    len(entry.get("features") or []) for entry in entries
                ),
                "artwork": resolved,
                "entries": titles,
            }
        )
        if errors:
            row["status"] = "FAIL"
            row["errors"] = errors
            report["status"] = "FAIL"
            report["errors"].extend(
                f"Chapter {chapter}: {message}" for message in errors
            )
        report["chapters"].append(row)
        all_source.append(complete_md)

    if report["status"] != "PASS":
        return None, report
    if artwork_count != 27:
        report["status"] = "FAIL"
        report["errors"].append(
            f"Character Origins staged artwork count is {artwork_count}; expected 27."
        )
        return None, report

    payload = CharacterOriginsPayload(
        chapter10_latex=fragments[10],
        chapter11_latex=fragments[11],
        ancestories=18,
        communities=9,
        artwork=artwork_count,
        source_sha256=_sha256_text("\n".join(all_source)),
    )
    report["checks"].append(
        {
            "code": "CHARACTER_ORIGINS_STAGE_COMPOSITION",
            "status": "PASS",
            "message": (
                "Composed frozen Chapters 10-11 from byte-equivalent Step 4 profile "
                "fragments using the inherited Long-Form Prose asset stager and "
                "without a standalone document shell."
            ),
        }
    )
    report["payload"] = payload.summary()
    return payload, report
