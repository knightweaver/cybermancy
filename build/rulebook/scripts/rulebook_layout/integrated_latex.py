from __future__ import annotations

import copy
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from rulebook_layout.integration_ast import canonical_ast_sha256, iter_ast_nodes, node_identifier, normalize_identifier
from rulebook_layout.post_transform_validation import validate_post_transform
from rulebook_layout.publication_shell import COLUMN_CHAPTERS, PACKAGE_HEADER_CHAPTERS, PROFILE_PART_IDS


STAGE_NAME = "integrated-latex"
STAGE_ORDER = 150
SHELL_PREFIX = "% CM-INTEGRATED-SHELL "
PACKAGE_FAMILY_BY_CHAPTER = {
    29: "features",
    30: "adversaries",
    31: "environments",
    32: "adversaries-features",
}
PACKAGE_FAMILIES = set(PACKAGE_FAMILY_BY_CHAPTER.values())
EQUIPMENT_FAMILIES = {
    "weapons",
    "ammo",
    "armors",
    "cybernetics",
    "drones-devices",
    "consumables",
    "mods",
    "loot",
}
DIRECT_GRAPHICS_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
CONVERT_GRAPHICS_EXTENSIONS = {".webp", ".gif", ".bmp", ".tif", ".tiff"}


def _check(
    report: dict[str, Any],
    code: str,
    ok: bool,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {
        "code": code,
        "status": "PASS" if ok else "ERROR",
        "message": message,
    }
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if not ok:
        report["status"] = "FAIL"
        report["errors"].append(item)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_stem(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return clean or "asset"


def _raw_latex_text(node: Any) -> str | None:
    if not isinstance(node, dict) or node.get("t") != "RawBlock":
        return None
    content = node.get("c")
    if not (
        isinstance(content, list)
        and len(content) == 2
        and content[0] == "latex"
    ):
        return None
    return str(content[1] or "")


def _raw_latex(text: str) -> dict[str, Any]:
    return {"t": "RawBlock", "c": ["latex", text]}


def _family_name(node: Any) -> str | None:
    if not isinstance(node, dict) or node.get("t") != "Div":
        return None
    ident = normalize_identifier(node_identifier(node))
    if not ident.startswith("family:"):
        return None
    return ident[len("family:") :]


def _family_body(node: dict[str, Any]) -> str | None:
    content = node.get("c")
    if not (
        isinstance(content, list)
        and len(content) == 2
        and isinstance(content[1], list)
        and len(content[1]) == 1
    ):
        return None
    return _raw_latex_text(content[1][0])


def _hex(style: dict[str, Any], key: str, default: str) -> str:
    value = str(style.get(key) or default).strip().lstrip("#")
    return value.upper()


def _class_wrapper(config: dict[str, Any]) -> tuple[str, str]:
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    begin = rf"""% CM-STAGE150 FAMILY classes BEGIN
\begingroup
\definecolor{{CMAccent}}{{HTML}}{{{_hex(style, 'accentColor', '0B6573')}}}
\definecolor{{CMBright}}{{HTML}}{{{_hex(style, 'accentBrightColor', '18A7B5')}}}
\definecolor{{CMInk}}{{HTML}}{{{_hex(style, 'inkColor', '183238')}}}
\definecolor{{CMMuted}}{{HTML}}{{{_hex(style, 'mutedColor', '58747A')}}}
\definecolor{{CMSoft}}{{HTML}}{{{_hex(style, 'softColor', 'EAF4F5')}}}
\definecolor{{CMSubclass}}{{HTML}}{{{_hex(style, 'subclassBandColor', 'DDEEF0')}}}
\let\sffamily\CMClassSans
\CMClassSans
"""
    return begin, "\\endgroup\n% CM-STAGE150 FAMILY classes END\n"


def _domain_wrapper(config: dict[str, Any]) -> tuple[str, str]:
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    begin = rf"""% CM-STAGE150 FAMILY domains BEGIN
\begingroup
\definecolor{{CMAccent}}{{HTML}}{{{_hex(style, 'accentColor', '0B6573')}}}
\definecolor{{CMBright}}{{HTML}}{{{_hex(style, 'accentBrightColor', '18A7B5')}}}
\definecolor{{CMInk}}{{HTML}}{{{_hex(style, 'inkColor', '183238')}}}
\definecolor{{CMMuted}}{{HTML}}{{{_hex(style, 'mutedColor', '58747A')}}}
\definecolor{{CMSoft}}{{HTML}}{{{_hex(style, 'softColor', 'EAF4F5')}}}
\definecolor{{CMCardSoft}}{{HTML}}{{{_hex(style, 'cardSoftColor', 'F3F8F8')}}}
\definecolor{{CMRule}}{{HTML}}{{{_hex(style, 'ruleColor', 'B9D9DC')}}}
\let\sffamily\CMDomainSans
\CMDomainSans
"""
    return begin, "\\endgroup\n% CM-STAGE150 FAMILY domains END\n"


def _equipment_wrapper(family: str, config: dict[str, Any]) -> tuple[str, str]:
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    begin = rf"""% CM-STAGE150 FAMILY {family} BEGIN
\begingroup
\definecolor{{CMTableHeader}}{{HTML}}{{{_hex(style, 'headerColor', '0B6573')}}}
\definecolor{{CMGroupBand}}{{HTML}}{{{_hex(style, 'groupBandColor', 'DDEEF0')}}}
\definecolor{{CMAltRow}}{{HTML}}{{{_hex(style, 'alternateRowColor', 'EEF7F8')}}}
\definecolor{{CMTextDark}}{{HTML}}{{{_hex(style, 'textDarkColor', '183238')}}}
\definecolor{{CMRule}}{{HTML}}{{{_hex(style, 'ruleColor', '18A7B5')}}}
\let\sffamily\CMEquipmentSans
\CMEquipmentSans
"""
    return begin, f"\\endgroup\n% CM-STAGE150 FAMILY {family} END\n"


def _ice_wrapper(config: dict[str, Any]) -> tuple[str, str]:
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    begin = rf"""% CM-STAGE150 FAMILY features BEGIN
\begingroup
\definecolor{{CMAccent}}{{HTML}}{{{_hex(style, 'accentColor', '0B6573')}}}
\definecolor{{CMBright}}{{HTML}}{{{_hex(style, 'accentBrightColor', '18A7B5')}}}
\definecolor{{CMInk}}{{HTML}}{{{_hex(style, 'inkColor', '111B28')}}}
\definecolor{{CMBodyText}}{{HTML}}{{{_hex(style, 'bodyTextColor', '202833')}}}
\definecolor{{CMMuted}}{{HTML}}{{{_hex(style, 'mutedColor', '58747A')}}}
\definecolor{{CMSoft}}{{HTML}}{{{_hex(style, 'softColor', 'EAF4F5')}}}
\definecolor{{CMRule}}{{HTML}}{{{_hex(style, 'ruleColor', 'B9D9DC')}}}
\definecolor{{CMPaper}}{{HTML}}{{{_hex(style, 'paperColor', 'F9F9F7')}}}
\definecolor{{CMDark}}{{HTML}}{{{_hex(style, 'darkBandColor', '111B28')}}}
\definecolor{{CMGM}}{{HTML}}{{{_hex(style, 'gmAccentColor', '6C55A6')}}}
"""
    return begin, "\\endgroup\n% CM-STAGE150 FAMILY features END\n"


def _encounter_wrapper(family: str) -> tuple[str, str]:
    begin = rf"""% CM-STAGE150 FAMILY {family} BEGIN
\begingroup
\definecolor{{CMInk}}{{HTML}}{{252431}}
\definecolor{{CMTeal}}{{HTML}}{{167E83}}
\definecolor{{CMTealDark}}{{HTML}}{{0D5E63}}
\definecolor{{CMViolet}}{{HTML}}{{5B3B82}}
\definecolor{{CMPale}}{{HTML}}{{F3F0EA}}
\definecolor{{CMLine}}{{HTML}}{{B7C6C4}}
\definecolor{{CMSoft}}{{HTML}}{{E8F1F0}}
\let\sffamily\CMEncounterSans
\CMEncounterSans
"""
    return begin, f"\\endgroup\n% CM-STAGE150 FAMILY {family} END\n"


def _family_wrapper(
    family: str,
    configs: dict[str, Any],
) -> tuple[str, str]:
    if family == "classes":
        return _class_wrapper(configs["class"])
    if family == "subclasses":
        return "", ""
    if family == "domains":
        return _domain_wrapper(configs["domain"])
    if family in EQUIPMENT_FAMILIES:
        return _equipment_wrapper(family, configs["equipment"][family])
    if family == "features":
        return _ice_wrapper(configs["ice"])
    if family in {"adversaries", "environments", "adversaries-features"}:
        return _encounter_wrapper(family)
    raise ValueError(f"Stage 150 has no visual wrapper for family:{family}")


def flatten_family_containers(
    ast: dict[str, Any], configs: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Flatten validated family Divs while preserving their accepted raw bodies."""
    candidate = copy.deepcopy(ast)
    blocks = candidate.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("Stage 150 input AST has no top-level blocks list")

    output: list[Any] = []
    flattened: list[str] = []
    package_pairs: list[str] = []
    index = 0
    while index < len(blocks):
        node = blocks[index]
        raw = _raw_latex_text(node)
        next_node = blocks[index + 1] if index + 1 < len(blocks) else None
        next_family = _family_name(next_node)

        if raw is not None and next_family in PACKAGE_FAMILIES and not raw.startswith(SHELL_PREFIX):
            body = _family_body(next_node)
            if body is None:
                raise ValueError(f"family:{next_family} is not exactly one raw LaTeX body")
            begin, end = _family_wrapper(str(next_family), configs)
            if begin:
                output.append(_raw_latex(begin))
            output.append(node)
            output.append(_raw_latex(body))
            if end:
                output.append(_raw_latex(end))
            flattened.append(str(next_family))
            package_pairs.append(str(next_family))
            index += 2
            continue

        family = _family_name(node)
        if family is not None:
            body = _family_body(node)
            if body is None:
                raise ValueError(f"family:{family} is not exactly one raw LaTeX body")
            begin, end = _family_wrapper(family, configs)
            if begin:
                output.append(_raw_latex(begin))
            output.append(_raw_latex(body))
            if end:
                output.append(_raw_latex(end))
            flattened.append(family)
            index += 1
            continue

        output.append(node)
        index += 1

    candidate["blocks"] = output
    remaining = [
        normalize_identifier(node_identifier(node))
        for node in iter_ast_nodes(candidate)
        if node.get("t") == "Div"
        and normalize_identifier(node_identifier(node)).startswith("family:")
    ]
    return candidate, {
        "flattenedFamilies": flattened,
        "packageHeaderPairs": package_pairs,
        "remainingFamilyDivs": remaining,
    }


def _convert_raster(source: Path, destination: Path) -> None:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required to convert WebP/GIF/BMP/TIFF assets for the integrated LuaLaTeX build. "
            "Install it with: python -m pip install Pillow"
        ) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        has_alpha = "A" in image.getbands() or (
            image.mode == "P" and "transparency" in image.info
        )
        prepared = image.convert("RGBA" if has_alpha else "RGB")
        prepared.save(destination, format="PNG", compress_level=9, optimize=False)


def _candidate_asset_roots(
    repo_root: Path,
    rulebook_dir: Path,
    integration_work_root: Path,
) -> list[Path]:
    roots = [
        integration_work_root / "stage130" / "prose-player",
        integration_work_root / "stage130" / "rules",
        integration_work_root / "stage130" / "character-origins",
        integration_work_root / "stage130" / "prose-gm",
        integration_work_root / "stage130" / "encounters",
        integration_work_root / "character-options",
        integration_work_root / "ice-render-assets",
        integration_work_root,
        rulebook_dir,
        rulebook_dir / "source",
        rulebook_dir / "source" / "assets",
        repo_root,
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _resolve_asset(raw_path: str, roots: list[Path], rulebook_dir: Path) -> Path:
    text = raw_path.strip().strip('"').replace("\\", "/")
    if not text:
        raise FileNotFoundError("blank graphics path")

    raw = Path(text)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    elif re.match(r"^[A-Za-z]:/", text):
        candidates.append(Path(text))
    else:
        for root in roots:
            candidates.append(root / Path(text))
        if text.startswith("assets/"):
            candidates.append(rulebook_dir / "source" / text)
            candidates.append(rulebook_dir / "source" / "assets" / text[len("assets/") :])

    existing: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = os.path.normcase(str(resolved))
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            existing.append(resolved)

    if not existing:
        raise FileNotFoundError(f"Could not resolve integrated graphics asset: {raw_path}")
    if len(existing) == 1:
        return existing[0]

    hashes = {_sha256_file(path) for path in existing}
    if len(hashes) != 1:
        raise RuntimeError(
            "Integrated graphics path is ambiguous across build contexts: "
            + raw_path
            + " -> "
            + ", ".join(str(path) for path in existing)
        )
    return sorted(existing, key=lambda path: os.path.normcase(str(path)))[0]


def _stage_asset(source: Path, assets_dir: Path) -> tuple[Path, bool]:
    digest = _sha256_file(source)
    ext = source.suffix.lower()
    stem = _safe_stem(source.stem)
    converted = ext in CONVERT_GRAPHICS_EXTENSIONS
    if converted:
        destination = assets_dir / f"{stem}-{digest[:16]}.png"
        if not destination.exists():
            _convert_raster(source, destination)
    elif ext in DIRECT_GRAPHICS_EXTENSIONS:
        destination = assets_dir / f"{stem}-{digest[:16]}{ext}"
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    else:
        raise RuntimeError(f"Unsupported integrated graphics extension: {source.suffix} ({source})")
    return destination, converted


def stage_generation_assets(
    ast: dict[str, Any],
    repo_root: Path,
    rulebook_dir: Path,
    integration_work_root: Path,
    assets_dir: Path,
) -> dict[str, Any]:
    """Rewrite every reachable graphics reference to the Stage 150 compile root."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    roots = _candidate_asset_roots(repo_root, rulebook_dir, integration_work_root)
    staged_by_source: dict[str, str] = {}
    rows: list[dict[str, Any]] = []

    def stage(raw_path: str) -> str:
        source = _resolve_asset(raw_path, roots, rulebook_dir)
        key = os.path.normcase(str(source.resolve()))
        if key in staged_by_source:
            return staged_by_source[key]
        destination, converted = _stage_asset(source, assets_dir)
        relative = destination.relative_to(assets_dir.parent).as_posix()
        staged_by_source[key] = relative
        rows.append(
            {
                "source": str(source),
                "sourceSha256": _sha256_file(source),
                "staged": relative,
                "stagedSha256": _sha256_file(destination),
                "converted": converted,
            }
        )
        return relative

    detok_re = re.compile(r"\\detokenize\{([^{}]+)\}")
    graphics_re = re.compile(r"(\\includegraphics(?:\[[^\]]*\])?\{)([^{}]+)(\})")

    def rewrite_latex(text: str) -> str:
        def detok_replace(match: re.Match[str]) -> str:
            return r"\detokenize{" + stage(match.group(1)) + "}"

        value = detok_re.sub(detok_replace, text)

        def graphics_replace(match: re.Match[str]) -> str:
            raw = match.group(2).strip()
            if raw.startswith(r"\detokenize"):
                return match.group(0)
            return match.group(1) + stage(raw) + match.group(3)

        return graphics_re.sub(graphics_replace, value)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("t") == "RawBlock":
                content = value.get("c")
                if (
                    isinstance(content, list)
                    and len(content) == 2
                    and content[0] == "latex"
                ):
                    content[1] = rewrite_latex(str(content[1] or ""))
            elif value.get("t") == "Image":
                content = value.get("c")
                if isinstance(content, list) and len(content) >= 3:
                    target = content[2]
                    if isinstance(target, list) and target:
                        target[0] = stage(str(target[0] or ""))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(ast)
    rows.sort(key=lambda row: row["staged"])
    return {
        "status": "PASS",
        "assetCount": len(rows),
        "convertedCount": sum(1 for row in rows if row["converted"]),
        "assets": rows,
        "searchRoots": [str(root) for root in roots],
    }


def _origin_extension(
    origin_config: dict[str, Any], prose_config: dict[str, Any]
) -> str:
    identity = origin_config["entryGrammar"]["identityRow"]
    feature = origin_config["entryGrammar"]["featureGroup"]
    typo = prose_config["typography"]
    image_fraction = float(identity["imageColumnFraction"])
    gap_fraction = float(identity["gapColumnFraction"])
    return rf"""
% ---- Character Origins v1.0 accepted delta ----
\newcommand{{\CMOriginEntryRule}}{{\par\vspace{{5pt}}\noindent{{\color{{CMCyan!38}}\rule{{\columnwidth}}{{0.45pt}}}}\vspace{{5pt}}\par}}
\newcommand{{\CMOriginIdentityImage}}[1]{{\includegraphics[width=\linewidth,height={float(identity['imageMaxHeightInches']):.3f}in,keepaspectratio]{{#1}}}}
\newcommand{{\CMOriginIdentityMissing}}[1]{{\fcolorbox{{CMCyan!45}}{{white}}{{\parbox[c][1.02in][c]{{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}}{{\centering\sffamily\fontsize{{7.3}}{{8.6}}\selectfont\color{{CMTeal}}\textbf{{STAGED ART}}\\\color{{CMInk}}#1}}}}}}
\newcommand{{\CMOriginIdentity}}[3]{{%
  \par\Needspace{{9\baselineskip}}\vspace{{2pt}}%
  \begin{{wrapfigure}}{{l}}[\dimexpr\columnsep-{gap_fraction:.3f}\columnwidth\relax]{{{image_fraction:.3f}\columnwidth}}%
    \vspace{{0pt}}#1%
  \end{{wrapfigure}}%
  {{\sffamily\fontsize{{{float(identity['titleSizePt']):.2f}}}{{{float(identity['titleLeadingPt']):.2f}}}\selectfont\bfseries\color{{CMInk}}#2\par}}%
  \vspace{{3pt}}%
  {{\fontsize{{{float(typo['bodySizePt']):.2f}}}{{{float(typo['bodyLeadingPt']):.2f}}}\selectfont\RaggedRight #3\par}}%
  \vspace{{4pt}}%
}}
\newcommand{{\CMOriginFeatureLabel}}[1]{{\par\Needspace{{4\baselineskip}}\vspace{{4pt}}{{\sffamily\fontsize{{8.4}}{{10.0}}\selectfont\bfseries\color{{CMTeal}}\MakeUppercase{{#1}}\par}}\vspace{{1.5pt}}}}
\newcommand{{\CMOriginFeature}}[2]{{\par\Needspace{{3\baselineskip}}{{\sffamily\fontsize{{{float(feature['featureNameSizePt']):.2f}}}{{{float(feature['featureNameLeadingPt']):.2f}}}\selectfont\bfseries\color{{CMInk}}#1\par}}\vspace{{0.6pt}}#2\par\vspace{{3.2pt}}}}
"""


def _rules_extension() -> str:
    return r"""
% ---- Part II Rules Layout v1.0 accepted delta ----
\newenvironment{CMRulesQuote}{%
  \par\vspace{0.5pt}%
  \begingroup
  \leftskip=0.12in%
  \rightskip=0.02in%
  \parindent=0pt%
  \parskip=2pt%
  \color{CMBody}\fontsize{9.6}{13.0}\selectfont
}{%
  \par\endgroup\vspace{0.5pt}\par
}
\newenvironment{CMRulesTable}{\begin{CMProseTable}}{\end{CMProseTable}}
\let\CMProseStandardImage\CMStandardImage
\newcommand{\CMRulesStandardImage}[1]{%
  \par\vspace{2pt}%
  \begin{center}%
    \includegraphics[width=\columnwidth,height=0.20\textheight,keepaspectratio]{#1}%
  \end{center}%
  \vspace{3pt}%
}
"""


def _shared_extensions(profile: str) -> str:
    footer = "PLAYER GUIDE" if profile == "player-guide" else "COMPLETE RULEBOOK"
    return rf"""
% ---- Stage 150 whole-book dependencies ----
\newfontfamily\CMClassSans{{Arial}}
\newfontfamily\CMEquipmentSans{{Arial}}
\newfontfamily\CMDomainSans{{Arial}}
\newfontfamily\CMEncounterSans{{Arial}}
\newfontfamily\CMDisplay{{Arial}}
\setlength{{\intextsep}}{{0pt}}
\newtcolorbox{{cmfeature}}[1][]{{enhanced,colback=white,colframe=CMLine,boxrule=0.45pt,arc=1.2mm,left=2mm,right=2mm,top=1.4mm,bottom=1.4mm,before skip=3pt,after skip=3pt,#1}}
\newtcolorbox{{cmfast}}{{enhanced,breakable,colback=CMSoft,colframe=CMTeal,boxrule=0.8pt,arc=1.2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,before skip=4pt,after skip=4pt}}

% One-document geometry lanes. Stage 130 determines structural boundaries;
% Stage 150 changes geometry only when the accepted publication lane changes.
\newcommand{{\CMGeometryMode}}{{prose}}
\newcommand{{\CMUseProseGeometry}}{{%
  \ifdefstring{{\CMGeometryMode}}{{prose}}{{}}{{%
    \newgeometry{{top=0.72in,bottom=0.70in,left=0.78in,right=0.78in}}%
    \gdef\CMGeometryMode{{prose}}%
  }}%
}}
\newcommand{{\CMUseStructuredGeometry}}{{%
  \ifdefstring{{\CMGeometryMode}}{{structured}}{{}}{{%
    \newgeometry{{top=0.72in,bottom=0.70in,left=0.55in,right=0.55in}}%
    \gdef\CMGeometryMode{{structured}}%
  }}%
}}
\newcommand{{\CMUseEquipmentGeometry}}{{%
  \ifdefstring{{\CMGeometryMode}}{{equipment}}{{}}{{%
    \newgeometry{{top=0.72in,bottom=0.70in,left=0.46in,right=0.46in}}%
    \gdef\CMGeometryMode{{equipment}}%
  }}%
}}
\newcommand{{\CMUsePackageGeometry}}{{%
  \ifdefstring{{\CMGeometryMode}}{{package}}{{}}{{%
    \newgeometry{{top=0.72in,bottom=0.70in,left=0.55in,right=0.55in}}%
    \gdef\CMGeometryMode{{package}}%
  }}%
}}

\newcommand{{\CMUseProseLane}}{{%
  \let\CMStandardImage\CMProseStandardImage
  \setlist[enumerate,1]{{label=\arabic*.,leftmargin=1.15em,itemsep=1.6pt,topsep=3pt}}%
}}
\newcommand{{\CMUseRulesLane}}{{%
  \let\CMStandardImage\CMRulesStandardImage
  \setlist[enumerate,1]{{label=\textcolor{{CMTeal}}{{\sffamily\bfseries\arabic*.}},leftmargin=1.45em,itemsep=2.8pt,topsep=3.5pt}}%
}}

\newcommand{{\CMIntegratedPart}}[4]{{%
  \ifstrequal{{#4}}{{part-iv-equipment}}{{\CMUseEquipmentGeometry}}{{%
    \ifstrequal{{#4}}{{part-vi-gm-toolkit}}{{\CMUsePackageGeometry}}{{\CMUseProseGeometry}}%
  }}%
  \ifstrequal{{#3}}{{gm}}{{\def\CMThisPartDeck{{GM MATERIAL}}\def\CMThisPartAccent{{CMViolet}}}}{{\def\CMThisPartDeck{{PLAYER MATERIAL}}\def\CMThisPartAccent{{CMCyan}}}}%
  \CMPartPage{{#1}}{{#2}}{{\CMThisPartDeck}}{{\CMThisPartAccent}}%
}}

\newcommand{{\CMIntegratedChapter}}[4]{{%
  \ifnum#1=12\relax
    \CMUseStructuredGeometry
  \else\ifnum#1=14\relax
    \CMUseStructuredGeometry
  \else\ifnum#1>14\relax
    \ifnum#1<23\relax\CMUseEquipmentGeometry\else\CMUseProseGeometry\fi
  \else
    \CMUseProseGeometry
  \fi\fi\fi
  \ifnum#1>3\relax
    \ifnum#1<10\relax\CMUseRulesLane\else\CMUseProseLane\fi
  \else
    \CMUseProseLane
  \fi
  \CMChapterBanner{{#1}}{{#2}}{{#3}}%
}}

\newcommand{{\CMIntegratedGMDivider}}[1]{{%
  \CMUseProseGeometry
  \clearpage
  \begingroup
  \thispagestyle{{empty}}
  \pagecolor{{CMInk}}\color{{white}}
  \vspace*{{0.95in}}
  {{\sffamily\fontsize{{10}}{{12}}\selectfont\bfseries\color{{CMViolet}} GM MATERIAL\par}}
  \vspace{{0.18in}}
  {{\sffamily\fontsize{{24}}{{28}}\selectfont\bfseries #1\par}}
  \vspace{{0.14in}}
  {{\color{{CMViolet}}\rule{{1.45in}}{{2pt}}\par}}
  \vfill
  {{\sffamily\fontsize{{10.5}}{{14}}\selectfont\color{{white!82}} The following material is intended for the Game Master.\par}}
  \vspace*{{0.55in}}
  \clearpage
  \pagecolor{{CMPaper}}\color{{CMBody}}
  \endgroup
}}

% Stage 150 profile furniture.
\fancyfoot[L]{{\sffamily\fontsize{{7.0}}{{8.5}}\selectfont\color{{CMTeal}}STEP 6 // {footer} // INTEGRATED}}
"""


def build_integrated_preamble(
    prose_preamble: str,
    profile: str,
    prose_config: dict[str, Any],
    origin_config: dict[str, Any],
) -> str:
    marker = r"\begin{document}"
    if marker not in prose_preamble:
        raise ValueError("Accepted Long-Form Prose preamble has no document-start marker")
    head = prose_preamble.split(marker, 1)[0]
    head = head.replace(r"\usepackage{xcolor}", r"\usepackage[table]{xcolor}")
    head = head.replace(r"\color{CMRunningAccent}", r"\color{\CMRunningAccent}")

    package_marker = r"\usepackage[hidelinks]{hyperref}"
    extras = "\n".join(
        [
            r"\usepackage{tabularx}",
            r"\usepackage{paracol}",
            r"\usepackage{wrapfig}",
            r"\usepackage{tcolorbox}",
            r"\tcbuselibrary{breakable,skins}",
            r"\usepackage{titlesec}",
        ]
    )
    if package_marker in head:
        head = head.replace(package_marker, extras + "\n" + package_marker, 1)
    else:
        head += extras + "\n"

    return (
        head.rstrip()
        + "\n"
        + _rules_extension().strip()
        + "\n"
        + _origin_extension(origin_config, prose_config).strip()
        + "\n"
        + _shared_extensions(profile).strip()
        + "\n"
    )


def _strip_comments(tex: str) -> str:
    lines: list[str] = []
    for line in tex.splitlines():
        out: list[str] = []
        index = 0
        while index < len(line):
            if line[index] == "%":
                slashes = 0
                cursor = index - 1
                while cursor >= 0 and line[cursor] == "\\":
                    slashes += 1
                    cursor -= 1
                if slashes % 2 == 0:
                    break
            out.append(line[index])
            index += 1
        lines.append("".join(out))
    return "\n".join(lines)


def custom_dependency_audit(preamble: str, body: str) -> dict[str, Any]:
    clean_body = _strip_comments(body)
    clean_preamble = _strip_comments(preamble)
    required_commands = set(re.findall(r"\\(CM[A-Za-z]+)\b", clean_body))
    required_envs = set(
        re.findall(r"\\begin\{((?:CM|cm)[A-Za-z]+)\}", clean_body)
    )

    defined_commands: set[str] = set()
    for pattern in (
        r"\\(?:newcommand|renewcommand|providecommand)\{\\(CM[A-Za-z]+)\}",
        r"\\newfontfamily\\(CM[A-Za-z]+)",
        r"\\let\\(CM[A-Za-z]+)",
    ):
        defined_commands.update(re.findall(pattern, clean_preamble))
    defined_envs = set(
        re.findall(r"\\newenvironment\{((?:CM|cm)[A-Za-z]+)\}", clean_preamble)
    )
    defined_envs.update(
        re.findall(r"\\newtcolorbox\{((?:CM|cm)[A-Za-z]+)\}", clean_preamble)
    )

    missing_commands = sorted(required_commands - defined_commands)
    missing_envs = sorted(required_envs - defined_envs)
    return {
        "status": "PASS" if not missing_commands and not missing_envs else "FAIL",
        "requiredCommands": sorted(required_commands),
        "definedCommands": sorted(defined_commands),
        "missingCommands": missing_commands,
        "requiredEnvironments": sorted(required_envs),
        "definedEnvironments": sorted(defined_envs),
        "missingEnvironments": missing_envs,
    }


def render_generation_ast(
    ast: dict[str, Any], pandoc: str, generation_ast_path: Path, body_path: Path
) -> dict[str, Any]:
    generation_ast_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    generation_ast_path.write_text(
        json.dumps(ast, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    command = [
        pandoc,
        "--from=json",
        "--to=latex",
        "--wrap=none",
        str(generation_ast_path),
    ]
    proc = subprocess.run(
        command,
        cwd=str(generation_ast_path.parent),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    body_path.write_text(proc.stdout or "", encoding="utf-8")
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "command": command,
        "returnCode": proc.returncode,
        "stdoutBytes": len((proc.stdout or "").encode("utf-8")),
        "stderr": (proc.stderr or "")[-12000:],
    }


def _profile_shell_counts(body: str, contract: dict[str, Any], profile: str) -> dict[str, Any]:
    chapters = [int(value) for value in contract["profiles"][profile]["chapters"]]
    expected_chapters = len(
        [number for number in chapters if number not in PACKAGE_HEADER_CHAPTERS]
    )
    expected_parts = len(PROFILE_PART_IDS[profile])
    expected_divider = int(contract["profiles"][profile].get("gmDividerCount") or 0)
    actual = {
        "parts": body.count(r"\CMIntegratedPart{"),
        "chapters": body.count(r"\CMIntegratedChapter{"),
        "gmDivider": body.count(r"\CMIntegratedGMDivider{"),
    }
    expected = {
        "parts": expected_parts,
        "chapters": expected_chapters,
        "gmDivider": expected_divider,
    }
    return {
        "status": "PASS" if actual == expected else "FAIL",
        "expected": expected,
        "actual": actual,
    }


def generate_integrated_latex(
    ast: dict[str, Any],
    contract: dict[str, Any],
    profile: str,
    configs: dict[str, Any],
    prose_preamble: str,
    pandoc: str,
    repo_root: Path,
    rulebook_dir: Path,
    integration_work_root: Path,
    output_dir: Path,
    work_dir: Path,
) -> tuple[str | None, dict[str, Any]]:
    """Generate one deterministic integrated TeX document without compiling it."""
    input_sha = canonical_ast_sha256(ast)
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-stage150-integrated-latex-v1",
        "status": "PASS",
        "stage": STAGE_NAME,
        "order": STAGE_ORDER,
        "profile": profile,
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputAstSha256": input_sha,
    }

    stage = next(
        (
            row
            for row in contract.get("transformationOrder", [])
            if isinstance(row, dict) and row.get("stage") == STAGE_NAME
        ),
        None,
    )
    stage_ok = isinstance(stage, dict) and int(stage.get("order") or -1) == STAGE_ORDER
    _check(
        report,
        "STAGE150_CONTRACT",
        stage_ok,
        "Integration contract contains Stage 150 at canonical order 150.",
        stage,
    )
    if not stage_ok:
        return None, report

    revalidation = validate_post_transform(ast, contract, profile)
    report["stage140Revalidation"] = revalidation
    revalidation_ok = revalidation.get("status") == "PASS"
    _check(
        report,
        "STAGE140_REVALIDATION",
        revalidation_ok,
        "Accepted Stage 140 semantic validation still passes immediately before integrated LaTeX generation.",
        revalidation,
    )
    if not revalidation_ok:
        return None, report

    try:
        generation_ast, flatten_report = flatten_family_containers(ast, configs)
    except Exception as exc:
        _check(
            report,
            "STAGE150_GENERATION_AST",
            False,
            f"Could not flatten validated family containers: {type(exc).__name__}: {exc}",
        )
        return None, report
    flatten_ok = not flatten_report["remainingFamilyDivs"]
    _check(
        report,
        "STAGE150_GENERATION_AST",
        flatten_ok,
        "Created a noncanonical generation AST with validated family containers flattened into accepted raw LaTeX bodies.",
        flatten_report,
    )
    if not flatten_ok:
        return None, report

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"

    try:
        asset_report = stage_generation_assets(
            generation_ast,
            repo_root,
            rulebook_dir,
            integration_work_root,
            assets_dir,
        )
    except Exception as exc:
        _check(
            report,
            "STAGE150_ASSET_STAGING",
            False,
            f"Integrated asset staging failed: {type(exc).__name__}: {exc}",
        )
        return None, report
    report["assetStaging"] = asset_report
    _check(
        report,
        "STAGE150_ASSET_STAGING",
        asset_report.get("status") == "PASS",
        "All graphics references were rewritten to one self-contained Stage 150 compile root.",
        asset_report,
    )

    generation_ast_path = work_dir / f"{profile}-stage150-generation.ast.json"
    body_path = work_dir / f"{profile}-stage150-body.tex"
    pandoc_report = render_generation_ast(
        generation_ast, pandoc, generation_ast_path, body_path
    )
    report["pandoc"] = pandoc_report
    pandoc_ok = pandoc_report.get("status") == "PASS"
    _check(
        report,
        "STAGE150_PANDOC",
        pandoc_ok,
        "Pandoc rendered the Stage 150 generation AST to one body-only LaTeX stream.",
        pandoc_report,
    )
    if not pandoc_ok:
        return None, report

    body = body_path.read_text(encoding="utf-8")
    shell_leakage = [
        token
        for token in (r"\documentclass", r"\begin{document}", r"\end{document}")
        if token in body
    ]
    _check(
        report,
        "STAGE150_BODY_RENDER",
        not shell_leakage,
        "Rendered body contains no nested standalone document shell.",
        shell_leakage,
    )
    if shell_leakage:
        return None, report

    preamble = build_integrated_preamble(
        prose_preamble,
        profile,
        configs["prose"],
        configs["origins"],
    )
    document = (
        preamble
        + "\\begin{document}\n"
        + "\\frenchspacing\n"
        + body.rstrip()
        + "\n\\end{document}\n"
    )
    document_shell = {
        "documentclass": document.count(r"\documentclass"),
        "beginDocument": document.count(r"\begin{document}"),
        "endDocument": document.count(r"\end{document}"),
    }
    shell_ok = document_shell == {
        "documentclass": 1,
        "beginDocument": 1,
        "endDocument": 1,
    }
    _check(
        report,
        "STAGE150_DOCUMENT_SHELL",
        shell_ok,
        "Integrated output has exactly one document class and one document boundary.",
        document_shell,
    )

    dependency_report = custom_dependency_audit(preamble, body)
    report["customDependencies"] = dependency_report
    _check(
        report,
        "STAGE150_CUSTOM_DEPENDENCIES",
        dependency_report.get("status") == "PASS",
        "Every Cybermancy custom command/environment referenced by the integrated body is defined by the one-document preamble.",
        dependency_report,
    )

    shell_counts = _profile_shell_counts(body, contract, profile)
    _check(
        report,
        "STAGE150_PROFILE_SHELL_COUNTS",
        shell_counts.get("status") == "PASS",
        "Integrated body retains the exact profile-specific Part, generic Chapter, and GM-divider shell calls.",
        shell_counts,
    )

    source_unchanged = canonical_ast_sha256(ast) == input_sha
    _check(
        report,
        "STAGE150_AST_IMMUTABILITY",
        source_unchanged,
        "Stage 150 left the accepted Stage 140 AST byte-stable and generated only from a deep copy.",
        {"before": input_sha, "after": canonical_ast_sha256(ast)},
    )
    if report["status"] != "PASS":
        return None, report

    filename = (
        "Cybermancy_Player_Guide_Step6_Integrated.tex"
        if profile == "player-guide"
        else "Cybermancy_Complete_Rulebook_Step6_Integrated.tex"
    )
    tex_path = output_dir / filename
    tex_path.write_text(document, encoding="utf-8")
    tex_sha = _sha256_file(tex_path)
    report["outputTex"] = str(tex_path)
    report["outputTexSha256"] = tex_sha
    report["generationAstSha256"] = canonical_ast_sha256(generation_ast)
    report["bodySha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    _check(
        report,
        "STAGE150_TEX_OUTPUT",
        tex_path.is_file() and tex_path.stat().st_size > 0,
        "Wrote deterministic body-complete integrated LaTeX for Stage 160 LuaLaTeX compilation.",
        {"path": str(tex_path), "sha256": tex_sha},
    )
    return document if report["status"] == "PASS" else None, report
