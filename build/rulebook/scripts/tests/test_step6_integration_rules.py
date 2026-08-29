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
from rulebook_layout.rules_adapters import integrate_rules_stage
from rulebook_layout.rules_integration import (
    CHAPTER_IDS,
    RULE_CHAPTERS,
    RulesPayload,
    _pandoc_latex,
    _stage_spec,
    compose_rules_stage,
)


def _header(chapter_id: str, title: str) -> dict:
    return {
        "t": "Header",
        "c": [2, [chapter_id, [], [["data-audience", "player"]]], [{"t": "Str", "c": title}]],
    }


def _ast() -> dict:
    blocks = []
    for number in range(4, 11):
        chapter_id = CHAPTER_IDS[number] if number in CHAPTER_IDS else "ch10-ancestories"
        blocks.extend(
            [
                _header(chapter_id, f"Chapter {number}"),
                {"t": "Para", "c": [{"t": "Str", "c": f"normalized-{number}"}]},
            ]
        )
    return {"pandoc-api-version": [1, 23, 1], "meta": {}, "blocks": blocks}


def _payload() -> RulesPayload:
    return RulesPayload(
        chapter_latex={number: f"\\CMRulesChapter{{{number}}}\n" for number in RULE_CHAPTERS},
        source_sha256="rules-source",
        artwork=4,
        stripped_html_wrappers=0,
    )


class Step6RulesAdapterTests(unittest.TestCase):
    def test_both_profiles_integrate_all_six_and_repeat_byte_stably(self) -> None:
        for profile in ("player-guide", "complete-rulebook"):
            with self.subTest(profile=profile):
                ast = _ast()
                first = integrate_rules_stage(ast, profile, _payload())
                self.assertEqual(first.status, "PASS")
                self.assertFalse(first.idempotent)
                self.assertEqual(first.replaced, {f"chapter{n}Body": 1 for n in RULE_CHAPTERS})
                before = canonical_ast_sha256(ast)
                second = integrate_rules_stage(ast, profile, _payload())
                after = canonical_ast_sha256(ast)
                self.assertEqual(second.status, "PASS")
                self.assertTrue(second.idempotent)
                self.assertEqual(before, after)

    def test_headers_are_preserved(self) -> None:
        ast = _ast()
        result = integrate_rules_stage(ast, "player-guide", _payload())
        self.assertEqual(result.status, "PASS")
        ids = [node["c"][1][0] for node in ast["blocks"] if node.get("t") == "Header"]
        self.assertEqual(ids, [CHAPTER_IDS[n] for n in RULE_CHAPTERS] + ["ch10-ancestories"])

    def test_duplicate_late_boundary_fails_closed_without_mutation(self) -> None:
        ast = _ast()
        ast["blocks"].insert(-2, _header("ch09-netrunning", "Duplicate"))
        original = copy.deepcopy(ast)
        result = integrate_rules_stage(ast, "complete-rulebook", _payload())
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(ast, original)

    def test_stage_contract_is_order_30_chapters_4_9(self) -> None:
        contract = {
            "transformationOrder": [
                {"order": 30, "stage": "rules", "chapters": [4, 5, 6, 7, 8, 9]}
            ]
        }
        self.assertEqual(_stage_spec(contract), contract["transformationOrder"][0])

    def test_fragment_renderer_rejects_standalone_shell(self) -> None:
        class Proc:
            returncode = 0
            stdout = "\\CMChapterBanner{4}{Rules}{player}\n"
            stderr = ""

        with patch("rulebook_layout.rules_integration.subprocess.run", return_value=Proc()):
            with self.assertRaisesRegex(RuntimeError, "Standalone publication shell leaked"):
                _pandoc_latex("test", "pandoc", "markdown", Path("rules.lua"))


class Step6RulesCompositionTests(unittest.TestCase):
    def test_composer_consumes_all_six_profiles_and_inherited_asset_stager(self) -> None:
        stage_calls: list[int] = []
        markdown_from = "accepted-reader"
        titles = {
            4: "Cybermancy Frame Rules",
            5: "Item Loadouts",
            6: "Flashbacks",
            7: "Bennies",
            8: "Driving and Chases",
            9: "Netrunning and Device Intrusion",
        }

        base = types.SimpleNamespace(
            MARKDOWN_FROM=markdown_from,
            sanitize_known_html_wrappers=lambda md: (md, 0),
            find_adjacent_image_headings=lambda _md: [],
        )

        def stage_markdown_assets(md, chapter, _asset_root, _asset_cache, missing):
            self.assertEqual(missing, [])
            stage_calls.append(chapter)
            return md + f"staged-{chapter}\n", 1 if chapter in (5, 6, 7, 8) else 0

        base.stage_markdown_assets = stage_markdown_assets

        def part_ii_map(_text):
            return {
                number: {
                    "number": number,
                    "title": titles[number],
                    "audience": "player",
                    "markdown": f"### Root {number}\n\nRules {number}.\n",
                }
                for number in RULE_CHAPTERS
            }

        rules = types.SimpleNamespace(BASE=base, _part_ii_map=part_ii_map)
        config = {
            "schema": "cybermancy-rulebook-rules-layout-v1",
            "version": "1.0",
            "status": "ACCEPTED",
            "requiredChapters": list(RULE_CHAPTERS),
        }
        contract = {
            "transformationOrder": [
                {"order": 30, "stage": "rules", "chapters": list(RULE_CHAPTERS)}
            ],
            "chapterMap": [
                {
                    "chapter": number,
                    "chapterId": CHAPTER_IDS[number],
                    "title": titles[number],
                    "audience": "player",
                }
                for number in RULE_CHAPTERS
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = root / "rules.py"
            config_path = root / "config.json"
            lua_filter = root / "rules.lua"
            player = root / "player.md"
            complete = root / "complete.md"
            assets = root / "assets"
            work = root / "work"
            builder.write_text("# fake\n", encoding="utf-8")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            lua_filter.write_text("-- fake\n", encoding="utf-8")
            player.write_text("same\n", encoding="utf-8")
            complete.write_text("same\n", encoding="utf-8")
            assets.mkdir()

            with patch(
                "rulebook_layout.rules_integration._load_module", return_value=rules
            ), patch(
                "rulebook_layout.rules_integration._pandoc_latex",
                side_effect=lambda markdown, *_args: f"\\CMRules{{{markdown.strip()}}}\n",
            ):
                payload, report = compose_rules_stage(
                    builder,
                    config_path,
                    lua_filter,
                    player,
                    complete,
                    assets,
                    work,
                    contract,
                    "pandoc",
                    markdown_from,
                )

        self.assertIsNotNone(payload)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["assetStagingOwner"], "long-form-prose-v1-via-rules-builder")
        self.assertEqual(stage_calls, list(RULE_CHAPTERS))
        self.assertEqual(sorted(payload.chapter_latex), list(RULE_CHAPTERS))
        self.assertEqual(payload.artwork, 4)

    def test_composer_rejects_profile_drift(self) -> None:
        base = types.SimpleNamespace(
            MARKDOWN_FROM="reader",
            sanitize_known_html_wrappers=lambda md: (md, 0),
            find_adjacent_image_headings=lambda _md: [],
            stage_markdown_assets=lambda md, *_args: (md, 0),
        )
        calls = {"count": 0}

        def part_ii_map(_text):
            calls["count"] += 1
            result = {
                number: {
                    "number": number,
                    "title": f"Title {number}",
                    "audience": "player",
                    "markdown": f"same-{number}\n",
                }
                for number in RULE_CHAPTERS
            }
            if calls["count"] == 2:
                result[7]["markdown"] = "different\n"
            return result

        rules = types.SimpleNamespace(BASE=base, _part_ii_map=part_ii_map)
        config = {
            "schema": "cybermancy-rulebook-rules-layout-v1",
            "version": "1.0",
            "status": "ACCEPTED",
            "requiredChapters": list(RULE_CHAPTERS),
        }
        contract = {
            "transformationOrder": [{"order": 30, "stage": "rules", "chapters": list(RULE_CHAPTERS)}],
            "chapterMap": [
                {"chapter": n, "chapterId": CHAPTER_IDS[n], "title": f"Title {n}", "audience": "player"}
                for n in RULE_CHAPTERS
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("rules.py", "rules.lua", "player.md", "complete.md"):
                (root / name).write_text("x\n", encoding="utf-8")
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            (root / "assets").mkdir()
            with patch("rulebook_layout.rules_integration._load_module", return_value=rules):
                payload, report = compose_rules_stage(
                    root / "rules.py",
                    root / "config.json",
                    root / "rules.lua",
                    root / "player.md",
                    root / "complete.md",
                    root / "assets",
                    root / "work",
                    contract,
                    "pandoc",
                    "reader",
                )

        self.assertIsNone(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("byte-equivalent" in message for message in report["errors"]))


if __name__ == "__main__":
    unittest.main()
