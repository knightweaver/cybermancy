from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.character_origins_adapters import integrate_character_origins_stage
from rulebook_layout.character_origins_integration import (
    CharacterOriginsPayload,
    _pandoc_latex,
    _stage_spec,
)
from rulebook_layout.integration_ast import canonical_ast_sha256


def _header(chapter_id: str, title: str) -> dict:
    return {
        "t": "Header",
        "c": [2, [chapter_id, [], [["data-audience", "player"]]], [{"t": "Str", "c": title}]],
    }


def _ast() -> dict:
    return {
        "pandoc-api-version": [1, 23, 1],
        "meta": {},
        "blocks": [
            _header("ch10-ancestories", "Ancestories"),
            {"t": "Para", "c": [{"t": "Str", "c": "ancestry-normalized"}]},
            _header("ch11-communities", "Communities"),
            {"t": "Para", "c": [{"t": "Str", "c": "community-normalized"}]},
            _header("ch12-classes", "Classes"),
            {"t": "Para", "c": [{"t": "Str", "c": "classes-normalized"}]},
        ],
    }


def _payload() -> CharacterOriginsPayload:
    return CharacterOriginsPayload(
        chapter10_latex=r"\CMOriginTen" + "\n",
        chapter11_latex=r"\CMOriginEleven" + "\n",
        ancestories=18,
        communities=9,
        artwork=27,
        source_sha256="abc123",
    )


class Step6CharacterOriginsIntegrationTests(unittest.TestCase):
    def test_both_profiles_integrate_and_repeat_byte_stably(self) -> None:
        for profile in ("player-guide", "complete-rulebook"):
            with self.subTest(profile=profile):
                ast = _ast()
                payload = _payload()
                first = integrate_character_origins_stage(ast, profile, payload)
                self.assertEqual(first.status, "PASS")
                self.assertFalse(first.idempotent)
                self.assertEqual(first.replaced, {"chapter10Body": 1, "chapter11Body": 1})
                before = canonical_ast_sha256(ast)
                second = integrate_character_origins_stage(ast, profile, payload)
                after = canonical_ast_sha256(ast)
                self.assertEqual(second.status, "PASS")
                self.assertTrue(second.idempotent)
                self.assertEqual(before, after)

    def test_chapter_headers_are_preserved(self) -> None:
        ast = _ast()
        result = integrate_character_origins_stage(ast, "player-guide", _payload())
        self.assertEqual(result.status, "PASS")
        headers = [node for node in ast["blocks"] if node.get("t") == "Header"]
        self.assertEqual(len(headers), 3)
        self.assertEqual(headers[0]["c"][1][0], "ch10-ancestories")
        self.assertEqual(headers[1]["c"][1][0], "ch11-communities")
        self.assertEqual(headers[2]["c"][1][0], "ch12-classes")

    def test_duplicate_boundary_fails_closed_without_mutation(self) -> None:
        ast = _ast()
        ast["blocks"].insert(3, _header("ch11-communities", "Duplicate Communities"))
        original = copy.deepcopy(ast)
        result = integrate_character_origins_stage(ast, "complete-rulebook", _payload())
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(ast, original)

    def test_stage_contract_is_order_40_chapters_10_11(self) -> None:
        contract = {
            "transformationOrder": [
                {"order": 40, "stage": "character-origins", "chapters": [10, 11]}
            ]
        }
        self.assertEqual(_stage_spec(contract), contract["transformationOrder"][0])

    def test_fragment_renderer_rejects_standalone_shell(self) -> None:
        class Proc:
            returncode = 0
            stdout = "\\documentclass{article}\n\\begin{document}\nX\n\\end{document}\n"
            stderr = ""

        with patch("rulebook_layout.character_origins_integration.subprocess.run", return_value=Proc()):
            with self.assertRaisesRegex(RuntimeError, "Standalone publication shell leaked"):
                _pandoc_latex(
                    "test",
                    "pandoc",
                    "markdown",
                    Path("character-origins.lua"),
                )


if __name__ == "__main__":
    unittest.main()
