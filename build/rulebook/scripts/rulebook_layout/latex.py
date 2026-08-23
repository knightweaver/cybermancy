from __future__ import annotations

from .equipment_catalog import latex_escape


def render_tier_prototype_document(table_latex: str, config: dict, tier: int) -> str:
    style = config.get("style", {})
    header = style.get("headerColor", "0B6573")
    group = style.get("groupBandColor", "DDEEF0")
    alt = style.get("alternateRowColor", "EEF7F8")
    text_dark = style.get("textDarkColor", "183238")
    rule = style.get("ruleColor", "18A7B5")

    chapter = int(config.get("chapter", 16))
    part_label = str(config.get("partLabel", "EQUIPMENT & TECHNOLOGY"))
    title = str(config.get("title", "Equipment"))
    tier_label = str(config.get("tierLabel", "TIER {tier}")).format(tier=tier)
    deck = str(config.get("deck", "") or "").strip()

    deck_tex = ""
    if deck:
        deck_tex = (
            r"\vspace{1.5mm}" "\n"
            r"{\fontsize{8.2}{10}\selectfont\color{CMTextDark} "
            + latex_escape(deck)
            + r"\par}" "\n"
        )

    return rf"""\documentclass[10pt]{{article}}
\usepackage[letterpaper,margin=0.46in]{{geometry}}
\usepackage{{fontspec}}
\usepackage[table]{{xcolor}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{ragged2e}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0pt}}
\IfFontExistsTF{{Roboto Condensed}}{{\setsansfont{{Roboto Condensed}}}}{{\setsansfont{{TeX Gyre Heros}}}}
\IfFontExistsTF{{Roboto}}{{\setmainfont{{Roboto}}}}{{\setmainfont{{TeX Gyre Heros}}}}
\definecolor{{CMTableHeader}}{{HTML}}{{{header}}}
\definecolor{{CMGroupBand}}{{HTML}}{{{group}}}
\definecolor{{CMAltRow}}{{HTML}}{{{alt}}}
\definecolor{{CMTextDark}}{{HTML}}{{{text_dark}}}
\definecolor{{CMRule}}{{HTML}}{{{rule}}}
\begin{{document}}
\sffamily
{{\fontsize{{7.4}}{{8.4}}\selectfont\bfseries\color{{CMRule}} CHAPTER {chapter} / {latex_escape(part_label)}\par}}
\vspace{{1.4mm}}
{{\fontsize{{26}}{{27}}\selectfont\bfseries\color{{CMTextDark}} {latex_escape(title.upper())}\par}}
\vspace{{0.8mm}}
{{\color{{CMRule}}\rule{{\linewidth}}{{0.7pt}}}}
{deck_tex}\vspace{{1.8mm}}
{{\fontsize{{11}}{{12}}\selectfont\bfseries\color{{CMTextDark}} {latex_escape(tier_label)}\par}}
\vspace{{1.2mm}}
{table_latex}
\end{{document}}
"""
