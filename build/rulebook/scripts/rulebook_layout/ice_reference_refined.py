from __future__ import annotations

import re
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


def _inline_tex(value: Any) -> str:
    text = latex_escape(value)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\emph{\1}", text)
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)
    return text


def markdown_to_tex(value: Any) -> str:
    """Render the small Markdown subset emitted by Step 4 ICE semantics."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = text.split("\n")
    out: list[str] = []
    list_depth = 0

    def open_list() -> None:
        nonlocal list_depth
        out.extend(
            [
                r"\begin{itemize}",
                r"\setlength{\itemsep}{0.45mm}",
                r"\setlength{\parsep}{0pt}",
                r"\setlength{\topsep}{0.6mm}",
            ]
        )
        list_depth += 1

    def close_lists(target: int = 0) -> None:
        nonlocal list_depth
        while list_depth > target:
            out.append(r"\end{itemize}")
            list_depth -= 1

    for raw in lines:
        if not raw.strip():
            close_lists()
            if out and out[-1] != r"\par":
                out.append(r"\par")
            continue
        match = re.match(r"^(?P<indent>\s*)[-*+]\s+(?P<body>.+)$", raw)
        if match:
            indent = len(match.group("indent").replace("\t", "  "))
            depth = max(1, indent // 2 + 1)
            while list_depth < depth:
                open_list()
            close_lists(depth)
            out.append(r"\item " + _inline_tex(match.group("body").strip()))
            continue
        close_lists()
        out.append(_inline_tex(raw.strip()) + r"\par")
    close_lists()
    return "\n".join(out)


def _style(config: dict[str, Any]) -> dict[str, float | str]:
    source = config.get("style") if isinstance(config.get("style"), dict) else {}
    minimum = float(source.get("minimumEntryTextFontPt", 10.5) or 10.5)
    body = max(minimum, float(source.get("entryBodyFontPt", minimum) or minimum))
    body_leading = max(body + 1.4, float(source.get("entryBodyLeadingPt", body + 1.4) or body + 1.4))
    title = max(minimum, float(source.get("entryTitleFontPt", 13.0) or 13.0))
    title_leading = max(title + 1.0, float(source.get("entryTitleLeadingPt", title + 1.0) or title + 1.0))
    entry_type = max(9.0, float(source.get("entryTypeFontPt", 9.5) or 9.5))
    entry_type_leading = max(entry_type + 1.0, float(source.get("entryTypeLeadingPt", entry_type + 1.0) or entry_type + 1.0))
    action_title = max(minimum, float(source.get("actionTitleFontPt", minimum) or minimum))
    action_leading = max(action_title + 1.0, float(source.get("actionTitleLeadingPt", action_title + 1.0) or action_title + 1.0))
    meta = max(9.0, float(source.get("metadataFontPt", 9.5) or 9.5))
    meta_leading = max(meta + 1.0, float(source.get("metadataLeadingPt", meta + 1.0) or meta + 1.0))
    return {
        "accent": str(source.get("accentColor", "0B6573")),
        "bright": str(source.get("accentBrightColor", "18A7B5")),
        "ink": str(source.get("inkColor", "111B28")),
        "body_text": str(source.get("bodyTextColor", "202833")),
        "muted": str(source.get("mutedColor", "58747A")),
        "soft": str(source.get("softColor", "EAF4F5")),
        "rule": str(source.get("ruleColor", "B9D9DC")),
        "paper": str(source.get("paperColor", "F9F9F7")),
        "dark": str(source.get("darkBandColor", "111B28")),
        "gm": str(source.get("gmAccentColor", "6C55A6")),
        "display_font": str(source.get("displayFont", "Arial")),
        "body_font": str(source.get("bodyFont", "Arial")),
        "margin": float(source.get("pageMarginIn", 0.55) or 0.55),
        "top_margin": float(source.get("pageTopMarginIn", 0.72) or 0.72),
        "bottom_margin": float(source.get("pageBottomMarginIn", 0.70) or 0.70),
        "column_sep": float(source.get("columnSepIn", 0.24) or 0.24),
        "body": body,
        "body_leading": body_leading,
        "title": title,
        "title_leading": title_leading,
        "type": entry_type,
        "type_leading": entry_type_leading,
        "action": action_title,
        "action_leading": action_leading,
        "meta": meta,
        "meta_leading": meta_leading,
        "entry_needspace": float(source.get("entryMinStartSpaceIn", 0.72) or 0.72),
        "action_needspace": float(source.get("actionMinStartSpaceIn", 0.42) or 0.42),
        "identity_image_height": float(source.get("entryIdentityImageHeightIn", 0.38) or 0.38),
        "identity_image_gap": float(source.get("entryIdentityImageGapIn", 0.07) or 0.07),
    }


def _format_cost(cost: Any) -> str:
    if not isinstance(cost, list):
        return ""
    parts: list[str] = []
    labels = {"fear": "Fear", "hope": "Hope", "stress": "Stress", "hp": "HP"}
    for row in cost:
        if not isinstance(row, dict):
            continue
        raw_key = str(row.get("key") or "").strip()
        key = labels.get(raw_key.casefold(), raw_key.replace("_", " ").title()) if raw_key else ""
        value = row.get("value")
        if key and value not in (None, ""):
            label = f"{value} {key}"
        elif key:
            label = key
        elif value not in (None, ""):
            label = str(value)
        else:
            continue
        if row.get("scalable"):
            label += " (scalable)"
        if row.get("consumeOnSuccess"):
            label += " on success"
        parts.append(label)
    return "; ".join(parts)


def _format_target(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    amount = value.get("amount")
    kind = str(value.get("type") or "").strip()
    if kind.casefold() == "any" and amount in (None, ""):
        return ""
    if amount not in (None, "") and kind:
        return f"{amount} {kind}"
    return kind or (str(amount) if amount not in (None, "") else "")


def _format_uses(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    current, maximum, recovery = value.get("value"), value.get("max"), value.get("recovery")
    if current not in (None, "") and maximum not in (None, ""):
        text = f"{current}/{maximum}"
    elif current not in (None, ""):
        text = str(current)
    elif maximum not in (None, ""):
        text = f"max {maximum}"
    else:
        text = ""
    if recovery not in (None, ""):
        text = (text + f"; recovers {recovery}").strip("; ")
    return text


def _format_damage(value: Any) -> str:
    if not isinstance(value, dict) or not isinstance(value.get("parts"), list):
        return ""
    rendered: list[str] = []
    for part in value["parts"]:
        if not isinstance(part, dict):
            continue
        formula = str(part.get("formula") or "").strip()
        target = str(part.get("target") or "").strip()
        types = part.get("types")
        type_text = "/".join(str(item) for item in types if str(item)) if isinstance(types, list) else str(types or "").strip()
        chunks = [chunk for chunk in (formula, type_text, target) if chunk]
        if chunks:
            rendered.append(" ".join(chunks))
    return "; ".join(rendered)


def _metadata_lines(action: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    cost = _format_cost(action.get("cost"))
    if cost:
        rows.append(("Cost", cost))
    if action.get("range") not in (None, ""):
        rows.append(("Range", str(action.get("range"))))
    target = _format_target(action.get("target"))
    if target:
        rows.append(("Target", target))
    damage = _format_damage(action.get("damage"))
    if damage:
        rows.append(("Damage", damage))
    uses = _format_uses(action.get("uses"))
    if uses:
        rows.append(("Uses", uses))
    return rows


def _action_tex(action: dict[str, Any], style: dict[str, Any]) -> str:
    name = str(action.get("name") or "Action").strip()
    action_type = str(action.get("actionType") or "").strip()
    type_suffix = ""
    if action_type:
        type_suffix = rf"\hspace{{0.6em}}{{\fontsize{{7.8}}{{8.8}}\selectfont\color{{CMMuted}}\MakeUppercase{{{_inline_tex(action_type)}}}}}"
    pieces = [
        rf"\Needspace{{{style['action_needspace']:.2f}in}}",
        rf"{{\CMDisplay\fontsize{{{style['action']:.2f}}}{{{style['action_leading']:.2f}}}\selectfont\bfseries\color{{CMInk}} {_inline_tex(name)}{type_suffix}\par}}",
    ]
    rules = markdown_to_tex(action.get("rulesMarkdown"))
    if rules:
        pieces.extend(
            [
                r"\begingroup",
                r"\setlength{\parskip}{0.6mm}",
                r"\setlength{\parindent}{0pt}",
                rf"\fontsize{{{style['body']:.2f}}}{{{style['body_leading']:.2f}}}\selectfont\color{{CMBodyText}}",
                rules,
                r"\endgroup",
            ]
        )
    for label, value in _metadata_lines(action):
        pieces.append(
            rf"{{\fontsize{{{style['meta']:.2f}}}{{{style['meta_leading']:.2f}}}\selectfont\color{{CMMuted}}\textbf{{{latex_escape(label)}:}} {_inline_tex(value)}\par}}"
        )
    return "\n".join(pieces)


def _resource_tex(resource: Any, style: dict[str, Any]) -> str:
    if not isinstance(resource, dict) or not resource:
        return ""
    label = str(resource.get("label") or "Resource").strip()
    values: list[str] = []
    if resource.get("value") not in (None, ""):
        values.append(str(resource.get("value")))
    if resource.get("max") not in (None, ""):
        values.append(f"max {resource.get('max')}")
    if not values:
        return ""
    return rf"{{\fontsize{{{style['meta']:.2f}}}{{{style['meta_leading']:.2f}}}\selectfont\color{{CMMuted}}\textbf{{{_inline_tex(label)}:}} {_inline_tex('; '.join(values))}\par}}"


def _entry_identity_tex(
    entry: dict[str, Any],
    style: dict[str, Any],
    render_assets: dict[str, str],
) -> str:
    name = str(entry.get("name") or "").strip()
    type_label = "SENTRY ICE" if str(entry.get("iceType") or "").strip().casefold() == "sentry" else "WALL ICE"
    title_block = "\n".join(
        [
            rf"{{\CMDisplay\fontsize{{{style['title']:.2f}}}{{{style['title_leading']:.2f}}}\selectfont\bfseries\color{{CMInk}} {_inline_tex(name)}\par}}",
            rf"{{\CMDisplay\fontsize{{{style['type']:.2f}}}{{{style['type_leading']:.2f}}}\selectfont\bfseries\color{{CMAccent}} {type_label}\par}}",
        ]
    )
    image_ref = str(entry.get("image") or "").strip().replace("\\", "/")
    render_path = str(render_assets.get(image_ref) or "").strip().replace("\\", "/")
    if not image_ref or not render_path:
        return title_block

    image_height = float(style["identity_image_height"])
    gap = float(style["identity_image_gap"])
    reserved = image_height + gap
    return "\n".join(
        [
            r"\noindent%",
            rf"\begin{{minipage}}[c]{{{image_height:.3f}in}}",
            r"\centering",
            rf"\includegraphics[height={image_height:.3f}in,width={image_height:.3f}in,keepaspectratio]{{\detokenize{{{render_path}}}}}",
            r"\end{minipage}%",
            rf"\hspace{{{gap:.3f}in}}%",
            rf"\begin{{minipage}}[c]{{\dimexpr\linewidth-{reserved:.3f}in\relax}}",
            title_block,
            r"\end{minipage}\par",
        ]
    )


def _entry_tex(
    entry: dict[str, Any],
    config: dict[str, Any],
    render_assets: dict[str, str],
) -> str:
    style = _style(config)
    pieces = [
        rf"\Needspace{{{style['entry_needspace']:.2f}in}}",
        _entry_identity_tex(entry, style, render_assets),
        r"\vspace{0.8mm}",
    ]
    rules = markdown_to_tex(entry.get("rulesMarkdown"))
    if rules:
        pieces.extend(
            [
                r"\begingroup",
                r"\setlength{\parskip}{0.8mm}",
                r"\setlength{\parindent}{0pt}",
                r"\setlength{\emergencystretch}{1.5em}",
                rf"\fontsize{{{style['body']:.2f}}}{{{style['body_leading']:.2f}}}\selectfont\color{{CMBodyText}}",
                rules,
                r"\endgroup",
            ]
        )
    actions = entry.get("actions")
    if isinstance(actions, list) and actions:
        pieces.extend(
            [
                r"\vspace{1.0mm}",
                rf"{{\CMDisplay\fontsize{{{style['meta']:.2f}}}{{{style['meta_leading']:.2f}}}\selectfont\bfseries\color{{CMAccent}} ACTIONS\par}}",
            ]
        )
        for action in actions:
            if isinstance(action, dict):
                pieces.append(_action_tex(action, style))
                pieces.append(r"\vspace{0.8mm}")
    resource = _resource_tex(entry.get("resource"), style)
    if resource:
        pieces.extend([r"\vspace{0.8mm}", resource])
    pieces.extend(
        [
            r"\vspace{1.5mm}",
            r"{\color{CMRule}\rule{\linewidth}{0.35pt}}",
            r"\vspace{2.0mm}",
        ]
    )
    return "\n".join(pieces)


def _chapter_header(view: dict[str, Any], config: dict[str, Any]) -> str:
    chapter = int(view.get("chapter") or config.get("chapter") or 29)
    part_label = _inline_tex(view.get("partLabel") or config.get("partLabel") or "GM ENCOUNTER TOOLKIT")
    title = _inline_tex(view.get("title") or config.get("title") or "ICE Reference")
    intro = markdown_to_tex(view.get("chapterIntro"))
    band = [
        r"\begingroup",
        r"\setlength{\fboxsep}{4.0mm}",
        r"\noindent\colorbox{CMDark}{%",
        r"\parbox{\dimexpr\linewidth-2\fboxsep\relax}{%",
        rf"{{\CMDisplay\fontsize{{8.0}}{{9.0}}\selectfont\bfseries\color{{CMGM}} STEP 6 // GM MATERIAL\hfill CHAPTER {chapter}\par}}",
        r"\vspace{1.6mm}",
        rf"{{\CMDisplay\fontsize{{30}}{{31}}\selectfont\bfseries\color{{white}} {title.upper()}\par}}",
        r"\vspace{1.0mm}",
        r"{\color{CMBright}\rule{\linewidth}{0.8pt}}",
        r"\vspace{1.0mm}",
        rf"{{\CMDisplay\fontsize{{8.2}}{{9.2}}\selectfont\bfseries\color{{white}} {part_label}\par}}",
        r"}%",
        r"}%",
        r"\endgroup",
    ]
    if intro:
        band.extend(
            [
                r"\vspace{2.5mm}",
                r"\begingroup",
                r"\setlength{\parskip}{0pt}",
                r"\setlength{\parindent}{0pt}",
                r"\fontsize{10.5}{13.0}\selectfont\color{CMBodyText}",
                intro,
                r"\endgroup",
            ]
        )
    band.append(r"\vspace{3.2mm}")
    return "\n".join(band)


def _group_tex(
    group: dict[str, Any],
    config: dict[str, Any],
    render_assets: dict[str, str],
) -> str:
    style = _style(config)
    title = _inline_tex(group.get("title"))
    entries = [row for row in group.get("entries", []) if isinstance(row, dict)]
    count_label = "ENTRY" if len(entries) == 1 else "ENTRIES"
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    columns = max(1, int(composition.get("pageColumns") or 2))
    pieces = [
        r"\Needspace{0.9in}",
        r"\noindent\begin{minipage}{\linewidth}",
        rf"{{\CMDisplay\fontsize{{17}}{{18}}\selectfont\bfseries\color{{CMAccent}} {title}\hfill\fontsize{{7.6}}{{8.6}}\selectfont\bfseries\color{{CMMuted}} {len(entries)} {count_label}\par}}",
        r"\vspace{0.8mm}",
        r"{\color{CMRule}\rule{\linewidth}{0.55pt}}",
        r"\end{minipage}",
        r"\vspace{1.8mm}",
        rf"\begin{{multicols}}{{{columns}}}",
        r"\raggedcolumns",
        rf"\setlength{{\columnsep}}{{{style['column_sep']:.3f}in}}",
    ]
    for entry in entries:
        pieces.append(_entry_tex(entry, config, render_assets))
    pieces.extend([r"\end{multicols}", r"\vspace{1.0mm}"])
    return "\n".join(pieces)


def render_ice_reference_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    render_assets: dict[str, str] | None = None,
) -> str:
    style = _style(config)
    render_assets = render_assets or {}
    groups = [row for row in view.get("groups", []) if isinstance(row, dict)]
    body = [_chapter_header(view, config)]
    for group in groups:
        body.append(_group_tex(group, config, render_assets))

    running_title = _inline_tex(view.get("title") or config.get("title") or "ICE Reference")
    footer_label = _inline_tex(str(config.get("footerLabel") or "STEP 6 // ICE REFERENCE PACKAGE V1"))
    return "\n".join(
        [
            r"\documentclass[10pt,twoside]{article}",
            rf"\usepackage[letterpaper,left={style['margin']:.3f}in,right={style['margin']:.3f}in,top={style['top_margin']:.3f}in,bottom={style['bottom_margin']:.3f}in,headheight=16pt,headsep=10pt,footskip=24pt]{{geometry}}",
            r"\usepackage{fontspec}",
            r"\usepackage{xcolor}",
            r"\usepackage{graphicx}",
            r"\usepackage{multicol}",
            r"\usepackage{needspace}",
            r"\usepackage{fancyhdr}",
            rf"\setmainfont{{{latex_escape(style['body_font'])}}}",
            rf"\newfontfamily\CMDisplay{{{latex_escape(style['display_font'])}}}",
            rf"\definecolor{{CMAccent}}{{HTML}}{{{style['accent']}}}",
            rf"\definecolor{{CMBright}}{{HTML}}{{{style['bright']}}}",
            rf"\definecolor{{CMInk}}{{HTML}}{{{style['ink']}}}",
            rf"\definecolor{{CMBodyText}}{{HTML}}{{{style['body_text']}}}",
            rf"\definecolor{{CMMuted}}{{HTML}}{{{style['muted']}}}",
            rf"\definecolor{{CMSoft}}{{HTML}}{{{style['soft']}}}",
            rf"\definecolor{{CMRule}}{{HTML}}{{{style['rule']}}}",
            rf"\definecolor{{CMPaper}}{{HTML}}{{{style['paper']}}}",
            rf"\definecolor{{CMDark}}{{HTML}}{{{style['dark']}}}",
            rf"\definecolor{{CMGM}}{{HTML}}{{{style['gm']}}}",
            r"\pagecolor{CMPaper}",
            r"\color{CMBodyText}",
            r"\setlength{\parindent}{0pt}",
            r"\setlength{\parskip}{0pt}",
            r"\setlength{\columnseprule}{0pt}",
            r"\setlength{\leftmargini}{1.25em}",
            r"\setlength{\leftmarginii}{1.15em}",
            r"\renewcommand{\labelitemi}{\textcolor{CMAccent}{\textbullet}}",
            r"\renewcommand{\labelitemii}{\textcolor{CMMuted}{\textendash}}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            rf"\fancyhead[L]{{\CMDisplay\fontsize{{7.8}}{{8.8}}\selectfont\bfseries\color{{CMMuted}} CYBERMANCY // {running_title.upper()}}}",
            r"\fancyhead[R]{\CMDisplay\fontsize{7.8}{8.8}\selectfont\bfseries\color{CMGM} GM MATERIAL}",
            rf"\fancyfoot[LO,RE]{{\CMDisplay\fontsize{{7.2}}{{8.2}}\selectfont\color{{CMMuted}} {footer_label}}}",
            r"\fancyfoot[LE,RO]{\CMDisplay\fontsize{8.0}{9.0}\selectfont\bfseries\color{CMInk} \thepage}",
            r"\renewcommand{\headrulewidth}{0pt}",
            r"\renewcommand{\footrulewidth}{0pt}",
            r"\begin{document}",
            r"\raggedbottom",
            *body,
            r"\end{document}",
            "",
        ]
    )
