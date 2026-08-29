from __future__ import annotations

import copy
from typing import Any

from rulebook_layout.character_options_integration import (
    ClassStagePayload,
    DomainStagePayload,
)
from rulebook_layout.equipment_catalog import replace_family_div_with_latex
from rulebook_layout.integration import AdapterResult, ExactAdapterSpec, execute_exact_adapter
from rulebook_layout.integration_ast import (
    canonical_ast_sha256,
    family_body_is_exact_raw_latex,
    find_family_divs,
)


CHARACTER_OPTION_PROFILES = ("complete-rulebook", "player-guide")

CLASS_ADAPTER = ExactAdapterSpec(
    name="class-package",
    order=50,
    profiles=CHARACTER_OPTION_PROFILES,
    expected={"familyClasses": 1, "familySubclasses": 1},
)

DOMAIN_ADAPTER = ExactAdapterSpec(
    name="domain-package",
    order=60,
    profiles=CHARACTER_OPTION_PROFILES,
    expected={"familyDomains": 1},
)


def _unresolved_family_count(
    ast: dict[str, Any], family: str, latex: str
) -> int:
    unresolved = 0
    for div in find_family_divs(ast, family):
        content = div.get("c")
        body = content[1] if isinstance(content, list) and len(content) == 2 else None
        if body != [{"t": "RawBlock", "c": ["latex", latex]}]:
            unresolved += 1
    return unresolved


def integrate_class_stage_with_adapter(
    ast: dict[str, Any],
    profile: str,
    payload: ClassStagePayload,
) -> AdapterResult:
    """Replace Chapter 12's Class/Subclass family bodies as one exact adapter."""

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyClasses": _unresolved_family_count(
                value, "classes", payload.classes_latex
            ),
            "familySubclasses": _unresolved_family_count(
                value, "subclasses", payload.subclasses_latex
            ),
        }

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyClasses": 1
            if family_body_is_exact_raw_latex(
                value, "classes", payload.classes_latex
            )
            else 0,
            "familySubclasses": 1
            if family_body_is_exact_raw_latex(
                value, "subclasses", payload.subclasses_latex
            )
            else 0,
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyClasses": replace_family_div_with_latex(
                value, "classes", payload.classes_latex
            ),
            "familySubclasses": replace_family_div_with_latex(
                value, "subclasses", payload.subclasses_latex
            ),
        }

    return execute_exact_adapter(
        ast,
        CLASS_ADAPTER,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )


def integrate_domain_stage_with_adapter(
    ast: dict[str, Any],
    profile: str,
    payload: DomainStagePayload,
) -> AdapterResult:
    """Replace Chapter 14's Domain family body through the common adapter."""

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyDomains": _unresolved_family_count(
                value, "domains", payload.domains_latex
            )
        }

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyDomains": 1
            if family_body_is_exact_raw_latex(
                value, "domains", payload.domains_latex
            )
            else 0
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        return {
            "familyDomains": replace_family_div_with_latex(
                value, "domains", payload.domains_latex
            )
        }

    return execute_exact_adapter(
        ast,
        DOMAIN_ADAPTER,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )


def integrate_character_options_stage(
    ast: dict[str, Any],
    profile: str,
    class_payload: ClassStagePayload,
    domain_payload: DomainStagePayload,
) -> dict[str, Any]:
    """Apply orders 50 and 60 transactionally; discard both on either failure."""
    input_digest = canonical_ast_sha256(ast)
    result: dict[str, Any] = {
        "schema": "cybermancy-step6-character-options-adapter-stage-v1",
        "status": "PASS",
        "profile": profile,
        "orders": [50, 60],
        "adapters": [],
        "idempotent": False,
        "inputAstSha256": input_digest,
        "outputAstSha256": input_digest,
    }

    if profile not in CHARACTER_OPTION_PROFILES:
        result["status"] = "FAIL"
        result["error"] = (
            f"Character-options stage is not allowed for profile {profile}."
        )
        return result

    candidate = copy.deepcopy(ast)
    class_result = integrate_class_stage_with_adapter(
        candidate, profile, class_payload
    )
    result["adapters"].append(class_result.as_dict())
    if class_result.status != "PASS":
        result["status"] = "FAIL"
        result["error"] = (
            "Chapter 12 ClassPackage adapter failed; the entire Character Options "
            "stage mutation was discarded."
        )
        return result

    domain_result = integrate_domain_stage_with_adapter(
        candidate, profile, domain_payload
    )
    result["adapters"].append(domain_result.as_dict())
    if domain_result.status != "PASS":
        result["status"] = "FAIL"
        result["error"] = (
            "Chapter 14 DomainPackage adapter failed after Chapter 12 staged "
            "successfully; both staged mutations were discarded."
        )
        return result

    output_digest = canonical_ast_sha256(candidate)
    ast.clear()
    ast.update(candidate)
    result["idempotent"] = class_result.idempotent and domain_result.idempotent
    result["outputAstSha256"] = output_digest
    return result
