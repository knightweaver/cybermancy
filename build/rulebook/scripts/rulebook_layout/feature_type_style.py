from __future__ import annotations

from typing import Any


FEATURE_TYPE_FONT_PT = 9.5
FEATURE_TYPE_LEADING_PT = 10.5

_LATEX_SPECIAL = {
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


def _latex_escape(value: Any) -> str:
    text = str(value or "")
    return "".join(_LATEX_SPECIAL.get(ch, ch) for ch in text)


def feature_type_label_tex(
    value: Any,
    *,
    color_role: str,
    font_size_pt: float = FEATURE_TYPE_FONT_PT,
    leading_pt: float = FEATURE_TYPE_LEADING_PT,
) -> str:
    """Render the shared reader-facing Feature/Action type-label role."""
    label = str(value or "").strip()
    if not label:
        return ""
    color = str(color_role or "").strip()
    if not color:
        raise ValueError("feature type label requires a caller-supplied color role")
    return (
        rf"{{\fontsize{{{float(font_size_pt):.1f}}}{{{float(leading_pt):.1f}}}"
        rf"\selectfont\bfseries\color{{{color}}} {_latex_escape(label.upper())}}}"
    )
