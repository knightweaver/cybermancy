from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.integration_ast import canonical_ast_sha256
from rulebook_layout.prose_adapters import (
    integrate_gm_prose_stage,
    integrate_player_prose_stage,
)
from rulebook_layout.prose_integration import (
    CHAPTER_IDS,
    GM_CHAPTERS,
    GM_STAGE,
    PLAYER_CHAPTERS,
    PLAYER_STAGE,
    ProsePayload,
    compose_prose_stage,
)


TITLES = {
    1: "Welcome to Cybermancy",
    2: "The Resonance Cascade",
    3: "Megacorporations",
    4: "Cybermancy Frame Rules",
    23: "Project Helios and the Hidden History",
    24: "The Council",
    25: "The Cabal",
    26: "Cabal Projects",
    27: "The Chessboard",
    28: "The Resonance: GM Interpretation",
    29: "ICE Reference",
}


def _header(number: int, chapter_id: str, audience: str) -> dict:
    return {
        "t": "Header",
        "c": [
            2,
            [chapter_id, ["rb-chapter"], [["data-audience", audience]]],
            [{"t": "Str", "c": f"Chapter {number}"}],
        ],
    }


def _body(label: str) -> dict:
    return {"t": "Para", "c": [{"t": "Str", "c": label}]}


def _ast_complete() -> dict:
    blocks = []
    for number in (1, 2, 3, 4):
        chapter_id = CHAPTER_IDS.get(number, "ch04-frame-rules")
        blocks.extend([_header(number, chapter_id, "player"), _body(f"old-{number}")])
    blocks.append(_body("middle-book"))
    for number in GM_CHAPTERS:
        blocks.extend([_header(number, CHAPTER_IDS[number], "gm"), _body(f"old-{number}")])
    blocks.extend([_header(29, "ch29-ice-reference", "gm"), _body("old-29")])
    return {"pandoc-api-version": [1, 23, 1], "meta": {}, "blocks": blocks}


def _ast_player() -> dict:
    blocks = []
    for number in (1, 2, 3, 4):
        chapter_id = CHAPTER_IDS.get(number, "ch04-frame-rules")
        blocks.extend([_header(number, chapter_id, "player"), _body(f"old-{number}")])
    return {"pandoc-api-version": [1, 23, 1], "meta": {}, "blocks": blocks}


def _payload(stage: str) -> ProsePayload:
    chapters = PLAYER_CHAPTERS if stage == PLAYER_STAGE else GM_CHAPTERS
    order = 20 if stage == PLAYER_STAGE else 80
    return ProsePayload(
        stage=stage,
        order=order,
        chapter_latex={number: f"\\CMProse{{{number}}}\n" for number in chapters},
        source_sha256="abc123",
        artwork=0,
        stripped_html_wrappers=0,
    )


class Step6ProseAdapterTests(unittest.TestCase):
    def test_player_prose_integrates_both_profiles_and_is_idempotent(self) -> None:
        payload = _payload(PLAYER_STAGE)
        for profile, maker in (
            ("player-guide", _ast_player),
            ("complete-rulebook", _ast_complete),
        ):
            ast = maker()
            result = integrate_player_prose_stage(ast, profile, payload)
            self.assertEqual(result.status, "PASS")
            self.assertFalse(result.idempotent)
            first_sha = canonical_ast_sha256(ast)
            repeated = integrate_player_prose_stage(ast, profile, payload)
            self.assertEqual(repeated.status, "PASS")
            self.assertTrue(repeated.idempotent)
            self.assertEqual(first_sha, canonical_ast_sha256(ast))
            for number in PLAYER_CHAPTERS:
                self.assertEqual(result.integrated[f"chapter{number}Body"], 1)

    def test_gm_prose_integrates_complete_and_rejects_player_without_mutation(self) -> None:
        payload = _payload(GM_STAGE)
        complete = _ast_complete()
        result = integrate_gm_prose_stage(complete, "complete-rulebook", payload)
        self.assertEqual(result.status, "PASS")
        repeated = integrate_gm_prose_stage(complete, "complete-rulebook", payload)
        self.assertEqual(repeated.status, "PASS")
        self.assertTrue(repeated.idempotent)

        player = _ast_player()
        before = canonical_ast_sha256(player)
        rejected = integrate_gm_prose_stage(player, "player-guide", payload)
        self.assertEqual(rejected.status, "FAIL")
        self.assertEqual(before, canonical_ast_sha256(player))

    def test_gm_late_boundary_failure_rolls_back_all_six_chapters(self) -> None:
        ast = _ast_complete()
        ast["blocks"] = [
            block
            for block in ast["blocks"]
            if not (
                isinstance(block, dict)
                and block.get("t") == "Header"
                and isinstance(block.get("c"), list)
                and block["c"][0] == 2
                and block["c"][1][0] == "ch29-ice-reference"
            )
        ]
        before = copy.deepcopy(ast)
        result = integrate_gm_prose_stage(ast, "complete-rulebook", _payload(GM_STAGE))
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(ast, before)

    def test_payload_scope_mismatch_fails_without_mutation(self) -> None:
        ast = _ast_player()
        before = canonical_ast_sha256(ast)
        bad = ProsePayload(
            stage=PLAYER_STAGE,
            order=20,
            chapter_latex={1: "x", 2: "y"},
            source_sha256="bad",
            artwork=0,
            stripped_html_wrappers=0,
        )
        result = integrate_player_prose_stage(ast, "player-guide", bad)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(before, canonical_ast_sha256(ast))


class Step6ProseComposerTests(unittest.TestCase):
    def _config(self) -> dict:
        return {
            "schema": "cybermancy-rulebook-prose-layout-v1",
            "version": "1.0",
            "status": "ACCEPTED",
            "validation": {
                "requiredChapters": list(PLAYER_CHAPTERS + GM_CHAPTERS),
            },
        }

    def _contract(self) -> dict:
        chapter_map = []
        for number in PLAYER_CHAPTERS:
            chapter_map.append(
                {
                    "chapter": number,
                    "chapterId": CHAPTER_IDS[number],
                    "title": TITLES[number],
                    "audience": "player",
                }
            )
        for number in GM_CHAPTERS:
            chapter_map.append(
                {
                    "chapter": number,
                    "chapterId": CHAPTER_IDS[number],
                    "title": TITLES[number],
                    "audience": "gm",
                }
            )
        return {
            "chapterMap": chapter_map,
            "transformationOrder": [
                {"order": 20, "stage": PLAYER_STAGE, "chapters": list(PLAYER_CHAPTERS)},
                {
                    "order": 80,
                    "stage": GM_STAGE,
                    "chapters": list(GM_CHAPTERS),
                    "profiles": ["complete-rulebook"],
                },
            ],
        }

    def _prose_module(self, diverge_player_ch2: bool = False):
        def make_chapter(number: int, audience: str, source: str) -> dict:
            markdown = f"### Root {number}\n\nBody {number}.\n"
            if diverge_player_ch2 and source == "player" and number == 2:
                markdown = "### Root 2\n\nDIVERGED.\n"
            return {
                "number": number,
                "title": TITLES[number],
                "semanticId": f"section:{CHAPTER_IDS[number]}",
                "audience": audience,
                "markdown": markdown,
            }

        def parse_source(text: str):
            source = text.strip()
            part_i = {
                "semanticId": "section:part-i-world",
                "chapters": [make_chapter(n, "player", source) for n in PLAYER_CHAPTERS],
            }
            part_v = {
                "semanticId": "section:part-v-gm-world",
                "chapters": [make_chapter(n, "gm", source) for n in GM_CHAPTERS],
            }
            return [part_i, part_v]

        def sanitize(md: str):
            return md, 0

        def stage(md, _chapter, _asset_root, _cache, missing):
            self.assertEqual(missing, [])
            return md, 0

        return types.SimpleNamespace(
            MARKDOWN_FROM="markdown",
            parse_source=parse_source,
            sanitize_known_html_wrappers=sanitize,
            find_adjacent_image_headings=lambda _md: [],
            stage_markdown_assets=stage,
        )

    def _run_composer(self, stage: str, prose_module):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = root / "prose.py"
            config = root / "config.json"
            lua_filter = root / "prose.lua"
            player = root / "player.md"
            complete = root / "complete.md"
            assets = root / "assets"
            work = root / "work"
            builder.write_text("# fake\n", encoding="utf-8")
            config.write_text(json.dumps(self._config()), encoding="utf-8")
            lua_filter.write_text("-- fake\n", encoding="utf-8")
            player.write_text("player\n", encoding="utf-8")
            complete.write_text("complete\n", encoding="utf-8")
            assets.mkdir()

            with patch(
                "rulebook_layout.prose_integration._load_module",
                return_value=prose_module,
            ), patch(
                "rulebook_layout.prose_integration._pandoc_latex",
                side_effect=lambda markdown, *_args: f"\\CMFragment{{{len(markdown)}}}\n",
            ):
                return compose_prose_stage(
                    stage,
                    builder,
                    config,
                    lua_filter,
                    player,
                    complete,
                    assets,
                    work,
                    self._contract(),
                    "pandoc",
                    "markdown",
                )

    def test_player_and_gm_composers_use_frozen_prose_runtime(self) -> None:
        player_payload, player_report = self._run_composer(
            PLAYER_STAGE, self._prose_module()
        )
        self.assertIsNotNone(player_payload)
        self.assertEqual(player_report["status"], "PASS")
        self.assertEqual(sorted(player_payload.chapter_latex), list(PLAYER_CHAPTERS))

        gm_payload, gm_report = self._run_composer(GM_STAGE, self._prose_module())
        self.assertIsNotNone(gm_payload)
        self.assertEqual(gm_report["status"], "PASS")
        self.assertEqual(sorted(gm_payload.chapter_latex), list(GM_CHAPTERS))

    def test_player_profile_divergence_fails_closed(self) -> None:
        payload, report = self._run_composer(
            PLAYER_STAGE, self._prose_module(diverge_player_ch2=True)
        )
        self.assertIsNone(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("byte-equivalent" in error for error in report.get("errors", []))
        )


if __name__ == "__main__":
    unittest.main()
