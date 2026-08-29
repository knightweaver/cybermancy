from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RULE_CHAPTERS = (4, 5, 6, 7, 8, 9)
CHAPTER_IDS = {
    4: "ch04-frame-rules",
    5: "ch05-item-loadouts",
    6: "ch06-flashbacks",
    7: "ch07-bennies",
    8: "ch08-driving-chases",
    9: "ch09-netrunning",
}


@dataclass(frozen=True)
class RulesPayload:
    chapter_latex: dict[int, str]
    source_sha256: str
    artwork: int
    stripped_html_wrappers: int

    def summary(self) -> dict[str, Any]:
        return {
            "order": 30,
            "chapters": list(RULE_CHAPTERS),
            "chapterIds": [CHAPTER_IDS[number] for number in RULE_CHAPTERS],
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


def _stage_spec(contract: dict[str, Any]) -> dict[str, Any] | None:
    for item in contract.get("transformationOrder") or []:
        if isinstance(item, dict) and item.get("stage") == "rules":
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
        raise RuntimeError(f"Rules Pandoc fragment generation failed:\n{tail}")
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
        raise RuntimeError(f"Standalone publication shell leaked into Rules fragment: {leaked}")
    if not latex.strip():
        raise RuntimeError("Rules Pandoc fragment is empty.")
    return latex


def compose_rules_stage(
    rules_builder_script: Path,
    config_path: Path,
    lua_filter: Path,
    player_source: Path,
    complete_source: Path,
    asset_root: Path,
    work_dir: Path,
    contract: dict[str, Any],
    pandoc: str,
    markdown_from: str,
) -> tuple[RulesPayload | None, dict[str, Any]]:
    """Compose accepted Part II Rules v1.0 chapter bodies for order-30 integration."""
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-rules-integration-composition-v1",
        "status": "PASS",
        "checks": [],
        "errors": [],
        "chapters": [],
        "assetStagingOwner": "long-form-prose-v1-via-rules-builder",
    }

    for label, path, is_dir in (
        ("rulesBuilder", rules_builder_script, False),
        ("config", config_path, False),
        ("luaFilter", lua_filter, False),
        ("playerSource", player_source, False),
        ("completeSource", complete_source, False),
        ("assetRoot", asset_root, True),
    ):
        exists = path.is_dir() if is_dir else path.is_file()
        if not exists:
            report["status"] = "FAIL"
            report["errors"].append(f"Required Rules integration input is missing: {label}={path}")
    if report["status"] != "PASS":
        return None, report

    stage = _stage_spec(contract)
    if (
        not isinstance(stage, dict)
        or int(stage.get("order") or -1) != 30
        or stage.get("chapters") != list(RULE_CHAPTERS)
    ):
        report["status"] = "FAIL"
        report["errors"].append(
            "Integration contract does not define Rules as order 30 for Chapters 4-9."
        )
        return None, report

    config = _load_json(config_path)
    if (
        config.get("schema") != "cybermancy-rulebook-rules-layout-v1"
        or config.get("version") != "1.0"
        or config.get("status") != "ACCEPTED"
        or config.get("requiredChapters") != list(RULE_CHAPTERS)
    ):
        report["status"] = "FAIL"
        report["errors"].append("Rules layout contract is not the accepted v1.0 Chapters 4-9 contract.")
        return None, report

    rules = _load_module(rules_builder_script, "cybermancy_rules_integration_source")
    base = getattr(rules, "BASE", None)
    if base is None:
        report["status"] = "FAIL"
        report["errors"].append("Accepted Rules builder does not expose its inherited Long-Form Prose runtime.")
        return None, report

    accepted_reader = str(getattr(base, "MARKDOWN_FROM", ""))
    if not accepted_reader or accepted_reader != markdown_from:
        report["status"] = "FAIL"
        report["errors"].append(
            f"Rules Markdown reader drifted from the integrated runtime: accepted={accepted_reader!r}, integrated={markdown_from!r}."
        )
        return None, report

    player = rules._part_ii_map(player_source.read_text(encoding="utf-8"))
    complete = rules._part_ii_map(complete_source.read_text(encoding="utf-8"))
    if sorted(player) != list(RULE_CHAPTERS) or sorted(complete) != list(RULE_CHAPTERS):
        report["status"] = "FAIL"
        report["errors"].append(
            f"Both publication profiles must contain exactly Part II Chapters 4-9; player={sorted(player)}, complete={sorted(complete)}."
        )
        return None, report

    chapter_map = {
        int(row["chapter"]): row
        for row in contract.get("chapterMap") or []
        if isinstance(row, dict) and int(row.get("chapter") or -1) in RULE_CHAPTERS
    }
    if sorted(chapter_map) != list(RULE_CHAPTERS):
        report["status"] = "FAIL"
        report["errors"].append("Integration contract chapter map is incomplete for Rules Chapters 4-9.")
        return None, report

    work_dir.mkdir(parents=True, exist_ok=True)
    asset_cache = work_dir / "assets"
    asset_cache.mkdir(parents=True, exist_ok=True)

    fragments: dict[int, str] = {}
    source_fragments: list[str] = []
    artwork_count = 0
    stripped_html = 0

    for chapter in RULE_CHAPTERS:
        left = player[chapter]
        right = complete[chapter]
        row: dict[str, Any] = {
            "chapter": chapter,
            "chapterId": CHAPTER_IDS[chapter],
            "status": "PASS",
        }
        errors: list[str] = []

        left_signature = (left.get("title"), left.get("audience"), left.get("markdown"))
        right_signature = (right.get("title"), right.get("audience"), right.get("markdown"))
        if left_signature != right_signature:
            errors.append("Player Guide and Complete Rulebook normalized chapter fragments are not byte-equivalent.")

        expected = chapter_map[chapter]
        if expected.get("chapterId") != CHAPTER_IDS[chapter]:
            errors.append(
                f"Integration contract chapter ID drifted: expected {CHAPTER_IDS[chapter]!r}, found {expected.get('chapterId')!r}."
            )
        if str(left.get("title") or "") != str(expected.get("title") or ""):
            errors.append(
                f"Normalized chapter title differs from the integration contract: {left.get('title')!r} vs {expected.get('title')!r}."
            )
        if str(left.get("audience") or "") != "player":
            errors.append(f"Rules Chapter {chapter} is not marked player audience in the normalized corpus.")

        raw_md = str(left.get("markdown") or "")
        source_fragments.append(raw_md)
        sanitized, removed = base.sanitize_known_html_wrappers(raw_md)
        stripped_html += int(removed)

        adjacency = list(base.find_adjacent_image_headings(sanitized))
        if adjacency:
            errors.append(
                f"Step 4 normalized source contains {len(adjacency)} image/heading block-boundary defect(s); Step 6 did not repair them."
            )

        missing: list[dict[str, Any]] = []
        try:
            staged, resolved = base.stage_markdown_assets(
                sanitized,
                chapter,
                asset_root,
                asset_cache,
                missing,
            )
        except Exception as exc:
            staged, resolved = "", 0
            errors.append(f"Rules asset staging failed: {exc}")

        if missing:
            errors.append(f"Chapter {chapter} has missing staged publication artwork: {missing}")

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
                "title": left.get("title"),
                "artwork": int(resolved),
                "strippedHtmlWrappers": int(removed),
                "adjacencyDefects": adjacency,
            }
        )
        if errors:
            row["status"] = "FAIL"
            row["errors"] = errors
            report["status"] = "FAIL"
            report["errors"].extend(f"Chapter {chapter}: {message}" for message in errors)
        report["chapters"].append(row)

    if report["status"] != "PASS":
        return None, report

    if sorted(fragments) != list(RULE_CHAPTERS):
        report["status"] = "FAIL"
        report["errors"].append(
            f"Rules fragment coverage is incomplete after composition: {sorted(fragments)}."
        )
        return None, report

    payload = RulesPayload(
        chapter_latex=fragments,
        source_sha256=_sha256_text("\n".join(source_fragments)),
        artwork=artwork_count,
        stripped_html_wrappers=stripped_html,
    )
    report["checks"].append(
        {
            "code": "RULES_STAGE_COMPOSITION",
            "status": "PASS",
            "message": "Composed accepted Rules v1.0 bodies for all six byte-equivalent Part II chapters without a standalone document shell.",
        }
    )
    report["payload"] = payload.summary()
    return payload, report
