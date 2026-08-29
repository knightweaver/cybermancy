from __future__ import annotations

import re
from typing import Any

from rulebook_layout.integration_ast import (
    block_text,
    canonical_ast_sha256,
    canonical_chapter_id,
    find_family_divs,
    iter_ast_nodes,
    node_classes,
    node_identifier,
    normalize_identifier,
)
from rulebook_layout.publication_shell import (
    COLUMN_CHAPTERS,
    GM_DIVIDER_DEFAULT,
    PACKAGE_HEADER_CHAPTERS,
    PART_BY_ID,
    PROFILE_PART_IDS,
    _chapter_end,
    _chapter_shell,
    _divider_shell,
    _part_shell,
)


STAGE_NAME = "post-transform-validation"
STAGE_ORDER = 140
SHELL_PREFIX = "% CM-INTEGRATED-SHELL "
PACKAGE_FAMILY_BY_CHAPTER = {
    29: "features",
    30: "adversaries",
    31: "environments",
    32: "adversaries-features",
}
PART_START_CHAPTER = {
    1: "part-i-world",
    4: "part-ii-rules",
    10: "part-iii-characters",
    15: "part-iv-equipment",
    23: "part-v-gm-world",
    29: "part-vi-gm-toolkit",
}


def _chapter_map(contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in contract.get("chapterMap") or []:
        if not isinstance(row, dict):
            continue
        try:
            number = int(row.get("chapter"))
        except (TypeError, ValueError):
            continue
        result[number] = row
    return result


def _profile_chapters(contract: dict[str, Any], profile: str) -> tuple[int, ...]:
    profiles = contract.get("profiles") if isinstance(contract.get("profiles"), dict) else {}
    row = profiles.get(profile) if isinstance(profiles.get(profile), dict) else {}
    return tuple(int(value) for value in row.get("chapters") or [])


def _shell_chapters(contract: dict[str, Any], profile: str) -> tuple[int, ...]:
    chapters = _profile_chapters(contract, profile)
    if profile == "complete-rulebook":
        return tuple(number for number in chapters if number not in PACKAGE_HEADER_CHAPTERS)
    return chapters


def _stage_spec(contract: dict[str, Any]) -> dict[str, Any] | None:
    for row in contract.get("transformationOrder") or []:
        if isinstance(row, dict) and row.get("stage") == STAGE_NAME:
            return row
    return None


def _raw_latex_text(node: Any) -> str | None:
    if not isinstance(node, dict) or node.get("t") != "RawBlock":
        return None
    content = node.get("c")
    if not (
        isinstance(content, list)
        and len(content) == 2
        and content[0] == "latex"
    ):
        return None
    return str(content[1] or "")


def _top_level_raw(ast: dict[str, Any]) -> list[tuple[int, str]]:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return []
    result: list[tuple[int, str]] = []
    for index, node in enumerate(blocks):
        raw = _raw_latex_text(node)
        if raw is not None:
            result.append((index, raw))
    return result


def _top_level_exact_count(ast: dict[str, Any], latex: str) -> int:
    return sum(1 for _index, raw in _top_level_raw(ast) if raw == latex)


def _expected_families(contract: dict[str, Any], profile: str) -> list[str]:
    result: list[str] = []
    for target in contract.get("structuredTargets") or []:
        if not isinstance(target, dict):
            continue
        profiles = target.get("profiles")
        if isinstance(profiles, list) and profile not in profiles:
            continue
        for family in target.get("families") or []:
            result.append(f"family:{family}")
    return result


def _family_identifiers(ast: dict[str, Any]) -> list[str]:
    return [
        normalize_identifier(node_identifier(node))
        for node in iter_ast_nodes(ast)
        if node.get("t") == "Div"
        and normalize_identifier(node_identifier(node)).startswith("family:")
    ]


def _family_body_exact_latex(ast: dict[str, Any], family: str) -> bool:
    divs = find_family_divs(ast, family)
    if len(divs) != 1:
        return False
    content = divs[0].get("c")
    if not (
        isinstance(content, list)
        and len(content) == 2
        and isinstance(content[1], list)
        and len(content[1]) == 1
    ):
        return False
    return bool(_raw_latex_text(content[1][0]))


def _expected_significant_sequence(
    contract: dict[str, Any], profile: str
) -> list[str]:
    chapters = _profile_chapters(contract, profile)
    families_by_chapter: dict[int, list[str]] = {}
    for target in contract.get("structuredTargets") or []:
        if not isinstance(target, dict):
            continue
        profiles = target.get("profiles")
        if isinstance(profiles, list) and profile not in profiles:
            continue
        chapter = int(target.get("chapter"))
        families_by_chapter.setdefault(chapter, []).extend(
            f"family:{family}" for family in target.get("families") or []
        )

    result: list[str] = []
    for chapter in chapters:
        if chapter == 23 and profile == "complete-rulebook":
            result.append("divider")
        part_id = PART_START_CHAPTER.get(chapter)
        if part_id and part_id in PROFILE_PART_IDS.get(profile, ()):
            result.append(f"part:{part_id}")
        if chapter not in PACKAGE_HEADER_CHAPTERS:
            result.append(f"chapter:{chapter}")
        result.extend(families_by_chapter.get(chapter, []))
    return result


def _actual_significant_sequence(
    ast: dict[str, Any], contract: dict[str, Any], profile: str
) -> list[str]:
    chapter_map = _chapter_map(contract)
    shell_chapters = _shell_chapters(contract, profile)
    expected_parts = PROFILE_PART_IDS.get(profile, ())
    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)

    part_lookup = {
        _part_shell(PART_BY_ID[part_id]): f"part:{part_id}"
        for part_id in expected_parts
    }
    chapter_lookup = {
        _chapter_shell(number, chapter_map[number], number in COLUMN_CHAPTERS): f"chapter:{number}"
        for number in shell_chapters
    }
    divider_latex = _divider_shell(divider_text)

    blocks = ast.get("blocks") if isinstance(ast.get("blocks"), list) else []
    result: list[str] = []
    for node in blocks:
        raw = _raw_latex_text(node)
        if raw is not None:
            if raw in part_lookup:
                result.append(part_lookup[raw])
                continue
            if raw in chapter_lookup:
                result.append(chapter_lookup[raw])
                continue
            if raw == divider_latex:
                result.append("divider")
                continue
        if isinstance(node, dict) and node.get("t") == "Div":
            ident = normalize_identifier(node_identifier(node))
            if ident.startswith("family:"):
                result.append(ident)
    return result


def _known_shell_raw(contract: dict[str, Any], profile: str) -> set[str]:
    chapter_map = _chapter_map(contract)
    shell_chapters = _shell_chapters(contract, profile)
    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)
    known: set[str] = set()
    for part_id in PROFILE_PART_IDS.get(profile, ()):
        known.add(_part_shell(PART_BY_ID[part_id]))
    for number in shell_chapters:
        known.add(_chapter_shell(number, chapter_map[number], number in COLUMN_CHAPTERS))
        if number in COLUMN_CHAPTERS:
            known.add(_chapter_end(number, str(chapter_map[number].get("chapterId") or "")))
    expected_divider = int(
        ((contract.get("profiles") or {}).get(profile) or {}).get("gmDividerCount") or 0
    )
    if expected_divider:
        known.add(_divider_shell(divider_text))
    return known


def _semantic_residue(ast: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    chapter_ids = {
        str(row.get("chapterId") or "")
        for row in contract.get("chapterMap") or []
        if isinstance(row, dict)
    }
    part_ids = {row["id"] for row in PART_BY_ID.values()}
    residue: list[dict[str, Any]] = []
    for node in iter_ast_nodes(ast):
        if node.get("t") != "Header":
            continue
        ident = normalize_identifier(node_identifier(node))
        canonical = canonical_chapter_id(ident)
        classes = node_classes(node)
        part_ident = ident[len("section:") :] if ident.startswith("section:") else ident
        if (
            "rb-part" in classes
            or "rb-chapter" in classes
            or canonical in chapter_ids
            or part_ident in part_ids
        ):
            residue.append(
                {
                    "identifier": ident,
                    "classes": classes,
                    "text": block_text(node),
                }
            )
    return residue


def _package_header_checks(ast: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    if profile != "complete-rulebook":
        return []
    blocks = ast.get("blocks") if isinstance(ast.get("blocks"), list) else []
    results: list[dict[str, Any]] = []
    for chapter, family in PACKAGE_FAMILY_BY_CHAPTER.items():
        identifier = f"family:{family}"
        indices = [
            index
            for index, node in enumerate(blocks)
            if isinstance(node, dict)
            and node.get("t") == "Div"
            and normalize_identifier(node_identifier(node)) == identifier
        ]
        ok = len(indices) == 1
        header_latex = None
        if ok:
            index = indices[0]
            if index <= 0:
                ok = False
            else:
                header_latex = _raw_latex_text(blocks[index - 1])
                if not header_latex or header_latex.startswith(SHELL_PREFIX):
                    ok = False
        results.append(
            {
                "chapter": chapter,
                "family": identifier,
                "status": "PASS" if ok else "ERROR",
                "headerPrecedesFamily": ok,
                "headerPreview": (header_latex or "")[:120],
            }
        )
    return results


def validate_post_transform(
    ast: dict[str, Any], contract: dict[str, Any], profile: str
) -> dict[str, Any]:
    """Validate the fully transformed Stage 130 AST without mutating it."""
    input_digest = canonical_ast_sha256(ast)
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage140-post-transform-validation-v1",
        "status": "PASS",
        "stage": STAGE_NAME,
        "order": STAGE_ORDER,
        "profile": profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputAstSha256": input_digest,
    }

    def check(code: str, ok: bool, message: str, details: Any = None) -> None:
        item: dict[str, Any] = {
            "code": code,
            "status": "PASS" if ok else "ERROR",
            "message": message,
        }
        if details is not None:
            item["details"] = details
        report["checks"].append(item)
        if not ok:
            report["status"] = "FAIL"
            report["errors"].append(item)

    stage = _stage_spec(contract)
    check(
        "STAGE140_CONTRACT",
        isinstance(stage, dict) and int(stage.get("order") or -1) == STAGE_ORDER,
        "Integration contract contains Stage 140 at canonical order 140.",
        stage,
    )

    blocks = ast.get("blocks")
    ast_shape_ok = isinstance(ast, dict) and isinstance(blocks, list)
    check(
        "STAGE140_AST_SHAPE",
        ast_shape_ok,
        "Input is a Pandoc JSON document with a top-level block list.",
    )
    if not ast_shape_ok:
        report["outputAstSha256"] = canonical_ast_sha256(ast)
        return report

    if profile not in PROFILE_PART_IDS:
        check(
            "STAGE140_PROFILE",
            False,
            f"Unsupported publication profile: {profile}",
        )
        report["outputAstSha256"] = canonical_ast_sha256(ast)
        return report
    check(
        "STAGE140_PROFILE",
        True,
        f"Validated publication profile {profile}.",
    )

    chapter_map = _chapter_map(contract)
    shell_chapters = _shell_chapters(contract, profile)
    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)
    expected_divider = int(
        ((contract.get("profiles") or {}).get(profile) or {}).get("gmDividerCount") or 0
    )

    shell_counts = {
        "parts": {
            part_id: _top_level_exact_count(ast, _part_shell(PART_BY_ID[part_id]))
            for part_id in PROFILE_PART_IDS[profile]
        },
        "chapters": {
            str(number): _top_level_exact_count(
                ast,
                _chapter_shell(number, chapter_map[number], number in COLUMN_CHAPTERS),
            )
            for number in shell_chapters
        },
        "columnEnds": {
            str(number): _top_level_exact_count(
                ast,
                _chapter_end(number, str(chapter_map[number].get("chapterId") or "")),
            )
            for number in shell_chapters
            if number in COLUMN_CHAPTERS
        },
        "gmDivider": _top_level_exact_count(ast, _divider_shell(divider_text)),
    }
    exact_shell_ok = (
        all(value == 1 for value in shell_counts["parts"].values())
        and all(value == 1 for value in shell_counts["chapters"].values())
        and all(value == 1 for value in shell_counts["columnEnds"].values())
        and shell_counts["gmDivider"] == expected_divider
    )
    check(
        "STAGE130_SHELL_EXACT",
        exact_shell_ok,
        "Every Stage 130 Part, Chapter, column-end, and divider shell occurs exactly as required.",
        shell_counts,
    )

    known_shell = _known_shell_raw(contract, profile)
    unexpected_shell = [
        {"index": index, "preview": raw[:180]}
        for index, raw in _top_level_raw(ast)
        if raw.startswith(SHELL_PREFIX) and raw not in known_shell
    ]
    check(
        "STAGE130_NO_UNEXPECTED_SHELL_MARKERS",
        not unexpected_shell,
        "No malformed, duplicate-purpose, or profile-inapplicable Stage 130 shell markers remain.",
        unexpected_shell,
    )

    expected_sequence = _expected_significant_sequence(contract, profile)
    actual_sequence = _actual_significant_sequence(ast, contract, profile)
    check(
        "POST_TRANSFORM_BOOK_ORDER",
        actual_sequence == expected_sequence,
        "Part, chapter, structured-family, and GM-divider landmarks remain in canonical publication order.",
        {"expected": expected_sequence, "actual": actual_sequence},
    )

    residue = _semantic_residue(ast, contract)
    check(
        "POST_TRANSFORM_NO_SEMANTIC_HEADER_RESIDUE",
        not residue,
        "No rb-part/rb-chapter or canonical Part/Chapter Header nodes remain after shell lowering.",
        residue,
    )

    reserved_hits: list[dict[str, Any]] = []
    for node in iter_ast_nodes(ast):
        ident = normalize_identifier(node_identifier(node))
        if ident and "ch13" in canonical_chapter_id(ident).lower():
            reserved_hits.append({"kind": node.get("t"), "identifier": ident})
        raw = _raw_latex_text(node)
        if raw and ("ch13" in raw.lower() or re.search(r"\\CMIntegratedChapter\{13\}", raw)):
            reserved_hits.append({"kind": "RawBlock", "preview": raw[:160]})
    check(
        "POST_TRANSFORM_RESERVED_CHAPTER_13",
        not reserved_hits,
        "Reserved Chapter 13 remains absent from semantic and lowered publication structures.",
        reserved_hits,
    )

    expected_families = _expected_families(contract, profile)
    actual_families = _family_identifiers(ast)
    family_coverage_ok = actual_families == expected_families
    check(
        "POST_TRANSFORM_STRUCTURED_FAMILY_COVERAGE",
        family_coverage_ok,
        "Structured family containers remain exact, unique, and in publication order.",
        {"expected": expected_families, "actual": actual_families},
    )

    family_body_errors = [
        family
        for family in expected_families
        if not _family_body_exact_latex(ast, family)
    ]
    check(
        "POST_TRANSFORM_STRUCTURED_FAMILY_BODIES",
        not family_body_errors,
        "Every structured family remains lowered to exactly one accepted LaTeX fragment.",
        family_body_errors,
    )

    package_checks = _package_header_checks(ast, profile)
    package_ok = all(row["status"] == "PASS" for row in package_checks)
    check(
        "POST_TRANSFORM_PACKAGE_HEADER_OWNERSHIP",
        package_ok,
        "Complete Rulebook package-owned Chapters 29-32 retain one package header immediately before their family body.",
        package_checks,
    )

    raw_texts = [
        raw
        for node in iter_ast_nodes(ast)
        for raw in [_raw_latex_text(node)]
        if raw is not None
    ]
    combined_raw = "\n".join(raw_texts)
    begin_multicols = combined_raw.count(r"\begin{multicols}{2}")
    end_multicols = combined_raw.count(r"\end{multicols}")
    expected_outer = sum(1 for number in shell_chapters if number in COLUMN_CHAPTERS)
    multicols_ok = (
        begin_multicols == end_multicols
        and shell_counts["columnEnds"]
        and sum(shell_counts["columnEnds"].values()) == expected_outer
    )
    check(
        "POST_TRANSFORM_MULTICOLS_BALANCE",
        bool(multicols_ok),
        "Integrated two-column scopes are globally balanced and every outer column chapter has its Stage 130 closing block.",
        {
            "beginMulticols": begin_multicols,
            "endMulticols": end_multicols,
            "expectedOuterScopes": expected_outer,
        },
    )

    shell_leakage = [
        token
        for token in (r"\documentclass", r"\begin{document}", r"\end{document}")
        if token in combined_raw
    ]
    check(
        "POST_TRANSFORM_NO_STANDALONE_DOCUMENT_SHELL",
        not shell_leakage,
        "No standalone LaTeX document shell leaked from frozen package/prose fragments.",
        shell_leakage,
    )

    gm_shell_hits = [raw for raw in raw_texts if "{gm}" in raw and raw.startswith(SHELL_PREFIX)]
    if profile == "player-guide":
        profile_boundary_ok = not gm_shell_hits and expected_divider == 0
    else:
        profile_boundary_ok = expected_divider == 1 and bool(gm_shell_hits)
    check(
        "POST_TRANSFORM_PROFILE_AUDIENCE_BOUNDARY",
        profile_boundary_ok,
        "Player/GM publication-shell audience boundaries match the selected profile.",
        {"gmShellBlockCount": len(gm_shell_hits), "expectedDivider": expected_divider},
    )

    output_digest = canonical_ast_sha256(ast)
    immutable = input_digest == output_digest
    check(
        "STAGE140_NON_MUTATING",
        immutable,
        "Stage 140 validation is a byte-stable, non-mutating inspection of the Stage 130 AST.",
        {"before": input_digest, "after": output_digest},
    )
    report["outputAstSha256"] = output_digest
    return report
