from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PLAYER_STAGE = "prose-player"
GM_STAGE = "prose-gm"
PLAYER_CHAPTERS = (1, 2, 3)
GM_CHAPTERS = (23, 24, 25, 26, 27, 28)
CHAPTER_IDS = {
    1: "ch01-welcome",
    2: "ch02-resonance",
    3: "ch03-megacorporations",
    23: "ch23-project-helios",
    24: "ch24-council",
    25: "ch25-cabal",
    26: "ch26-cabal-projects",
    27: "ch27-chessboard",
    28: "ch28-gm-resonance",
}
PART_IDS = {
    PLAYER_STAGE: "section:part-i-world",
    GM_STAGE: "section:part-v-gm-world",
}
STAGE_ORDERS = {PLAYER_STAGE: 20, GM_STAGE: 80}
STAGE_CHAPTERS = {PLAYER_STAGE: PLAYER_CHAPTERS, GM_STAGE: GM_CHAPTERS}
EXPECTED_AUDIENCE = {PLAYER_STAGE: "player", GM_STAGE: "gm"}


@dataclass(frozen=True)
class ProsePayload:
    stage: str
    order: int
    chapter_latex: dict[int, str]
    source_sha256: str
    artwork: int
    stripped_html_wrappers: int

    @property
    def chapters(self) -> tuple[int, ...]:
        return STAGE_CHAPTERS[self.stage]

    def summary(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "order": self.order,
            "chapters": list(self.chapters),
            "chapterIds": [CHAPTER_IDS[number] for number in self.chapters],
            "artwork": self.artwork,
            "strippedHtmlWrappers": self.stripped_html_wrappers,
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


def _stage_spec(contract: dict[str, Any], stage_name: str) -> dict[str, Any] | None:
    for item in contract.get("transformationOrder") or []:
        if isinstance(item, dict) and item.get("stage") == stage_name:
            return item
    return None


def _part_map(prose: Any, text: str, part_id: str) -> dict[int, dict[str, Any]]:
    for part in prose.parse_source(text):
        if part.get("semanticId") == part_id:
            return {int(ch["number"]): ch for ch in part.get("chapters", [])}
    return {}


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
        raise RuntimeError(f"Long-Form Prose Pandoc fragment generation failed:\n{tail}")
    latex = (proc.stdout or "").strip() + "\n"
    forbidden = (
        r"\documentclass",
        r"\usepackage",
        r"\begin{document}",
        r"\end{document}",
        r"\CMPartPage",
        r"\CMChapterBanner",
    )
    leaked = [token for token in forbidden if token in latex]
    if leaked:
        raise RuntimeError(
            f"Standalone publication shell leaked into Long-Form Prose fragment: {leaked}"
        )
    if not latex.strip():
        raise RuntimeError("Long-Form Prose Pandoc fragment is empty.")
    return latex


def _validate_layout_config(config: dict[str, Any]) -> str | None:
    required = ((config.get("validation") or {}).get("requiredChapters") or [])
    expected = list(PLAYER_CHAPTERS + GM_CHAPTERS)
    if (
        config.get("schema") != "cybermancy-rulebook-prose-layout-v1"
        or config.get("version") != "1.0"
        or config.get("status") != "ACCEPTED"
        or list(required) != expected
    ):
        return (
            "Long-Form Prose layout contract is not the accepted v1.0 contract "
            "for canonical Chapters 1-3 and 23-28."
        )
    return None


def compose_prose_stage(
    stage_name: str,
    prose_builder_script: Path,
    config_path: Path,
    lua_filter: Path,
    player_source: Path,
    complete_source: Path,
    asset_root: Path,
    work_dir: Path,
    contract: dict[str, Any],
    pandoc: str,
    markdown_from: str,
) -> tuple[ProsePayload | None, dict[str, Any]]:
    """Compose one accepted Long-Form Prose stage as body-only LaTeX fragments."""
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-prose-integration-composition-v1",
        "status": "PASS",
        "stage": stage_name,
        "checks": [],
        "errors": [],
        "chapters": [],
        "assetStagingOwner": "long-form-prose-v1",
    }

    if stage_name not in STAGE_CHAPTERS:
        report["status"] = "FAIL"
        report["errors"].append(f"Unknown Long-Form Prose integration stage: {stage_name}")
        return None, report

    required_paths = [
        ("proseBuilder", prose_builder_script, False),
        ("config", config_path, False),
        ("luaFilter", lua_filter, False),
        ("completeSource", complete_source, False),
        ("assetRoot", asset_root, True),
    ]
    if stage_name == PLAYER_STAGE:
        required_paths.append(("playerSource", player_source, False))
    for label, path, is_dir in required_paths:
        exists = path.is_dir() if is_dir else path.is_file()
        if not exists:
            report["status"] = "FAIL"
            report["errors"].append(
                f"Required Long-Form Prose integration input is missing: {label}={path}"
            )
    if report["status"] != "PASS":
        return None, report

    chapters = STAGE_CHAPTERS[stage_name]
    order = STAGE_ORDERS[stage_name]
    stage = _stage_spec(contract, stage_name)
    if (
        not isinstance(stage, dict)
        or int(stage.get("order") or -1) != order
        or stage.get("chapters") != list(chapters)
    ):
        report["status"] = "FAIL"
        report["errors"].append(
            f"Integration contract does not define {stage_name} as order {order} "
            f"for Chapters {chapters[0]}-{chapters[-1]}."
        )
        return None, report
    if stage_name == GM_STAGE and stage.get("profiles") != ["complete-rulebook"]:
        report["status"] = "FAIL"
        report["errors"].append(
            "Integration contract does not gate prose-gm to complete-rulebook."
        )
        return None, report

    config = _load_json(config_path)
    config_error = _validate_layout_config(config)
    if config_error:
        report["status"] = "FAIL"
        report["errors"].append(config_error)
        return None, report

    prose = _load_module(prose_builder_script, "cybermancy_prose_integration_source")
    accepted_reader = str(getattr(prose, "MARKDOWN_FROM", ""))
    if not accepted_reader or accepted_reader != markdown_from:
        report["status"] = "FAIL"
        report["errors"].append(
            f"Long-Form Prose Markdown reader drifted from the integrated runtime: "
            f"accepted={accepted_reader!r}, integrated={markdown_from!r}."
        )
        return None, report

    complete = _part_map(
        prose,
        complete_source.read_text(encoding="utf-8"),
        PART_IDS[stage_name],
    )
    if sorted(complete) != list(chapters):
        report["status"] = "FAIL"
        report["errors"].append(
            f"Complete Rulebook {stage_name} corpus must contain exactly {list(chapters)}; "
            f"found {sorted(complete)}."
        )
        return None, report

    player: dict[int, dict[str, Any]] = {}
    if stage_name == PLAYER_STAGE:
        player = _part_map(
            prose,
            player_source.read_text(encoding="utf-8"),
            PART_IDS[stage_name],
        )
        if sorted(player) != list(chapters):
            report["status"] = "FAIL"
            report["errors"].append(
                f"Player Guide prose-player corpus must contain exactly {list(chapters)}; "
                f"found {sorted(player)}."
            )
            return None, report

    chapter_map = {
        int(row["chapter"]): row
        for row in contract.get("chapterMap") or []
        if isinstance(row, dict) and int(row.get("chapter") or -1) in chapters
    }
    if sorted(chapter_map) != list(chapters):
        report["status"] = "FAIL"
        report["errors"].append(
            f"Integration contract chapter map is incomplete for {stage_name}."
        )
        return None, report

    work_dir.mkdir(parents=True, exist_ok=True)
    asset_cache = work_dir / "assets"
    asset_cache.mkdir(parents=True, exist_ok=True)

    fragments: dict[int, str] = {}
    source_fragments: list[str] = []
    artwork_count = 0
    stripped_html = 0

    for chapter in chapters:
        canonical = complete[chapter]
        row: dict[str, Any] = {
            "chapter": chapter,
            "chapterId": CHAPTER_IDS[chapter],
            "status": "PASS",
        }
        errors: list[str] = []

        if stage_name == PLAYER_STAGE:
            other = player[chapter]
            left_signature = (
                canonical.get("title"),
                canonical.get("audience"),
                canonical.get("markdown"),
            )
            right_signature = (
                other.get("title"),
                other.get("audience"),
                other.get("markdown"),
            )
            if left_signature != right_signature:
                errors.append(
                    "Player Guide and Complete Rulebook normalized chapter fragments "
                    "are not byte-equivalent."
                )

        expected = chapter_map[chapter]
        if expected.get("chapterId") != CHAPTER_IDS[chapter]:
            errors.append(
                f"Integration contract chapter ID drifted: expected {CHAPTER_IDS[chapter]!r}, "
                f"found {expected.get('chapterId')!r}."
            )
        if str(canonical.get("title") or "") != str(expected.get("title") or ""):
            errors.append(
                "Normalized chapter title differs from the integration contract: "
                f"{canonical.get('title')!r} vs {expected.get('title')!r}."
            )
        expected_audience = EXPECTED_AUDIENCE[stage_name]
        if str(canonical.get("audience") or "") != expected_audience:
            errors.append(
                f"Chapter {chapter} is not marked {expected_audience} audience in the normalized corpus."
            )

        raw_md = str(canonical.get("markdown") or "")
        source_fragments.append(raw_md)
        sanitized, removed = prose.sanitize_known_html_wrappers(raw_md)
        stripped_html += int(removed)

        adjacency = list(prose.find_adjacent_image_headings(sanitized))
        if adjacency:
            errors.append(
                f"Step 4 normalized source contains {len(adjacency)} image/heading "
                "block-boundary defect(s); Step 6 did not repair them."
            )

        missing: list[dict[str, Any]] = []
        try:
            staged, resolved = prose.stage_markdown_assets(
                sanitized,
                chapter,
                asset_root,
                asset_cache,
                missing,
            )
        except Exception as exc:
            staged, resolved = "", 0
            errors.append(f"Long-Form Prose asset staging failed: {exc}")

        if missing:
            errors.append(
                f"Chapter {chapter} has missing staged publication artwork: {missing}"
            )

        if not errors:
            try:
                fragments[chapter] = _pandoc_latex(
                    staged,
                    pandoc,
                    markdown_from,
                    lua_filter,
                )
            except Exception as exc:
                errors.append(str(exc))

        artwork_count += int(resolved)
        row.update(
            {
                "title": canonical.get("title"),
                "artwork": int(resolved),
                "strippedHtmlWrappers": int(removed),
                "adjacencyDefects": adjacency,
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

    if report["status"] != "PASS":
        return None, report

    if sorted(fragments) != list(chapters):
        report["status"] = "FAIL"
        report["errors"].append(
            f"{stage_name} fragment coverage is incomplete after composition: {sorted(fragments)}."
        )
        return None, report

    payload = ProsePayload(
        stage=stage_name,
        order=order,
        chapter_latex=fragments,
        source_sha256=_sha256_text("\n".join(source_fragments)),
        artwork=artwork_count,
        stripped_html_wrappers=stripped_html,
    )
    check_code = "PLAYER_PROSE_STAGE_COMPOSITION" if stage_name == PLAYER_STAGE else "GM_PROSE_STAGE_COMPOSITION"
    report["checks"].append(
        {
            "code": check_code,
            "status": "PASS",
            "message": (
                f"Composed accepted Long-Form Prose v1.0 bodies for {stage_name} "
                "without a standalone document shell."
            ),
        }
    )
    report["payload"] = payload.summary()
    return payload, report
