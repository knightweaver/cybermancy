from __future__ import annotations

import json
import unittest
from pathlib import Path


RULEBOOK_DIR = Path(__file__).resolve().parents[2]
CONTRACT_PATH = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"


class Step6IntegrationChapterMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_chapter_map_matches_complete_profile_exactly(self) -> None:
        chapter_map = self.contract["chapterMap"]
        self.assertEqual(
            [item["chapter"] for item in chapter_map],
            self.contract["profiles"]["complete-rulebook"]["chapters"],
        )
        self.assertEqual(len(chapter_map), len({item["chapterId"] for item in chapter_map}))

    def test_chapter_map_locks_authoritative_ids(self) -> None:
        expected = {
            1: "ch01-welcome",
            2: "ch02-resonance",
            3: "ch03-megacorporations",
            4: "ch04-frame-rules",
            5: "ch05-item-loadouts",
            6: "ch06-flashbacks",
            7: "ch07-bennies",
            8: "ch08-driving-chases",
            9: "ch09-netrunning",
            10: "ch10-ancestories",
            11: "ch11-communities",
            12: "ch12-classes",
            14: "ch14-domains",
            15: "ch15-weapons",
            16: "ch16-ammunition",
            17: "ch17-armor",
            18: "ch18-cybernetics",
            19: "ch19-drones-devices",
            20: "ch20-consumables",
            21: "ch21-mods",
            22: "ch22-loot",
            23: "ch23-project-helios",
            24: "ch24-council",
            25: "ch25-cabal",
            26: "ch26-cabal-projects",
            27: "ch27-chessboard",
            28: "ch28-gm-resonance",
            29: "ch29-ice-reference",
            30: "ch30-adversaries",
            31: "ch31-environments",
            32: "ch32-adversary-features",
        }
        self.assertEqual(
            {item["chapter"]: item["chapterId"] for item in self.contract["chapterMap"]},
            expected,
        )

    def test_audience_boundary_and_gm_divider_are_explicit(self) -> None:
        by_chapter = {item["chapter"]: item for item in self.contract["chapterMap"]}
        for chapter in self.contract["profiles"]["player-guide"]["chapters"]:
            self.assertEqual(by_chapter[chapter]["audience"], "player")
        for chapter in range(23, 33):
            self.assertEqual(by_chapter[chapter]["audience"], "gm")
        self.assertEqual(
            self.contract["gmDividerText"],
            "GM MATERIAL — SPOILERS BEYOND THIS POINT",
        )


if __name__ == "__main__":
    unittest.main()
