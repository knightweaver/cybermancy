from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout import prose_adapters, rules_adapters
from rulebook_layout.integration_ast import canonical_ast_sha256, document_text, node_classes
from rulebook_layout.publication_shell import (
    COLUMN_CHAPTERS,
    PACKAGE_HEADER_CHAPTERS,
    PARTS,
    lower_publication_shell,
)

CONTRACT_PATH = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _words(text: str) -> list[dict]:
    result: list[dict] = []
    for index, word in enumerate(text.split()):
        if index:
            result.append({"t": "Space"})
        result.append({"t": "Str", "c": word})
    return result


def _header(level: int, identifier: str, cls: str, audience: str, title: str) -> dict:
    return {
        "t": "Header",
        "c": [
            level,
            [f"section:{identifier}", [cls], [["data-audience", audience]]],
            _words(title),
        ],
    }


def _para(text: str) -> dict:
    return {"t": "Para", "c": _words(text)}


def _raw(text: str) -> dict:
    return {"t": "RawBlock", "c": ["latex", text]}


def _family(family: str) -> dict:
    return {
        "t": "Div",
        "c": [
            [f"family:{family}", [], []],
            [_raw(f"% integrated family:{family}\n\\CMFamily{{{family}}}\n")],
        ],
    }


def _top_level_raw_latex(ast: dict) -> list[str]:
    return [
        str(node["c"][1])
        for node in ast.get("blocks", [])
        if isinstance(node, dict)
        and node.get("t") == "RawBlock"
        and isinstance(node.get("c"), list)
        and len(node["c"]) == 2
        and node["c"][0] == "latex"
    ]


def _synthetic_phase_c(profile: str) -> dict:
    contract = _contract()
    chapter_map = {int(row["chapter"]): row for row in contract["chapterMap"]}
    profile_chapters = [int(value) for value in contract["profiles"][profile]["chapters"]]
    part_starts = {
        1: PARTS[0],
        4: PARTS[1],
        10: PARTS[2],
        15: PARTS[3],
        23: PARTS[4],
        29: PARTS[5],
    }
    families_by_chapter: dict[int, list[str]] = {}
    for target in contract["structuredTargets"]:
        profiles = target.get("profiles")
        if isinstance(profiles, list) and profile not in profiles:
            continue
        families_by_chapter.setdefault(int(target["chapter"]), []).extend(target["families"])

    blocks: list[dict] = []
    for chapter in profile_chapters:
        if chapter in part_starts:
            part = part_starts[chapter]
            if chapter == 23:
                blocks.append(_para(contract["gmDividerText"]))
            blocks.append(
                _header(
                    1,
                    part["id"],
                    "rb-part",
                    part["audience"],
                    part["title"],
                )
            )
            if chapter == 23:
                blocks.append(_para("Preserved GM front matter."))

        spec = chapter_map[chapter]
        if profile == "complete-rulebook" and chapter in PACKAGE_HEADER_CHAPTERS:
            blocks.append(_raw(f"% frozen package header CHAPTER {chapter}\n"))
            for family in families_by_chapter.get(chapter, []):
                blocks.append(_family(family))
            continue

        blocks.append(
            _header(
                2,
                spec["chapterId"],
                "rb-chapter",
                spec["audience"],
                spec["title"],
            )
        )
        if chapter in COLUMN_CHAPTERS:
            blocks.append(_raw(f"% integrated chapter {chapter} body\n\\CMBody{{{chapter}}}\n"))
        else:
            for family in families_by_chapter.get(chapter, []):
                blocks.append(_family(family))

    return {"pandoc-api-version": [1, 23, 1], "meta": {}, "blocks": blocks}


class PublicationShellTests(unittest.TestCase):
    def test_player_guide_lowering_is_exact_and_idempotent(self) -> None:
        contract = _contract()
        ast = _synthetic_phase_c("player-guide")
        result = lower_publication_shell(ast, contract, "player-guide")
        self.assertEqual(result.status, "PASS", result.as_dict())
        self.assertFalse(result.idempotent)
        self.assertEqual(result.replaced["parts"], 4)
        self.assertEqual(result.replaced["chapters"], 21)
        self.assertEqual(result.replaced["columnEnds"], 11)
        self.assertEqual(result.replaced["gmDivider"], 0)
        self.assertFalse(
            any(
                node.get("t") == "Header" and ({"rb-part", "rb-chapter"} & set(node_classes(node)))
                for node in ast["blocks"]
                if isinstance(node, dict)
            )
        )
        before = canonical_ast_sha256(ast)
        repeated = lower_publication_shell(ast, contract, "player-guide")
        self.assertEqual(repeated.status, "PASS", repeated.as_dict())
        self.assertTrue(repeated.idempotent)
        self.assertEqual(before, canonical_ast_sha256(ast))

    def test_complete_lowering_preserves_gm_front_matter_and_package_headers(self) -> None:
        contract = _contract()
        ast = _synthetic_phase_c("complete-rulebook")
        package_headers = [
            raw
            for raw in _top_level_raw_latex(ast)
            if "frozen package header" in raw
        ]
        self.assertEqual(len(package_headers), len(PACKAGE_HEADER_CHAPTERS))

        result = lower_publication_shell(ast, contract, "complete-rulebook")
        self.assertEqual(result.status, "PASS", result.as_dict())
        self.assertEqual(result.replaced["parts"], 6)
        self.assertEqual(result.replaced["chapters"], 27)
        self.assertEqual(result.replaced["columnEnds"], 17)
        self.assertEqual(result.replaced["gmDivider"], 1)
        self.assertIn("Preserved GM front matter.", document_text(ast))

        lowered_raw = _top_level_raw_latex(ast)
        for header in package_headers:
            self.assertIn(header, lowered_raw)

    def test_stage130_fails_closed_if_package_header_is_not_already_lowered(self) -> None:
        contract = _contract()
        ast = _synthetic_phase_c("complete-rulebook")
        before = copy.deepcopy(ast)
        spec = next(row for row in contract["chapterMap"] if int(row["chapter"]) == 29)
        part_vi_index = next(
            index
            for index, node in enumerate(ast["blocks"])
            if node.get("t") == "Header" and "part-vi-gm-toolkit" in str(node)
        )
        ast["blocks"].insert(
            part_vi_index + 1,
            _header(2, spec["chapterId"], "rb-chapter", spec["audience"], spec["title"]),
        )
        before = copy.deepcopy(ast)
        result = lower_publication_shell(ast, contract, "complete-rulebook")
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(ast, before)
        self.assertEqual(
            result.readiness["status"],
            "FAIL",
            result.as_dict(),
        )

    def test_prose_adapter_does_not_cross_part_header(self) -> None:
        ast = {
            "meta": {},
            "blocks": [
                _header(2, "ch03-megacorporations", "rb-chapter", "player", "Megacorporations"),
                _para("old body"),
                _header(1, "part-ii-rules", "rb-part", "player", "Cybermancy Rules"),
                _header(2, "ch04-frame-rules", "rb-chapter", "player", "Cybermancy Frame Rules"),
            ],
        }
        replaced = prose_adapters._replace_body(
            ast,
            "ch03-megacorporations",
            "ch04-frame-rules",
            "NEW",
        )
        self.assertEqual(replaced, 1)
        self.assertEqual(ast["blocks"][1], _raw("NEW"))
        self.assertTrue(any("rb-part" in node_classes(node) for node in ast["blocks"] if isinstance(node, dict)))

    def test_rules_adapter_does_not_cross_part_header(self) -> None:
        ast = {
            "meta": {},
            "blocks": [
                _header(2, "ch09-netrunning", "rb-chapter", "player", "Netrunning and Device Intrusion"),
                _para("old body"),
                _header(1, "part-iii-characters", "rb-part", "player", "Characters and Character Options"),
                _header(2, "ch10-ancestories", "rb-chapter", "player", "Ancestories"),
            ],
        }
        replaced = rules_adapters._replace_body(
            ast,
            "ch09-netrunning",
            "ch10-ancestories",
            "NEW",
        )
        self.assertEqual(replaced, 1)
        self.assertEqual(ast["blocks"][1], _raw("NEW"))
        self.assertTrue(any("rb-part" in node_classes(node) for node in ast["blocks"] if isinstance(node, dict)))


if __name__ == "__main__":
    unittest.main()
