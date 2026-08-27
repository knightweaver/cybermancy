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


def _style(config: dict[str, Any]) -> dict[str, Any]:
    source = config.get("style") if isinstance(config.get("style"), dict) else {}
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
        "column_sep": float(source.get("columnSepIn", 0.26) or 0.26),
        "body_size": float(source.get("cardBodyFontPt", 9.0) or 9.0),
        "body_leading": float(source.get("cardBodyLeadingPt", 11.3) or 11.3),
        "title_size": float(source.get("cardTitleFontPt", 12.4) or 12.4),
        "title_leading": float(source.get("cardTitleLeadingPt", 13.4) or 13.4),
    }


def _tex_image_path(source_root: Path, output_dir: Path, publication_path: str) -> str:
    absolute = source_root / Path(*PurePosixPath(publication_path).parts)
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


def _card_tex(
    card: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = _style(config)
    name = latex_escape(card.get("name"))
    description = latex_escape(card.get("description"))
    image = _tex_image_path(source_root, output_dir, str(card.get("image") or ""))
    level = int(card.get("level") or 0)
    recall = int(card.get("recallCost") or 0)
    in_vault = bool(card.get("inVault"))
    art_fraction = max(0.18, min(0.34, style["card_art_fraction"]))
    text_fraction = 0.965 - art_fraction
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    default_card_type = str(composition.get("defaultCardType") or "ability").strip().casefold()
    card_type = str(card.get("cardType") or "").strip()
    markers: list[str] = []
    if card_type and card_type.casefold() != default_card_type:
        markers.append(latex_escape(card_type.upper()))
    if in_vault:
        markers.append("IN VAULT")
    marker_tex = "".join(
        rf"\hspace{{0.8em}}\textbullet\hspace{{0.35em}}{marker}" for marker in markers
    )

    return "\n".join(
        [
            r"\Needspace{1.55in}",
            r"{\color{CMBright}\rule{\linewidth}{0.75pt}}",
            r"\vspace{1.2mm}",
            r"\noindent\begin{minipage}{\linewidth}",
            rf"\begin{{minipage}}[t]{{{art_fraction:.3f}\linewidth}}",
            r"\vspace{0pt}\centering",
            rf"\includegraphics[width=\linewidth,height={style['card_art_height']:.3f}in,keepaspectratio]{{{image}}}",
            r"\end{minipage}\hfill",
            rf"\begin{{minipage}}[t]{{{text_fraction:.3f}\linewidth}}",
            r"\vspace{0pt}",
            rf"{{\fontsize{{{style['title_size']:.2f}}}{{{style['title_leading']:.2f}}}\selectfont\bfseries\color{{CMInk}} {name}\par}}",
            r"\vspace{0.8mm}",
            rf"{{\fontsize{{7.2}}{{8.3}}\selectfont\bfseries\color{{CMAccent}} LEVEL {level}\hspace{{0.8em}}\textbullet\hspace{{0.35em}}RECALL COST {recall}{marker_tex}\par}}",
            r"\end{minipage}",
            r"\end{minipage}",
            r"\vspace{1.2mm}",
            rf"{{\fontsize{{{style['body_size']:.2f}}}{{{style['body_leading']:.2f}}}\selectfont\color{{CMInk}} {description}\par}}",
            r"\vspace{1.6mm}",
            r"{\color{CMRule}\rule{\linewidth}{0.35pt}}",
            r"\vspace{2.2mm}",
        ]
    )


def _identity_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = _style(config)
    domain = view.get("domain") if isinstance(view.get("domain"), dict) else {}
    name = latex_escape(domain.get("name"))
    image = _tex_image_path(source_root, output_dir, str((domain.get("artwork") or {}).get("image") or ""))
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
) -> str:
    level = int(level_row.get("level") or 0)
    cards = level_row.get("cards") if isinstance(level_row.get("cards"), list) else []
    count_label = "CARD" if len(cards) == 1 else "CARDS"
    style_config = config.get("style") if isinstance(config.get("style"), dict) else {}
    level_min_start = float(style_config.get("levelMinStartSpaceIn", 2.65) or 2.65)
    pieces = [
        rf"\Needspace{{{level_min_start:.2f}in}}",
        r"\vspace{1.0mm}",
        r"\noindent\begin{tabularx}{\linewidth}{@{}X r@{}}",
        rf"{{\fontsize{{17}}{{18}}\selectfont\bfseries\color{{CMAccent}} LEVEL {level}}} & {{\fontsize{{7.4}}{{8.4}}\selectfont\bfseries\color{{CMMuted}} {len(cards)} {count_label}}} \\",
        r"\end{tabularx}",
        r"\vspace{0.8mm}",
        r"{\color{CMRule}\rule{\linewidth}{0.55pt}}",
        r"\vspace{1.8mm}",
        r"\begin{multicols}{2}",
        r"\raggedcolumns",
    ]
    for card in cards:
        if isinstance(card, dict):
            pieces.append(_card_tex(card, config, source_root, output_dir))
    pieces.extend([r"\end{multicols}", r"\vspace{0.5mm}"])
    return "\n".join(pieces)


def render_domain_package_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    """Render one standalone Step 6 DomainPackage visual prototype as LuaLaTeX."""
    style = _style(config)
    levels = view.get("levels") if isinstance(view.get("levels"), list) else []
    content = [
        _identity_tex(view, config, source_root, output_dir),
        *[
            _level_tex(row, config, source_root, output_dir)
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
\usepackage{{needspace}}
\setmainfont{{Latin Modern Roman}}
\setsansfont{{Latin Modern Sans}}
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
\pagestyle{{plain}}
\begin{{document}}
\sffamily
{chr(10).join(content)}
\end{{document}}
"""
