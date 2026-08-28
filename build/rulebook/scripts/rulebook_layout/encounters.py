from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

SUPPORTED_SCHEMA = "cybermancy-step4-encounter-semantics-v1.0"
FAMILIES = ("adversaries", "environments", "adversaries-features")

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
    else:
        entries.sort(key=lambda e: (int((e.get("publicationData") or {}).get("tier") or 0), str(e.get("name") or "").casefold()))
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


def _preamble(title: str, subtitle: str, *, columns: int = 1) -> str:
    multicol = "\\usepackage{multicol}\n" if columns > 1 else ""
    return rf'''\documentclass[10pt,letterpaper]{{article}}
\usepackage[letterpaper,margin=0.55in,top=0.50in,bottom=0.55in]{{geometry}}
\usepackage[T1]{{fontenc}}
\usepackage{{lmodern}}
\renewcommand{{\familydefault}}{{\sfdefault}}
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
\thispagestyle{{empty}}
\begin{{tcolorbox}}[colback=CMInk,colframe=CMInk,arc=0mm,boxrule=0pt,left=7mm,right=7mm,top=7mm,bottom=7mm]
{{\sffamily\bfseries\fontsize{{23}}{{25}}\selectfont\color{{white}} {esc(title)}}}\\[3pt]
{{\sffamily\large\color{{white!78}} {esc(subtitle)}}}
\end{{tcolorbox}}
\vspace{{-1mm}}
'''


def _end() -> str:
    return "\\end{document}\n"


def _art_block(pdata: dict[str, Any], source_root: Path, width: str = "0.96\\linewidth") -> str:
    art = pdata.get("publicationArt") if isinstance(pdata.get("publicationArt"), dict) else {}
    rel = str(art.get("image") or pdata.get("image") or "").strip()
    if not rel:
        return rf'''\begin{{tcolorbox}}[colback=CMPale,colframe=CMLine,boxrule=0.4pt,arc=1mm,width={width},height=32mm,valign=center,halign=center]\sffamily\scriptsize\color{{CMInk!65}}NO PUBLICATION ART\end{{tcolorbox}}'''
    path = source_root / rel
    if not path.is_file():
        return rf'''\begin{{tcolorbox}}[colback=CMPale,colframe=CMLine,boxrule=0.4pt,arc=1mm,width={width},height=32mm,valign=center,halign=center]\sffamily\scriptsize\color{{CMInk!65}}ART NOT STAGED\\{esc(rel)}\end{{tcolorbox}}'''
    return rf'''\includegraphics[width={width},height=39mm,keepaspectratio]{{{esc(path.as_posix())}}}'''


def _stat(value: Any, label: str) -> str:
    if value in (None, "", [], {}):
        return ""
    return rf'''\textbf{{{esc(label)}}} {esc(value)}'''


def _fast_play(fp: Any) -> str:
    if not isinstance(fp, dict) or not fp:
        return ""
    prompts = fp.get("prompts") if isinstance(fp.get("prompts"), list) else []
    parts = [r'''\begin{cmfast}{\sffamily\bfseries\color{CMTealDark} FAST PLAY}\par''']
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        label = esc(prompt.get("label") or "Prompt")
        text = md(prompt.get("text") or "")
        refs = _list_text(prompt.get("featureRefs"))
        ref_text = rf''' {{\scriptsize\color{{CMViolet}}[Features: {esc(refs)}]}}''' if refs else ""
        parts.append(rf'''\textbf{{{label}:}} {text}{ref_text}\par''')
    goal = str(fp.get("goal") or "").strip()
    if goal:
        parts.append(rf'''\textbf{{Goal:}} {md(goal)}''')
    parts.append(r'''\end{cmfast}''')
    return "\n".join(parts)


def _actions(actions: Any) -> str:
    if not isinstance(actions, list) or not actions:
        return ""
    out: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        name = esc(action.get("name") or "Action")
        atype = esc(action.get("actionType") or action.get("type") or "")
        rules = md(action.get("rulesMarkdown") or action.get("description") or "")
        tag = rf'''{{\scriptsize\bfseries\color{{CMViolet}} {atype.upper()}}}\hspace{{0.4em}}''' if atype else ""
        out.append(rf'''{tag}\textbf{{{name}.}} {rules}''')
    return "\\par\n".join(out)


def _features(features: Any) -> str:
    if not isinstance(features, list) or not features:
        return r'''{\sffamily\scriptsize\color{CMInk!65}No embedded Features.}'''
    out: list[str] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        name = esc(feature.get("name") or "Feature")
        rules = md(feature.get("rulesMarkdown") or "")
        actions = _actions(feature.get("actions"))
        body = rules
        if actions and actions not in body:
            body = (body + "\\par\n" + actions).strip()
        out.append(rf'''\begin{{cmfeature}}{{\sffamily\bfseries\color{{CMTealDark}} {name}}}\par {body}\end{{cmfeature}}''')
    return "\n".join(out)


def _adversary_entry(entity: dict[str, Any], source_root: Path) -> str:
    p = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    name = esc(entity.get("name") or "Adversary")
    tier = p.get("tier")
    classification = p.get("classification") or "Unclassified"
    difficulty = p.get("difficulty")
    thresholds = p.get("damageThresholds") if isinstance(p.get("damageThresholds"), dict) else {}
    threshold_text = " / ".join(str(thresholds.get(k)) for k in ("major", "severe") if thresholds.get(k) not in (None, ""))
    header_stats = [
        _stat(difficulty, "Difficulty"), _stat(threshold_text, "Thresholds"), _stat(p.get("hitPoints"), "HP"), _stat(p.get("stress"), "Stress")
    ]
    header_stats = [x for x in header_stats if x]
    attack = p.get("attack") if isinstance(p.get("attack"), dict) else {}
    attack_parts = []
    if attack:
        attack_parts.append(str(attack.get("name") or "Attack"))
        if attack.get("bonus") not in (None, ""):
            attack_parts.append(f"+{attack.get('bonus')}")
        if attack.get("range"):
            attack_parts.append(str(attack.get("range")))
        dmg = str(attack.get("damageFormula") or "")
        dtypes = "/".join(str(v) for v in attack.get("damageTypes") or [])
        if dmg:
            attack_parts.append((dmg + (f" {dtypes}" if dtypes else "")).strip())
    exps = p.get("experiences") if isinstance(p.get("experiences"), list) else []
    exp_text = ", ".join(f"{e.get('name')} +{e.get('value')}" if e.get("value") not in (None, "") else str(e.get("name")) for e in exps if isinstance(e, dict) and e.get("name"))
    desc = md(p.get("descriptionMarkdown") or p.get("description") or "")
    motives = md(p.get("motivesAndTactics") or "")
    features = _features(p.get("features"))
    fp = _fast_play(p.get("fastPlay"))
    art = _art_block(p, source_root)
    return rf'''
\Needspace{{14\baselineskip}}
\vspace{{4mm}}
\noindent\begin{{minipage}}[t]{{0.68\textwidth}}
{{\sffamily\bfseries\small\color{{CMTealDark}} {esc(classification).upper()} \textbullet\ TIER {esc(tier if tier is not None else "-")}}}\\[-1pt]
{{\sffamily\bfseries\fontsize{{21}}{{22}}\selectfont\color{{CMInk}} {name}}}\\[3pt]
{{\sffamily\small {' \\quad '.join(header_stats)}}}
\end{{minipage}}\hfill\begin{{minipage}}[t]{{0.29\textwidth}}\raggedleft {art}\end{{minipage}}
\vspace{{2mm}}{{\color{{CMTeal}}\hrule height 0.7pt}}\vspace{{2mm}}
{desc if desc else r'{\itshape\color{CMInk!60}No canonical description supplied.}'}
{rf'\par\textbf{{Attack:}} {esc(" / ".join(attack_parts))}' if attack_parts else ''}
{rf'\par\textbf{{Motives \& Tactics:}} {motives}' if motives else ''}
{rf'\par\textbf{{Experiences:}} {esc(exp_text)}' if exp_text else ''}
{fp}
\Needspace{{7\baselineskip}}{{\sffamily\bfseries\large\color{{CMInk}} FEATURES}}\par
{features}
'''


def _environment_entry(entity: dict[str, Any], source_root: Path) -> str:
    p = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    name = esc(entity.get("name") or "Environment")
    tier = p.get("tier")
    classification = p.get("classification") or "Unclassified"
    desc = md(p.get("descriptionMarkdown") or p.get("description") or "")
    impulses = md(p.get("impulses") or "")
    potential = _list_text(p.get("potentialAdversaries"))
    fp = _fast_play(p.get("fastPlay"))
    features = _features(p.get("features"))
    actions = _actions(p.get("actions"))
    art = _art_block(p, source_root, "0.96\\linewidth")
    return rf'''
\clearpage
\noindent\begin{{minipage}}[t]{{0.62\textwidth}}
{{\sffamily\bfseries\small\color{{CMTealDark}} {esc(classification).upper()} \textbullet\ TIER {esc(tier if tier is not None else "-")}}}\\[-1pt]
{{\sffamily\bfseries\fontsize{{21}}{{22}}\selectfont\color{{CMInk}} {name}}}\\[2pt]
{{\sffamily\small\textbf{{Difficulty}} {esc(p.get("difficulty") if p.get("difficulty") is not None else "-")}}}
\end{{minipage}}\hfill\begin{{minipage}}[t]{{0.35\textwidth}}\raggedleft {art}\end{{minipage}}
\vspace{{2mm}}{{\color{{CMTeal}}\hrule height 0.7pt}}\vspace{{2mm}}
{desc if desc else r'{\itshape\color{CMInk!60}No canonical description supplied.}'}
{rf'\par\textbf{{Impulses:}} {impulses}' if impulses else r'\par{\itshape\color{CMInk!60}No canonical impulses supplied.}'}
{rf'\par\textbf{{Potential Adversaries:}} {esc(potential)}' if potential else ''}
{fp}
{rf'\Needspace{{6\baselineskip}}{{\sffamily\bfseries\large\color{{CMInk}} ACTIONS}}\par {actions}' if actions else ''}
\Needspace{{7\baselineskip}}{{\sffamily\bfseries\large\color{{CMInk}} FEATURES}}\par
{features}
'''


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
    if family == "adversaries":
        tex.append(r"\clearpage")
        tex.extend(_adversary_entry(entity, source_root) for entity in entities)
    elif family == "environments":
        tex.extend(_environment_entry(entity, source_root) for entity in entities)
    else:
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
        "status": "PASS" if entities else "FAIL",
    }
    return "\n".join(tex), report
