from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from rulebook_layout.integration_ast import (
    block_text,
    canonical_ast_sha256,
    canonical_chapter_id,
    find_family_divs,
    node_attributes,
    node_classes,
    node_identifier,
    normalize_identifier,
)


STAGE_NAME = "publication-shell-lowering"
STAGE_ORDER = 130
GM_DIVIDER_DEFAULT = "GM MATERIAL — SPOILERS BEYOND THIS POINT"

# Part identity is frozen by the approved Step 3 book architecture. Stage 130
# binds those semantic Part nodes to an intermediate whole-book shell interface;
# Stage 150 will define the macros in one integrated LaTeX preamble.
PARTS: tuple[dict[str, str], ...] = (
    {
        "id": "part-i-world",
        "roman": "I",
        "title": "The World of Cybermancy",
        "audience": "player",
    },
    {
        "id": "part-ii-rules",
        "roman": "II",
        "title": "Cybermancy Rules",
        "audience": "player",
    },
    {
        "id": "part-iii-characters",
        "roman": "III",
        "title": "Characters and Character Options",
        "audience": "player",
    },
    {
        "id": "part-iv-equipment",
        "roman": "IV",
        "title": "Equipment and Technology",
        "audience": "player",
    },
    {
        "id": "part-v-gm-world",
        "roman": "V",
        "title": "GM World Guide",
        "audience": "gm",
    },
    {
        "id": "part-vi-gm-toolkit",
        "roman": "VI",
        "title": "GM Encounter Toolkit",
        "audience": "gm",
    },
)
PART_BY_ID = {row["id"]: row for row in PARTS}
PROFILE_PART_IDS = {
    "player-guide": tuple(row["id"] for row in PARTS[:4]),
    "complete-rulebook": tuple(row["id"] for row in PARTS),
}

# Frozen prose/rules/origins body fragments expect an outer two-column context.
COLUMN_CHAPTERS = (
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    23,
    24,
    25,
    26,
    27,
    28,
)

# Orders 90-120 already lower these package-owned chapter headers.
PACKAGE_HEADER_CHAPTERS = (29, 30, 31, 32)


@dataclass
class PublicationShellResult:
    status: str
    profile: str
    expected: dict[str, int]
    found: dict[str, int]
    replaced: dict[str, int]
    integrated: dict[str, int]
    idempotent: bool = False
    error: str | None = None
    inputAstSha256: str | None = None
    outputAstSha256: str | None = None
    readiness: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "stage": STAGE_NAME,
            "order": STAGE_ORDER,
            "status": self.status,
            "profile": self.profile,
            "expected": dict(self.expected),
            "found": dict(self.found),
            "replaced": dict(self.replaced),
            "integrated": dict(self.integrated),
            "idempotent": self.idempotent,
            "inputAstSha256": self.inputAstSha256,
            "outputAstSha256": self.outputAstSha256,
        }
        if self.error:
            value["error"] = self.error
        if self.readiness is not None:
            value["readiness"] = self.readiness
        return value


def _latex_escape(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def _raw_latex(text: str) -> dict[str, Any]:
    return {"t": "RawBlock", "c": ["latex", text]}


def _header_level(node: dict[str, Any]) -> int | None:
    if node.get("t") != "Header":
        return None
    content = node.get("c")
    if not isinstance(content, list) or not content:
        return None
    return content[0] if isinstance(content[0], int) else None


def _canonical_part_id(value: str) -> str:
    ident = normalize_identifier(value)
    if ident.startswith("section:"):
        ident = ident[len("section:") :]
    return ident


def _is_part_header(node: dict[str, Any]) -> bool:
    return (
        _header_level(node) == 1
        and "rb-part" in node_classes(node)
        and _canonical_part_id(node_identifier(node)).startswith("part-")
    )


def _is_chapter_header(node: dict[str, Any]) -> bool:
    return (
        _header_level(node) == 2
        and "rb-chapter" in node_classes(node)
        and canonical_chapter_id(node_identifier(node)).startswith("ch")
    )


def _part_shell(row: dict[str, str]) -> str:
    return (
        f"% CM-INTEGRATED-SHELL PART {row['id']}\n"
        f"\\CMIntegratedPart{{{row['roman']}}}"
        f"{{{_latex_escape(row['title'])}}}"
        f"{{{row['audience']}}}"
        f"{{{_latex_escape(row['id'])}}}\n"
    )


def _chapter_shell(chapter: int, spec: dict[str, Any], columns: bool) -> str:
    chapter_id = str(spec.get("chapterId") or "")
    text = (
        f"% CM-INTEGRATED-SHELL CHAPTER {chapter_id} BEGIN\n"
        f"\\CMIntegratedChapter{{{chapter}}}"
        f"{{{_latex_escape(spec.get('title'))}}}"
        f"{{{_latex_escape(spec.get('audience'))}}}"
        f"{{{_latex_escape(chapter_id)}}}\n"
    )
    if columns:
        text += "\\begin{multicols}{2}\n"
    return text


def _chapter_end(chapter: int, chapter_id: str) -> str:
    return (
        f"% CM-INTEGRATED-SHELL CHAPTER {chapter_id} END\n"
        "\\end{multicols}\n"
    )


def _divider_shell(text: str) -> str:
    return (
        "% CM-INTEGRATED-SHELL GM-DIVIDER\n"
        f"\\CMIntegratedGMDivider{{{_latex_escape(text)}}}\n"
    )


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


def _count_exact_raw(ast: dict[str, Any], text: str) -> int:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return 0
    return sum(1 for node in blocks if _raw_latex_text(node) == text)


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


def _stage_spec(contract: dict[str, Any]) -> dict[str, Any] | None:
    for row in contract.get("transformationOrder") or []:
        if isinstance(row, dict) and row.get("stage") == STAGE_NAME:
            return row
    return None


def _expected_shell_chapters(
    contract: dict[str, Any], profile: str
) -> tuple[int, ...]:
    profiles = (
        contract.get("profiles")
        if isinstance(contract.get("profiles"), dict)
        else {}
    )
    profile_row = (
        profiles.get(profile)
        if isinstance(profiles.get(profile), dict)
        else {}
    )
    chapters = tuple(int(value) for value in profile_row.get("chapters") or [])
    if profile == "complete-rulebook":
        return tuple(
            number for number in chapters if number not in PACKAGE_HEADER_CHAPTERS
        )
    return chapters


def _top_level_part_headers(
    ast: dict[str, Any],
) -> list[tuple[int, dict[str, Any]]]:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return []
    return [
        (i, node)
        for i, node in enumerate(blocks)
        if isinstance(node, dict) and _is_part_header(node)
    ]


def _top_level_chapter_headers(
    ast: dict[str, Any],
) -> list[tuple[int, dict[str, Any]]]:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return []
    return [
        (i, node)
        for i, node in enumerate(blocks)
        if isinstance(node, dict) and _is_chapter_header(node)
    ]


def _next_structural_header(blocks: list[Any], start: int) -> int:
    for index in range(start + 1, len(blocks)):
        node = blocks[index]
        if isinstance(node, dict) and (
            _is_part_header(node) or _is_chapter_header(node)
        ):
            return index
    return len(blocks)


def _exact_divider_indices(
    ast: dict[str, Any], divider_text: str
) -> list[int]:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return []
    wanted = " ".join(divider_text.split())
    return [
        index
        for index, node in enumerate(blocks)
        if isinstance(node, dict) and block_text(node) == wanted
    ]


def _family_body_is_raw_latex(ast: dict[str, Any], family: str) -> bool:
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


def _readiness_report(
    ast: dict[str, Any], contract: dict[str, Any], profile: str
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage130-readiness-v1",
        "status": "PASS",
        "checks": [],
        "errors": [],
    }

    def check(code: str, ok: bool, details: Any = None) -> None:
        item: dict[str, Any] = {
            "code": code,
            "status": "PASS" if ok else "ERROR",
        }
        if details is not None:
            item["details"] = details
        report["checks"].append(item)
        if not ok:
            report["status"] = "FAIL"
            report["errors"].append(item)

    stage = _stage_spec(contract)
    check(
        "STAGE130_CONTRACT",
        isinstance(stage, dict)
        and int(stage.get("order") or -1) == STAGE_ORDER,
        stage,
    )

    expected_parts = PROFILE_PART_IDS.get(profile, ())
    part_rows = _top_level_part_headers(ast)
    actual_parts = [
        _canonical_part_id(node_identifier(node)) for _index, node in part_rows
    ]
    part_details: list[dict[str, Any]] = []
    for _index, node in part_rows:
        part_id = _canonical_part_id(node_identifier(node))
        expected = PART_BY_ID.get(part_id) or {}
        part_details.append(
            {
                "partId": part_id,
                "title": block_text(node),
                "audience": node_attributes(node).get("data-audience"),
                "expectedTitle": expected.get("title"),
                "expectedAudience": expected.get("audience"),
            }
        )
    parts_ok = actual_parts == list(expected_parts) and all(
        row["title"] == row["expectedTitle"]
        and row["audience"] == row["expectedAudience"]
        for row in part_details
    )
    check(
        "PHASE_C_PART_BOUNDARIES",
        parts_ok,
        {
            "expected": list(expected_parts),
            "actual": actual_parts,
            "parts": part_details,
        },
    )

    chapter_map = _chapter_map(contract)
    expected_chapters = _expected_shell_chapters(contract, profile)
    chapter_rows = _top_level_chapter_headers(ast)
    actual_chapters = [
        canonical_chapter_id(node_identifier(node))
        for _index, node in chapter_rows
    ]
    expected_ids = [
        str(chapter_map[number].get("chapterId") or "")
        for number in expected_chapters
    ]

    chapter_details: list[dict[str, Any]] = []
    for _index, node in chapter_rows:
        chapter_id = canonical_chapter_id(node_identifier(node))
        number = next(
            (
                n
                for n, spec in chapter_map.items()
                if str(spec.get("chapterId") or "") == chapter_id
            ),
            None,
        )
        expected = chapter_map.get(number or -1, {})
        chapter_details.append(
            {
                "chapter": number,
                "chapterId": chapter_id,
                "title": block_text(node),
                "audience": node_attributes(node).get("data-audience"),
                "expectedTitle": expected.get("title"),
                "expectedAudience": expected.get("audience"),
            }
        )

    # Stage 10 has already proven exact semantic chapter identity/order and
    # authoritative audience. Stage 130 owns the visible shell title and lowers
    # it from the accepted integration contract. Therefore title text in the
    # surviving semantic H2 is diagnostic input, not a fail-closed precondition.
    # This matters for the real Step 4 AST, whose semantic headings can retain a
    # source/publication label while still targeting the exact canonical chapter.
    audience_mismatches = [
        row
        for row in chapter_details
        if row["audience"] != row["expectedAudience"]
    ]
    title_canonicalizations = [
        {
            "chapter": row["chapter"],
            "chapterId": row["chapterId"],
            "sourceTitle": row["title"],
            "canonicalTitle": row["expectedTitle"],
        }
        for row in chapter_details
        if row["title"] != row["expectedTitle"]
    ]
    chapters_ok = actual_chapters == expected_ids and not audience_mismatches
    check(
        "PHASE_C_REMAINING_CHAPTER_HEADERS",
        chapters_ok,
        {
            "expected": expected_ids,
            "actual": actual_chapters,
            "audienceMismatches": audience_mismatches,
            "titleCanonicalizations": title_canonicalizations,
        },
    )

    package_header_errors: list[int] = []
    if profile == "complete-rulebook":
        semantic_ids = set(actual_chapters)
        for number in PACKAGE_HEADER_CHAPTERS:
            chapter_id = str(chapter_map[number].get("chapterId") or "")
            if chapter_id in semantic_ids:
                package_header_errors.append(number)
    check(
        "PHASE_C_PACKAGE_HEADERS_ALREADY_LOWERED",
        not package_header_errors,
        package_header_errors
        or list(
            PACKAGE_HEADER_CHAPTERS
            if profile == "complete-rulebook"
            else ()
        ),
    )

    blocks = ast.get("blocks") if isinstance(ast.get("blocks"), list) else []
    body_errors: list[dict[str, Any]] = []
    column_scope = [
        number for number in COLUMN_CHAPTERS if number in expected_chapters
    ]
    index_by_id = {
        canonical_chapter_id(node_identifier(node)): index
        for index, node in chapter_rows
    }
    for number in column_scope:
        spec = chapter_map[number]
        chapter_id = str(spec.get("chapterId") or "")
        start = index_by_id.get(chapter_id)
        if start is None:
            body_errors.append(
                {"chapter": number, "chapterId": chapter_id, "issue": "missing-header"}
            )
            continue
        end = _next_structural_header(blocks, start)
        body = blocks[start + 1 : end]
        if len(body) != 1 or not _raw_latex_text(body[0]):
            body_errors.append(
                {
                    "chapter": number,
                    "chapterId": chapter_id,
                    "issue": "body-not-exactly-one-latex-fragment",
                    "blockCount": len(body),
                    "blockTypes": [
                        node.get("t")
                        if isinstance(node, dict)
                        else type(node).__name__
                        for node in body
                    ],
                }
            )
    check(
        "PHASE_C_COLUMN_BODY_FRAGMENTS",
        not body_errors,
        body_errors or column_scope,
    )

    family_errors: list[dict[str, Any]] = []
    for target in contract.get("structuredTargets") or []:
        if not isinstance(target, dict):
            continue
        profiles = target.get("profiles")
        applies = not isinstance(profiles, list) or profile in profiles
        if not applies:
            continue
        for family in target.get("families") or []:
            if not _family_body_is_raw_latex(ast, str(family)):
                family_errors.append(
                    {
                        "chapter": target.get("chapter"),
                        "family": family,
                    }
                )
    check(
        "PHASE_C_STRUCTURED_FAMILY_BODIES",
        not family_errors,
        family_errors or "all applicable family bodies are exact LaTeX fragments",
    )

    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)
    divider_indices = _exact_divider_indices(ast, divider_text)
    expected_dividers = int(
        ((contract.get("profiles") or {}).get(profile) or {}).get(
            "gmDividerCount"
        )
        or 0
    )
    check(
        "PHASE_C_GM_DIVIDER",
        len(divider_indices) == expected_dividers,
        {
            "expected": expected_dividers,
            "actual": len(divider_indices),
            "indices": divider_indices,
        },
    )

    return report


def _integrated_counts(
    ast: dict[str, Any], contract: dict[str, Any], profile: str
) -> dict[str, int]:
    expected_parts = PROFILE_PART_IDS.get(profile, ())
    chapter_map = _chapter_map(contract)
    shell_chapters = _expected_shell_chapters(contract, profile)
    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)
    expected_divider = int(
        ((contract.get("profiles") or {}).get(profile) or {}).get(
            "gmDividerCount"
        )
        or 0
    )

    part_count = sum(
        _count_exact_raw(ast, _part_shell(PART_BY_ID[part_id]))
        for part_id in expected_parts
    )
    chapter_count = sum(
        _count_exact_raw(
            ast,
            _chapter_shell(
                number,
                chapter_map[number],
                number in COLUMN_CHAPTERS,
            ),
        )
        for number in shell_chapters
    )
    column_end_count = sum(
        _count_exact_raw(
            ast,
            _chapter_end(
                number,
                str(chapter_map[number].get("chapterId") or ""),
            ),
        )
        for number in shell_chapters
        if number in COLUMN_CHAPTERS
    )
    divider_count = _count_exact_raw(ast, _divider_shell(divider_text))
    return {
        "parts": part_count,
        "chapters": chapter_count,
        "columnEnds": column_end_count,
        "gmDivider": divider_count,
        "semanticParts": len(_top_level_part_headers(ast)),
        "semanticChapters": len(_top_level_chapter_headers(ast)),
        "rawDividerText": len(_exact_divider_indices(ast, divider_text)),
        "expectedDivider": expected_divider,
    }


def _expected_counts(contract: dict[str, Any], profile: str) -> dict[str, int]:
    shell_chapters = _expected_shell_chapters(contract, profile)
    expected_divider = int(
        ((contract.get("profiles") or {}).get(profile) or {}).get(
            "gmDividerCount"
        )
        or 0
    )
    return {
        "parts": len(PROFILE_PART_IDS.get(profile, ())),
        "chapters": len(shell_chapters),
        "columnEnds": sum(
            1 for number in shell_chapters if number in COLUMN_CHAPTERS
        ),
        "gmDivider": expected_divider,
        "semanticParts": 0,
        "semanticChapters": 0,
        "rawDividerText": 0,
    }


def _is_integrated(counts: dict[str, int], expected: dict[str, int]) -> bool:
    return all(counts.get(key) == value for key, value in expected.items())


def _lower_candidate(
    ast: dict[str, Any], contract: dict[str, Any], profile: str
) -> dict[str, int]:
    blocks = ast.get("blocks")
    if not isinstance(blocks, list):
        return {
            "parts": 0,
            "chapters": 0,
            "columnEnds": 0,
            "gmDivider": 0,
        }

    chapter_map = _chapter_map(contract)
    shell_chapters = set(_expected_shell_chapters(contract, profile))
    divider_text = str(contract.get("gmDividerText") or GM_DIVIDER_DEFAULT)
    divider_indices = set(_exact_divider_indices(ast, divider_text))

    output: list[Any] = []
    replaced = {
        "parts": 0,
        "chapters": 0,
        "columnEnds": 0,
        "gmDivider": 0,
    }
    index = 0
    while index < len(blocks):
        node = blocks[index]

        if index in divider_indices:
            output.append(_raw_latex(_divider_shell(divider_text)))
            replaced["gmDivider"] += 1
            index += 1
            continue

        if isinstance(node, dict) and _is_part_header(node):
            part_id = _canonical_part_id(node_identifier(node))
            row = PART_BY_ID.get(part_id)
            if row is None:
                output.append(node)
            else:
                output.append(_raw_latex(_part_shell(row)))
                replaced["parts"] += 1
            index += 1
            continue

        if isinstance(node, dict) and _is_chapter_header(node):
            chapter_id = canonical_chapter_id(node_identifier(node))
            number = next(
                (
                    n
                    for n, spec in chapter_map.items()
                    if str(spec.get("chapterId") or "") == chapter_id
                ),
                None,
            )
            if number not in shell_chapters:
                output.append(node)
                index += 1
                continue

            columns = number in COLUMN_CHAPTERS
            output.append(
                _raw_latex(
                    _chapter_shell(number, chapter_map[number], columns)
                )
            )
            replaced["chapters"] += 1
            if not columns:
                index += 1
                continue

            end = _next_structural_header(blocks, index)
            output.extend(blocks[index + 1 : end])
            output.append(_raw_latex(_chapter_end(number, chapter_id)))
            replaced["columnEnds"] += 1
            index = end
            continue

        output.append(node)
        index += 1

    ast["blocks"] = output
    return replaced


def lower_publication_shell(
    ast: dict[str, Any], contract: dict[str, Any], profile: str
) -> PublicationShellResult:
    """Lower semantic Part/Chapter/divider nodes after orders 20-120.

    The transform is deliberately structural. It emits stable intermediate
    whole-book macros but does not define a LaTeX preamble or compile a PDF;
    those responsibilities remain stages 150 and 160.
    """
    input_digest = canonical_ast_sha256(ast)
    expected = _expected_counts(contract, profile)

    if profile not in PROFILE_PART_IDS:
        return PublicationShellResult(
            status="FAIL",
            profile=profile,
            expected=expected,
            found={},
            replaced={},
            integrated={},
            error=f"Unknown publication-shell profile: {profile}",
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
        )

    before_integrated = _integrated_counts(ast, contract, profile)
    if _is_integrated(before_integrated, expected):
        return PublicationShellResult(
            status="PASS",
            profile=profile,
            expected=expected,
            found=before_integrated,
            replaced={
                "parts": 0,
                "chapters": 0,
                "columnEnds": 0,
                "gmDivider": 0,
            },
            integrated=before_integrated,
            idempotent=True,
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
        )

    readiness = _readiness_report(ast, contract, profile)
    if readiness.get("status") != "PASS":
        return PublicationShellResult(
            status="FAIL",
            profile=profile,
            expected=expected,
            found=before_integrated,
            replaced={},
            integrated=before_integrated,
            error=(
                "Stage 130 preconditions were not met; Phase C AST was not "
                "mutated."
            ),
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
            readiness=readiness,
        )

    candidate = copy.deepcopy(ast)
    replaced = _lower_candidate(candidate, contract, profile)
    integrated = _integrated_counts(candidate, contract, profile)
    if not _is_integrated(integrated, expected):
        return PublicationShellResult(
            status="FAIL",
            profile=profile,
            expected=expected,
            found=before_integrated,
            replaced=replaced,
            integrated=integrated,
            error=(
                "Stage 130 postconditions failed; staged publication-shell "
                "mutation was discarded."
            ),
            inputAstSha256=input_digest,
            outputAstSha256=input_digest,
            readiness=readiness,
        )

    ast.clear()
    ast.update(candidate)
    return PublicationShellResult(
        status="PASS",
        profile=profile,
        expected=expected,
        found=before_integrated,
        replaced=replaced,
        integrated=integrated,
        inputAstSha256=input_digest,
        outputAstSha256=canonical_ast_sha256(ast),
        readiness=readiness,
    )
