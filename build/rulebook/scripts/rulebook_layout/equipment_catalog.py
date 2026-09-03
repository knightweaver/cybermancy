from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


_TIER_RE = re.compile(r"^[1-4]$")


@dataclass(frozen=True)
class CatalogRow:
    semantic_id: str
    name: str
    tier: Any
    group: str
    cells: dict[str, str]


def get_path(obj: Any, dotted: str, default=None):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _tier_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 4 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and 1 <= int(value) <= 4 else None
    if isinstance(value, str):
        text = value.strip()
        return int(text) if _TIER_RE.fullmatch(text) else None
    return None


def _mechanic_display(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if text == text.casefold():
        return text.title()
    return text


def _human_label(value: Any) -> str:
    """Convert code-style enum values to ordinary sentence-case publication text."""
    text = str(value).strip()
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text[:1].upper() + text[1:] if text else ""


def _feature_definition_display(value: Any) -> str:
    """Render one normalized feature definition as reader-facing table text."""
    if not isinstance(value, dict):
        return str(value).strip()
    name = str(value.get("name") or "").strip()
    description = str(value.get("description") or "").strip()
    if name and description:
        return f"{name}: {description}"
    return name or description


def _flatten_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [x for x in value if _present(x)]
    return [value] if _present(value) else []


def _cell_value(entity: dict, column: dict, missing: str) -> str:
    sources = column.get("compose")
    if isinstance(sources, list):
        values: list[Any] = []
        for path in sources:
            values.extend(_flatten_values(get_path(entity, str(path))))
    else:
        values = _flatten_values(get_path(entity, str(column["key"])))

    transform = column.get("transform")
    if transform == "mechanic-list":
        rendered = [_mechanic_display(v) for v in values]
    elif transform == "human-label":
        rendered = [_human_label(v) for v in values]
    elif transform == "feature-definitions":
        rendered = [_feature_definition_display(v) for v in values]
    else:
        rendered = [str(v).strip() for v in values]
    rendered = [v for v in rendered if v]
    if not rendered:
        return missing
    return str(column.get("separator", ", ")).join(rendered)


def _sort_atom(value: Any):
    if value in (None, ""):
        return (1, "")
    if isinstance(value, (int, float)):
        return (0, value)
    return (0, str(value).casefold())


def build_catalog_rows(
    entities: Iterable[dict],
    config: dict,
    *,
    tier: int | None = None,
) -> list[CatalogRow]:
    family = str(config["family"])
    missing = str(config.get("display", {}).get("missing", "—"))
    group_path = str(config.get("groupBy") or "")
    tiered = str(config.get("layoutMode") or "single-catalog").casefold() == "tiered-catalog"
    rows: list[tuple[tuple, CatalogRow]] = []

    for entity in entities:
        if entity.get("family") != family:
            continue
        entity_tier = get_path(entity, "publicationData.tier")
        normalized_tier = _tier_number(entity_tier)
        if tier is not None:
            if normalized_tier != _tier_number(tier):
                continue
        elif tiered and normalized_tier is None:
            # A structural tiered catalog must never quietly admit an untiered
            # or malformed row. Omitting it here causes the generic validator's
            # CATALOG_ROW_COUNT check to fail closed before rendering begins.
            continue

        raw_group = get_path(entity, group_path) if group_path else ""
        group = str(raw_group or missing)
        if config.get("display", {}).get("groupUppercase") and group != missing:
            group = group.upper()

        cells = {
            str(column["key"]): _cell_value(entity, column, missing)
            for column in config.get("columns", [])
        }
        row = CatalogRow(
            semantic_id=str(entity.get("semanticId") or ""),
            name=str(entity.get("name") or ""),
            tier=normalized_tier if tiered else entity_tier,
            group=group,
            cells=cells,
        )

        sort_key = []
        for path in config.get("sort", []):
            sort_key.append(_sort_atom(get_path(entity, str(path))))
        sort_key.extend([_sort_atom(entity.get("name")), _sort_atom(entity.get("semanticId"))])
        rows.append((tuple(sort_key), row))

    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows]


def group_catalog_rows(rows: Iterable[CatalogRow]) -> list[tuple[str, list[CatalogRow]]]:
    grouped: list[tuple[str, list[CatalogRow]]] = []
    for row in rows:
        if not grouped or grouped[-1][0] != row.group:
            grouped.append((row.group, [row]))
        else:
            grouped[-1][1].append(row)
    return grouped


def partition_catalog_rows_by_tier(rows: Iterable[CatalogRow]) -> dict[int, list[CatalogRow]]:
    """Partition normalized catalog rows into deterministic numeric Tier tables.

    ``tiered-catalog`` is reserved for families whose Step 4 publication Tier is
    complete. Treat an absent, non-numeric, or out-of-range Tier as a contract
    error rather than silently mixing it into a table.
    """
    result: dict[int, list[CatalogRow]] = {}
    invalid: list[dict[str, Any]] = []
    for row in rows:
        tier = _tier_number(row.tier)
        if tier is None:
            invalid.append({"name": row.name, "tier": row.tier})
            continue
        result.setdefault(tier, []).append(row)
    if invalid:
        raise ValueError(f"Tiered Equipment catalog contains invalid Tier values: {invalid}")
    return {tier: result[tier] for tier in sorted(result)}


def latex_escape(value: Any) -> str:
    text = str(value)
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


def _column_spec(column: dict) -> str:
    width = float(column["widthIn"])
    align = str(column.get("align", "left")).casefold()
    prefix = r">{\Centering\arraybackslash}" if align == "center" else r">{\RaggedRight\arraybackslash}"
    return f"{prefix}m{{{width:.3f}in}}"


def _render_header(columns: list[dict]) -> str:
    cells = [
        rf"\textbf{{\color{{white}}\MakeUppercase{{{latex_escape(col['label'])}}}}}"
        for col in columns
    ]
    return r"\rowcolor{CMTableHeader}" + " & ".join(cells) + r" \\"


def _render_cell(value: str, column: dict) -> str:
    rendered = latex_escape(value)
    if column.get("bold"):
        rendered = rf"\textbf{{{rendered}}}"
    padding = float(column.get("verticalPaddingPt", 0) or 0)
    if padding > 0:
        rendered = rf"\vspace*{{{padding:g}pt}}\strut {rendered}\strut\par\vspace*{{{padding:g}pt}}"
    return rendered


def _continuation_label(rows: list[CatalogRow], config: dict) -> str:
    pagination = config.get("pagination", {}) if isinstance(config.get("pagination"), dict) else {}
    explicit = str(pagination.get("continuationLabel") or "").strip()
    if explicit:
        base = explicit
    elif rows and rows[0].tier not in (None, ""):
        base = str(config.get("tierLabel", "TIER {tier}")).format(tier=rows[0].tier)
    else:
        base = str(config.get("title") or config.get("family") or "Catalog")
    template = str(pagination.get("continuationTemplate", "{label} — CONTINUED"))
    return template.format(label=base).upper()


def _render_continuation_band(label: str, column_count: int) -> str:
    if not label:
        return ""
    return (
        rf"\rowcolor{{CMGroupBand}}\multicolumn{{{column_count}}}{{@{{}}l@{{}}}}{{"
        rf"\textbf{{\color{{CMTextDark}} {latex_escape(label)}}}}} \\"
    )


def _table_style(config: dict) -> tuple[float, float, float, float]:
    style = config.get("tableStyle", {}) if isinstance(config.get("tableStyle"), dict) else {}
    return (
        float(style.get("tabcolsepPt", 1.4) or 1.4),
        float(style.get("arrayStretch", 1.10) or 1.10),
        float(style.get("fontSizePt", 6.55) or 6.55),
        float(style.get("leadingPt", 7.55) or 7.55),
    )


def _render_single_catalog_latex(rows: list[CatalogRow], config: dict) -> str:
    columns = list(config.get("columns", []))
    if not columns:
        raise ValueError("Equipment catalog config has no columns.")

    spec = "@{}" + "".join(_column_spec(col) for col in columns) + "@{}"
    header = _render_header(columns)
    continuation_band = _render_continuation_band(_continuation_label(rows, config), len(columns))
    tabcolsep, array_stretch, font_size, leading = _table_style(config)
    lines = [
        r"\begingroup",
        rf"\setlength{{\tabcolsep}}{{{tabcolsep:g}pt}}",
        r"\setlength{\LTpre}{0pt}",
        r"\setlength{\LTpost}{0pt}",
        rf"\renewcommand{{\arraystretch}}{{{array_stretch:g}}}",
        rf"\fontsize{{{font_size:g}}}{{{leading:g}}}\selectfont",
        rf"\begin{{longtable}}{{{spec}}}",
        header,
        r"\endfirsthead",
    ]
    if continuation_band:
        lines.append(continuation_band)
    lines.extend([header, r"\endhead"])

    row_index = 0
    grouped = bool(config.get("groupBy"))
    row_groups = group_catalog_rows(rows) if grouped else [("", list(rows))]

    for group, group_rows in row_groups:
        if grouped:
            lines.append(
                rf"\rowcolor{{CMGroupBand}}\multicolumn{{{len(columns)}}}{{@{{}}l@{{}}}}{{"
                rf"\textbf{{\color{{CMTextDark}}\MakeUppercase{{{latex_escape(group)}}}}}}} \\*"
            )
        for row in group_rows:
            if row_index % 2 == 0:
                lines.append(r"\rowcolor{CMAltRow}")
            rendered_cells = [
                _render_cell(row.cells[str(column["key"])], column)
                for column in columns
            ]
            lines.append(" & ".join(rendered_cells) + r" \\")
            row_index += 1

    lines += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines) + "\n"


def _tier_heading(config: dict, tier: int) -> str:
    label = str(config.get("tierLabel", "TIER {tier}")).format(tier=tier)
    return (
        rf"{{\fontsize{{11}}{{12}}\selectfont\bfseries\color{{CMTextDark}} {latex_escape(label)}\par}}" "\n"
        r"\vspace{1.2mm}" "\n"
    )


def _tiered_catalog_latex(rows: list[CatalogRow], config: dict) -> str:
    tier_rows = partition_catalog_rows_by_tier(rows)
    if not tier_rows:
        raise ValueError("Tiered Equipment catalog has no Tier rows.")

    pagination = config.get("pagination", {}) if isinstance(config.get("pagination"), dict) else {}
    tier_needspace = float(pagination.get("tierStartNeedspaceIn", 1.25) or 1.25)
    inter_table_space = float(pagination.get("interTableSpacePt", 10) or 10)
    pieces: list[str] = []

    for index, (tier, subset) in enumerate(tier_rows.items()):
        if index:
            pieces.append(rf"\par\addvspace{{{inter_table_space:g}pt}}")
        pieces.append(rf"\Needspace{{{tier_needspace:g}in}}")
        pieces.append(_tier_heading(config, tier).rstrip())

        # A continuing longtable should identify the Tier it is continuing, not
        # merely the overall family title. Do this on a shallow config copy so
        # the canonical family config remains untouched.
        tier_config = dict(config)
        tier_pagination = dict(pagination)
        tier_pagination["continuationLabel"] = str(
            config.get("tierLabel", "TIER {tier}")
        ).format(tier=tier)
        tier_config["pagination"] = tier_pagination
        pieces.append(_render_single_catalog_latex(subset, tier_config).rstrip())

    return "\n".join(pieces) + "\n"


def render_equipment_catalog_latex(rows: list[CatalogRow], config: dict) -> str:
    """Render one Equipment catalog, using structural Tier tables when configured."""
    if str(config.get("layoutMode") or "single-catalog").casefold() == "tiered-catalog":
        return _tiered_catalog_latex(rows, config)
    return _render_single_catalog_latex(rows, config)


def _div_identifier(node: dict) -> str:
    if node.get("t") != "Div":
        return ""
    content = node.get("c")
    if not (isinstance(content, list) and len(content) == 2):
        return ""
    attr = content[0]
    if not (isinstance(attr, list) and len(attr) == 3):
        return ""
    return str(attr[0] or "")


def replace_family_div_with_latex(ast: dict, family: str, latex: str) -> int:
    """Replace a normalized family Div's body with a Step 6 raw-LaTeX catalog."""
    target = f"family:{family}"
    replaced = 0

    def walk(value: Any) -> None:
        nonlocal replaced
        if isinstance(value, dict):
            if _div_identifier(value) == target:
                value["c"][1] = [{"t": "RawBlock", "c": ["latex", latex]}]
                replaced += 1
                return
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(ast)
    return replaced
