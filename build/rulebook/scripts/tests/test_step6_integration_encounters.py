from __future__ import annotations

import copy
import unittest

from rulebook_layout.encounter_adapters import integrate_encounter_stage
from rulebook_layout.encounter_integration import EncounterPayload, extract_encounter_fragments
from rulebook_layout.integration_ast import canonical_ast_sha256


def _header(chapter_id: str, title: str) -> dict:
    return {
        "t": "Header",
        "c": [2, [chapter_id, [], [["data-audience", "gm"]]], [{"t": "Str", "c": title}]],
    }


def _family(name: str) -> dict:
    return {
        "t": "Div",
        "c": [[f"family:{name}", [], []], [{"t": "Para", "c": [{"t": "Str", "c": "normalized"}]}]],
    }


def _ast() -> dict:
    return {
        "pandoc-api-version": [1, 23, 1],
        "meta": {},
        "blocks": [
            _header("ch30-adversaries", "Adversaries"),
            _family("adversaries"),
            _header("ch31-environments", "Environments"),
            _family("environments"),
            _header("ch32-adversary-features", "Adversary Feature Reference"),
            _family("adversaries-features"),
        ],
    }


def _payload(chapter: int, family: str, adapter: str, order: int, chapter_id: str) -> EncounterPayload:
    return EncounterPayload(
        kind=adapter,
        chapter=chapter,
        chapter_id=chapter_id,
        family=family,
        adapter=adapter,
        order=order,
        entry_count={30: 106, 31: 8, 32: 344}[chapter],
        package_version={30: "v1.1", 31: "v1.0", 32: "v1.0"}[chapter],
        header_latex=rf"\chapteropener{{{chapter}}}",
        body_latex=rf"\packagebody{{{family}}}",
        source_tex_sha256=str(chapter) * 16,
    )


def _payloads() -> list[EncounterPayload]:
    return [
        _payload(30, "adversaries", "adversary-package", 100, "ch30-adversaries"),
        _payload(31, "environments", "environment-package", 110, "ch31-environments"),
        _payload(32, "adversaries-features", "adversary-feature-reference", 120, "ch32-adversary-features"),
    ]


class Step6EncounterIntegrationTests(unittest.TestCase):
    def test_complete_stage_integrates_and_is_byte_stable_on_repeat(self) -> None:
        ast = _ast()
        first = integrate_encounter_stage(ast, "complete-rulebook", _payloads())
        self.assertEqual(first["status"], "PASS")
        self.assertFalse(first["idempotent"])
        before = canonical_ast_sha256(ast)
        second = integrate_encounter_stage(ast, "complete-rulebook", _payloads())
        after = canonical_ast_sha256(ast)
        self.assertEqual(second["status"], "PASS")
        self.assertTrue(second["idempotent"])
        self.assertEqual(before, after)
        self.assertTrue(all(row["idempotent"] for row in second["adapters"]))

    def test_player_profile_is_rejected_without_mutation(self) -> None:
        ast = _ast()
        original = copy.deepcopy(ast)
        result = integrate_encounter_stage(ast, "player-guide", _payloads())
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(ast, original)

    def test_late_failure_rolls_back_earlier_chapters(self) -> None:
        ast = _ast()
        ast["blocks"].append(_family("environments"))
        original = copy.deepcopy(ast)
        result = integrate_encounter_stage(ast, "complete-rulebook", _payloads())
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(ast, original)
        self.assertEqual(result["adapters"][0]["status"], "PASS")
        self.assertEqual(result["adapters"][1]["status"], "FAIL")

    def test_payload_order_fails_closed(self) -> None:
        ast = _ast()
        original = copy.deepcopy(ast)
        result = integrate_encounter_stage(ast, "complete-rulebook", list(reversed(_payloads())))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(ast, original)

    def test_fragment_extraction_removes_standalone_shell(self) -> None:
        tex = "\n".join(
            [
                r"\documentclass{article}",
                r"\usepackage{xcolor}",
                r"\begin{document}",
                r"\thispagestyle{empty}",
                r"\begin{tcolorbox}CHAPTER 30\end{tcolorbox}",
                r"\vspace{-1mm}",
                r"\begin{multicols}{2}BODY\end{multicols}",
                r"\end{document}",
            ]
        )
        header, body = extract_encounter_fragments(tex)
        self.assertIn("CHAPTER 30", header)
        self.assertIn(r"\begin{multicols}{2}", body)
        combined = header + body
        self.assertNotIn(r"\documentclass", combined)
        self.assertNotIn(r"\usepackage", combined)
        self.assertNotIn(r"\begin{document}", combined)
        self.assertNotIn(r"\end{document}", combined)


if __name__ == "__main__":
    unittest.main()
