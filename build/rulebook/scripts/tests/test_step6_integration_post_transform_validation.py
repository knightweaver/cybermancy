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

from rulebook_layout.integration_ast import canonical_ast_sha256, node_identifier
from rulebook_layout.post_transform_validation import validate_post_transform
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


def _stage130(profile: str) -> dict:
    ast = _synthetic_phase_c(profile)
    result = lower_publication_shell(ast, _contract(), profile)
    if result.status != "PASS":
        raise AssertionError(result.as_dict())
    return ast


def _check(report: dict, code: str) -> dict:
    return next(item for item in report["checks"] if item["code"] == code)


class PostTransformValidationTests(unittest.TestCase):
    def test_player_guide_validates_without_mutation(self) -> None:
        contract = _contract()
        ast = _stage130("player-guide")
        before = canonical_ast_sha256(ast)
        report = validate_post_transform(ast, contract, "player-guide")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(before, canonical_ast_sha256(ast))
        self.assertEqual(_check(report, "STAGE140_NON_MUTATING")["status"], "PASS")
        self.assertEqual(_check(report, "POST_TRANSFORM_BOOK_ORDER")["status"], "PASS")
        self.assertEqual(_check(report, "POST_TRANSFORM_PROFILE_AUDIENCE_BOUNDARY")["status"], "PASS")

    def test_complete_rulebook_validates_package_owned_headers(self) -> None:
        contract = _contract()
        ast = _stage130("complete-rulebook")
        report = validate_post_transform(ast, contract, "complete-rulebook")
        self.assertEqual(report["status"], "PASS", report)
        package = _check(report, "POST_TRANSFORM_PACKAGE_HEADER_OWNERSHIP")
        self.assertEqual(package["status"], "PASS", package)
        self.assertEqual(len(package["details"]), 4)
        self.assertTrue(all(row["headerPrecedesFamily"] for row in package["details"]))

    def test_missing_shell_chapter_fails_closed(self) -> None:
        contract = _contract()
        ast = _stage130("player-guide")
        ast["blocks"] = [
            node
            for node in ast["blocks"]
            if not (
                node.get("t") == "RawBlock"
                and "CM-INTEGRATED-SHELL CHAPTER ch03-megacorporations BEGIN" in str(node)
            )
        ]
        report = validate_post_transform(ast, contract, "player-guide")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(_check(report, "STAGE130_SHELL_EXACT")["status"], "ERROR")

    def test_semantic_chapter_header_residue_fails(self) -> None:
        contract = _contract()
        ast = _stage130("player-guide")
        ast["blocks"].append(
            _header(2, "ch01-welcome", "rb-chapter", "player", "Welcome to Cybermancy")
        )
        report = validate_post_transform(ast, contract, "player-guide")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(
            _check(report, "POST_TRANSFORM_NO_SEMANTIC_HEADER_RESIDUE")["status"],
            "ERROR",
        )

    def test_gm_divider_misplacement_fails_book_order(self) -> None:
        contract = _contract()
        ast = _stage130("complete-rulebook")
        blocks = ast["blocks"]
        divider_index = next(
            index
            for index, node in enumerate(blocks)
            if node.get("t") == "RawBlock" and "CM-INTEGRATED-SHELL GM-DIVIDER" in str(node)
        )
        divider = blocks.pop(divider_index)
        part_v_index = next(
            index
            for index, node in enumerate(blocks)
            if node.get("t") == "RawBlock" and "CM-INTEGRATED-SHELL PART part-v-gm-world" in str(node)
        )
        blocks.insert(part_v_index + 1, divider)
        report = validate_post_transform(ast, contract, "complete-rulebook")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(_check(report, "POST_TRANSFORM_BOOK_ORDER")["status"], "ERROR")

    def test_standalone_document_shell_leakage_fails(self) -> None:
        contract = _contract()
        ast = _stage130("player-guide")
        ast["blocks"].append(_raw("\\documentclass{article}\n"))
        report = validate_post_transform(ast, contract, "player-guide")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(
            _check(report, "POST_TRANSFORM_NO_STANDALONE_DOCUMENT_SHELL")["status"],
            "ERROR",
        )

    def test_reserved_chapter_13_marker_fails(self) -> None:
        contract = _contract()
        ast = _stage130("player-guide")
        ast["blocks"].append(_raw("% ch13-reserved must not exist\n"))
        report = validate_post_transform(ast, contract, "player-guide")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(_check(report, "POST_TRANSFORM_RESERVED_CHAPTER_13")["status"], "ERROR")

    def test_validation_does_not_depend_on_unrelated_header(self) -> None:
        contract = _contract()
        ast = _stage130("player-guide")
        ast["blocks"].append(_header(4, "appendix-note", "note", "player", "Editorial Note"))
        report = validate_post_transform(ast, contract, "player-guide")
        self.assertEqual(report["status"], "PASS", report)
        identifiers = [node_identifier(node) for node in ast["blocks"] if isinstance(node, dict)]
        self.assertIn("section:appendix-note", identifiers)


if __name__ == "__main__":
    unittest.main()
