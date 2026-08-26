from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any

from .class_package import latex_escape


MIN_BODY_SIZE = 10.5


def _style(config: dict[str, Any]) -> dict[str, Any]:
    source = config.get("style") if isinstance(config.get("style"), dict) else {}
    return {
        "accent": source.get("accentColor", "0B6573"),
        "bright": source.get("accentBrightColor", "18A7B5"),
        "ink": source.get("inkColor", "183238"),
        "muted": source.get("mutedColor", "58747A"),
        "soft": source.get("softColor", "EAF4F5"),
        "subclass": source.get("subclassBandColor", "DDEEF0"),
        "margin": float(source.get("pageMarginIn", 0.55) or 0.55),
        "class_art": float(source.get("classArtWidthFraction", 0.43) or 0.43),
        "class_art_max": float(source.get("classArtMaxHeightIn", 3.9) or 3.9),
        "subclass_column": float(source.get("subclassColumnWidthFraction", 0.485) or 0.485),
        "subclass_art": float(source.get("subclassArtWidthFraction", 0.34) or 0.34),
        "subclass_art_max": float(source.get("subclassArtMaxHeightIn", 1.55) or 1.55),
    }


def _tex_image_path(source_root: Path, output_dir: Path, publication_path: str) -> str:
    absolute = source_root / Path(*PurePosixPath(publication_path).parts)
    relative = os.path.relpath(absolute, output_dir).replace("\\", "/")
    return r"\detokenize{" + relative + "}"


def _feature_tex(feature: dict[str, Any], *, compact: bool = False) -> str:
    name = latex_escape(feature.get("name"))
    description = latex_escape(feature.get("description"))
    needspace = "0.52in" if compact else "0.62in"
    line_width = "0.35pt" if compact else "0.45pt"
    bottom_space = "0.7mm" if compact else "1.0mm"

    lines = [
        rf"\Needspace{{{needspace}}}",
        rf"{{\fontsize{{12}}{{13.2}}\selectfont\bfseries\color{{CMInk}} {name}\par}}",
        r"\vspace{0.15mm}",
    ]
    if description:
        lines.append(rf"{{\fontsize{{10.5}}{{12.1}}\selectfont {description}\par}}")
    else:
        lines.append(r"{\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted} No publication description supplied.\par}")
    lines.extend([
        r"\vspace{0.25mm}",
        rf"{{\color{{CMBright}}\rule{{\linewidth}}{{{line_width}}}}}",
        rf"\vspace{{{bottom_space}}}",
    ])
    return "\n".join(lines)


def _reference_names(items: list[dict[str, Any]]) -> str:
    return ", ".join(latex_escape(item.get("name")) for item in items) or "—"


def _class_opening_tex(view: dict[str, Any], config: dict[str, Any], source_root: Path, output_dir: Path) -> str:
    style = _style(config)
    cls = view["class"]
    title = latex_escape(cls.get("name"))
    description = latex_escape(cls.get("description"))
    domains = " • ".join(latex_escape(str(v).upper()) for v in cls.get("domains", []))
    image = _tex_image_path(source_root, output_dir, str(cls.get("image") or ""))
    art_width = max(0.25, min(0.55, style["class_art"]))
    text_width = 0.96 - art_width

    pieces = [
        rf"{{\fontsize{{10.5}}{{11.5}}\selectfont\bfseries\color{{CMBright}} CHAPTER {int(view.get('chapter') or 12)} / {latex_escape(config.get('partLabel', 'CHARACTER OPTIONS'))}\par}}",
        r"\vspace{1.0mm}",
        rf"{{\fontsize{{31}}{{32}}\selectfont\bfseries\color{{CMInk}} {title.upper()}\par}}",
        r"\vspace{0.4mm}",
        rf"{{\fontsize{{14}}{{15}}\selectfont\bfseries\color{{CMAccent}} {domains}\par}}",
        r"\vspace{0.7mm}",
        r"{\color{CMBright}\rule{\linewidth}{0.8pt}}",
        r"\vspace{1.8mm}",
        rf"\begin{{minipage}}[t]{{{art_width:.3f}\linewidth}}",
        r"\vspace{0pt}",
        r"\centering",
        rf"\includegraphics[width=\linewidth,height={style['class_art_max']:g}in,keepaspectratio]{{{image}}}",
        r"\end{minipage}\hfill",
        rf"\begin{{minipage}}[t]{{{text_width:.3f}\linewidth}}",
        r"\vspace{0pt}",
        r"\begin{tabularx}{\linewidth}{>{\centering\arraybackslash}X >{\centering\arraybackslash}X}",
        r"\rowcolor{CMSoft}",
        r"{\fontsize{10.5}{11.5}\selectfont\bfseries\color{CMMuted} HIT POINTS} & {\fontsize{10.5}{11.5}\selectfont\bfseries\color{CMMuted} EVASION} \\",
        rf"{{\fontsize{{21}}{{22}}\selectfont\bfseries\color{{CMInk}} {latex_escape(cls.get('hitPoints'))}}} & {{\fontsize{{21}}{{22}}\selectfont\bfseries\color{{CMInk}} {latex_escape(cls.get('evasion'))}}} \\",
        r"\end{tabularx}",
        r"\vspace{1.6mm}",
        rf"{{\fontsize{{10.5}}{{12.3}}\selectfont {description}\par}}",
        r"\end{minipage}",
        r"\vspace{0.8mm}",
    ]
    return "\n".join(pieces)


def _class_support_tex(cls: dict[str, Any]) -> str:
    pieces: list[str] = []
    features = cls.get("features") if isinstance(cls.get("features"), dict) else {}
    for key, label in (("hope", "Hope Feature"), ("class", "Class Features")):
        rows = features.get(key) if isinstance(features.get(key), list) else []
        if not rows:
            continue
        pieces.extend([
            r"\Needspace{0.5in}",
            rf"{{\fontsize{{15}}{{16}}\selectfont\bfseries\color{{CMAccent}} {label.upper()}\par}}",
            r"\vspace{0.35mm}",
        ])
        pieces.extend(_feature_tex(row) for row in rows)

    inventory = cls.get("startingInventory") if isinstance(cls.get("startingInventory"), dict) else {}
    guide = cls.get("characterGuide") if isinstance(cls.get("characterGuide"), dict) else {}
    class_items = cls.get("classItems") if isinstance(cls.get("classItems"), list) else []
    if inventory or guide or class_items:
        pieces.extend([
            r"\Needspace{0.9in}",
            r"{\fontsize{15}{16}\selectfont\bfseries\color{CMAccent} STARTING PACKAGE\par}",
            r"\vspace{0.4mm}",
            r"\begin{tabularx}{\linewidth}{>{\bfseries\color{CMMuted}}p{1.35in} X}",
        ])
        if class_items:
            pieces.append(rf"Class Items & {_reference_names(class_items)} \\")
        for key, label in (("take", "Take"), ("choiceA", "Choice A"), ("choiceB", "Choice B")):
            rows = inventory.get(key) if isinstance(inventory.get(key), list) else []
            if rows:
                pieces.append(rf"{label} & {_reference_names(rows)} \\")
        primary = guide.get("suggestedPrimaryWeapon")
        secondary = guide.get("suggestedSecondaryWeapon")
        armor = guide.get("suggestedArmor")
        if isinstance(primary, dict):
            pieces.append(rf"Suggested Weapon & {latex_escape(primary.get('name'))} \\")
        if isinstance(secondary, dict):
            pieces.append(rf"Secondary Weapon & {latex_escape(secondary.get('name'))} \\")
        if isinstance(armor, dict):
            pieces.append(rf"Suggested Armor & {latex_escape(armor.get('name'))} \\")
        traits = guide.get("suggestedTraits")
        if isinstance(traits, dict) and traits:
            trait_text = ", ".join(
                f"{latex_escape(str(name).title())} {latex_escape(value)}"
                for name, value in traits.items()
            )
            pieces.append(rf"Suggested Traits & {trait_text} \\")
        pieces.extend([r"\end{tabularx}", r"\vspace{0.8mm}"])

    for field, label in (("backgroundQuestions", "Background Questions"), ("connections", "Connections")):
        values = cls.get(field)
        if not isinstance(values, list) or not values:
            continue
        pieces.extend([
            rf"{{\fontsize{{13}}{{14}}\selectfont\bfseries\color{{CMAccent}} {label.upper()}\par}}",
            r"\begin{itemize}",
            *[rf"\item {latex_escape(value)}" for value in values],
            r"\end{itemize}",
        ])
    return "\n".join(pieces)


def _subclass_tex(
    subclass: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = _style(config)
    name = latex_escape(subclass.get("name"))
    description = latex_escape(subclass.get("description"))
    image = _tex_image_path(source_root, output_dir, str(subclass.get("image") or ""))
    art_width = max(0.25, min(0.44, style["subclass_art"]))
    text_width = 0.94 - art_width
    trait = str(subclass.get("spellcastingTrait") or "").strip()

    pieces = [
        r"\vspace{0pt}",
        r"{\fontsize{10.5}{11.5}\selectfont\bfseries\color{CMBright} SUBCLASS\par}",
        rf"{{\fontsize{{20.5}}{{21.5}}\selectfont\bfseries\color{{CMInk}} {name.upper()}\par}}",
        r"\vspace{0.3mm}",
        r"{\color{CMBright}\rule{\linewidth}{0.55pt}}",
        r"\vspace{1.0mm}",
        rf"\begin{{minipage}}[t]{{{art_width:.3f}\linewidth}}",
        r"\vspace{0pt}",
        r"\centering",
        rf"\includegraphics[width=\linewidth,height={style['subclass_art_max']:g}in,keepaspectratio]{{{image}}}",
        r"\end{minipage}\hfill",
        rf"\begin{{minipage}}[t]{{{text_width:.3f}\linewidth}}",
        r"\vspace{0pt}",
    ]
    if trait:
        pieces.extend([
            r"\colorbox{CMSubclass}{\parbox{0.90\linewidth}{\centering",
            rf"\fontsize{{10.5}}{{11.5}}\selectfont\bfseries\color{{CMInk}} SPELLCAST TRAIT: {latex_escape(trait.upper())}",
            r"}}",
            r"\vspace{0.6mm}",
        ])
    if description:
        pieces.append(rf"{{\fontsize{{10.5}}{{12.1}}\selectfont {description}\par}}")
    else:
        pieces.append(r"{\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted} No subclass lead text is currently supplied by Step 4.\par}")
    pieces.extend([r"\end{minipage}", r"\vspace{0.8mm}"])

    progression = subclass.get("progression") if isinstance(subclass.get("progression"), dict) else {}
    for stage in (config.get("composition") or {}).get(
        "subclassProgressionOrder", ["foundation", "specialization", "mastery"]
    ):
        stage_name = str(stage)
        rows = progression.get(stage_name) if isinstance(progression.get(stage_name), list) else []
        pieces.extend([
            r"\Needspace{0.45in}",
            rf"{{\fontsize{{12.5}}{{13.5}}\selectfont\bfseries\color{{CMAccent}} {latex_escape(stage_name.upper())}\par}}",
            r"\vspace{0.2mm}",
        ])
        if rows:
            pieces.extend(_feature_tex(row, compact=True) for row in rows)
        else:
            pieces.append(r"{\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted} No features at this progression stage.\par}")
    return "\n".join(pieces)


def _subclass_pages_tex(
    subclasses: list[dict[str, Any]],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    if not subclasses:
        return ""
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    columns = int(composition.get("subclassPageColumns", 2) or 2)
    columns = max(1, min(2, columns))
    style = _style(config)
    column_width = style["subclass_column"] if columns > 1 else 1.0
    column_width = max(0.45, min(0.495, column_width)) if columns > 1 else 1.0

    pages: list[str] = []
    for offset in range(0, len(subclasses), columns):
        group = subclasses[offset : offset + columns]
        blocks: list[str] = []
        for subclass in group:
            blocks.append(
                "\n".join(
                    [
                        rf"\begin{{minipage}}[t]{{{column_width:.3f}\linewidth}}",
                        r"\vspace{0pt}",
                        r"\setlength{\parskip}{0.7mm}",
                        _subclass_tex(subclass, config, source_root, output_dir),
                        r"\end{minipage}",
                    ]
                )
            )
        pages.append("\n\\hfill\n".join(blocks))
    return "\n\\clearpage\n".join(pages)


def render_class_package_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    """Render the compact D ClassPackage design proof as LuaLaTeX."""
    style = _style(config)
    preamble = rf"""\documentclass[11pt]{{article}}
\usepackage[letterpaper,margin={style['margin']:g}in]{{geometry}}
\usepackage{{fontspec}}
\usepackage[table]{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{ragged2e}}
\usepackage{{microtype}}
\usepackage{{needspace}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{1.35mm}}
\IfFontExistsTF{{Roboto Condensed}}{{\setsansfont{{Roboto Condensed}}}}{{\setsansfont{{TeX Gyre Heros}}}}
\IfFontExistsTF{{Roboto}}{{\setmainfont{{Roboto}}}}{{\setmainfont{{TeX Gyre Heros}}}}
\definecolor{{CMAccent}}{{HTML}}{{{style['accent']}}}
\definecolor{{CMBright}}{{HTML}}{{{style['bright']}}}
\definecolor{{CMInk}}{{HTML}}{{{style['ink']}}}
\definecolor{{CMMuted}}{{HTML}}{{{style['muted']}}}
\definecolor{{CMSoft}}{{HTML}}{{{style['soft']}}}
\definecolor{{CMSubclass}}{{HTML}}{{{style['subclass']}}}
"""
    pieces = [
        preamble,
        r"\begin{document}",
        r"\sffamily",
        r"\fontsize{10.5}{12.2}\selectfont",
        r"\frenchspacing",
        _class_opening_tex(view, config, source_root, output_dir),
        _class_support_tex(view["class"]),
    ]
    subclasses = view.get("subclasses") if isinstance(view.get("subclasses"), list) else []
    if subclasses:
        pieces.extend([
            r"\clearpage",
            _subclass_pages_tex(subclasses, config, source_root, output_dir),
        ])
    pieces.extend([r"\end{document}", ""])
    return "\n".join(pieces)
