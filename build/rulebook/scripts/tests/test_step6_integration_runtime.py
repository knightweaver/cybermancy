from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = HERE.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.integration import integrate_chapter29_with_adapter, structural_preflight
from rulebook_layout.integration_ast import canonical_ast_sha256


CONTRACT_PATH = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"


def _words(text: str) -> list[dict]:
    result: list[dict] = []
    for index, word in enumerate(text.split(" ")):
        if index:
            result.append({"t": "Space"})
        result.append({"t": "Str", "c": word})
    return result


class Step6IntegrationRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.chapter_map = {int(item["chapter"]): item for item in cls.contract["chapterMap"]}

    def make_ast(self, profile: str) -> dict:
        blocks: list[dict] = []
        profile_contract = self.contract["profiles"][profile]
        structured_by_chapter: dict[int, list[str]] = {}
        for target in self.contract["structuredTargets"]:
            profiles = target.get("profiles")
            if isinstance(profiles, list) and profile not in profiles:
                continue
            structured_by_chapter.setdefault(int(target["chapter"]), []).extend(target["families"])

        for chapter in profile_contract["chapters"]:
            if profile == "complete-rulebook" and chapter == 23:
                blocks.append({"t": "Para", "c": _words(self.contract["gmDividerText"])})

            spec = self.chapter_map[int(chapter)]
            blocks.append(
                {
                    "t": "Header",
                    "c": [
                        2,
                        [
                            f"section:{spec['chapterId']}",
                            ["rb-chapter"],
                            [["data-audience", spec["audience"]]],
                        ],
                        [{"t": "Str", "c": spec["title"]}],
                    ],
                }
            )
            for family in structured_by_chapter.get(int(chapter), []):
                blocks.append(
                    {
                        "t": "Div",
                        "c": [
                            [f"family:{family}", [], []],
                            [{"t": "Para", "c": [{"t": "Str", "c": f"placeholder-{family}"}]}],
                        ],
                    }
                )

        return {"pandoc-api-version": [1, 23, 1], "meta": {}, "blocks": blocks}

    def test_complete_profile_structural_preflight_passes(self) -> None:
        ast = self.make_ast("complete-rulebook")
        report = structural_preflight(ast, self.contract, "complete-rulebook")
        self.assertEqual(report["status"], "PASS", report)
        checks = {row["code"]: row["status"] for row in report["checks"]}
        self.assertEqual(checks["CHAPTER_IDENTITY_ORDER"], "PASS")
        self.assertEqual(checks["CHAPTER_AUDIENCE"], "PASS")
        self.assertEqual(checks["STRUCTURED_FAMILY_TARGETS"], "PASS")
        self.assertEqual(checks["GM_DIVIDER"], "PASS")

    def test_player_profile_structural_preflight_excludes_gm_targets(self) -> None:
        ast = self.make_ast("player-guide")
        report = structural_preflight(ast, self.contract, "player-guide")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["inventory"]["gmDividerCount"], 0)
        self.assertNotIn("family:features", report["inventory"]["families"])
        self.assertNotIn("ch29-ice-reference", report["inventory"]["chapters"])

    def test_preflight_fails_on_duplicate_chapter(self) -> None:
        ast = self.make_ast("complete-rulebook")
        chapter29 = next(
            block
            for block in ast["blocks"]
            if block.get("t") == "Header" and "ch29-ice-reference" in str(block)
        )
        ast["blocks"].append(copy.deepcopy(chapter29))
        report = structural_preflight(ast, self.contract, "complete-rulebook")
        self.assertEqual(report["status"], "FAIL")
        checks = {row["code"]: row["status"] for row in report["checks"]}
        self.assertEqual(checks["CHAPTER_IDENTITY_ORDER"], "ERROR")

    def test_preflight_fails_on_reserved_chapter_13(self) -> None:
        ast = self.make_ast("player-guide")
        ast["blocks"].insert(
            12,
            {
                "t": "Header",
                "c": [
                    2,
                    ["section:ch13-reserved", ["rb-chapter"], [["data-audience", "player"]]],
                    [{"t": "Str", "c": "Reserved"}],
                ],
            },
        )
        report = structural_preflight(ast, self.contract, "player-guide")
        self.assertEqual(report["status"], "FAIL")
        checks = {row["code"]: row["status"] for row in report["checks"]}
        self.assertEqual(checks["RESERVED_CHAPTERS"], "ERROR")

    def test_preflight_fails_on_wrong_audience(self) -> None:
        ast = self.make_ast("complete-rulebook")
        header23 = next(
            block
            for block in ast["blocks"]
            if block.get("t") == "Header" and "ch23-project-helios" in str(block)
        )
        header23["c"][1][2] = [["data-audience", "player"]]
        report = structural_preflight(ast, self.contract, "complete-rulebook")
        self.assertEqual(report["status"], "FAIL")
        checks = {row["code"]: row["status"] for row in report["checks"]}
        self.assertEqual(checks["CHAPTER_AUDIENCE"], "ERROR")

    def test_preflight_fails_on_missing_structured_family(self) -> None:
        ast = self.make_ast("complete-rulebook")
        ast["blocks"] = [
            block
            for block in ast["blocks"]
            if not (
                block.get("t") == "Div"
                and block.get("c", [[None]])[0][0] == "family:features"
            )
        ]
        report = structural_preflight(ast, self.contract, "complete-rulebook")
        self.assertEqual(report["status"], "FAIL")
        checks = {row["code"]: row["status"] for row in report["checks"]}
        self.assertEqual(checks["STRUCTURED_FAMILY_TARGETS"], "ERROR")

    def test_chapter29_adapter_is_exact_and_idempotent(self) -> None:
        ast = self.make_ast("complete-rulebook")
        first = integrate_chapter29_with_adapter(ast, "complete-rulebook", "HEADER-LATEX", "BODY-LATEX")
        self.assertEqual(first.status, "PASS", first.as_dict())
        self.assertFalse(first.idempotent)
        self.assertEqual(first.found, {"chapterHeader": 1, "familyFeatures": 1})
        self.assertEqual(first.replaced, {"chapterHeader": 1, "familyFeatures": 1})
        self.assertEqual(first.remaining, {"chapterHeader": 0, "familyFeatures": 0})

        digest = canonical_ast_sha256(ast)
        second = integrate_chapter29_with_adapter(ast, "complete-rulebook", "HEADER-LATEX", "BODY-LATEX")
        self.assertEqual(second.status, "PASS", second.as_dict())
        self.assertTrue(second.idempotent)
        self.assertEqual(canonical_ast_sha256(ast), digest)

    def test_chapter29_adapter_discards_partial_mutation_on_bad_preconditions(self) -> None:
        ast = self.make_ast("complete-rulebook")
        features = next(
            block
            for block in ast["blocks"]
            if block.get("t") == "Div" and block.get("c", [[None]])[0][0] == "family:features"
        )
        ast["blocks"].append(copy.deepcopy(features))
        before = canonical_ast_sha256(ast)
        result = integrate_chapter29_with_adapter(ast, "complete-rulebook", "HEADER-LATEX", "BODY-LATEX")
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(canonical_ast_sha256(ast), before)
        self.assertEqual(result.replaced, {"chapterHeader": 0, "familyFeatures": 0})

    def test_chapter29_adapter_is_not_allowed_in_player_guide(self) -> None:
        ast = self.make_ast("player-guide")
        before = canonical_ast_sha256(ast)
        result = integrate_chapter29_with_adapter(ast, "player-guide", "HEADER-LATEX", "BODY-LATEX")
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(canonical_ast_sha256(ast), before)


if __name__ == "__main__":
    unittest.main()
