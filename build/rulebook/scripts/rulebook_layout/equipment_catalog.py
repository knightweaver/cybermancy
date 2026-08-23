from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


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


def _mechanic_display(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""
    # Foundry weaponFeature values are commonly lowercase identifiers while
    # authored action names already carry intentional capitalization. Step 6
    # owns display casing, so lowercase semantic identifiers become title case.
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
    rows: list[tuple[tuple, CatalogRow]] = []

    for entity in entities:
        if entity.get("family") != family:
            continue
        entity_tier = get_path(entity, "publicationData.tier")
        if tier is not None:
            try:
                if int(entity_tier) != int(tier):
                    continue
            except (TypeError, ValueError):
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
            tier=entity_tier,
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
    # array's m{} columns vertically center their contents within the row.
    # The Description cell remains the natural row-height driver because its
    # configured vertical padding is emitted inside the cell.
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


def render_equipment_catalog_latex(rows: list[CatalogRow], config: dict) -> str:
    columns = list(config.get("columns", []))
    if not columns:
        raise ValueError("Equipment catalog config has no columns.")

    spec = "@{}" + "".join(_column_spec(col) for col in columns) + "@{}"
    header = _render_header(columns)
    lines = [
        r"\begingroup",
        r"\setlength{\tabcolsep}{1.4pt}",
        r"\renewcommand{\arraystretch}{1.10}",
        r"\fontsize{6.55}{7.55}\selectfont",
        rf"\begin{{longtable}}{{{spec}}}",
        header,
        r"\endfirsthead",
        header,
        r"\endhead",
    ]

    row_index = 0
    for group, group_rows in group_catalog_rows(rows):
        lines.append(
            rf"\rowcolor{{CMGroupBand}}\multicolumn{{{len(columns)}}}{{@{{}}l@{{}}}}{{"
            rf"\textbf{{\color{{CMTextDark}}\MakeUppercase{{{latex_escape(group)}}}}}}} \\"
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
    """Replace a normalized family Div's body with a Step 6 raw-LaTeX catalog.

    C exposes this transformation for later full-book integration. The Tier 1
    prototype builder uses the same table renderer without deleting Tiers 2–4
    from the current full manuscript; D can invoke this replacer once all four
    Weapon tiers and references are ready.
    """
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
