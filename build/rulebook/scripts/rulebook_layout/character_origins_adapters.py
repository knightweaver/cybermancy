from __future__ import annotations

from typing import Any

from rulebook_layout.character_origins_integration import CharacterOriginsPayload
from rulebook_layout.integration import AdapterResult, ExactAdapterSpec, execute_exact_adapter
from rulebook_layout.integration_ast import canonical_chapter_id, node_identifier


CHARACTER_ORIGINS_PROFILES = ("complete-rulebook", "player-guide")
CHARACTER_ORIGINS_ADAPTER = ExactAdapterSpec(
    name="character-origins",
    order=40,
    profiles=CHARACTER_ORIGINS_PROFILES,
    expected={"chapter10Body": 1, "chapter11Body": 1},
)


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


def integrate_character_origins_stage(
    ast: dict[str, Any],
    profile: str,
    payload: CharacterOriginsPayload,
) -> AdapterResult:
    """Replace Chapter 10-11 bodies while preserving their semantic H2 nodes."""

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "chapter10Body": _unresolved_count(
                value,
                "ch10-ancestories",
                "ch11-communities",
                payload.chapter10_latex,
            ),
            "chapter11Body": _unresolved_count(
                value,
                "ch11-communities",
                "ch12-classes",
                payload.chapter11_latex,
            ),
        }

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "chapter10Body": 1
            if _body_exact(
                value,
                "ch10-ancestories",
                "ch11-communities",
                payload.chapter10_latex,
            )
            else 0,
            "chapter11Body": 1
            if _body_exact(
                value,
                "ch11-communities",
                "ch12-classes",
                payload.chapter11_latex,
            )
            else 0,
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        # Replace the later body first so index movement cannot affect Chapter 10.
        chapter11 = _replace_body(
            value,
            "ch11-communities",
            "ch12-classes",
            payload.chapter11_latex,
        )
        chapter10 = _replace_body(
            value,
            "ch10-ancestories",
            "ch11-communities",
            payload.chapter10_latex,
        )
        return {"chapter10Body": chapter10, "chapter11Body": chapter11}

    return execute_exact_adapter(
        ast,
        CHARACTER_ORIGINS_ADAPTER,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )
