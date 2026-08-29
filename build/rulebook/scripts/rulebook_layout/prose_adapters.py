from __future__ import annotations

from typing import Any

from rulebook_layout.integration import AdapterResult, ExactAdapterSpec, execute_exact_adapter
from rulebook_layout.integration_ast import canonical_chapter_id, node_identifier
from rulebook_layout.prose_integration import (
    CHAPTER_IDS,
    GM_CHAPTERS,
    GM_STAGE,
    PLAYER_CHAPTERS,
    PLAYER_STAGE,
    ProsePayload,
)


PLAYER_PROSE_PROFILES = ("complete-rulebook", "player-guide")
GM_PROSE_PROFILES = ("complete-rulebook",)

PLAYER_PROSE_ADAPTER = ExactAdapterSpec(
    name=PLAYER_STAGE,
    order=20,
    profiles=PLAYER_PROSE_PROFILES,
    expected={f"chapter{number}Body": 1 for number in PLAYER_CHAPTERS},
)
GM_PROSE_ADAPTER = ExactAdapterSpec(
    name=GM_STAGE,
    order=80,
    profiles=GM_PROSE_PROFILES,
    expected={f"chapter{number}Body": 1 for number in GM_CHAPTERS},
)

NEXT_CHAPTER_IDS = {
    1: CHAPTER_IDS[2],
    2: CHAPTER_IDS[3],
    3: "ch04-frame-rules",
    23: CHAPTER_IDS[24],
    24: CHAPTER_IDS[25],
    25: CHAPTER_IDS[26],
    26: CHAPTER_IDS[27],
    27: CHAPTER_IDS[28],
    28: "ch29-ice-reference",
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


def _chapter_body(
    ast: dict[str, Any], chapter_id: str, next_chapter_id: str
) -> list[Any] | None:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return None
    starts = _top_level_header_indices(ast, chapter_id)
    ends = _top_level_header_indices(ast, next_chapter_id)
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return None
    return blocks[starts[0] + 1 : ends[0]]


def _body_exact(
    ast: dict[str, Any], chapter_id: str, next_chapter_id: str, latex: str
) -> bool:
    return _chapter_body(ast, chapter_id, next_chapter_id) == [
        {"t": "RawBlock", "c": ["latex", latex]}
    ]


def _unresolved_count(
    ast: dict[str, Any], chapter_id: str, next_chapter_id: str, latex: str
) -> int:
    starts = _top_level_header_indices(ast, chapter_id)
    ends = _top_level_header_indices(ast, next_chapter_id)
    if len(starts) != 1:
        return len(starts)
    if len(ends) != 1:
        return len(ends)
    if starts[0] >= ends[0]:
        return 0
    return 0 if _body_exact(ast, chapter_id, next_chapter_id, latex) else 1


def _replace_body(
    ast: dict[str, Any], chapter_id: str, next_chapter_id: str, latex: str
) -> int:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return 0
    starts = _top_level_header_indices(ast, chapter_id)
    ends = _top_level_header_indices(ast, next_chapter_id)
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return 0
    blocks[starts[0] + 1 : ends[0]] = [
        {"t": "RawBlock", "c": ["latex", latex]}
    ]
    return 1


def _payload_failure(
    adapter: ExactAdapterSpec, profile: str, error: str
) -> AdapterResult:
    empty = {key: 0 for key in adapter.expected}
    return AdapterResult(
        adapter=adapter.name,
        order=adapter.order,
        profile=profile,
        status="FAIL",
        expected=dict(adapter.expected),
        found=dict(empty),
        replaced=dict(empty),
        remaining=dict(empty),
        integrated=dict(empty),
        idempotent=False,
        error=error,
    )


def _integrate_prose_payload(
    ast: dict[str, Any],
    profile: str,
    payload: ProsePayload,
    adapter: ExactAdapterSpec,
    expected_stage: str,
    chapters: tuple[int, ...],
) -> AdapterResult:
    if payload.stage != expected_stage or payload.order != adapter.order:
        return _payload_failure(
            adapter,
            profile,
            (
                f"Prose payload does not match adapter: payload stage/order="
                f"{payload.stage}/{payload.order}, expected={expected_stage}/{adapter.order}."
            ),
        )
    if tuple(payload.chapters) != tuple(chapters) or sorted(payload.chapter_latex) != list(chapters):
        return _payload_failure(
            adapter,
            profile,
            "Prose payload chapter coverage does not match adapter scope.",
        )

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            f"chapter{number}Body": _unresolved_count(
                value,
                CHAPTER_IDS[number],
                NEXT_CHAPTER_IDS[number],
                payload.chapter_latex[number],
            )
            for number in chapters
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
            for number in chapters
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        replaced: dict[str, int] = {}
        for number in reversed(chapters):
            replaced[f"chapter{number}Body"] = _replace_body(
                value,
                CHAPTER_IDS[number],
                NEXT_CHAPTER_IDS[number],
                payload.chapter_latex[number],
            )
        return {
            f"chapter{number}Body": replaced[f"chapter{number}Body"]
            for number in chapters
        }

    return execute_exact_adapter(
        ast,
        adapter,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )


def integrate_player_prose_stage(
    ast: dict[str, Any], profile: str, payload: ProsePayload
) -> AdapterResult:
    """Replace Chapters 1-3 bodies as one exact order-20 transaction."""
    return _integrate_prose_payload(
        ast,
        profile,
        payload,
        PLAYER_PROSE_ADAPTER,
        PLAYER_STAGE,
        PLAYER_CHAPTERS,
    )


def integrate_gm_prose_stage(
    ast: dict[str, Any], profile: str, payload: ProsePayload
) -> AdapterResult:
    """Replace Chapters 23-28 bodies as one exact order-80 transaction."""
    return _integrate_prose_payload(
        ast,
        profile,
        payload,
        GM_PROSE_ADAPTER,
        GM_STAGE,
        GM_CHAPTERS,
    )
