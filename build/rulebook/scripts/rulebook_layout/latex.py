from __future__ import annotations

from .equipment_catalog import latex_escape


def _style_values(config: dict) -> dict[str, str]:
    style = config.get("style", {})
    return {
        "header": style.get("headerColor", "0B6573"),
        "group": style.get("groupBandColor", "DDEEF0"),
        "alt": style.get("alternateRowColor", "EEF7F8"),
        "text_dark": style.get("textDarkColor", "183238"),
        "rule": style.get("ruleColor", "18A7B5"),
    }


def _pagination_values(config: dict) -> dict[str, float | str]:
    pagination = config.get("pagination", {}) if isinstance(config.get("pagination"), dict) else {}
    return {
        "tier_needspace": float(pagination.get("tierStartNeedspaceIn", 1.25) or 1.25),
        "reference_needspace": float(pagination.get("referenceStartNeedspaceIn", 1.25) or 1.25),
        "inter_table_space": float(pagination.get("interTableSpacePt", 10) or 10),
    }


def _needspace(inches: float) -> str:
    return rf"\Needspace{{{inches:g}in}}"


def _inter_table_gap(points: float) -> str:
    return rf"\par\addvspace{{{points:g}pt}}"


def _document_preamble(config: dict) -> str:
    style = _style_values(config)
    return rf"""\documentclass[10pt]{{article}}
\usepackage[letterpaper,margin=0.46in]{{geometry}}
\usepackage{{fontspec}}
\usepackage[table]{{xcolor}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{ragged2e}}
\usepackage{{microtype}}
\usepackage{{titlesec}}
\usepackage{{needspace}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0pt}}
\IfFontExistsTF{{Roboto Condensed}}{{\setsansfont{{Roboto Condensed}}}}{{\setsansfont{{TeX Gyre Heros}}}}
\IfFontExistsTF{{Roboto}}{{\setmainfont{{Roboto}}}}{{\setmainfont{{TeX Gyre Heros}}}}
\definecolor{{CMTableHeader}}{{HTML}}{{{style['header']}}}
\definecolor{{CMGroupBand}}{{HTML}}{{{style['group']}}}
\definecolor{{CMAltRow}}{{HTML}}{{{style['alt']}}}
\definecolor{{CMTextDark}}{{HTML}}{{{style['text_dark']}}}
\definecolor{{CMRule}}{{HTML}}{{{style['rule']}}}
"""


def _chapter_header(config: dict) -> str:
    chapter = int(config.get("chapter", 16))
    part_label = str(config.get("partLabel", "EQUIPMENT & TECHNOLOGY"))
    title = str(config.get("title", "Equipment"))
    deck = str(config.get("deck", "") or "").strip()
    deck_tex = ""
    if deck:
        deck_tex = (
            r"\vspace{1.5mm}" "\n"
            r"{\fontsize{8.2}{10}\selectfont\color{CMTextDark} "
            + latex_escape(deck)
            + r"\par}" "\n"
        )
    return (
        rf"{{\fontsize{{7.4}}{{8.4}}\selectfont\bfseries\color{{CMRule}} CHAPTER {chapter} / {latex_escape(part_label)}\par}}" "\n"
        r"\vspace{1.4mm}" "\n"
        rf"{{\fontsize{{26}}{{27}}\selectfont\bfseries\color{{CMTextDark}} {latex_escape(title.upper())}\par}}" "\n"
        r"\vspace{0.8mm}" "\n"
        r"{\color{CMRule}\rule{\linewidth}{0.7pt}}" "\n"
        + deck_tex
    )


def _tier_heading(config: dict, tier: int) -> str:
    label = str(config.get("tierLabel", "TIER {tier}")).format(tier=tier)
    return (
        rf"{{\fontsize{{11}}{{12}}\selectfont\bfseries\color{{CMTextDark}} {latex_escape(label)}\par}}" "\n"
        r"\vspace{1.2mm}" "\n"
    )


def _reference_heading(title: str) -> str:
    return (
        rf"{{\fontsize{{16}}{{17}}\selectfont\bfseries\color{{CMTextDark}} {latex_escape(title.upper())}\par}}" "\n"
        r"\vspace{0.6mm}" "\n"
        r"{\color{CMRule}\rule{\linewidth}{0.55pt}}" "\n"
        r"\vspace{1.4mm}" "\n"
    )


def render_tier_prototype_document(table_latex: str, config: dict, tier: int) -> str:
    """Retain the accepted Step 6C single-tier proof document."""
    return (
        _document_preamble(config)
        + r"\begin{document}" + "\n"
        + r"\sffamily" + "\n"
        + _chapter_header(config)
        + r"\vspace{1.8mm}" + "\n"
        + _tier_heading(config, tier)
        + table_latex
        + r"\end{document}" + "\n"
    )


def render_weapons_family_latex(
    tier_tables: dict[int, str],
    actions_reference_latex: str,
    critical_reference_latex: str,
    config: dict,
) -> str:
    """Render the complete Weapons family using flowing longtable pagination."""
    pagination = _pagination_values(config)
    tier_needspace = float(pagination["tier_needspace"])
    reference_needspace = float(pagination["reference_needspace"])
    inter_table_space = float(pagination["inter_table_space"])
    gap = _inter_table_gap(inter_table_space)

    pieces: list[str] = []
    for index, tier in enumerate(sorted(tier_tables)):
        if index:
            pieces.append(gap)
        pieces.append(_needspace(tier_needspace))
        pieces.append(_tier_heading(config, tier).rstrip())
        pieces.append(tier_tables[tier].rstrip())

    references = config.get("references", {}) if isinstance(config.get("references"), dict) else {}
    actions_title = str(references.get("actionsTitle", "Weapon Actions"))
    critical_title = str(references.get("criticalEffectsTitle", "Critical Effects"))
    pieces.extend([
        gap,
        _needspace(reference_needspace),
        _reference_heading(actions_title).rstrip(),
        actions_reference_latex.rstrip(),
        gap,
        _needspace(reference_needspace),
        _reference_heading(critical_title).rstrip(),
        critical_reference_latex.rstrip(),
    ])
    return "\n".join(pieces) + "\n"


def render_equipment_chapter_document(family_latex: str, config: dict) -> str:
    """Wrap a Step 6 Equipment family payload in its configured chapter shell."""
    return (
        _document_preamble(config)
        + r"\begin{document}" + "\n"
        + r"\sffamily" + "\n"
        + _chapter_header(config)
        + r"\vspace{1.8mm}" + "\n"
        + family_latex
        + r"\end{document}" + "\n"
    )


def render_weapons_chapter_document(family_latex: str, config: dict) -> str:
    """Backward-compatible alias for the accepted Chapter 16 Weapons builder."""
    return render_equipment_chapter_document(family_latex, config)
