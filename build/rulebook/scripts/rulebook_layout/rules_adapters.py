from __future__ import annotations

from typing import Any

from rulebook_layout.integration import AdapterResult, ExactAdapterSpec, execute_exact_adapter
from rulebook_layout.integration_ast import canonical_chapter_id, node_identifier
from rulebook_layout.rules_integration import CHAPTER_IDS, RULE_CHAPTERS, RulesPayload


RULES_PROFILES = ("complete-rulebook", "player-guide")
RULES_ADAPTER = ExactAdapterSpec(
    name="rules",
    order=30,
    profiles=RULES_PROFILES,
    expected={f"chapter{number}Body": 1 for number in RULE_CHAPTERS},
)

NEXT_CHAPTER_IDS = {
    4: CHAPTER_IDS[5],
    5: CHAPTER_IDS[6],
    6: CHAPTER_IDS[7],
    7: CHAPTER_IDS[8],
    8: CHAPTER_IDS[9],
    9: "ch10-ancestories",
}


def _top_level_header_indices(ast: dict[str, Any], chapter_id: str) -> list[int]:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return []
    wanted = canonical_chapter_id(chapter_id)
    result: list[int] = []
    for index, node in enumerate(blocks):
        if not isinstance(node, dict) or node.get("t") != "Header":
            continue
        content = node.get("c")
        level = content[0] if isinstance(content, list) and content else None
        if level != 2:
            continue
        if canonical_chapter_id(node_identifier(node)) == wanted:
            result.append(index)
    return result


def _chapter_body(ast: dict[str, Any], chapter_id: str, next_chapter_id: str) -> list[Any] | None:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return None
    starts = _top_level_header_indices(ast, chapter_id)
    ends = _top_level_header_indices(ast, next_chapter_id)
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return None
    return blocks[starts[0] + 1 : ends[0]]


def _body_exact(ast: dict[str, Any], chapter_id: str, next_chapter_id: str, latex: str) -> bool:
    return _chapter_body(ast, chapter_id, next_chapter_id) == [
        {"t": "RawBlock", "c": ["latex", latex]}
    ]


def _unresolved_count(ast: dict[str, Any], chapter_id: str, next_chapter_id: str, latex: str) -> int:
    starts = _top_level_header_indices(ast, chapter_id)
    ends = _top_level_header_indices(ast, next_chapter_id)
    if len(starts) != 1:
        return len(starts)
    if len(ends) != 1:
        return len(ends)
    if starts[0] >= ends[0]:
        return 0
    return 0 if _body_exact(ast, chapter_id, next_chapter_id, latex) else 1


def _replace_body(ast: dict[str, Any], chapter_id: str, next_chapter_id: str, latex: str) -> int:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return 0
    starts = _top_level_header_indices(ast, chapter_id)
    ends = _top_level_header_indices(ast, next_chapter_id)
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return 0
    blocks[starts[0] + 1 : ends[0]] = [{"t": "RawBlock", "c": ["latex", latex]}]
    return 1


def integrate_rules_stage(ast: dict[str, Any], profile: str, payload: RulesPayload) -> AdapterResult:
    """Replace all Part II Chapter 4-9 bodies as one exact order-30 transaction."""

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            f"chapter{number}Body": _unresolved_count(
                value,
                CHAPTER_IDS[number],
                NEXT_CHAPTER_IDS[number],
                payload.chapter_latex[number],
            )
            for number in RULE_CHAPTERS
        }

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            f"chapter{number}Body": 1
            if _body_exact(
                value,
                CHAPTER_IDS[number],
                NEXT_CHAPTER_IDS[number],
                payload.chapter_latex[number],
            )
            else 0
            for number in RULE_CHAPTERS
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        replaced: dict[str, int] = {}
        # Work backwards so replacing an earlier chapter cannot move a later boundary.
        for number in reversed(RULE_CHAPTERS):
            replaced[f"chapter{number}Body"] = _replace_body(
                value,
                CHAPTER_IDS[number],
                NEXT_CHAPTER_IDS[number],
                payload.chapter_latex[number],
            )
        return {f"chapter{number}Body": replaced[f"chapter{number}Body"] for number in RULE_CHAPTERS}

    return execute_exact_adapter(
        ast,
        RULES_ADAPTER,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )
