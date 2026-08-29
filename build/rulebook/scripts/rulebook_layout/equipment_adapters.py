from __future__ import annotations

import copy
from typing import Any, Iterable

from rulebook_layout.equipment_catalog import replace_family_div_with_latex
from rulebook_layout.equipment_integration import EQUIPMENT_FAMILIES, EquipmentPayload
from rulebook_layout.integration import AdapterResult, ExactAdapterSpec, execute_exact_adapter
from rulebook_layout.integration_ast import (
    canonical_ast_sha256,
    family_body_is_exact_raw_latex,
    find_family_divs,
)


EQUIPMENT_PROFILES = ("complete-rulebook", "player-guide")
EQUIPMENT_ORDER = tuple(family for _chapter, family, _config in EQUIPMENT_FAMILIES)


def integrate_equipment_family_with_adapter(
    ast: dict[str, Any],
    profile: str,
    family: str,
    latex: str,
) -> AdapterResult:
    """Replace one Equipment family body through the common exact-adapter contract."""
    spec = ExactAdapterSpec(
        name=f"equipment:{family}",
        order=70,
        profiles=EQUIPMENT_PROFILES,
        expected={"familyBody": 1},
    )

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        unresolved = 0
        for div in find_family_divs(value, family):
            content = div.get("c")
            body = content[1] if isinstance(content, list) and len(content) == 2 else None
            if body != [{"t": "RawBlock", "c": ["latex", latex]}]:
                unresolved += 1
        return {"familyBody": unresolved}

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyBody": 1 if family_body_is_exact_raw_latex(value, family, latex) else 0,
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        return {"familyBody": replace_family_div_with_latex(value, family, latex)}

    return execute_exact_adapter(
        ast,
        spec,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )


def _payload_order(payloads: Iterable[EquipmentPayload]) -> tuple[str, ...]:
    return tuple(payload.family for payload in payloads)


def integrate_equipment_stage(
    ast: dict[str, Any],
    profile: str,
    payloads: list[EquipmentPayload],
) -> dict[str, Any]:
    """Apply Chapters 15–22 atomically; discard the whole stage on any failure."""
    input_digest = canonical_ast_sha256(ast)
    result: dict[str, Any] = {
        "schema": "cybermancy-step6-equipment-adapter-stage-v1",
        "status": "PASS",
        "profile": profile,
        "order": 70,
        "families": list(EQUIPMENT_ORDER),
        "adapters": [],
        "idempotent": False,
        "inputAstSha256": input_digest,
        "outputAstSha256": input_digest,
    }

    if profile not in EQUIPMENT_PROFILES:
        result["status"] = "FAIL"
        result["error"] = f"Equipment stage is not allowed for profile {profile}."
        return result

    actual_order = _payload_order(payloads)
    if actual_order != EQUIPMENT_ORDER:
        result["status"] = "FAIL"
        result["error"] = "Equipment payloads are incomplete, duplicated, or out of Chapters 15–22 order."
        result["actualFamilies"] = list(actual_order)
        return result

    candidate = copy.deepcopy(ast)
    adapter_results: list[AdapterResult] = []
    for payload in payloads:
        adapter = integrate_equipment_family_with_adapter(
            candidate,
            profile,
            payload.family,
            payload.latex,
        )
        adapter_results.append(adapter)
        result["adapters"].append(adapter.as_dict())
        if adapter.status != "PASS":
            result["status"] = "FAIL"
            result["error"] = (
                f"Equipment adapter failed for Chapter {payload.chapter} family:{payload.family}; "
                "the entire stage mutation was discarded."
            )
            return result

    output_digest = canonical_ast_sha256(candidate)
    stage_idempotent = all(adapter.idempotent for adapter in adapter_results)
    ast.clear()
    ast.update(candidate)
    result["idempotent"] = stage_idempotent
    result["outputAstSha256"] = output_digest
    return result
