from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Any


def latex_escape(value: Any) -> str:
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


def _single_paragraph(value: Any) -> str:
    """Collapse normalized publication prose to one LaTeX paragraph."""
    return " ".join(str(value or "").split())


def _description_block_tex(description: str, body_size: float, body_leading: float) -> str:
    return "\n".join(
        [
            r"\begingroup",
            r"\setlength{\parskip}{0pt}",
            r"\setlength{\parindent}{0pt}",
            r"\setlength{\emergencystretch}{1.5em}",
            r"\RaggedRight",
            rf"\fontsize{{{body_size:.2f}}}{{{body_leading:.2f}}}\selectfont\color{{CMInk}}",
            rf"\noindent {description}\par",
            r"\endgroup",
        ]
    )


def _style(config: dict[str, Any]) -> dict[str, Any]:
    source = config.get("style") if isinstance(config.get("style"), dict) else {}
    minimum = float(source.get("minimumCardTextFontPt", 10.5) or 10.5)
    body_size = max(minimum, float(source.get("cardBodyFontPt", minimum) or minimum))
    body_leading = max(
        body_size + 1.6,
        float(source.get("cardBodyLeadingPt", body_size + 1.6) or (body_size + 1.6)),
    )
    meta_size = max(minimum, float(source.get("cardMetaFontPt", minimum) or minimum))
    meta_leading = max(
        meta_size + 1.0,
        float(source.get("cardMetaLeadingPt", meta_size + 1.0) or (meta_size + 1.0)),
    )
    title_size = max(minimum, float(source.get("cardTitleFontPt", 12.0) or 12.0))
    title_leading = max(
        title_size + 1.0,
        float(source.get("cardTitleLeadingPt", title_size + 1.0) or (title_size + 1.0)),
    )
    return {
        "accent": str(source.get("accentColor", "0B6573")),
        "bright": str(source.get("accentBrightColor", "18A7B5")),
        "ink": str(source.get("inkColor", "183238")),
        "muted": str(source.get("mutedColor", "58747A")),
        "soft": str(source.get("softColor", "EAF4F5")),
        "card_soft": str(source.get("cardSoftColor", "F3F8F8")),
        "rule": str(source.get("ruleColor", "B9D9DC")),
        "margin": float(source.get("pageMarginIn", 0.55) or 0.55),
        "identity_art": float(source.get("identityArtWidthIn", 1.10) or 1.10),
        "card_art_fraction": float(source.get("cardArtWidthFraction", 0.24) or 0.24),
        "card_art_height": float(source.get("cardArtMaxHeightIn", 0.88) or 0.88),
        "column_sep": float(source.get("columnSepIn", 0.18) or 0.18),
        "page_bottom_safety_pt": max(
            0.0, float(source.get("pageBottomSafetyPt", 2.0) or 2.0)
        ),
        "minimum_card_text": minimum,
        "body_size": body_size,
        "body_leading": body_leading,
        "meta_size": meta_size,
        "meta_leading": meta_leading,
        "title_size": title_size,
        "title_leading": title_leading,
    }


def _tex_image_path(
    source_root: Path,
    output_dir: Path,
    publication_path: str,
    render_assets: dict[str, str] | None = None,
) -> str:
    mapped = (render_assets or {}).get(publication_path)
    absolute = (
        Path(mapped)
        if mapped
        else source_root / Path(*PurePosixPath(publication_path).parts)
    )
    relative = os.path.relpath(absolute, output_dir).replace("\\", "/")
    return r"\detokenize{" + relative + "}"


def _slug(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip()).strip("-").lower()
    return text or "domain"


def domain_package_output_stem(domain_name: Any) -> str:
    clean = re.sub(r"[^A-Za-z0-9]+", "_", str(domain_name or "Domain").strip()).strip("_") or "Domain"
    return f"Cybermancy_Chapter14_{clean}_DomainPackage_Step6"


def domain_package_view_filename(domain_name: Any) -> str:
    return f"{_slug(domain_name)}-domain-package-view.json"


def _partition_cards(cards: list[dict[str, Any]], columns: int) -> list[list[dict[str, Any]]]:
    """Partition in publication order into balanced, top-aligned column stacks."""
    columns = max(1, columns)
    count = len(cards)
    base, extra = divmod(count, columns)
    sizes = [base + (1 if index < extra else 0) for index in range(columns)]
    groups: list[list[dict[str, Any]]] = []
    offset = 0
    for size in sizes:
        groups.append(cards[offset : offset + size])
        offset += size
    return groups


def _card_tex(
    card: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
    render_assets: dict[str, str] | None = None,
    *,
    first_in_column: bool = False,
) -> str:
    style = _style(config)
    name = latex_escape(card.get("name"))
    description = latex_escape(_single_paragraph(card.get("description")))
    image = _tex_image_path(
        source_root, output_dir, str(card.get("image") or ""), render_assets
    )
    level = int(card.get("level") or 0)
    recall = int(card.get("recallCost") or 0)
    in_vault = bool(card.get("inVault"))
    art_fraction = max(0.20, min(0.32, style["card_art_fraction"]))
    text_fraction = 0.955 - art_fraction
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    default_card_type = str(composition.get("defaultCardType") or "ability").strip().casefold()
    card_type = str(card.get("cardType") or "").strip()
    markers: list[str] = []
    if card_type and card_type.casefold() != default_card_type:
        markers.append(latex_escape(card_type.upper()))
    if in_vault:
        markers.append("IN VAULT")

    pieces: list[str] = []
    if not first_in_column:
        pieces.append(r"\Needspace{1.55in}")
    pieces.extend(
        [
            r"\noindent\begin{minipage}[t]{\linewidth}",
            r"\vspace{0pt}",
            rf"\begin{{minipage}}[t]{{{art_fraction:.3f}\linewidth}}",
            r"\vspace{0pt}\centering",
            rf"\includegraphics[width=\linewidth,height={style['card_art_height']:.3f}in,keepaspectratio]{{{image}}}",
            r"\end{minipage}\hfill",
            rf"\begin{{minipage}}[t]{{{text_fraction:.3f}\linewidth}}",
            r"\vspace{0pt}\raggedright",
            rf"{{\fontsize{{{style['title_size']:.2f}}}{{{style['title_leading']:.2f}}}\selectfont\bfseries\color{{CMInk}} {name}\par}}",
            r"\vspace{0.55mm}",
            rf"{{\fontsize{{{style['meta_size']:.2f}}}{{{style['meta_leading']:.2f}}}\selectfont\bfseries\color{{CMAccent}} LEVEL {level}\par}}",
            rf"{{\fontsize{{{style['meta_size']:.2f}}}{{{style['meta_leading']:.2f}}}\selectfont\bfseries\color{{CMAccent}} RECALL COST {recall}\par}}",
        ]
    )
    if markers:
        pieces.append(
            rf"{{\fontsize{{{style['meta_size']:.2f}}}{{{style['meta_leading']:.2f}}}\selectfont\bfseries\color{{CMAccent}} {' / '.join(markers)}\par}}"
        )
    pieces.extend(
        [
            r"\end{minipage}",
            r"\end{minipage}",
            r"\par",
            r"\vspace{1.0mm}",
            _description_block_tex(description, style["body_size"], style["body_leading"]),
            r"\vspace{1.35mm}",
            r"{\color{CMRule}\rule{\linewidth}{0.35pt}}",
            r"\vspace{1.8mm}",
        ]
    )
    return "\n".join(pieces)


def _identity_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
    render_assets: dict[str, str] | None = None,
) -> str:
    style = _style(config)
    domain = view.get("domain") if isinstance(view.get("domain"), dict) else {}
    name = latex_escape(domain.get("name"))
    image = _tex_image_path(
        source_root,
        output_dir,
        str((domain.get("artwork") or {}).get("image") or ""),
        render_assets,
    )
    card_count = int(domain.get("cardCount") or 0)
    levels = [
        int(row.get("level"))
        for row in view.get("levels", [])
        if isinstance(row, dict) and row.get("level")
    ]
    level_span = ""
    if levels:
        level_span = f"LEVELS {min(levels)}-{max(levels)}"
    summary = f"{card_count} DOMAIN CARDS"
    if level_span:
        summary += rf"\hspace{{0.8em}}\textbullet\hspace{{0.35em}}{level_span}"

    art_width = style["identity_art"]
    return "\n".join(
        [
            rf"{{\fontsize{{7.4}}{{8.4}}\selectfont\bfseries\color{{CMBright}} CHAPTER {int(view.get('chapter') or 14)} / {latex_escape(config.get('partLabel', 'CHARACTER OPTIONS'))}\par}}",
            r"\vspace{1.4mm}",
            r"\noindent\begin{minipage}[t]{0.76\linewidth}",
            r"\vspace{0pt}",
            r"{\fontsize{8.4}{9.4}\selectfont\bfseries\color{CMAccent} DOMAIN\par}",
            r"\vspace{0.6mm}",
            rf"{{\fontsize{{31}}{{32}}\selectfont\bfseries\color{{CMInk}} {name.upper()}\par}}",
            r"\vspace{1.0mm}",
            rf"{{\fontsize{{8.2}}{{9.2}}\selectfont\bfseries\color{{CMMuted}} {summary}\par}}",
            r"\end{minipage}\hfill",
            r"\begin{minipage}[t]{0.20\linewidth}",
            r"\vspace{0pt}\raggedleft",
            rf"\includegraphics[width={art_width:.3f}in,height={art_width:.3f}in,keepaspectratio]{{{image}}}",
            r"\end{minipage}",
            r"\vspace{1.8mm}",
            r"{\color{CMBright}\rule{\linewidth}{0.9pt}}",
            r"\vspace{3.0mm}",
        ]
    )


def _level_tex(
    level_row: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
    render_assets: dict[str, str] | None = None,
) -> str:
    level = int(level_row.get("level") or 0)
    cards = [card for card in (level_row.get("cards") or []) if isinstance(card, dict)]
    count_label = "CARD" if len(cards) == 1 else "CARDS"
    style_config = config.get("style") if isinstance(config.get("style"), dict) else {}
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    level_min_start = float(style_config.get("levelMinStartSpaceIn", 2.20) or 2.20)
    columns = max(1, int(composition.get("pageColumns") or 3))

    pieces = [
        rf"\Needspace{{{level_min_start:.2f}in}}",
        r"\vspace{1.0mm}",
        r"\noindent\begin{tabularx}{\linewidth}{@{}X r@{}}",
        rf"{{\fontsize{{17}}{{18}}\selectfont\bfseries\color{{CMAccent}} LEVEL {level}}} & {{\fontsize{{7.4}}{{8.4}}\selectfont\bfseries\color{{CMMuted}} {len(cards)} {count_label}}} \\",
        r"\end{tabularx}",
        r"\vspace{0.8mm}",
        r"{\color{CMRule}\rule{\linewidth}{0.55pt}}",
        r"\vspace{1.8mm}",
    ]

    if columns >= 3:
        groups = _partition_cards(cards, columns)
        pieces.append(rf"\begin{{paracol}}{{{columns}}}")
        for column_index, group in enumerate(groups):
            if column_index:
                pieces.append(r"\switchcolumn")
            pieces.append(r"\vspace{0pt}")
            for card_index, card in enumerate(group):
                pieces.append(
                    _card_tex(
                        card,
                        config,
                        source_root,
                        output_dir,
                        render_assets,
                        first_in_column=card_index == 0,
                    )
                )
        pieces.append(r"\end{paracol}")
    else:
        pieces.extend([rf"\begin{{multicols}}{{{columns}}}", r"\raggedcolumns"])
        for card in cards:
            pieces.append(_card_tex(card, config, source_root, output_dir, render_assets))
        pieces.append(r"\end{multicols}")

    pieces.append(r"\vspace{0.5mm}")
    return "\n".join(pieces)


def render_domain_package_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
    render_assets: dict[str, str] | None = None,
) -> str:
    """Render one standalone Step 6 DomainPackage visual prototype as LuaLaTeX."""
    style = _style(config)
    levels = view.get("levels") if isinstance(view.get("levels"), list) else []
    content = [
        _identity_tex(view, config, source_root, output_dir, render_assets),
        *[
            _level_tex(row, config, source_root, output_dir, render_assets)
            for row in levels
            if isinstance(row, dict)
        ],
    ]

    return rf"""\documentclass[10pt]{{article}}
\usepackage[letterpaper,margin={style['margin']:g}in]{{geometry}}
\usepackage{{fontspec}}
\usepackage[table]{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{multicol}}
\usepackage{{paracol}}
\usepackage{{needspace}}
\usepackage{{ragged2e}}
\setsansfont{{Arial}}
\setmainfont{{Arial}}
\definecolor{{CMAccent}}{{HTML}}{{{style['accent']}}}
\definecolor{{CMBright}}{{HTML}}{{{style['bright']}}}
\definecolor{{CMInk}}{{HTML}}{{{style['ink']}}}
\definecolor{{CMMuted}}{{HTML}}{{{style['muted']}}}
\definecolor{{CMSoft}}{{HTML}}{{{style['soft']}}}
\definecolor{{CMCardSoft}}{{HTML}}{{{style['card_soft']}}}
\definecolor{{CMRule}}{{HTML}}{{{style['rule']}}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0pt}}
\setlength{{\columnsep}}{{{style['column_sep']:.3f}in}}
\setlength{{\multicolsep}}{{0pt}}
\setlength{{\columnseprule}}{{0pt}}
\addtolength{{\textheight}}{{-{style['page_bottom_safety_pt']:.2f}pt}}
\pagestyle{{plain}}
\raggedbottom
\begin{{document}}
\sffamily
\RaggedRight
{chr(10).join(content)}
\end{{document}}
"""