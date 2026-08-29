from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from rulebook_layout.unified_lualatex import (
    DEFAULT_PASSES,
    _run_utf8,
    blocking_diagnostic_contexts,
    latex_error_context,
    parse_latex_diagnostics,
    sha256_file,
)


_STAGE160_SHELL_MARKER = "% CM-INTEGRATED-SHELL PART "
_PROFILE_TITLES = {
    "player-guide": "Cybermancy Player Guide",
    "complete-rulebook": "Cybermancy Complete Rulebook",
}
_SOURCE_PROVENANCE_RE = re.compile(
    r"(?P<document>\\begin\{document\}\r?\n\\frenchspacing\r?\n)"
    r"\\begin\{center\}\\rule\{0\.5\\linewidth\}\{0\.5pt\}\\end\{center\}\r?\n"
    r"(?:[ \t]*\r?\n)+"
    r"title: ``(?P<title>[^\r\n]+?)'' profile: ``(?P<profile>[^\r\n]+?)'' "
    r"source-commit: ``(?P<commit>[0-9a-f]{40})'' ---\r?\n"
    r"(?:[ \t]*\r?\n)*"
)
_OUTPUT_ROUTINE_VBOX_RE = re.compile(
    r"^Overfull \\vbox .* while \\output is active$"
)


def strip_publication_provenance_residue(
    tex_path: Path,
    profile: str,
) -> dict[str, Any]:
    """Remove the exact Step 4 publication-provenance residue from the Stage 160 copy.

    The accepted Stage 150 handoff remains byte-stable.  This cleanup is deliberately
    narrow and fail-closed: if provenance-like text is present before the first
    integrated Part marker but does not match the exact known generated form for the
    selected profile, Stage 160 refuses to compile it.
    """
    original = tex_path.read_text(encoding="utf-8")
    expected_title = _PROFILE_TITLES.get(profile)
    if expected_title is None:
        return {
            "status": "FAIL",
            "stripped": False,
            "error": f"Unsupported Stage 160 profile for provenance cleanup: {profile}",
        }

    shell_index = original.find(_STAGE160_SHELL_MARKER)
    prefix = original if shell_index < 0 else original[:shell_index]
    match = _SOURCE_PROVENANCE_RE.search(prefix)

    provenance_markers = (
        "source-commit:",
        "profile: ``",
        r"\begin{center}\rule{0.5\linewidth}{0.5pt}\end{center}",
    )
    has_provenance_like_residue = any(marker in prefix for marker in provenance_markers)

    if match is None:
        if has_provenance_like_residue:
            return {
                "status": "FAIL",
                "stripped": False,
                "error": (
                    "Publication provenance-like residue was present before the first "
                    "integrated Part marker but did not match the exact Stage 4 generated form."
                ),
                "inputSha256": sha256_file(tex_path),
            }
        return {
            "status": "PASS",
            "stripped": False,
            "profile": profile,
            "inputSha256": sha256_file(tex_path),
            "outputSha256": sha256_file(tex_path),
        }

    found_title = match.group("title")
    found_profile = match.group("profile")
    source_commit = match.group("commit")
    if found_title != expected_title or found_profile != profile:
        return {
            "status": "FAIL",
            "stripped": False,
            "error": "Publication provenance residue does not match the selected profile.",
            "expected": {"title": expected_title, "profile": profile},
            "found": {"title": found_title, "profile": found_profile},
            "sourceCommit": source_commit,
            "inputSha256": sha256_file(tex_path),
        }

    replacement = match.group("document") + "\n"
    cleaned = original[: match.start()] + replacement + original[match.end() :]
    input_sha = sha256_file(tex_path)
    tex_path.write_text(cleaned, encoding="utf-8")
    output_sha = sha256_file(tex_path)
    return {
        "status": "PASS",
        "stripped": True,
        "profile": profile,
        "title": found_title,
        "sourceCommit": source_commit,
        "inputSha256": input_sha,
        "outputSha256": output_sha,
    }


def classify_latex_diagnostics(log_text: str) -> dict[str, Any]:
    """Classify Stage 160 compiler diagnostics by compile-vs-render ownership.

    Overfull hboxes and non-output-routine vboxes remain blocking at Stage 160.
    TeX output-routine vboxes are retained verbatim as rendered-layout warnings for
    Stage 170, where page-level clipping and geometry can be inspected directly.
    """
    report = parse_latex_diagnostics(log_text)
    overfull = [str(value) for value in report.get("overfull") or []]
    output_routine_vboxes = sorted(
        value for value in overfull if _OUTPUT_ROUTINE_VBOX_RE.match(value)
    )
    deferred = set(output_routine_vboxes)
    blocking_overfull = sorted(value for value in overfull if value not in deferred)
    missing = [str(value) for value in report.get("missingCharacters") or []]
    report["blockingOverfull"] = blocking_overfull
    report["outputRoutineVboxes"] = output_routine_vboxes
    report["blockingCount"] = len(blocking_overfull) + len(missing)
    report["renderedLayoutWarningCount"] = len(output_routine_vboxes)
    return report


def compile_unified_lualatex_stage160(
    tex_path: Path,
    lualatex: str,
    work_dir: Path,
    passes: int = DEFAULT_PASSES,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = _run_utf8,
) -> dict[str, Any]:
    """Compile Stage 160 with diagnostics classified for the Stage 170 handoff."""
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
            diagnostics = classify_latex_diagnostics("\n".join(combined_logs))
            blocking_view = {"overfull": diagnostics["blockingOverfull"]}
            return {
                "status": "FAIL",
                "command": command,
                "passesRequested": passes,
                "passesCompleted": pass_number - 1,
                "passReports": pass_reports,
                "failedPass": pass_number,
                "diagnostics": diagnostics,
                "blockingContexts": blocking_diagnostic_contexts(
                    tex_path, blocking_view
                ),
            }
        pass_reports.append(pass_report)

    pdf_path = work_dir / f"{tex_path.stem}.pdf"
    diagnostics = classify_latex_diagnostics("\n".join(combined_logs))
    pdf_ok = pdf_path.is_file() and pdf_path.stat().st_size > 0
    ok = pdf_ok and diagnostics["blockingCount"] == 0
    blocking_view = {"overfull": diagnostics["blockingOverfull"]}
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
        "blockingContexts": blocking_diagnostic_contexts(tex_path, blocking_view),
    }
