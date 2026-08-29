from __future__ import annotations

import copy
from typing import Any

from rulebook_layout.encounter_integration import EncounterPayload
from rulebook_layout.equipment_catalog import replace_family_div_with_latex
from rulebook_layout.integration import AdapterResult, ExactAdapterSpec, execute_exact_adapter
from rulebook_layout.integration_ast import (
    canonical_ast_sha256,
    canonical_chapter_id,
    count_chapter_header,
    count_raw_latex,
    family_body_is_exact_raw_latex,
    find_family_divs,
    iter_ast_nodes,
)


ENCOUNTER_PROFILE = "complete-rulebook"
ENCOUNTER_CHAPTER_ORDER = (30, 31, 32)


def _unresolved_family_count(ast: dict[str, Any], family: str, latex: str) -> int:
    unresolved = 0
    for div in find_family_divs(ast, family):
        content = div.get("c")
        body = content[1] if isinstance(content, list) and len(content) == 2 else None
        if body != [{"t": "RawBlock", "c": ["latex", latex]}]:
            unresolved += 1
    return unresolved


def _replace_chapter_header_with_latex(
    ast: dict[str, Any], chapter_id: str, latex: str
) -> int:
    replaced = 0
    for node in iter_ast_nodes(ast):
        if node.get("t") != "Header":
            continue
        content = node.get("c")
        if not (isinstance(content, list) and len(content) >= 2):
            continue
        attr = content[1]
        identifier = str(attr[0] or "") if isinstance(attr, list) and attr else ""
        if canonical_chapter_id(identifier) != chapter_id:
            continue
        node.clear()
        node.update({"t": "RawBlock", "c": ["latex", latex]})
        replaced += 1
    return replaced


def integrate_encounter_payload_with_adapter(
    ast: dict[str, Any], profile: str, payload: EncounterPayload
) -> AdapterResult:
    spec = ExactAdapterSpec(
        name=payload.adapter,
        order=payload.order,
        profiles=(ENCOUNTER_PROFILE,),
        expected={"chapterHeader": 1, "familyBody": 1},
    )

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "chapterHeader": count_chapter_header(value, payload.chapter_id),
            "familyBody": _unresolved_family_count(
                value, payload.family, payload.body_latex
            ),
        }

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "chapterHeader": count_raw_latex(value, payload.header_latex),
            "familyBody": 1
            if family_body_is_exact_raw_latex(
                value, payload.family, payload.body_latex
            )
            else 0,
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        return {
            "chapterHeader": _replace_chapter_header_with_latex(
                value, payload.chapter_id, payload.header_latex
            ),
            "familyBody": replace_family_div_with_latex(
                value, payload.family, payload.body_latex
            ),
        }

    return execute_exact_adapter(
        ast,
        spec,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )


def integrate_encounter_stage(
    ast: dict[str, Any], profile: str, payloads: list[EncounterPayload]
) -> dict[str, Any]:
    """Apply Chapters 30-32 transactionally; discard all on any failure."""
    input_digest = canonical_ast_sha256(ast)
    result: dict[str, Any] = {
        "schema": "cybermancy-step6-encounter-adapter-stage-v1",
        "status": "PASS",
        "profile": profile,
        "orders": [100, 110, 120],
        "chapters": list(ENCOUNTER_CHAPTER_ORDER),
        "adapters": [],
        "idempotent": False,
        "inputAstSha256": input_digest,
        "outputAstSha256": input_digest,
    }

    if profile != ENCOUNTER_PROFILE:
        result["status"] = "FAIL"
        result["error"] = "Encounter Toolkit Chapters 30-32 are Complete Rulebook only."
        return result

    actual_order = tuple(payload.chapter for payload in payloads)
    if actual_order != ENCOUNTER_CHAPTER_ORDER:
        result["status"] = "FAIL"
        result["error"] = (
            "Encounter Toolkit payloads are incomplete, duplicated, or out of "
            "Chapters 30-32 order."
        )
        result["actualChapters"] = list(actual_order)
        return result

    candidate = copy.deepcopy(ast)
    adapter_results: list[AdapterResult] = []
    for payload in payloads:
        adapter = integrate_encounter_payload_with_adapter(
            candidate, profile, payload
        )
        adapter_results.append(adapter)
        result["adapters"].append(adapter.as_dict())
        if adapter.status != "PASS":
            result["status"] = "FAIL"
            result["error"] = (
                f"Encounter adapter failed for Chapter {payload.chapter}; all "
                "staged Chapters 30-32 mutations were discarded."
            )
            return result

    output_digest = canonical_ast_sha256(candidate)
    ast.clear()
    ast.update(candidate)
    result["idempotent"] = all(adapter.idempotent for adapter in adapter_results)
    result["outputAstSha256"] = output_digest
    return result
