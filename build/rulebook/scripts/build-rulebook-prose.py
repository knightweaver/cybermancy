#!/usr/bin/env python3
"""Cybermancy Step 6 long-form prose builder v1.0.5 (Pandoc/LuaLaTeX).

Consumes Step 4 normalized `complete-rulebook.md` and staged Step 4 assets, selects
Parts I and V, converts chapter Markdown through Pandoc + a prose-specific Lua
filter, and compiles the accepted two-column publication grammar with LuaLaTeX.

No WeasyPrint/GTK/Pango runtime is used.

Typical repository-root usage:
    python build/rulebook/scripts/build-rulebook-prose.py

Explicit validation only:
    python build/rulebook/scripts/build-rulebook-prose.py validate

Explicit build:
    python build/rulebook/scripts/build-rulebook-prose.py build
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
DEFAULT_REPO_ROOT = RULEBOOK_DIR.parent.parent
LAYOUT_DIR = RULEBOOK_DIR / "layout" / "prose"
DEFAULT_CONFIG = LAYOUT_DIR / "prose-layout-v1.json"
DEFAULT_FILTER = LAYOUT_DIR / "pandoc" / "prose.lua"
DEFAULT_SOURCE = RULEBOOK_DIR / "source" / "assembled" / "complete-rulebook.md"
DEFAULT_ASSET_ROOT = RULEBOOK_DIR / "source" / "assets"
DEFAULT_OUTPUT = LAYOUT_DIR / "output" / "Cybermancy_Parts_I_V_Prose_Regression_v1.pdf"
DEFAULT_REPORT = LAYOUT_DIR / "reports" / "prose-regression-v1.json"
DEFAULT_WORK = LAYOUT_DIR / "work" / "pandoc-lualatex-v1"

MARKDOWN_FROM = (
    "markdown-yaml_metadata_block-implicit_figures-simple_tables-multiline_tables+fenced_divs+bracketed_spans+pipe_tables+grid_tables+definition_lists"
    "+raw_attribute+raw_html+markdown_in_html_blocks"
)

PART_RE = re.compile(
    r'^#\s+(.+?)\s+\{#(section:[^\s]+)\s+\.rb-part\s+data-audience="(player|gm)"\}\s*$',
    re.M,
)
CHAPTER_RE = re.compile(
    r'^##\s+Chapter\s+(\d+):\s+(.+?)\s+\{#(section:[^\s]+)\s+\.rb-chapter\s+data-audience="(player|gm)"\}\s*$',
    re.M,
)
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)(\{[^\n}]*\})?')
KNOWN_HTML_WRAPPER_RE = re.compile(r'^\s*</?div(?:\s+[^>]*)?>\s*$', re.I)

TARGET_PARTS: dict[str, tuple[str, str, str]] = {
    "section:part-i-world": (
        "I",
        "The World of Cybermancy",
        "The signal changed everything. This is the world that grew from the scar.",
    ),
    "section:part-v-gm-world": (
        "V",
        "GM World Guide",
        "Hidden history, faction truth, and the forces behind the visible world.",
    ),
}
TARGET_CHAPTERS = {1, 2, 3, 23, 24, 25, 26, 27, 28}
DIRECT_GRAPHICS_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
PILLOW_CONVERT_EXTENSIONS = {".webp", ".gif", ".bmp", ".tif", ".tiff"}
WARNING_PATTERNS = (
    re.compile(r"Overfull \\hbox.*"),
    re.compile(r"Underfull \\hbox.*"),
    re.compile(r"Missing character:.*"),
    re.compile(r"LaTeX Warning:.*"),
    re.compile(r"Package .* Warning:.*"),
)


@dataclass
class Paths:
    repo_root: Path
    config: Path
    lua_filter: Path
    source: Path
    asset_root: Path
    output: Path
    report: Path
    work: Path


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


_TOOL_CACHE: dict[str, str | None] = {}


def _windows_app_path(name: str) -> str | None:
    """Resolve an executable through Windows App Paths when available."""
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None

    exe_name = name if name.lower().endswith(".exe") else f"{name}.exe"
    subkey = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access in (
            getattr(winreg, "KEY_WOW64_64KEY", 0),
            getattr(winreg, "KEY_WOW64_32KEY", 0),
            0,
        ):
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | access) as key:
                    value, _ = winreg.QueryValueEx(key, None)
            except OSError:
                continue
            candidate = Path(str(value).strip('"')).expanduser()
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def _windows_tool_candidates(name: str) -> list[Path]:
    if os.name != "nt":
        return []
    exe = name if name.lower().endswith(".exe") else f"{name}.exe"
    env = os.environ
    roots: list[Path] = []
    for key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        value = env.get(key)
        if value:
            roots.append(Path(value))

    candidates: list[Path] = []
    local = env.get("LOCALAPPDATA")
    if local:
        local_root = Path(local)
        candidates.extend(
            [
                local_root / "Pandoc" / exe,
                local_root / "Programs" / "Pandoc" / exe,
                local_root / "Microsoft" / "WinGet" / "Links" / exe,
            ]
        )
    for root in roots:
        candidates.extend(
            [
                root / "Pandoc" / exe,
                root / "MiKTeX" / "miktex" / "bin" / "x64" / exe,
                root / "MiKTeX" / "miktex" / "bin" / exe,
            ]
        )
    return candidates


def resolve_tool(name: str) -> str | None:
    """Resolve a production tool without requiring a freshly updated Windows PATH."""
    key = name.lower()
    if key in _TOOL_CACHE:
        return _TOOL_CACHE[key]

    env_override = os.environ.get(f"CYBERMANCY_{key.upper()}_PATH")
    if env_override:
        candidate = Path(env_override).expanduser()
        if candidate.is_file():
            _TOOL_CACHE[key] = str(candidate.resolve())
            return _TOOL_CACHE[key]

    found = shutil.which(name)
    if found:
        _TOOL_CACHE[key] = found
        return found

    app_path = _windows_app_path(name)
    if app_path:
        _TOOL_CACHE[key] = app_path
        return app_path

    for candidate in _windows_tool_candidates(name):
        if candidate.is_file():
            _TOOL_CACHE[key] = str(candidate.resolve())
            return _TOOL_CACHE[key]

    _TOOL_CACHE[key] = None
    return None


def executable_version(name: str) -> str | None:
    exe = resolve_tool(name)
    if not exe:
        return None
    version_args = {"pdfinfo": ["-v"], "pdftotext": ["-v"]}.get(name, ["--version"])
    p = run([exe, *version_args])
    lines = ((p.stdout or "") + "\n" + (p.stderr or "")).splitlines()
    return lines[0] if lines else exe


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add_check(report: dict[str, Any], code: str, status: str, message: str, details: Any = None) -> None:
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["errors"].append(item)
        report["status"] = "FAIL"
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def parse_source(text: str) -> list[dict[str, Any]]:
    parts = []
    part_matches = list(PART_RE.finditer(text))
    for i, pm in enumerate(part_matches):
        part_end = part_matches[i + 1].start() if i + 1 < len(part_matches) else len(text)
        part_text = text[pm.end():part_end]
        chapters = []
        chapter_matches = list(CHAPTER_RE.finditer(part_text))
        for j, cm in enumerate(chapter_matches):
            end = chapter_matches[j + 1].start() if j + 1 < len(chapter_matches) else len(part_text)
            chapters.append(
                {
                    "number": int(cm.group(1)),
                    "title": cm.group(2).strip(),
                    "semanticId": cm.group(3),
                    "audience": cm.group(4),
                    "markdown": part_text[cm.end():end].strip() + "\n",
                }
            )
        parts.append(
            {
                "title": pm.group(1).strip(),
                "semanticId": pm.group(2),
                "audience": pm.group(3),
                "chapters": chapters,
            }
        )
    return parts


def select_target_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [p for p in parts if p["semanticId"] in TARGET_PARTS]
    selected.sort(key=lambda p: (0 if p["semanticId"] == "section:part-i-world" else 1))
    for p in selected:
        p["chapters"] = [c for c in p["chapters"] if c["number"] in TARGET_CHAPTERS]
    return selected


def sanitize_known_html_wrappers(md: str) -> tuple[str, int]:
    out = []
    removed = 0
    for line in md.splitlines():
        if KNOWN_HTML_WRAPPER_RE.match(line):
            removed += 1
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n", removed


IMAGE_LINE_RE = re.compile(
    r'^\s*!\[[^\]\n]*\]\([^\n]+\)(?:\{[^\n}]*\})?\s*$'
)
HEADING_LINE_RE = re.compile(r'^\s*#{1,6}\s+[^\n]+$')


def find_adjacent_image_headings(md: str) -> list[dict[str, Any]]:
    """Detect a physical image-line -> heading-line adjacency without consuming blank lines."""
    lines = md.splitlines()
    defects: list[dict[str, Any]] = []
    for index in range(len(lines) - 1):
        image = lines[index]
        heading = lines[index + 1]
        if IMAGE_LINE_RE.fullmatch(image) and HEADING_LINE_RE.fullmatch(heading):
            defects.append(
                {
                    "line": index + 1,
                    "image": image.strip(),
                    "heading": heading.strip(),
                }
            )
    return defects


def image_role(source: str, chapter: int) -> str:
    normalized = source.replace("\\", "/").lower()
    name = Path(normalized).name
    if "/icons/corps/" in normalized:
        return "mark"
    if name == "council-vs-cabal.png":
        return "wide"
    if name == "triune-sigil.png":
        return "symbolic"
    if chapter == 23:
        return "wide"
    return "standard"


def resolve_asset(source: str, asset_root: Path) -> Path | None:
    source_path = Path(source)
    candidates = []
    normalized = source.replace("\\", "/")
    if normalized.startswith("../assets/"):
        candidates.append(asset_root / normalized[len("../assets/"):])
    elif normalized.startswith("assets/"):
        candidates.append(asset_root / normalized[len("assets/"):])
    else:
        candidates.append(asset_root / normalized.lstrip("/"))
        candidates.append(asset_root / source_path.name)
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


def _safe_asset_stem(stem: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
    return clean or "asset"


def stage_asset_for_lualatex(src: Path, cache_dir: Path) -> Path:
    """Stage every asset beneath work/assets with a whitespace-safe relative name."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower()
    digest = sha256_file(src)[:16]
    stem = _safe_asset_stem(src.stem)

    if ext in PILLOW_CONVERT_EXTENSIONS:
        out = cache_dir / f"{stem}-{digest}.png"
        if not out.exists():
            try:
                from PIL import Image, ImageOps
            except ImportError as exc:
                raise RuntimeError(
                    f"Pillow is required to convert {src.suffix} assets for LuaLaTeX. "
                    "Install it with: python -m pip install Pillow"
                ) from exc
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)
                has_alpha = "A" in im.getbands() or (im.mode == "P" and "transparency" in im.info)
                prepared = im.convert("RGBA" if has_alpha else "RGB")
                prepared.save(out, format="PNG", compress_level=9, optimize=False)
        return out

    out_ext = ext or ".asset"
    out = cache_dir / f"{stem}-{digest}{out_ext}"
    if not out.exists():
        shutil.copy2(src, out)
    return out


def stage_markdown_assets(md: str, chapter: int, asset_root: Path, cache_dir: Path,
                          missing: list[dict[str, Any]]) -> tuple[str, int]:
    resolved_count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal resolved_count
        alt, src, attr = m.group(1), m.group(2), m.group(3) or ""
        resolved = resolve_asset(src, asset_root)
        role = image_role(src, chapter)
        attrs = []
        if attr:
            attrs.extend(x for x in attr.strip("{}").split() if x)
        attrs.append(f'data-role="{role}"')
        attrs.append(f'data-original="{src}"')

        if resolved is None:
            attrs.append('data-missing="true"')
            missing.append({"chapter": chapter, "source": src})
            out_src = src
        else:
            staged = stage_asset_for_lualatex(resolved, cache_dir).resolve()
            out_src = staged.relative_to(cache_dir.parent.resolve()).as_posix()
            resolved_count += 1
        return f"![{alt}]({out_src}){{{' '.join(attrs)}}}"

    return IMAGE_RE.sub(repl, md), resolved_count


def run_pandoc_body(md_path: Path, body_path: Path, lua_filter: Path, work: Path) -> tuple[str, str]:
    pandoc = resolve_tool("pandoc")
    if not pandoc:
        raise RuntimeError("Pandoc is not installed or could not be resolved.")
    cmd = [
        pandoc,
        "--from", MARKDOWN_FROM,
        "--to", "latex",
        "--lua-filter", str(lua_filter),
        "--wrap=none",
        str(md_path),
    ]
    p = run(cmd, cwd=work)
    logs = work / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"pandoc-{md_path.stem}.txt").write_text(
        "COMMAND:\n" + " ".join(cmd) + "\n\nCWD:\n" + str(work) +
        "\n\nSTDOUT:\n" + (p.stdout or "") + "\n\nSTDERR:\n" + (p.stderr or ""),
        encoding="utf-8",
    )
    if p.returncode != 0:
        raise RuntimeError(
            "Pandoc failed for " + md_path.name + "\n" +
            "\n".join(((p.stdout or "") + "\n" + (p.stderr or "")).splitlines()[-60:])
        )
    body_path.write_text(p.stdout, encoding="utf-8")
    return p.stdout, p.stderr


def latex_escape(s: str) -> str:
    repl = {
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
    return "".join(repl.get(c, c) for c in s)


def _body_alignment_tex(config: dict[str, Any] | None = None) -> str:
    source = config if isinstance(config, dict) else load_json(DEFAULT_CONFIG)
    typography = source.get("typography") if isinstance(source.get("typography"), dict) else {}
    alignment = str(typography.get("bodyAlignment") or "justified").strip().casefold()
    if alignment == "ragged-right":
        return r"\RaggedRight"
    if alignment == "justified":
        return r"\justifying"
    raise ValueError(f"Unsupported prose bodyAlignment: {alignment}")


def document_preamble(config: dict[str, Any] | None = None) -> str:
    preamble = r'''\documentclass[10pt,letterpaper]{article}
\usepackage[letterpaper,top=0.72in,bottom=0.70in,inner=0.78in,outer=0.78in]{geometry}
\usepackage{fontspec}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{multicol}
\usepackage{fancyhdr}
\usepackage{microtype}
\usepackage{needspace}
\usepackage{longtable}
% Pandoc >= 3.8 can emit \def\LTcaptype{none} for uncaptioned longtables.
% Recent longtable then expects a corresponding LaTeX counter.  Define it
% defensively so the same generated document works across MiKTeX/TeX Live
% and across older/newer Pandoc versions.
\makeatletter
\@ifundefined{c@none}{\newcounter{none}}{}
\makeatother
\usepackage{booktabs}
\usepackage{array}
\usepackage{ragged2e}
\usepackage{enumitem}
\usepackage{calc}
\usepackage{etoolbox}
\usepackage[hidelinks]{hyperref}

\setsansfont{{Arial}}
\setmainfont{{Arial}}

\definecolor{CMPaper}{HTML}{F9F9F7}
\definecolor{CMInk}{HTML}{111B28}
\definecolor{CMBody}{HTML}{202833}
\definecolor{CMCyan}{HTML}{3CCBC7}
\definecolor{CMTeal}{HTML}{1B7078}
\definecolor{CMIndigo}{HTML}{5968D9}
\definecolor{CMViolet}{HTML}{6C55A6}
\definecolor{CMPaleCyan}{HTML}{EAF6F5}
\definecolor{CMPaleViolet}{HTML}{F0EDF7}

\pagecolor{CMPaper}
\color{CMBody}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4.4pt plus 1.0pt minus 0.5pt}
\setlength{\columnsep}{0.24in}
\setlength{\columnseprule}{0pt}
\setlength{\emergencystretch}{1.4em}
\raggedcolumns
\linespread{1.04}
\setlist{nosep,leftmargin=1.15em,itemsep=1.6pt,topsep=3pt}
\widowpenalty=10000
\clubpenalty=10000
\displaywidowpenalty=10000
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

\newcommand{\CMPartAccent}{CMCyan}
\newcommand{\CMChapterAccent}{CMCyan}
\newcommand{\CMRunningAccent}{CMCyan}
\newcommand{\CMRunningMarker}{PLAYER WORLD}
\newcommand{\CMRunningChapter}{}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyhead[L]{\sffamily\fontsize{7.5}{9}\selectfont\color{CMInk}\textbf{CYBERMANCY} \color{CMRunningAccent}// \color{CMInk}\CMRunningChapter}
\fancyhead[R]{\sffamily\fontsize{7.4}{9}\selectfont\color{CMRunningAccent}\textbf{\CMRunningMarker}}
\fancyfoot[L]{\sffamily\fontsize{7.0}{8.5}\selectfont\color{CMTeal}STEP 6 // LONG-FORM PROSE // V1.0}
\fancyfoot[R]{\sffamily\fontsize{7.0}{8.5}\selectfont\color{CMInk}\thepage}
\setlength{\headheight}{12pt}

\newcommand{\CMSetAudience}[1]{%
  \def\CMtmp{#1}%
  \def\CMgm{gm}%
  \ifx\CMtmp\CMgm
    \renewcommand{\CMChapterAccent}{CMViolet}%
    \renewcommand{\CMRunningAccent}{CMViolet}%
    \renewcommand{\CMRunningMarker}{GM MATERIAL}%
  \else
    \renewcommand{\CMChapterAccent}{CMCyan}%
    \renewcommand{\CMRunningAccent}{CMCyan}%
    \renewcommand{\CMRunningMarker}{PLAYER WORLD}%
  \fi
}

\newcommand{\CMPartPage}[4]{%
  \clearpage
  \begingroup
  \thispagestyle{empty}
  \pagecolor{CMInk}\color{white}
  \vspace*{0.78in}
  {\sffamily\fontsize{11}{13}\selectfont\color{#4}\bfseries PART #1\par}
  \vspace{0.15in}
  {\sffamily\fontsize{28}{31}\selectfont\bfseries #2\par}
  \vspace{0.12in}
  {\color{#4}\rule{1.25in}{2pt}\par}
  \vfill
  \begin{minipage}{0.78\textwidth}
    \sffamily\fontsize{11}{15}\selectfont\color{white!82}#3
  \end{minipage}
  \vspace*{0.50in}
  \clearpage
  \pagecolor{CMPaper}\color{CMBody}
  \endgroup
}

\newcommand{\CMChapterBanner}[3]{%
  \clearpage
  \CMSetAudience{#3}%
  \renewcommand{\CMRunningChapter}{#2}%
  \noindent\begin{minipage}{\textwidth}
    \colorbox{CMInk}{%
      \parbox{\dimexpr\textwidth-2\fboxsep\relax}{%
        \vspace{0.10in}
        {\sffamily\fontsize{8.3}{10}\selectfont\color{\CMChapterAccent}\bfseries CHAPTER #1\par}
        \vspace{0.045in}
        {\sffamily\fontsize{20}{22}\selectfont\color{white}\bfseries #2\par}
        \vspace{0.09in}
      }%
    }%
  \end{minipage}
  \vspace{0.15in}
}

\newcommand{\CMHThree}[1]{\par\Needspace{5\baselineskip}\vspace{4pt}{\sffamily\fontsize{13.2}{15}\selectfont\bfseries\color{CMTeal}#1\par}\vspace{1pt}}
\newcommand{\CMHFour}[1]{\par\Needspace{4\baselineskip}\vspace{3.4pt}{\sffamily\fontsize{10.8}{12.5}\selectfont\bfseries\color{CMInk}#1\par}\vspace{0.7pt}}
\newcommand{\CMHFive}[1]{\par\vspace{2.6pt}{\sffamily\fontsize{9.4}{11.2}\selectfont\bfseries\color{CMIndigo}#1\par}\vspace{0.3pt}}
\newcommand{\CMSectionRule}{\par\vspace{4pt}\noindent{\color{CMTeal!45}\rule{\columnwidth}{0.55pt}}\vspace{3pt}\par}

\newenvironment{CMQuote}{%
  \par\vspace{4pt}\noindent\begin{minipage}{\columnwidth}%
  \color{CMBody}\itshape\fontsize{9.8}{13.5}\selectfont
  \setlength{\parskip}{3pt}%
  \hspace*{0.02in}\color{CMTeal}\rule{1.8pt}{\dimexpr\baselineskip+5pt\relax}\hspace{0.08in}%
  \color{CMBody}\begin{minipage}[t]{\dimexpr\columnwidth-0.18in\relax}
}{%
  \end{minipage}\end{minipage}\par\vspace{4pt}
}

\newcommand{\CMStandardImage}[1]{\par\vspace{3pt}\noindent\includegraphics[width=\columnwidth,height=0.30\textheight,keepaspectratio]{#1}\par\vspace{4pt}}
\newcommand{\CMMarkImage}[1]{\par\vspace{2pt}\begin{center}\includegraphics[width=0.62\columnwidth,height=0.14\textheight,keepaspectratio]{#1}\end{center}\vspace{2pt}}
\newcommand{\CMSymbolicImage}[1]{\par\vspace{3pt}\begin{center}\includegraphics[width=0.78\columnwidth,height=0.24\textheight,keepaspectratio]{#1}\end{center}\vspace{3pt}}
\newcommand{\CMPortraitImage}[1]{\par\vspace{3pt}\begin{center}\includegraphics[width=0.88\columnwidth,height=0.28\textheight,keepaspectratio]{#1}\end{center}\vspace{3pt}}
\newcommand{\CMWideImage}[1]{\par\vspace{5pt}\begin{center}\includegraphics[width=\textwidth,height=0.38\textheight,keepaspectratio]{#1}\end{center}\vspace{6pt}}

\newcommand{\CMAssetPlaceholder}[1]{\par\vspace{4pt}\noindent\fcolorbox{CMTeal!45}{white}{\parbox[c][0.55in][c]{\dimexpr\columnwidth-2\fboxsep-2\fboxrule\relax}{\centering\sffamily\fontsize{7.7}{9}\selectfont\color{CMTeal}\textbf{STAGED ART}\\\color{CMInk}#1}}\par\vspace{4pt}}
\newcommand{\CMWideAssetPlaceholder}[1]{\par\vspace{5pt}\noindent\fcolorbox{CMTeal!45}{white}{\parbox[c][0.75in][c]{\dimexpr\textwidth-2\fboxsep-2\fboxrule\relax}{\centering\sffamily\fontsize{8.2}{10}\selectfont\color{CMTeal}\textbf{STAGED WIDE ART}\\\color{CMInk}#1}}\par\vspace{6pt}}

\newenvironment{CMProseTable}{%
  \par\vspace{5pt}\begingroup\fontsize{8.35}{10.3}\selectfont
  \setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.14}
}{%
  \endgroup\par\vspace{6pt}
}

\begin{document}
\frenchspacing
'''
    return preamble + _body_alignment_tex(config) + "\n"


def document_end() -> str:
    return "\\end{document}\n"


def part_tex(part_id: str) -> str:
    number, title, deck = TARGET_PARTS[part_id]
    accent = "CMViolet" if part_id == "section:part-v-gm-world" else "CMCyan"
    return (
        "\\CMPartPage{" + latex_escape(number) + "}{" + latex_escape(title) + "}{" +
        latex_escape(deck) + "}{" + accent + "}\n"
    )


def chapter_banner_tex(chapter: dict[str, Any]) -> str:
    return (
        "\\CMChapterBanner{" + str(chapter["number"]) + "}{" +
        latex_escape(chapter["title"]) + "}{" + chapter["audience"] + "}\n"
        "\\begin{multicols}{2}\n"
    )


def _latex_error_context(tex_path: Path, log_text: str, radius: int = 12) -> str:
    """Return generated-TeX context around the first file-line-error diagnostic."""
    patterns = [
        re.compile(rf"{re.escape(tex_path.name)}:(\d+):"),
        re.compile(r"l\.(\d+)\s"),
    ]
    line_no = None
    for pattern in patterns:
        match = pattern.search(log_text)
        if match:
            line_no = int(match.group(1))
            break
    if line_no is None or not tex_path.is_file():
        return ""

    lines = tex_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    rendered = []
    for n in range(start, end + 1):
        prefix = ">>" if n == line_no else "  "
        rendered.append(f"{prefix} {n:5d}: {lines[n - 1]}")
    return "\n".join(rendered)


def compile_lualatex(tex_path: Path, output: Path, work: Path) -> tuple[str, list[str]]:
    lualatex = resolve_tool("lualatex")
    if not lualatex:
        raise RuntimeError("LuaLaTeX is not installed or could not be resolved.")

    logs_dir = work / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []

    command = [
        lualatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        tex_path.name,
    ]

    for pass_number in (1, 2):
        p = run(command, cwd=work)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        logs.append(combined)

        pass_log = logs_dir / f"lualatex-pass-{pass_number}.txt"
        pass_log.write_text(
            "COMMAND:\n"
            + " ".join(command)
            + "\n\nCWD:\n"
            + str(work)
            + "\n\nOUTPUT:\n"
            + combined,
            encoding="utf-8",
        )

        if p.returncode != 0:
            excerpt = "\n".join(combined.splitlines()[-80:])
            context = _latex_error_context(tex_path, combined)
            native_log = work / f"{tex_path.stem}.log"
            details = [
                f"LuaLaTeX pass {pass_number} failed.",
                f"Command log: {pass_log}",
                f"Native LaTeX log: {native_log}",
                f"Generated TeX: {tex_path}",
            ]
            if context:
                details.append("Generated TeX context:\n" + context)
            details.append("LuaLaTeX tail:\n" + excerpt)
            raise RuntimeError("\n".join(details))

    built = work / (tex_path.stem + ".pdf")
    if not built.is_file():
        raise RuntimeError(f"LuaLaTeX reported success but did not create {built}")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, output)

    warnings: list[str] = []
    for log in logs:
        for line in log.splitlines():
            if any(p.search(line) for p in WARNING_PATTERNS):
                warnings.append(line.strip())
    return "\n".join(logs), sorted(set(warnings))


def pdf_page_count(path: Path) -> int | None:
    pdfinfo = resolve_tool("pdfinfo")
    if pdfinfo:
        p = run([pdfinfo, str(path)])
        if p.returncode == 0:
            m = re.search(r"^Pages:\s+(\d+)", p.stdout, re.M)
            if m:
                return int(m.group(1))
    try:
        data = path.read_bytes()
        count = len(re.findall(rb"/Type\s*/Page\b", data))
        return count or None
    except OSError:
        return None


def resolve_paths(args: argparse.Namespace) -> Paths:
    return Paths(
        repo_root=Path(args.repo_root).resolve(),
        config=Path(args.config).resolve(),
        lua_filter=Path(args.lua_filter).resolve(),
        source=Path(args.source).resolve(),
        asset_root=Path(args.asset_root).resolve(),
        output=Path(args.output).resolve(),
        report=Path(args.report).resolve(),
        work=Path(args.work).resolve(),
    )


def report_shell(paths: Paths) -> dict[str, Any]:
    return {
        "schema": "cybermancy-step6-prose-pandoc-lualatex-validation-v1.0",
        "status": "PASS",
        "implementation": "pandoc-lualatex",
        "implementationPatch": "1.0.5-linewise-boundary-validation",
        "layoutContract": str(paths.config),
        "checks": [],
        "warnings": [],
        "errors": [],
        "toolchain": {
            "python": sys.version.split()[0],
            "pandoc": executable_version("pandoc"),
            "pandocPath": resolve_tool("pandoc"),
            "lualatex": executable_version("lualatex"),
            "lualatexPath": resolve_tool("lualatex"),
            "pdfinfo": executable_version("pdfinfo") or "",
            "pdftotext": executable_version("pdftotext") or "",
        },
        "paths": {
            "source": str(paths.source),
            "assetRoot": str(paths.asset_root),
            "output": str(paths.output),
            "work": str(paths.work),
        },
    }


def validate_inputs(paths: Paths, report: dict[str, Any]) -> dict[str, Any] | None:
    for code, path in [
        ("CONFIG_PRESENT", paths.config),
        ("SOURCE_PRESENT", paths.source),
        ("LUA_FILTER_PRESENT", paths.lua_filter),
    ]:
        add_check(
            report,
            code,
            "PASS" if path.is_file() else "ERROR",
            f"{code.split('_')[0]} {'present' if path.is_file() else 'missing'}",
            str(path),
        )
    pandoc_path = resolve_tool("pandoc")
    lualatex_path = resolve_tool("lualatex")
    add_check(
        report,
        "TOOL_PANDOC",
        "PASS" if pandoc_path else "ERROR",
        "pandoc available" if pandoc_path else "pandoc not found on PATH or normal Windows install locations",
        {"path": pandoc_path, "version": report["toolchain"]["pandoc"]} if pandoc_path else None,
    )
    add_check(
        report,
        "TOOL_LUALATEX",
        "PASS" if lualatex_path else "ERROR",
        "lualatex available" if lualatex_path else "lualatex not found on PATH or normal Windows install locations",
        {"path": lualatex_path, "version": report["toolchain"]["lualatex"]} if lualatex_path else None,
    )
    if report["status"] != "PASS":
        return None
    config = load_json(paths.config)
    if config.get("schema") != "cybermancy-rulebook-prose-layout-v1" or config.get("version") != "1.0":
        add_check(report, "LAYOUT_VERSION", "ERROR", "Expected frozen prose layout v1.0")
    else:
        add_check(report, "LAYOUT_VERSION", "PASS", "Frozen prose layout v1.0 loaded")
    add_check(
        report,
        "PANDOC_LONGTABLE_COMPAT",
        "PASS",
        "LaTeX preamble defines the compatibility counter used by Pandoc >= 3.8 uncaptioned longtables",
        r"\@ifundefined{c@none}{\newcounter{none}}{}",
    )
    return config


def validate_structure(parts: list[dict[str, Any]], report: dict[str, Any]) -> None:
    found_parts = {p["semanticId"] for p in parts}
    missing_parts = sorted(set(TARGET_PARTS) - found_parts)
    found_chapters = {c["number"] for p in parts for c in p["chapters"]}
    missing_chapters = sorted(TARGET_CHAPTERS - found_chapters)
    if missing_parts or missing_chapters:
        add_check(
            report,
            "CHAPTER_ROUTING",
            "ERROR",
            "Required Parts I/V source structure is incomplete",
            {"missingParts": missing_parts, "missingChapters": missing_chapters},
        )
    else:
        add_check(
            report,
            "CHAPTER_ROUTING",
            "PASS",
            "All required Parts I and V chapters found",
            sorted(found_chapters),
        )


def build(paths: Paths) -> dict[str, Any]:
    report = report_shell(paths)
    config = validate_inputs(paths, report)
    if report["status"] != "PASS" or config is None:
        paths.report.parent.mkdir(parents=True, exist_ok=True)
        paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    source_text = paths.source.read_text(encoding="utf-8")
    parts = select_target_parts(parse_source(source_text))
    validate_structure(parts, report)
    if report["status"] != "PASS":
        paths.report.parent.mkdir(parents=True, exist_ok=True)
        paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    if paths.output.exists():
        paths.output.unlink()

    # Remove the obsolete WeasyPrint-era HTML regression artifact if it is
    # still present beside the PDF. The Pandoc/LuaLaTeX production builder does
    # not produce HTML, and a stale copy can disagree with the current PDF.
    legacy_html = paths.output.with_suffix(".html")
    legacy_html_removed = legacy_html.is_file()
    if legacy_html_removed:
        legacy_html.unlink()

    if paths.work.exists():
        shutil.rmtree(paths.work)
    paths.work.mkdir(parents=True, exist_ok=True)
    fragments = paths.work / "fragments"
    fragments.mkdir(parents=True, exist_ok=True)
    asset_cache = paths.work / "assets"
    asset_cache.mkdir(parents=True, exist_ok=True)

    missing_assets: list[dict[str, Any]] = []
    pandoc_warnings: list[str] = []
    stripped_html = 0
    resolved_assets = 0

    # Step 6 must not repair normalized manuscript structure. Fail early and
    # point back to Step 4 if any image/heading block boundary remains invalid.
    adjacency_defects: list[dict[str, Any]] = []
    for part in parts:
        for chapter in part["chapters"]:
            md, _ = sanitize_known_html_wrappers(chapter["markdown"])
            for defect in find_adjacent_image_headings(md):
                adjacency_defects.append(
                    {
                        "chapter": chapter["number"],
                        "title": chapter["title"],
                        **defect,
                    }
                )
    if adjacency_defects:
        add_check(
            report,
            "IMAGE_HEADING_ADJACENCY",
            "ERROR",
            (
                f"Step 4 normalized source contains {len(adjacency_defects)} "
                "image/heading block-boundary defect(s); Step 6 did not repair them."
            ),
            adjacency_defects,
        )
        paths.report.parent.mkdir(parents=True, exist_ok=True)
        paths.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return report
    add_check(
        report,
        "IMAGE_HEADING_ADJACENCY",
        "PASS",
        "Step 4 normalized source contains no adjacent image/heading block defects",
    )

    document: list[str] = [document_preamble(config)]

    for part in parts:
        document.append(part_tex(part["semanticId"]))
        for chapter in part["chapters"]:
            md, removed = sanitize_known_html_wrappers(chapter["markdown"])
            stripped_html += removed
            md, resolved = stage_markdown_assets(md, chapter["number"], paths.asset_root, asset_cache, missing_assets)
            resolved_assets += resolved

            md_path = fragments / f"chapter-{chapter['number']:02d}.md"
            body_path = fragments / f"chapter-{chapter['number']:02d}.body.tex"
            md_path.write_text(md, encoding="utf-8")
            _, stderr = run_pandoc_body(md_path, body_path, paths.lua_filter, paths.work)
            for line in stderr.splitlines():
                if line.strip():
                    pandoc_warnings.append(line.strip())

            document.append(chapter_banner_tex(chapter))
            document.append(body_path.read_text(encoding="utf-8"))
            document.append("\\end{multicols}\n")

    document.append(document_end())
    tex_path = paths.work / "Cybermancy_Parts_I_V_Prose_Regression_v1.tex"
    tex_path.write_text("\n".join(document), encoding="utf-8")
    add_check(report, "LATEX_GENERATED", "PASS", "Pandoc/Lua-filter LaTeX assembled", str(tex_path))

    if pandoc_warnings:
        add_check(report, "PANDOC_WARNINGS", "WARNING", f"Pandoc emitted {len(pandoc_warnings)} diagnostic line(s)", pandoc_warnings[:80])
    else:
        add_check(report, "PANDOC_WARNINGS", "PASS", "Pandoc emitted no warnings")

    unique_missing = sorted({x["source"] for x in missing_assets})
    if unique_missing:
        add_check(
            report,
            "ASSETS",
            "WARNING",
            f"{len(unique_missing)} source assets were absent; fail-visible placeholders rendered",
            unique_missing,
        )
    else:
        add_check(report, "ASSETS", "PASS", f"All {resolved_assets} source asset references resolved")

    add_check(
        report,
        "LEGACY_HTML_ARTIFACT",
        "INFO" if legacy_html_removed else "PASS",
        (
            f"Removed obsolete WeasyPrint-era HTML artifact: {legacy_html}"
            if legacy_html_removed
            else "No obsolete HTML regression artifact was present"
        ),
    )

    if stripped_html:
        add_check(
            report,
            "RAW_HTML_WRAPPERS",
            "INFO",
            f"Dropped {stripped_html} known MkDocs-only div wrapper line(s) before Pandoc conversion",
        )
    else:
        add_check(report, "RAW_HTML_WRAPPERS", "PASS", "No known MkDocs-only wrapper lines required cleanup")

    try:
        _, latex_warnings = compile_lualatex(tex_path, paths.output, paths.work)
    except Exception as exc:
        add_check(report, "PDF_COMPILED", "ERROR", str(exc))
    else:
        add_check(report, "PDF_COMPILED", "PASS", "LuaLaTeX produced PDF", str(paths.output))
        if latex_warnings:
            add_check(report, "LATEX_WARNINGS", "WARNING", f"LuaLaTeX emitted {len(latex_warnings)} material warning(s)", latex_warnings[:100])
        else:
            add_check(report, "LATEX_WARNINGS", "PASS", "No material LaTeX warnings detected")
        pages = pdf_page_count(paths.output)
        add_check(report, "PAGE_COUNT", "PASS" if pages else "WARNING", f"PDF page count: {pages if pages else 'unknown'}", pages)

    report["implementationDetails"] = {
        "renderer": "Pandoc Markdown AST -> prose Lua filter -> LuaLaTeX",
        "markdownReader": MARKDOWN_FROM,
        "bodyColumns": 2,
        "targetChapters": sorted(TARGET_CHAPTERS),
        "resolvedAssetReferences": resolved_assets,
        "missingAssetCount": len(unique_missing),
        "pandocLongtableCompatibility": "guarded LaTeX counter 'none' for Pandoc >= 3.8",
        "imageHeadingPolicy": "strict Step 4 validation; Step 6 performs no boundary repair",
        "diagnosticArtifacts": {
            "generatedTex": str(tex_path),
            "nativeLatexLog": str(paths.work / (tex_path.stem + ".log")),
            "passLogsDirectory": str(paths.work / "logs"),
        },
    }
    if paths.output.is_file():
        report["outputSha256"] = sha256_file(paths.output)

    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def validate_only(paths: Paths) -> dict[str, Any]:
    report = report_shell(paths)
    config = validate_inputs(paths, report)
    if config is None or report["status"] != "PASS":
        paths.report.parent.mkdir(parents=True, exist_ok=True)
        paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report
    parts = select_target_parts(parse_source(paths.source.read_text(encoding="utf-8")))
    validate_structure(parts, report)
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build the accepted Cybermancy long-form prose regression PDF")
    p.add_argument("command", nargs="?", choices=["build", "validate"], default="build")
    p.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--lua-filter", default=str(DEFAULT_FILTER))
    p.add_argument("--source", default=str(DEFAULT_SOURCE))
    p.add_argument("--asset-root", default=str(DEFAULT_ASSET_ROOT))
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--work", default=str(DEFAULT_WORK))
    return p


def main() -> int:
    args = parser().parse_args()
    paths = resolve_paths(args)
    if args.command == "validate":
        report = validate_only(paths)
    else:
        report = build(paths)
    print(json.dumps({"status": report["status"], "report": str(paths.report), "output": str(paths.output)}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())