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
_USEPACKAGE_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^{}]+)\}")
_DETOKENIZE_RE = re.compile(r"\\detokenize\{([^{}]+)\}")
_INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")


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
    ok = (
        tex_source_sha == tex_copy_sha
        and source_assets_sha == copied_assets_sha
        and source_rows == copied_rows
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "sourceTex": str(source_tex),
        "compileTex": str(compile_tex),
        "sourceTexSha256": tex_source_sha,
        "compileTexSha256": tex_copy_sha,
        "sourceAssets": str(source_assets),
        "compileAssets": str(compile_assets),
        "assetCount": len(source_rows),
        "sourceAssetsSha256": source_assets_sha,
        "compileAssetsSha256": copied_assets_sha,
        "assets": copied_rows,
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


def latex_error_context(tex_path: Path, log_text: str, radius: int = 12) -> str:
    line_no: int | None = None
    match = _FILE_LINE_ERROR_RE.search(log_text)
    if match:
        line_no = int(match.group("line"))
    else:
        match = _LINE_ERROR_RE.search(log_text)
        if match:
            line_no = int(match.group("line"))
    if line_no is None or not tex_path.is_file():
        return ""

    lines = tex_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    rendered: list[str] = []
    for number in range(start, end + 1):
        prefix = ">>" if number == line_no else "  "
        rendered.append(f"{prefix} {number:5d}: {lines[number - 1]}")
    return "\n".join(rendered)


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
            return {
                "status": "FAIL",
                "command": command,
                "passesRequested": passes,
                "passesCompleted": pass_number - 1,
                "passReports": pass_reports,
                "failedPass": pass_number,
                "diagnostics": parse_latex_diagnostics("\n".join(combined_logs)),
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
