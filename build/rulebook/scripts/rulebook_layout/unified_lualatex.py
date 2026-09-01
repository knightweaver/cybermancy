from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


STAGE_NAME = "lualatex"
STAGE_ORDER = 160
DEFAULT_PASSES = 2

_OVERFULL_RE = re.compile(r"^Overfull \\[hv]box.*$", re.M)
_UNDERFULL_RE = re.compile(r"^Underfull \\[hv]box.*$", re.M)
_MISSING_CHARACTER_RE = re.compile(r"^Missing character:.*$", re.M)
_LATEX_WARNING_RE = re.compile(r"^LaTeX Warning:.*$", re.M)
_PACKAGE_WARNING_RE = re.compile(r"^Package .* Warning:.*$", re.M)
_FONT_WARNING_RE = re.compile(r"^(?:LaTeX Font Warning:|Package fontspec Warning:).*$", re.M)
_FILE_LINE_ERROR_RE = re.compile(r"^(?P<file>[^:\n]+\.tex):(?P<line>\d+):\s*(?P<message>.+)$", re.M)
_LINE_ERROR_RE = re.compile(r"^l\.(?P<line>\d+)\s(?P<message>.*)$", re.M)
_OVERFULL_LINE_RE = re.compile(r"at lines (?P<line>\d+)(?:--\d+)?")
_USEPACKAGE_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^{}]+)\}")
_DETOKENIZE_RE = re.compile(r"\\detokenize\{([^{}]+)\}")
_INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")

_STAGE150_FOOTER_PREFIX = r"\fancyfoot[L]{"
_STAGE150_FOOTER_TOKEN = "STEP 6 // "
_STAGE150_FOOTER_SUFFIX = " // INTEGRATED"
_HFUZZ_LINE = r"\hfuzz=0.25pt"
_SOUL_PACKAGE = r"\usepackage{soul}"
_HYPERREF_PACKAGE = r"\usepackage[hidelinks]{hyperref}"
_BEGIN_DOCUMENT = r"\begin{document}"
_FATAL_MESSAGE_HINTS = (
    "undefined control sequence",
    "fatal error",
    "emergency stop",
    "latex error",
    "missing ",
    "extra ",
    "runaway argument",
    "file ended while scanning",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> tuple[str, list[dict[str, Any]]]:
    digest = hashlib.sha256()
    rows: list[dict[str, Any]] = []
    if not root.is_dir():
        return digest.hexdigest(), rows
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        file_sha = sha256_file(path)
        size = path.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\n")
        rows.append({"path": relative, "sha256": file_sha, "bytes": size})
    return digest.hexdigest(), rows


def contract_stage(contract: dict[str, Any]) -> dict[str, Any] | None:
    rows = [
        row
        for row in contract.get("transformationOrder", [])
        if isinstance(row, dict) and row.get("stage") == STAGE_NAME
    ]
    return rows[0] if len(rows) == 1 else None


def extract_usepackages(tex: str) -> list[str]:
    result: set[str] = set()
    for match in _USEPACKAGE_RE.finditer(tex):
        for value in match.group(1).split(","):
            name = value.strip()
            if name:
                result.add(name)
    return sorted(result)


def static_graphics_references(tex: str) -> list[str]:
    """Return concrete graphics paths while ignoring macro placeholders such as #1."""
    refs: set[str] = set()
    for match in _DETOKENIZE_RE.finditer(tex):
        value = match.group(1).strip()
        if value and "#" not in value and "\\" not in value:
            refs.add(value)
    for match in _INCLUDEGRAPHICS_RE.finditer(tex):
        value = match.group(1).strip()
        if not value or "#" in value or "\\" in value:
            continue
        refs.add(value)
    return sorted(refs)


def validate_static_graphics(tex: str, compile_root: Path) -> dict[str, Any]:
    refs = static_graphics_references(tex)
    missing: list[str] = []
    absolute: list[str] = []
    outside: list[str] = []
    root = compile_root.resolve()
    for value in refs:
        normalized = value.replace("\\", "/")
        raw = Path(normalized)
        if raw.is_absolute() or re.match(r"^[A-Za-z]:/", normalized):
            absolute.append(value)
            continue
        candidate = (root / raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            outside.append(value)
            continue
        if not candidate.is_file():
            missing.append(value)
    ok = not missing and not absolute and not outside
    return {
        "status": "PASS" if ok else "FAIL",
        "referenceCount": len(refs),
        "references": refs,
        "missing": missing,
        "absolute": absolute,
        "outsideCompileRoot": outside,
    }


def _anchor_profile_footer(tex: str) -> tuple[str, bool]:
    """Make the Stage 150 left footer zero-width to avoid fancyhdr field overrun."""
    lines = tex.splitlines()
    changed = False
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith(_STAGE150_FOOTER_PREFIX)
            and _STAGE150_FOOTER_TOKEN in stripped
            and _STAGE150_FOOTER_SUFFIX in stripped
            and not stripped.startswith(_STAGE150_FOOTER_PREFIX + r"\rlap{")
            and stripped.endswith("}")
        ):
            leading = line[: len(line) - len(line.lstrip())]
            inner = stripped[len(_STAGE150_FOOTER_PREFIX) : -1]
            line = leading + _STAGE150_FOOTER_PREFIX + r"\rlap{" + inner + "}}"
            changed = True
        output.append(line)
    trailing_newline = "\n" if tex.endswith("\n") else ""
    return "\n".join(output) + trailing_newline, changed


def apply_compile_compatibility_overlay(tex_path: Path) -> dict[str, Any]:
    """Apply deterministic LuaLaTeX-only shims to the isolated Stage 160 TeX copy.

    Stage 150 remains the provenance handoff and is never modified.  The overlay
    addresses three integration defects exposed only by the first unified compile:
    Pandoc strikeout's ``\\st`` dependency, fancyhdr's profile-footer width, and
    sub-hairline (<0.25pt) TeX rounding noise from frozen package boxes.
    """
    original = tex_path.read_text(encoding="utf-8")
    text = original
    patches: list[str] = []

    uses_strikeout = r"\st{" in text
    has_strikeout_support = _SOUL_PACKAGE in text or re.search(
        r"\\(?:newcommand|providecommand|renewcommand)\{\\st\}", text
    ) is not None
    if uses_strikeout and not has_strikeout_support:
        if _HYPERREF_PACKAGE in text:
            text = text.replace(
                _HYPERREF_PACKAGE,
                _SOUL_PACKAGE + "\n" + _HYPERREF_PACKAGE,
                1,
            )
        elif _BEGIN_DOCUMENT in text:
            text = text.replace(
                _BEGIN_DOCUMENT,
                _SOUL_PACKAGE + "\n" + _BEGIN_DOCUMENT,
                1,
            )
        else:
            return {
                "status": "FAIL",
                "patches": patches,
                "error": "Could not inject Pandoc strikeout support because the document boundary is missing.",
            }
        patches.append("pandoc-strikeout-soul")

    if _HFUZZ_LINE not in text:
        if _BEGIN_DOCUMENT not in text:
            return {
                "status": "FAIL",
                "patches": patches,
                "error": "Could not install the Stage 160 micro-overflow tolerance because the document boundary is missing.",
            }
        text = text.replace(
            _BEGIN_DOCUMENT,
            "% Stage 160: ignore only sub-hairline TeX rounding noise; material overfull boxes remain blocking.\n"
            + _HFUZZ_LINE
            + "\n"
            + _BEGIN_DOCUMENT,
            1,
        )
        patches.append("hfuzz-0.25pt")

    text, footer_changed = _anchor_profile_footer(text)
    if footer_changed:
        patches.append("profile-footer-zero-width-anchor")

    if text != original:
        tex_path.write_text(text, encoding="utf-8")

    final = tex_path.read_text(encoding="utf-8")
    strikeout_ok = not uses_strikeout or (
        _SOUL_PACKAGE in final
        or re.search(r"\\(?:newcommand|providecommand|renewcommand)\{\\st\}", final)
        is not None
    )
    hfuzz_ok = _HFUZZ_LINE in final
    footer_lines = [
        line.strip()
        for line in final.splitlines()
        if line.strip().startswith(_STAGE150_FOOTER_PREFIX)
        and _STAGE150_FOOTER_TOKEN in line
        and _STAGE150_FOOTER_SUFFIX in line
    ]
    footer_ok = all(
        line.startswith(_STAGE150_FOOTER_PREFIX + r"\rlap{") for line in footer_lines
    )
    ok = strikeout_ok and hfuzz_ok and footer_ok
    return {
        "status": "PASS" if ok else "FAIL",
        "patches": patches,
        "usesStrikeout": uses_strikeout,
        "strikeoutSupport": strikeout_ok,
        "microOverflowTolerancePt": 0.25,
        "profileFooterCount": len(footer_lines),
        "profileFooterAnchored": footer_ok,
        "inputSha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "outputSha256": sha256_file(tex_path),
    }


def prepare_compile_tree(
    source_tex: Path,
    source_assets: Path,
    work_dir: Path,
) -> dict[str, Any]:
    """Create an isolated Stage 160 compile root from the Stage 150 output."""
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    compile_tex = work_dir / source_tex.name
    shutil.copy2(source_tex, compile_tex)
    compile_assets = work_dir / "assets"
    if source_assets.is_dir():
        shutil.copytree(source_assets, compile_assets)
    else:
        compile_assets.mkdir(parents=True, exist_ok=True)

    source_assets_sha, source_rows = sha256_tree(source_assets)
    copied_assets_sha, copied_rows = sha256_tree(compile_assets)
    tex_source_sha = sha256_file(source_tex)
    tex_copy_sha = sha256_file(compile_tex)
    exact_copy_ok = (
        tex_source_sha == tex_copy_sha
        and source_assets_sha == copied_assets_sha
        and source_rows == copied_rows
    )
    if not exact_copy_ok:
        return {
            "status": "FAIL",
            "sourceTex": str(source_tex),
            "compileTex": str(compile_tex),
            "sourceTexSha256": tex_source_sha,
            "copiedTexSha256": tex_copy_sha,
            "sourceAssets": str(source_assets),
            "compileAssets": str(compile_assets),
            "assetCount": len(source_rows),
            "sourceAssetsSha256": source_assets_sha,
            "compileAssetsSha256": copied_assets_sha,
            "assets": copied_rows,
            "compatibilityOverlay": {"status": "SKIPPED"},
        }

    overlay = apply_compile_compatibility_overlay(compile_tex)
    compile_tex_sha = sha256_file(compile_tex)
    ok = overlay.get("status") == "PASS"
    return {
        "status": "PASS" if ok else "FAIL",
        "sourceTex": str(source_tex),
        "compileTex": str(compile_tex),
        "sourceTexSha256": tex_source_sha,
        "copiedTexSha256": tex_copy_sha,
        "compileTexSha256": compile_tex_sha,
        "sourceAssets": str(source_assets),
        "compileAssets": str(compile_assets),
        "assetCount": len(source_rows),
        "sourceAssetsSha256": source_assets_sha,
        "compileAssetsSha256": copied_assets_sha,
        "assets": copied_rows,
        "compatibilityOverlay": overlay,
    }


def _run_utf8(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def probe_tex_packages(
    tex: str,
    kpsewhich: str | None,
    work_dir: Path,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    packages = extract_usepackages(tex)
    if not kpsewhich:
        return {
            "status": "SKIPPED",
            "packages": packages,
            "missing": [],
            "message": "kpsewhich is unavailable; LuaLaTeX will perform dependency resolution.",
        }

    missing: list[str] = []
    resolved: dict[str, str] = {}
    for package in packages:
        proc = runner([kpsewhich, f"{package}.sty"], work_dir)
        location = (proc.stdout or "").strip().splitlines()
        if proc.returncode != 0 or not location:
            missing.append(package)
        else:
            resolved[package] = location[0]
    return {
        "status": "PASS" if not missing else "FAIL",
        "packages": packages,
        "resolved": resolved,
        "missing": missing,
    }


def parse_latex_diagnostics(log_text: str) -> dict[str, Any]:
    overfull = sorted(set(_OVERFULL_RE.findall(log_text)))
    underfull = sorted(set(_UNDERFULL_RE.findall(log_text)))
    missing_characters = sorted(set(_MISSING_CHARACTER_RE.findall(log_text)))
    latex_warnings = sorted(set(_LATEX_WARNING_RE.findall(log_text)))
    package_warnings = sorted(set(_PACKAGE_WARNING_RE.findall(log_text)))
    font_warnings = sorted(set(_FONT_WARNING_RE.findall(log_text)))
    return {
        "overfull": overfull,
        "underfull": underfull,
        "missingCharacters": missing_characters,
        "latexWarnings": latex_warnings,
        "packageWarnings": package_warnings,
        "fontWarnings": font_warnings,
        "blockingCount": len(overfull) + len(missing_characters),
        "warningCount": len(latex_warnings) + len(package_warnings) + len(font_warnings),
    }


def _tex_context(tex_path: Path, line_no: int, radius: int = 12) -> str:
    if not tex_path.is_file():
        return ""
    lines = tex_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if line_no < 1 or line_no > len(lines):
        return ""
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    rendered: list[str] = []
    for number in range(start, end + 1):
        prefix = ">>" if number == line_no else "  "
        rendered.append(f"{prefix} {number:5d}: {lines[number - 1]}")
    return "\n".join(rendered)


def latex_error_context(tex_path: Path, log_text: str, radius: int = 12) -> str:
    file_matches = list(_FILE_LINE_ERROR_RE.finditer(log_text))
    line_no: int | None = None
    if file_matches:
        preferred = None
        for match in reversed(file_matches):
            message = match.group("message").lower()
            if any(hint in message for hint in _FATAL_MESSAGE_HINTS):
                preferred = match
                break
        chosen = preferred or file_matches[-1]
        line_no = int(chosen.group("line"))
    else:
        line_matches = list(_LINE_ERROR_RE.finditer(log_text))
        if line_matches:
            line_no = int(line_matches[-1].group("line"))
    if line_no is None:
        return ""
    return _tex_context(tex_path, line_no, radius=radius)


def blocking_diagnostic_contexts(
    tex_path: Path,
    diagnostics: dict[str, Any],
    radius: int = 5,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    seen: set[int] = set()
    for diagnostic in diagnostics.get("overfull") or []:
        match = _OVERFULL_LINE_RE.search(str(diagnostic))
        if not match:
            continue
        line_no = int(match.group("line"))
        if line_no in seen:
            continue
        seen.add(line_no)
        contexts.append(
            {
                "diagnostic": diagnostic,
                "line": line_no,
                "texContext": _tex_context(tex_path, line_no, radius=radius),
            }
        )
    return contexts


def compile_unified_lualatex(
    tex_path: Path,
    lualatex: str,
    work_dir: Path,
    passes: int = DEFAULT_PASSES,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    """Compile one Stage 150 integrated TeX document in an isolated work root."""
    logs_dir = work_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    command = [
        lualatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        tex_path.name,
    ]
    pass_reports: list[dict[str, Any]] = []
    combined_logs: list[str] = []

    for pass_number in range(1, passes + 1):
        proc = runner(command, work_dir)
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        combined_logs.append(combined)
        log_path = logs_dir / f"lualatex-pass-{pass_number}.txt"
        log_path.write_text(
            "COMMAND:\n"
            + " ".join(command)
            + "\n\nCWD:\n"
            + str(work_dir)
            + "\n\nOUTPUT:\n"
            + combined,
            encoding="utf-8",
        )
        pass_report = {
            "pass": pass_number,
            "returnCode": proc.returncode,
            "log": str(log_path),
            "outputTail": "\n".join(combined.splitlines()[-100:]),
        }
        if proc.returncode != 0:
            context = latex_error_context(tex_path, combined)
            if context:
                pass_report["texContext"] = context
            native_log = work_dir / f"{tex_path.stem}.log"
            if native_log.is_file():
                pass_report["nativeLog"] = str(native_log)
            pass_reports.append(pass_report)
            diagnostics = parse_latex_diagnostics("\n".join(combined_logs))
            return {
                "status": "FAIL",
                "command": command,
                "passesRequested": passes,
                "passesCompleted": pass_number - 1,
                "passReports": pass_reports,
                "failedPass": pass_number,
                "diagnostics": diagnostics,
                "blockingContexts": blocking_diagnostic_contexts(tex_path, diagnostics),
            }
        pass_reports.append(pass_report)

    pdf_path = work_dir / f"{tex_path.stem}.pdf"
    all_logs = "\n".join(combined_logs)
    diagnostics = parse_latex_diagnostics(all_logs)
    pdf_ok = pdf_path.is_file() and pdf_path.stat().st_size > 0
    ok = pdf_ok and diagnostics["blockingCount"] == 0
    return {
        "status": "PASS" if ok else "FAIL",
        "command": command,
        "passesRequested": passes,
        "passesCompleted": passes,
        "passReports": pass_reports,
        "pdf": str(pdf_path),
        "pdfBytes": pdf_path.stat().st_size if pdf_ok else 0,
        "pdfSha256": sha256_file(pdf_path) if pdf_ok else None,
        "diagnostics": diagnostics,
        "blockingContexts": blocking_diagnostic_contexts(tex_path, diagnostics),
    }


def pdf_page_count(
    path: Path,
    pdfinfo: str | None = None,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> int | None:
    if pdfinfo:
        proc = runner([pdfinfo, str(path)], path.parent)
        if proc.returncode == 0:
            match = re.search(r"^Pages:\s+(\d+)", proc.stdout or "", re.M)
            if match:
                return int(match.group(1))
    try:
        data = path.read_bytes()
    except OSError:
        return None
    count = len(re.findall(rb"/Type\s*/Page\b", data))
    return count or None


def copy_compiled_pdf(compiled_pdf: Path, output_pdf: Path) -> dict[str, Any]:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(compiled_pdf, output_pdf)
    valid_magic = output_pdf.read_bytes()[:5] == b"%PDF-"
    return {
        "status": "PASS" if output_pdf.is_file() and output_pdf.stat().st_size > 0 and valid_magic else "FAIL",
        "path": str(output_pdf),
        "bytes": output_pdf.stat().st_size if output_pdf.is_file() else 0,
        "sha256": sha256_file(output_pdf) if output_pdf.is_file() else None,
        "pdfMagic": valid_magic,
    }
