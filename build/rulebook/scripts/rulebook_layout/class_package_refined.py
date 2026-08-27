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


def _subclass_tex(
    subclass: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = base._style(config)
    name = latex_escape(subclass.get("name"))
    description = latex_escape(base._single_paragraph(subclass.get("description")))
    image = base._tex_image_path(source_root, output_dir, str(subclass.get("image") or ""))
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
        pieces.extend(
            [
                r"\colorbox{CMSubclass}{\parbox{0.90\linewidth}{\centering",
                rf"\fontsize{{10.5}}{{11.5}}\selectfont\bfseries\color{{CMInk}} SPELLCAST TRAIT: {latex_escape(trait.upper())}",
                r"}}",
                r"\par",
                r"\vspace{2.0mm}",
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
    pieces.extend([r"\end{minipage}", r"\vspace{0.8mm}"])

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
            pieces.extend(base._feature_tex(row, compact=True) for row in rows)
        else:
            pieces.append(
                r"{\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted} No features at this progression stage.\par}"
            )
    return "\n".join(pieces)


def render_class_package_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    """Apply the approved structural alignment refinements to the compact renderer."""
    original = (base._class_opening_tex, base._subclass_tex, base._package_column_tex, base.latex_escape)
    base._class_opening_tex = _class_opening_tex
    base._subclass_tex = _subclass_tex
    base._package_column_tex = _package_column_tex
    base.latex_escape = _latex_escape_value
    try:
        return base.render_class_package_tex(view, config, source_root, output_dir)
    finally:
        base._class_opening_tex, base._subclass_tex, base._package_column_tex, base.latex_escape = original
