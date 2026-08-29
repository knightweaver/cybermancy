from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from rulebook_layout.ice_reference_package import integrate_chapter29_ast
from rulebook_layout.integration_ast import (
    canonical_ast_sha256,
    chapter_headers,
    count_chapter_header,
    count_raw_latex,
    document_text,
    family_body_is_exact_raw_latex,
    family_divs,
    find_family_divs,
)


GM_DIVIDER_DEFAULT = "GM MATERIAL — SPOILERS BEYOND THIS POINT"


def _check(
    report: dict[str, Any],
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def _chapter_map(contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in contract.get("chapterMap", []):
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("chapter"))
        except (TypeError, ValueError):
            continue
        result[number] = item
    return result


def structural_preflight(
    ast: dict[str, Any],
    contract: dict[str, Any],
    profile: str,
) -> dict[str, Any]:
    """Validate semantic AST structure before any Step 6 replacement."""
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-structural-preflight-v1",
        "status": "PASS",
        "profile": profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputAstSha256": canonical_ast_sha256(ast),
    }

    profiles = contract.get("profiles")
    if not isinstance(profiles, dict) or profile not in profiles:
        _check(report, "PROFILE_CONTRACT", "ERROR", f"Unknown Step 6 integration profile: {profile}")
        return report

    if not isinstance(ast.get("blocks"), list) or not isinstance(ast.get("meta"), dict):
        _check(
            report,
            "PANDOC_AST_SHAPE",
            "ERROR",
            "Input is not a Pandoc JSON document with meta and blocks.",
        )
        return report
    _check(report, "PANDOC_AST_SHAPE", "PASS", "Input has the required Pandoc JSON document shape.")

    profile_contract = profiles[profile]
    expected_chapters = [int(value) for value in profile_contract.get("chapters", [])]
    chapter_map = _chapter_map(contract)
    missing_map = [number for number in expected_chapters if number not in chapter_map]
    if missing_map:
        _check(
            report,
            "CHAPTER_MAP_CONTRACT",
            "ERROR",
            "Integration contract does not map every profile chapter.",
            missing_map,
        )
        return report
    _check(
        report,
        "CHAPTER_MAP_CONTRACT",
        "PASS",
        f"Integration contract maps all {len(expected_chapters)} profile chapters.",
    )

    headers = [item for item in chapter_headers(ast) if item.get("level") == 2]
    actual_ids = [str(item.get("chapterId") or "") for item in headers]
    expected_ids = [str(chapter_map[number].get("chapterId") or "") for number in expected_chapters]
    header_counts = {chapter_id: actual_ids.count(chapter_id) for chapter_id in expected_ids}
    extras = [chapter_id for chapter_id in actual_ids if chapter_id not in expected_ids]
    chapter_ok = actual_ids == expected_ids and all(count == 1 for count in header_counts.values()) and not extras
    _check(
        report,
        "CHAPTER_IDENTITY_ORDER",
        "PASS" if chapter_ok else "ERROR",
        "Profile chapter headers are present exactly once and in authoritative order."
        if chapter_ok
        else "Profile chapter headers are missing, duplicated, unexpected, or out of order.",
        {
            "expected": expected_ids,
            "actual": actual_ids,
            "counts": header_counts,
            "unexpected": extras,
        },
    )

    audience_errors: list[dict[str, Any]] = []
    actual_by_id = {str(item.get("chapterId") or ""): item for item in headers}
    for number in expected_chapters:
        spec = chapter_map[number]
        chapter_id = str(spec.get("chapterId") or "")
        expected_audience = str(spec.get("audience") or "")
        actual = actual_by_id.get(chapter_id)
        actual_audience = str((actual or {}).get("audience") or "")
        if actual_audience != expected_audience:
            audience_errors.append(
                {
                    "chapter": number,
                    "chapterId": chapter_id,
                    "expected": expected_audience,
                    "actual": actual_audience or None,
                }
            )
    _check(
        report,
        "CHAPTER_AUDIENCE",
        "ERROR" if audience_errors else "PASS",
        "Every chapter carries the authoritative audience marker."
        if not audience_errors
        else "One or more chapter audience markers differ from the integration contract.",
        audience_errors or None,
    )

    reserved_errors: list[dict[str, Any]] = []
    for reserved_text, rule in (contract.get("reservedChapters") or {}).items():
        try:
            reserved = int(reserved_text)
        except (TypeError, ValueError):
            continue
        prefix = f"ch{reserved:02d}-"
        matches = [chapter_id for chapter_id in actual_ids if chapter_id.startswith(prefix)]
        if matches and not bool((rule or {}).get("chapterNodeAllowed", False)):
            reserved_errors.append({"chapter": reserved, "chapterIds": matches})
    _check(
        report,
        "RESERVED_CHAPTERS",
        "ERROR" if reserved_errors else "PASS",
        "Reserved chapters have no AST chapter nodes."
        if not reserved_errors
        else "A reserved chapter unexpectedly has an AST chapter node.",
        reserved_errors or None,
    )

    present_families = family_divs(ast)
    family_errors: list[dict[str, Any]] = []
    expected_families: list[str] = []
    for target in contract.get("structuredTargets", []):
        if not isinstance(target, dict):
            continue
        profiles_for_target = target.get("profiles")
        applies = not isinstance(profiles_for_target, list) or profile in profiles_for_target
        for family in target.get("families", []):
            identifier = f"family:{family}"
            count = present_families.count(identifier)
            expected = 1 if applies else 0
            if applies:
                expected_families.append(identifier)
            if count != expected:
                family_errors.append(
                    {
                        "chapter": target.get("chapter"),
                        "family": identifier,
                        "expected": expected,
                        "actual": count,
                    }
                )
    _check(
        report,
        "STRUCTURED_FAMILY_TARGETS",
        "ERROR" if family_errors else "PASS",
        "Structured family containers match the profile integration contract."
        if not family_errors
        else "Structured family containers are missing, duplicated, or present in the wrong profile.",
        {
            "expected": expected_families,
            "actual": present_families,
            "mismatches": family_errors,
        },
    )

    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)
    divider_count = document_text(ast).count(divider_text)
    expected_dividers = int(profile_contract.get("gmDividerCount") or 0)
    _check(
        report,
        "GM_DIVIDER",
        "PASS" if divider_count == expected_dividers else "ERROR",
        f"GM divider count is {divider_count}, expected {expected_dividers}."
        if divider_count == expected_dividers
        else "GM divider count does not match the profile contract.",
        {"text": divider_text, "expected": expected_dividers, "actual": divider_count},
    )

    if profile == "player-guide":
        gm_headers = [item for item in headers if str(item.get("audience") or "") == "gm"]
        _check(
            report,
            "PLAYER_GUIDE_GM_EXCLUSION",
            "ERROR" if gm_headers else "PASS",
            "Player Guide contains no GM chapter headers."
            if not gm_headers
            else "Player Guide contains GM chapter headers.",
            gm_headers or None,
        )

    report["inventory"] = {
        "chapters": actual_ids,
        "families": present_families,
        "gmDividerCount": divider_count,
    }
    return report


@dataclass(frozen=True)
class ExactAdapterSpec:
    name: str
    order: int
    profiles: tuple[str, ...]
    expected: dict[str, int]


@dataclass
class AdapterResult:
    adapter: str
    order: int
    profile: str
    status: str
    expected: dict[str, int]
    found: dict[str, int]
    replaced: dict[str, int]
    remaining: dict[str, int]
    integrated: dict[str, int]
    idempotent: bool = False
    error: str | None = None
    inputAstSha256: str | None = None
    outputAstSha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "adapter": self.adapter,
            "order": self.order,
            "profile": self.profile,
            "status": self.status,
            "expected": dict(self.expected),
            "found": dict(self.found),
            "replaced": dict(self.replaced),
            "remaining": dict(self.remaining),
            "integrated": dict(self.integrated),
            "idempotent": self.idempotent,
            "inputAstSha256": self.inputAstSha256,
            "outputAstSha256": self.outputAstSha256,
        }
        if self.error:
            value["error"] = self.error
        return value


Probe = Callable[[dict[str, Any]], dict[str, int]]
Mutator = Callable[[dict[str, Any]], dict[str, int]]


def _matches(actual: dict[str, int], expected: dict[str, int]) -> bool:
    return all(int(actual.get(key, 0)) == int(value) for key, value in expected.items())


def execute_exact_adapter(
    ast: dict[str, Any],
    spec: ExactAdapterSpec,
    profile: str,
    unresolved_probe: Probe,
    integrated_probe: Probe,
    mutate: Mutator,
) -> AdapterResult:
    """Apply one semantic adapter exactly once, without partial mutation."""
    input_digest = canonical_ast_sha256(ast)
    empty = {key: 0 for key in spec.expected}

    if profile not in spec.profiles:
        return AdapterResult(
            adapter=spec.name,
            order=spec.order,
            profile=profile,
            status="FAIL",
            expected=dict(spec.expected),
            found=empty,
            replaced=empty,
            remaining=empty,
            integrated=empty,
            error=f"Adapter {spec.name} is not allowed for profile {profile}.",
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
        )

    found = unresolved_probe(ast)
    already = integrated_probe(ast)
    if _matches(found, empty) and _matches(already, spec.expected):
        return AdapterResult(
            adapter=spec.name,
            order=spec.order,
            profile=profile,
            status="PASS",
            expected=dict(spec.expected),
            found=found,
            replaced=empty,
            remaining=empty,
            integrated=already,
            idempotent=True,
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
        )

    if not _matches(found, spec.expected):
        return AdapterResult(
            adapter=spec.name,
            order=spec.order,
            profile=profile,
            status="FAIL",
            expected=dict(spec.expected),
            found=found,
            replaced=empty,
            remaining=found,
            integrated=already,
            error="Adapter semantic preconditions were not met; AST was not mutated.",
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
        )

    candidate = copy.deepcopy(ast)
    replaced = mutate(candidate)
    remaining = unresolved_probe(candidate)
    integrated = integrated_probe(candidate)
    if not _matches(replaced, spec.expected) or not _matches(remaining, empty) or not _matches(integrated, spec.expected):
        return AdapterResult(
            adapter=spec.name,
            order=spec.order,
            profile=profile,
            status="FAIL",
            expected=dict(spec.expected),
            found=found,
            replaced=replaced,
            remaining=remaining,
            integrated=integrated,
            error="Adapter postconditions failed; staged mutation was discarded.",
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
        )

    ast.clear()
    ast.update(candidate)
    return AdapterResult(
        adapter=spec.name,
        order=spec.order,
        profile=profile,
        status="PASS",
        expected=dict(spec.expected),
        found=found,
        replaced=replaced,
        remaining=remaining,
        integrated=integrated,
        inputAstSha256=input_digest,
        outputAstSha256=canonical_ast_sha256(ast),
    )


CHAPTER29_ADAPTER = ExactAdapterSpec(
    name="ice-reference",
    order=90,
    profiles=("complete-rulebook",),
    expected={"chapterHeader": 1, "familyFeatures": 1},
)


def integrate_chapter29_with_adapter(
    ast: dict[str, Any],
    profile: str,
    header_latex: str,
    body_latex: str,
) -> AdapterResult:
    """Apply frozen Chapter 29 through the common exact adapter contract."""

    def unresolved_probe(value: dict[str, Any]) -> dict[str, int]:
        header_count = count_chapter_header(value, "ch29-ice-reference")
        divs = find_family_divs(value, "features")
        unresolved_family = 0
        for div in divs:
            content = div.get("c")
            body = content[1] if isinstance(content, list) and len(content) == 2 else None
            if body != [{"t": "RawBlock", "c": ["latex", body_latex]}]:
                unresolved_family += 1
        return {"chapterHeader": header_count, "familyFeatures": unresolved_family}

    def integrated_probe(value: dict[str, Any]) -> dict[str, int]:
        return {
            "chapterHeader": count_raw_latex(value, header_latex),
            "familyFeatures": 1 if family_body_is_exact_raw_latex(value, "features", body_latex) else 0,
        }

    def mutate(value: dict[str, Any]) -> dict[str, int]:
        return integrate_chapter29_ast(value, header_latex, body_latex)

    return execute_exact_adapter(
        ast,
        CHAPTER29_ADAPTER,
        profile,
        unresolved_probe,
        integrated_probe,
        mutate,
    )
