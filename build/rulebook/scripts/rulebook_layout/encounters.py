from __future__ import annotations

import copy
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from rulebook_layout.feature_type_style import feature_type_label_tex

SUPPORTED_SCHEMA = "cybermancy-step4-encounter-semantics-v1.0"
PRESENTATION_SCHEMA = "cybermancy-encounter-presentation-view-v1.0"
FAMILIES = ("adversaries", "environments", "adversaries-features")

DEFAULT_SECTION_ORDERS = {
    "adversaries": [
        "identity",
        "description",
        "attack",
        "motivesAndTactics",
        "experiences",
        "fastPlay",
        "actions",
        "features",
    ],
    "environments": [
        "identity",
        "description",
        "impulses",
        "potentialAdversaries",
        "fastPlay",
        "actions",
        "features",
    ],
}

_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    text = str(value or "")
    return "".join(_LATEX_SPECIAL.get(ch, ch) for ch in text)


def _inline_markdown(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    pattern = re.compile(r"(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|_[^_]+_)")
    out: list[str] = []
    cursor = 0
    for match in pattern.finditer(text):
        out.append(esc(text[cursor:match.start()]))
        token = match.group(0)
        if token.startswith(("**", "__")):
            out.append(r"\textbf{" + esc(token[2:-2]) + "}")
        elif token.startswith("`"):
            out.append(r"\texttt{" + esc(token[1:-1]) + "}")
        else:
            out.append(r"\emph{" + esc(token[1:-1]) + "}")
        cursor = match.end()
    out.append(esc(text[cursor:]))
    return "".join(out)


def md(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    lines = text.split("\n")
    out: list[str] = []
    bullet_mode: str | None = None

    def close_list() -> None:
        nonlocal bullet_mode
        if bullet_mode:
            out.append(r"\end{" + bullet_mode + "}")
            bullet_mode = None

    for raw in lines:
        line = raw.strip()
        if not line:
            close_list()
            if out and out[-1] != r"\par":
                out.append(r"\par")
            continue
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            close_list()
            out.append(r"\textbf{" + _inline_markdown(heading.group(1)) + r"}\par")
            continue
        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            mode = "itemize" if bullet else "enumerate"
            if bullet_mode != mode:
                close_list()
                bullet_mode = mode
                out.append(r"\begin{" + mode + "}")
            out.append(r"\item " + _inline_markdown((bullet or numbered).group(1)))
            continue
        close_list()
        out.append(_inline_markdown(line))
    close_list()
    while out and out[-1] == r"\par":
        out.pop()
    return "\n".join(out)


def _list_text(values: Any) -> str:
    if isinstance(values, list):
        return ", ".join(str(v) for v in values if str(v or "").strip())
    return str(values or "")


def _normalized_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(text.split()).casefold()


def adversary_sort_key(entity: dict[str, Any]) -> tuple[str, str]:
    """Return the publication ordering key for Chapter 30 adversaries."""
    return (
        _normalized_name(entity.get("name")),
        str(entity.get("semanticId") or ""),
    )


def _entity_index(sidecar: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out = {family: [] for family in FAMILIES}
    for entity in sidecar.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        family = str(entity.get("family") or "")
        if family in out:
            out[family].append(entity)
    return out


def _select(index: dict[str, list[dict[str, Any]]], family: str, names: Iterable[str]) -> list[dict[str, Any]]:
    wanted = [str(name) for name in names]
    by_name: dict[str, list[dict[str, Any]]] = {}
    for entity in index.get(family, []):
        by_name.setdefault(str(entity.get("name") or ""), []).append(entity)
    result: list[dict[str, Any]] = []
    for name in wanted:
        matches = by_name.get(name, [])
        result.extend(sorted(matches, key=lambda e: str(e.get("semanticId") or "")))
    return result


def _family_entities(sidecar: dict[str, Any], family: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    index = _entity_index(sidecar)
    selection = config.get("selection") if isinstance(config.get("selection"), dict) else {}
    semantic_ids = selection.get("semanticIds") if isinstance(selection.get("semanticIds"), list) else []
    if semantic_ids:
        wanted = {str(value) for value in semantic_ids}
        entries = [entity for entity in index.get(family, []) if str(entity.get("semanticId") or "") in wanted]
        order = {str(value): i for i, value in enumerate(semantic_ids)}
        entries.sort(key=lambda entity: order.get(str(entity.get("semanticId") or ""), 10**9))
        return entries
    names = selection.get("names") if isinstance(selection.get("names"), list) else []
    if names:
        return _select(index, family, names)
    entries = list(index.get(family, []))
    if family == "adversaries-features":
        entries.sort(key=lambda e: (str(e.get("name") or "").casefold(), str(e.get("semanticId") or "")))
    elif family == "adversaries":
        entries.sort(key=adversary_sort_key)
    else:
        entries.sort(
            key=lambda e: (
                int((e.get("publicationData") or {}).get("tier") or 0),
                str((e.get("publicationData") or {}).get("classification") or "").casefold(),
                str(e.get("name") or "").casefold(),
                str(e.get("semanticId") or ""),
            )
        )
    return entries


def validate_sidecar(sidecar: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    semantics = sidecar.get("encounterSemantics")
    if not isinstance(semantics, dict):
        errors.append("structured sidecar is missing encounterSemantics")
    elif semantics.get("schema") != SUPPORTED_SCHEMA:
        errors.append(f"encounterSemantics.schema must be {SUPPORTED_SCHEMA}")
    if not isinstance(sidecar.get("entities"), list):
        errors.append("structured sidecar is missing entities[]")
    return errors


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_content(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_content(item) for item in value)
    return True


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "")
        if text.strip():
            return text
    return ""


def normalize_encounter_entity(entity: dict[str, Any], family: str | None = None) -> dict[str, Any]:
    """Project one Adversary/Environment into the in-memory publication view.

    This projection never mutates canonical/Step 4 data and never fills missing
    reader-facing content. Optional values are present in the view only when the
    normalized source already supplies them.
    """
    resolved_family = str(family or entity.get("family") or "")
    if resolved_family not in {"adversaries", "environments"}:
        raise ValueError(f"encounter presentation normalization does not support family {resolved_family!r}")

    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    identity: dict[str, Any] = {}
    if pdata.get("classification") not in (None, ""):
        identity["classification"] = copy.deepcopy(pdata.get("classification"))
    if pdata.get("tier") not in (None, ""):
        identity["tier"] = copy.deepcopy(pdata.get("tier"))

    art = pdata.get("publicationArt") if isinstance(pdata.get("publicationArt"), dict) else {}
    image = _first_text(art.get("image"), pdata.get("image"))
    if image:
        identity["art"] = {"image": image}

    statistics: dict[str, Any] = {}
    for source_key, view_key in (
        ("difficulty", "difficulty"),
        ("hitPoints", "hitPoints"),
        ("stress", "stress"),
    ):
        if pdata.get(source_key) not in (None, ""):
            statistics[view_key] = copy.deepcopy(pdata.get(source_key))
    thresholds = pdata.get("damageThresholds") if isinstance(pdata.get("damageThresholds"), dict) else {}
    if _has_content(thresholds):
        statistics["damageThresholds"] = copy.deepcopy(thresholds)
    if statistics:
        identity["statistics"] = statistics

    sections: dict[str, Any] = {}
    description = _first_text(pdata.get("descriptionMarkdown"), pdata.get("description"))
    if description:
        sections["description"] = description

    if resolved_family == "adversaries":
        for source_key, view_key in (
            ("attack", "attack"),
            ("motivesAndTactics", "motivesAndTactics"),
            ("experiences", "experiences"),
            ("fastPlay", "fastPlay"),
            ("actions", "actions"),
            ("features", "features"),
        ):
            value = pdata.get(source_key)
            if _has_content(value):
                sections[view_key] = copy.deepcopy(value)
    else:
        for source_key, view_key in (
            ("impulses", "impulses"),
            ("potentialAdversaries", "potentialAdversaries"),
            ("fastPlay", "fastPlay"),
            ("actions", "actions"),
            ("features", "features"),
        ):
            value = pdata.get(source_key)
            if _has_content(value):
                sections[view_key] = copy.deepcopy(value)

    return {
        "schema": PRESENTATION_SCHEMA,
        "semanticId": str(entity.get("semanticId") or ""),
        "family": resolved_family,
        "name": str(entity.get("name") or ""),
        "identity": identity,
        "sections": sections,
    }


def normalize_encounter_presentations(
    entities: Iterable[dict[str, Any]],
    family: str,
) -> list[dict[str, Any]]:
    return [normalize_encounter_entity(entity, family) for entity in entities]


def _section_order(config: dict[str, Any], family: str) -> list[str]:
    policy = config.get("presentationPolicy") if isinstance(config.get("presentationPolicy"), dict) else {}
    configured = policy.get("sectionOrder") if isinstance(policy.get("sectionOrder"), list) else None
    default = DEFAULT_SECTION_ORDERS.get(family, [])
    order = [str(value) for value in (configured or default) if str(value)]
    if "identity" not in order:
        order.insert(0, "identity")
    return order


def _preamble(title: str, subtitle: str, *, columns: int = 1) -> str:
    multicol = "\\usepackage{multicol}\n" if columns > 1 else ""
    return rf'''\documentclass[10pt,letterpaper]{{article}}
\usepackage[letterpaper,margin=0.55in,top=0.50in,bottom=0.55in]{{geometry}}
\usepackage[T1]{{fontenc}}
\usepackage{{fontspec}}
\setmainfont{{Arial}}
\setsansfont{{Arial}}
\usepackage{{microtype}}
\usepackage{{graphicx}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{xcolor}}
\usepackage{{tcolorbox}}
\tcbuselibrary{{breakable,skins}}
\usepackage{{titlesec}}
\usepackage{{enumitem}}
\usepackage{{fancyhdr}}
\usepackage{{needspace}}
\usepackage{{ragged2e}}
{multicol}\definecolor{{CMInk}}{{HTML}}{{252431}}
\definecolor{{CMTeal}}{{HTML}}{{167E83}}
\definecolor{{CMTealDark}}{{HTML}}{{0D5E63}}
\definecolor{{CMViolet}}{{HTML}}{{5B3B82}}
\definecolor{{CMPale}}{{HTML}}{{F3F0EA}}
\definecolor{{CMLine}}{{HTML}}{{B7C6C4}}
\definecolor{{CMSoft}}{{HTML}}{{E8F1F0}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[L]{{\sffamily\scriptsize\color{{CMTealDark}} CYBERMANCY / ENCOUNTER TOOLKIT}}
\fancyhead[R]{{\sffamily\scriptsize\color{{CMInk}} {esc(title)}}}
\fancyfoot[C]{{\sffamily\scriptsize\color{{CMInk}}\thepage}}
\renewcommand{{\headrulewidth}}{{0pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{3.5pt}}
\setlist[itemize]{{leftmargin=1.2em,itemsep=1pt,topsep=2pt}}
\titleformat{{\section}}{{\sffamily\bfseries\Large\color{{CMInk}}}}{{}}{{0pt}}{{}}
\newtcolorbox{{cmfeature}}[1][]{{enhanced,colback=white,colframe=CMLine,boxrule=0.45pt,arc=1.2mm,left=2mm,right=2mm,top=1.4mm,bottom=1.4mm,before skip=3pt,after skip=3pt,#1}}
\newtcolorbox{{cmfast}}{{enhanced,breakable,colback=CMSoft,colframe=CMTeal,boxrule=0.8pt,arc=1.2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,before skip=4pt,after skip=4pt}}
\begin{{document}}
\RaggedRight
\thispagestyle{{empty}}
\begin{{tcolorbox}}[colback=CMInk,colframe=CMInk,arc=0mm,boxrule=0pt,left=7mm,right=7mm,top=7mm,bottom=7mm]
{{\sffamily\bfseries\fontsize{{23}}{{25}}\selectfont\color{{white}} {esc(title)}}}\\[3pt]
{{\sffamily\large\color{{white!78}} {esc(subtitle)}}}
\end{{tcolorbox}}
\vspace{{-1mm}}
'''


def _end() -> str:
    return "\\end{document}\n"


def _mm(value: float | int) -> str:
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else f"{numeric:g}"


def _art_block(
    image_ref: Any,
    source_root: Path,
    width: str = "0.96\\linewidth",
    *,
    max_height_mm: float = 30,
    placeholder_height_mm: float = 28,
) -> str:
    rel = str(image_ref or "").strip()
    if not rel:
        return ""
    placeholder_height = _mm(placeholder_height_mm)
    max_height = _mm(max_height_mm)
    path = source_root / rel
    if not path.is_file():
        return rf'''\begin{{tcolorbox}}[colback=CMPale,colframe=CMLine,boxrule=0.4pt,arc=1mm,width={width},height={placeholder_height}mm,valign=center,halign=center]\sffamily\scriptsize\color{{CMInk!65}}ART NOT STAGED\\{esc(rel)}\end{{tcolorbox}}'''
    return rf'''\includegraphics[width={width},height={max_height}mm,keepaspectratio]{{{esc(path.as_posix())}}}'''


def _stat(value: Any, label: str) -> str:
    if value in (None, "", [], {}):
        return ""
    return rf'''\textbf{{{esc(label)}}} {esc(value)}'''


def _fast_play(fp: Any) -> str:
    if not isinstance(fp, dict) or not fp:
        return ""
    prompts = fp.get("prompts") if isinstance(fp.get("prompts"), list) else []
    body: list[str] = []
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        label = str(prompt.get("label") or "").strip()
        text = md(prompt.get("text") or "")
        refs = _list_text(prompt.get("featureRefs"))
        ref_text = rf''' {{\scriptsize\color{{CMViolet}}[Features: {esc(refs)}]}}''' if refs else ""
        if label and text:
            body.append(rf'''\textbf{{{esc(label)}:}} {text}{ref_text}\par''')
        elif text:
            body.append(rf'''{text}{ref_text}\par''')
    goal = str(fp.get("goal") or "").strip()
    if goal:
        body.append(rf'''\textbf{{Goal:}} {md(goal)}''')
    if not body:
        return ""
    return "\n".join(
        [
            r'''\begin{cmfast}{\sffamily\bfseries\color{CMTealDark} FAST PLAY}\par''',
            *body,
            r'''\end{cmfast}''',
        ]
    )


def _actions(actions: Any) -> str:
    if not isinstance(actions, list) or not actions:
        return ""
    out: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        name = esc(action.get("name") or "")
        atype = str(action.get("actionType") or action.get("type") or "").strip()
        rules = md(action.get("rulesMarkdown") or action.get("description") or "")
        tag = (
            feature_type_label_tex(atype, color_role="CMTealDark") + r"\hspace{0.4em}"
            if atype
            else ""
        )
        name_text = rf'''\textbf{{{name}.}}''' if name else ""
        line = " ".join(part for part in (tag + name_text, rules) if part).strip()
        if line:
            out.append(line)
    return "\\par\n".join(out)


def _features(features: Any) -> str:
    if not isinstance(features, list) or not features:
        return ""
    out: list[str] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        name = esc(feature.get("name") or "")
        rules = md(feature.get("rulesMarkdown") or "")
        actions = _actions(feature.get("actions"))
        body = rules
        if actions and actions not in body:
            body = (body + "\\par\n" + actions).strip()
        if not name and not body:
            continue
        title = rf'''{{\sffamily\bfseries\color{{CMTealDark}} {name}}}\par ''' if name else ""
        out.append(rf'''\begin{{cmfeature}}{title}{body}\end{{cmfeature}}''')
    return "\n".join(out)


def _identity_meta(view: dict[str, Any]) -> str:
    identity = view.get("identity") if isinstance(view.get("identity"), dict) else {}
    parts: list[str] = []
    classification = str(identity.get("classification") or "").strip()
    if classification:
        parts.append(esc(classification).upper())
    if identity.get("tier") not in (None, ""):
        parts.append(f"TIER {esc(identity.get('tier'))}")
    return r" \textbullet\ ".join(parts)


def _statistics_tex(view: dict[str, Any], *, environment: bool = False) -> str:
    identity = view.get("identity") if isinstance(view.get("identity"), dict) else {}
    stats = identity.get("statistics") if isinstance(identity.get("statistics"), dict) else {}
    values: list[str] = []
    if stats.get("difficulty") not in (None, ""):
        values.append(_stat(stats.get("difficulty"), "Difficulty"))
    if not environment:
        thresholds = stats.get("damageThresholds") if isinstance(stats.get("damageThresholds"), dict) else {}
        threshold_text = " / ".join(
            str(thresholds.get(key))
            for key in ("major", "severe")
            if thresholds.get(key) not in (None, "")
        )
        if threshold_text:
            values.append(_stat(threshold_text, "Thresholds"))
        values.extend(
            value
            for value in (
                _stat(stats.get("hitPoints"), "HP"),
                _stat(stats.get("stress"), "Stress"),
            )
            if value
        )
    return r" \hspace{0.65em} ".join(values)


def _art_ref(view: dict[str, Any]) -> str:
    identity = view.get("identity") if isinstance(view.get("identity"), dict) else {}
    art = identity.get("art") if isinstance(identity.get("art"), dict) else {}
    return str(art.get("image") or "").strip()


def _adversary_identity(view: dict[str, Any], source_root: Path) -> str:
    name = esc(view.get("name") or "")
    meta = _identity_meta(view)
    stats = _statistics_tex(view)
    art = _art_block(_art_ref(view), source_root, "0.96\\linewidth", max_height_mm=18, placeholder_height_mm=18)

    lines: list[str] = []
    if meta:
        lines.append(rf'''{{\sffamily\bfseries\scriptsize\color{{CMTealDark}} {meta}}}\\[1.5pt]''')
    lines.append(rf'''{{\sffamily\bfseries\fontsize{{15.5}}{{16.5}}\selectfont\color{{CMInk}} {name}}}''')
    if stats:
        lines.append(rf'''\\[2pt]{{\sffamily\scriptsize {stats}}}''')
    text_block = "\n".join(lines)

    if art:
        header = "\n".join(
            [
                rf'''\noindent\begin{{minipage}}[t]{{0.20\linewidth}}\vspace{{0pt}}\raggedright {art}\end{{minipage}}\hfill''',
                rf'''\begin{{minipage}}[t]{{0.76\linewidth}}\vspace{{0pt}}{text_block}\end{{minipage}}''',
            ]
        )
    else:
        header = rf'''\noindent\begin{{minipage}}[t]{{\linewidth}}\vspace{{0pt}}{text_block}\end{{minipage}}'''
    return "\n".join(
        [
            r'''\Needspace{10\baselineskip}''',
            r'''\vspace{3mm}''',
            header,
            r'''\vspace{1.5mm}{\color{CMTeal}\hrule height 0.7pt}\vspace{1.5mm}''',
        ]
    )


def _environment_identity(view: dict[str, Any], source_root: Path) -> str:
    name = esc(view.get("name") or "")
    meta = _identity_meta(view)
    stats = _statistics_tex(view, environment=True)
    art = _art_block(_art_ref(view), source_root, "0.96\\linewidth")

    lines: list[str] = []
    if meta:
        lines.append(rf'''{{\sffamily\bfseries\small\color{{CMTealDark}} {meta}}}\\[2.5pt]''')
    lines.append(rf'''{{\sffamily\bfseries\fontsize{{21}}{{22}}\selectfont\color{{CMInk}} {name}}}''')
    if stats:
        lines.append(rf'''\\[3pt]{{\sffamily\small {stats}}}''')
    text_block = "\n".join(lines)

    if art:
        header = "\n".join(
            [
                rf'''\noindent\begin{{minipage}}[t]{{0.17\textwidth}}\vspace{{0pt}}\raggedright {art}\end{{minipage}}\hfill''',
                rf'''\begin{{minipage}}[t]{{0.80\textwidth}}\vspace{{0pt}}{text_block}\end{{minipage}}''',
            ]
        )
    else:
        header = rf'''\noindent\begin{{minipage}}[t]{{\textwidth}}\vspace{{0pt}}{text_block}\end{{minipage}}'''
    return "\n".join(
        [
            r'''\clearpage''',
            header,
            r'''\vspace{2mm}{\color{CMTeal}\hrule height 0.7pt}\vspace{2mm}''',
        ]
    )


def _attack_tex(attack: Any) -> str:
    if not isinstance(attack, dict):
        return ""
    parts: list[str] = []
    name = str(attack.get("name") or "").strip()
    if name:
        parts.append(name)
    if attack.get("bonus") not in (None, ""):
        bonus = str(attack.get("bonus"))
        parts.append(bonus if bonus.startswith(("+", "-")) else f"+{bonus}")
    if attack.get("range") not in (None, ""):
        parts.append(str(attack.get("range")))
    damage = str(attack.get("damageFormula") or "").strip()
    damage_types = "/".join(str(value) for value in attack.get("damageTypes") or [] if str(value))
    if damage:
        parts.append((damage + (f" {damage_types}" if damage_types else "")).strip())
    return esc(" / ".join(parts)) if parts else ""


def _experiences_tex(experiences: Any) -> str:
    if not isinstance(experiences, list):
        return ""
    parts: list[str] = []
    for experience in experiences:
        if not isinstance(experience, dict):
            continue
        name = str(experience.get("name") or "").strip()
        if not name:
            continue
        if experience.get("value") not in (None, ""):
            parts.append(f"{name} +{experience.get('value')}")
        else:
            parts.append(name)
    return esc(", ".join(parts))


def _adversary_section(view: dict[str, Any], section: str, source_root: Path) -> str:
    sections = view.get("sections") if isinstance(view.get("sections"), dict) else {}
    if section == "identity":
        return _adversary_identity(view, source_root)
    if section == "description":
        return md(sections.get("description"))
    if section == "attack":
        text = _attack_tex(sections.get("attack"))
        return rf'''\par\textbf{{Attack:}} {text}''' if text else ""
    if section == "motivesAndTactics":
        text = md(sections.get("motivesAndTactics"))
        return rf'''\par\textbf{{Motives \& Tactics:}} {text}''' if text else ""
    if section == "experiences":
        text = _experiences_tex(sections.get("experiences"))
        return rf'''\par\textbf{{Experiences:}} {text}''' if text else ""
    if section == "fastPlay":
        return _fast_play(sections.get("fastPlay"))
    if section == "actions":
        body = _actions(sections.get("actions"))
        return (
            rf'''\Needspace{{5\baselineskip}}{{\sffamily\bfseries\normalsize\color{{CMInk}} ACTIONS}}\par
{body}'''
            if body
            else ""
        )
    if section == "features":
        body = _features(sections.get("features"))
        return (
            rf'''\Needspace{{5\baselineskip}}{{\sffamily\bfseries\normalsize\color{{CMInk}} FEATURES}}\par
{body}'''
            if body
            else ""
        )
    return ""


def _environment_section(view: dict[str, Any], section: str, source_root: Path) -> str:
    sections = view.get("sections") if isinstance(view.get("sections"), dict) else {}
    if section == "identity":
        return _environment_identity(view, source_root)
    if section == "description":
        return md(sections.get("description"))
    if section == "impulses":
        text = md(sections.get("impulses"))
        return rf'''\par\textbf{{Impulses:}} {text}''' if text else ""
    if section == "potentialAdversaries":
        text = _list_text(sections.get("potentialAdversaries"))
        return rf'''\par\textbf{{Potential Adversaries:}} {esc(text)}''' if text else ""
    if section == "fastPlay":
        return _fast_play(sections.get("fastPlay"))
    if section == "actions":
        body = _actions(sections.get("actions"))
        return (
            rf'''\Needspace{{6\baselineskip}}{{\sffamily\bfseries\large\color{{CMInk}} ACTIONS}}\par
{body}'''
            if body
            else ""
        )
    if section == "features":
        body = _features(sections.get("features"))
        return (
            rf'''\Needspace{{7\baselineskip}}{{\sffamily\bfseries\large\color{{CMInk}} FEATURES}}\par
{body}'''
            if body
            else ""
        )
    return ""


def _adversary_entry(view: dict[str, Any], source_root: Path, section_order: list[str]) -> str:
    return "\n".join(
        part for part in (_adversary_section(view, section, source_root) for section in section_order) if part
    )


def _environment_entry(view: dict[str, Any], source_root: Path, section_order: list[str]) -> str:
    return "\n".join(
        part for part in (_environment_section(view, section, source_root) for section in section_order) if part
    )


def _feature_entry(entity: dict[str, Any]) -> str:
    p = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    name = esc(entity.get("name") or "Feature")
    rules = md(p.get("rulesMarkdown") or p.get("descriptionMarkdown") or p.get("description") or "")
    actions = _actions(p.get("actions"))
    if actions and actions not in rules:
        rules = (rules + "\\par\n" + actions).strip()
    if not rules:
        rules = r'''{\itshape\color{CMInk!60}No canonical rules text supplied.}'''
    return rf'''\begin{{cmfeature}}
{{\sffamily\bfseries\color{{CMTealDark}} {name}}}\\[-1pt]
{rules}
\end{{cmfeature}}
'''


def render_package(sidecar: dict[str, Any], config: dict[str, Any], source_root: Path) -> tuple[str, dict[str, Any]]:
    family = str(config.get("family") or "")
    if family not in FAMILIES:
        raise ValueError(f"unsupported encounter family: {family}")
    entities = _family_entities(sidecar, family, config)
    title = str(config.get("title") or family.replace("-", " ").title())
    subtitle = str(config.get("subtitle") or "Phase C proof package")
    columns = int(config.get("columns") or (2 if family == "adversaries-features" else 1))
    tex = [_preamble(title, subtitle, columns=columns)]
    proof_note = config.get("proofNote")
    if proof_note:
        tex.append(rf'''\begin{{tcolorbox}}[colback=CMPale,colframe=CMViolet,boxrule=0.55pt]\sffamily\small\textbf{{PHASE C PROOF.}} {esc(proof_note)}\end{{tcolorbox}}''')

    rendered_ids: list[str] = []
    presentation_schema: str | None = None
    if family in {"adversaries", "environments"}:
        views = normalize_encounter_presentations(entities, family)
        section_order = _section_order(config, family)
        presentation_schema = PRESENTATION_SCHEMA
        rendered_ids = [str(view.get("semanticId") or "") for view in views]
        if family == "adversaries":
            if columns > 1:
                tex.append(rf'''\setlength{{\columnsep}}{{0.22in}}\begin{{multicols}}{{{columns}}}\raggedcolumns''')
            tex.extend(_adversary_entry(view, source_root, section_order) for view in views)
            if columns > 1:
                tex.append(r'''\end{multicols}''')
        else:
            tex.extend(_environment_entry(view, source_root, section_order) for view in views)
    else:
        rendered_ids = [str(entity.get("semanticId") or "") for entity in entities]
        tex.append(r'''\begin{multicols}{2}\raggedcolumns''')
        tex.extend(_feature_entry(entity) for entity in entities)
        tex.append(r'''\end{multicols}''')

    tex.append(_end())
    report = {
        "schema": "cybermancy-phase-c-encounter-package-report-v1",
        "family": family,
        "title": title,
        "entryCount": len(entities),
        "selectedSemanticIds": [e.get("semanticId") for e in entities],
        "selectedNames": [e.get("name") for e in entities],
        "renderedSemanticIds": rendered_ids,
        "presentationSchema": presentation_schema,
        "status": "PASS" if entities else "FAIL",
    }
    return "\n".join(tex), report
