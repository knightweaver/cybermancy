from __future__ import annotations

from pathlib import Path
from typing import Any

from . import class_package_compact as base
from .class_package import latex_escape


def _latex_escape_value(value: Any) -> str:
    """Escape publication values without treating numeric zero as blank."""
    return latex_escape("" if value is None else str(value))


def _description_block_tex(description: str, leading: str, *, italic: bool = False) -> str:
    style = r"\itshape\color{CMMuted}" if italic else ""
    font_line = rf"\fontsize{{10.5}}{{{leading}}}\selectfont"
    if style:
        font_line += style
    return "\n".join(
        [
            r"\begingroup",
            r"\setlength{\parskip}{0pt}",
            r"\setlength{\parindent}{0pt}",
            font_line,
            rf"\noindent {description}\par",
            r"\endgroup",
        ]
    )


def _feature_tex(feature: dict[str, Any], *, compact: bool = False) -> str:
    """Render one feature without a section separator.

    Separators belong to the enclosing feature type (Hope, Class Features,
    Foundation, Specialization, Mastery), not to individual features.
    """
    name = _latex_escape_value(feature.get("name"))
    description = _latex_escape_value(feature.get("description"))
    needspace = "0.52in" if compact else "0.62in"
    between_space = "0.7mm" if compact else "1.0mm"

    lines = [
        rf"\Needspace{{{needspace}}}",
        rf"{{\fontsize{{12}}{{13.2}}\selectfont\bfseries\color{{CMInk}} {name}\par}}",
        r"\vspace{0.15mm}",
    ]
    if description:
        lines.append(rf"{{\fontsize{{10.5}}{{12.1}}\selectfont {description}\par}}")
    else:
        lines.append(
            r"{\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted} No publication description supplied.\par}"
        )
    lines.append(rf"\vspace{{{between_space}}}")
    return "\n".join(lines)


def _feature_group_separator_tex(*, compact: bool = False) -> str:
    line_width = "0.35pt" if compact else "0.45pt"
    bottom_space = "0.7mm" if compact else "1.0mm"
    return "\n".join(
        [
            r"\vspace{0.25mm}",
            rf"{{\color{{CMBright}}\rule{{\linewidth}}{{{line_width}}}}}",
            rf"\vspace{{{bottom_space}}}",
        ]
    )


def _feature_group_tex(rows: list[dict[str, Any]], *, compact: bool = False) -> str:
    """Render all features in one semantic type followed by one separator."""
    pieces = [_feature_tex(row, compact=compact) for row in rows]
    pieces.append(_feature_group_separator_tex(compact=compact))
    return "\n".join(pieces)


def _package_column_tex(rows: list[tuple[str, str]], label_width: str) -> str:
    if label_width == "0.82in":
        label_fraction, value_fraction = 0.300, 0.660
    else:
        label_fraction, value_fraction = 0.430, 0.530

    pieces: list[str] = []
    for label, value in rows:
        pieces.extend(
            [
                r"\noindent",
                rf"\begin{{minipage}}[t]{{{label_fraction:.3f}\linewidth}}",
                r"\vspace{0pt}",
                r"\setlength{\parskip}{0pt}",
                rf"{{\bfseries\color{{CMMuted}}\raggedright\strut {label}\par}}",
                r"\end{minipage}\hfill",
                rf"\begin{{minipage}}[t]{{{value_fraction:.3f}\linewidth}}",
                r"\vspace{0pt}",
                r"\setlength{\parskip}{0pt}",
                rf"{{\raggedright\strut {value}\par}}",
                r"\end{minipage}",
                r"\par\vspace{0.65mm}",
            ]
        )
    return "\n".join(pieces)


def _class_opening_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = base._style(config)
    cls = view["class"]
    title = latex_escape(cls.get("name"))
    description = latex_escape(base._single_paragraph(cls.get("description")))
    domains = " • ".join(latex_escape(str(v).upper()) for v in cls.get("domains", []))
    image = base._tex_image_path(source_root, output_dir, str(cls.get("image") or ""))
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
        rf"{{\fontsize{{21}}{{22}}\selectfont\bfseries\color{{CMInk}} {_latex_escape_value(cls.get('hitPoints'))}}} & {{\fontsize{{21}}{{22}}\selectfont\bfseries\color{{CMInk}} {_latex_escape_value(cls.get('evasion'))}}} \\",
        r"\end{tabularx}",
        r"\par",
        r"\vspace{3.0mm}",
        _description_block_tex(description, "12.3"),
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
        pieces.extend(
            [
                r"\Needspace{0.5in}",
                rf"{{\fontsize{{15}}{{16}}\selectfont\bfseries\color{{CMAccent}} {label.upper()}\par}}",
                r"\vspace{0.35mm}",
                _feature_group_tex(rows),
            ]
        )

    inventory = cls.get("startingInventory") if isinstance(cls.get("startingInventory"), dict) else {}
    guide = cls.get("characterGuide") if isinstance(cls.get("characterGuide"), dict) else {}
    class_items = cls.get("classItems") if isinstance(cls.get("classItems"), list) else []

    left_rows: list[tuple[str, str]] = []
    right_rows: list[tuple[str, str]] = []

    if class_items:
        left_rows.append(("Class Items", base._reference_names(class_items)))
    for key, label in (("take", "Take"), ("choiceA", "Choice A"), ("choiceB", "Choice B")):
        rows = inventory.get(key) if isinstance(inventory.get(key), list) else []
        if rows:
            left_rows.append((label, base._reference_names(rows)))

    primary = guide.get("suggestedPrimaryWeapon")
    secondary = guide.get("suggestedSecondaryWeapon")
    armor = guide.get("suggestedArmor")
    if isinstance(primary, dict):
        right_rows.append(("Suggested Weapon", _latex_escape_value(primary.get("name"))))
    if isinstance(secondary, dict):
        right_rows.append(("Secondary Weapon", _latex_escape_value(secondary.get("name"))))
    if isinstance(armor, dict):
        right_rows.append(("Suggested Armor", _latex_escape_value(armor.get("name"))))
    traits = guide.get("suggestedTraits")
    if isinstance(traits, dict) and traits:
        trait_text = ", ".join(
            f"{_latex_escape_value(str(name).title())} {_latex_escape_value(value)}"
            for name, value in traits.items()
        )
        right_rows.append(("Suggested Traits", trait_text))

    if left_rows or right_rows:
        pieces.extend(
            [
                r"\Needspace{0.9in}",
                r"{\fontsize{15}{16}\selectfont\bfseries\color{CMAccent} STARTING PACKAGE\par}",
                r"\vspace{0.5mm}",
                r"\begin{minipage}[t]{0.485\linewidth}",
                r"\vspace{0pt}",
                _package_column_tex(left_rows, "0.82in"),
                r"\end{minipage}\hfill",
                r"\begin{minipage}[t]{0.485\linewidth}",
                r"\vspace{0pt}",
                _package_column_tex(right_rows, "1.28in"),
                r"\end{minipage}",
                r"\vspace{0.8mm}",
            ]
        )

    for field, label in (("backgroundQuestions", "Background Questions"), ("connections", "Connections")):
        values = cls.get(field)
        if not isinstance(values, list) or not values:
            continue
        pieces.extend(
            [
                rf"{{\fontsize{{13}}{{14}}\selectfont\bfseries\color{{CMAccent}} {label.upper()}\par}}",
                r"\begin{itemize}",
                *[rf"\item {_latex_escape_value(value)}" for value in values],
                r"\end{itemize}",
            ]
        )
    return "\n".join(pieces)


def _subclass_tex(
    subclass: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = base._style(config)
    name = latex_escape(subclass.get("name"))
    description = latex_escape(base._single_paragraph(subclass.get("description")))
    image_path = str(subclass.get("image") or "").strip()
    image = base._tex_image_path(source_root, output_dir, image_path) if image_path else ""
    art_width = max(0.25, min(0.44, style["subclass_art"]))
    trait = str(subclass.get("spellcastingTrait") or "").strip()

    pieces = [
        r"\vspace{0pt}",
        r"{\fontsize{10.5}{11.5}\selectfont\bfseries\color{CMBright} SUBCLASS\par}",
        rf"{{\fontsize{{20.5}}{{21.5}}\selectfont\bfseries\color{{CMInk}} {name.upper()}\par}}",
        r"\vspace{0.3mm}",
        r"{\color{CMBright}\rule{\linewidth}{0.55pt}}",
        r"\vspace{1.0mm}",
    ]

    if image:
        pieces.extend(
            [
                rf"\begin{{wrapfigure}}{{l}}{{{art_width:.3f}\linewidth}}",
                r"\vspace{-0.8\baselineskip}",
                r"\centering",
                rf"\includegraphics[width=\linewidth,height={style['subclass_art_max']:g}in,keepaspectratio]{{{image}}}",
                r"\vspace{-0.35\baselineskip}",
                r"\end{wrapfigure}",
            ]
        )

    if trait:
        pieces.extend(
            [
                r"\noindent\colorbox{CMSubclass}{\strut",
                rf"\fontsize{{10.5}}{{11.5}}\selectfont\bfseries\color{{CMInk}} SPELLCAST TRAIT: {latex_escape(trait.upper())}",
                r"}\par",
                r"\vspace{1.2mm}",
            ]
        )
    if description:
        pieces.append(_description_block_tex(description, "12.1"))
    else:
        pieces.append(
            _description_block_tex(
                latex_escape("No subclass lead text is currently supplied by Step 4."),
                "12.1",
                italic=True,
            )
        )

    # The wrap belongs only to the Subclass lead. Progression headings/features
    # must always return to the full width of the paracol column.
    pieces.extend([r"\WFclear", r"\vspace{0.8mm}"])

    progression = subclass.get("progression") if isinstance(subclass.get("progression"), dict) else {}
    for stage in (config.get("composition") or {}).get(
        "subclassProgressionOrder", ["foundation", "specialization", "mastery"]
    ):
        stage_name = str(stage)
        rows = progression.get(stage_name) if isinstance(progression.get(stage_name), list) else []
        pieces.extend(
            [
                r"\Needspace{0.45in}",
                rf"{{\fontsize{{12.5}}{{13.5}}\selectfont\bfseries\color{{CMAccent}} {latex_escape(stage_name.upper())}\par}}",
                r"\vspace{0.2mm}",
            ]
        )
        if rows:
            pieces.append(_feature_group_tex(rows, compact=True))
        else:
            pieces.extend(
                [
                    r"{\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted} No features at this progression stage.\par}",
                    _feature_group_separator_tex(compact=True),
                ]
            )
    return "\n".join(pieces)


def render_class_package_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    """Apply the approved structural alignment refinements to the compact renderer."""
    original = (
        base._class_opening_tex,
        base._class_support_tex,
        base._subclass_tex,
        base._package_column_tex,
        base.latex_escape,
    )
    base._class_opening_tex = _class_opening_tex
    base._class_support_tex = _class_support_tex
    base._subclass_tex = _subclass_tex
    base._package_column_tex = _package_column_tex
    base.latex_escape = _latex_escape_value
    try:
        return base.render_class_package_tex(view, config, source_root, output_dir)
    finally:
        (
            base._class_opening_tex,
            base._class_support_tex,
            base._subclass_tex,
            base._package_column_tex,
            base.latex_escape,
        ) = original
