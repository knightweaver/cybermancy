from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.stage160_policy import (
    classify_latex_diagnostics,
    compile_unified_lualatex_stage160,
    strip_publication_provenance_residue,
)


def _completed(
    command: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def _tex_with_residue(title: str, profile: str, commit: str = "a" * 40) -> str:
    return "\n".join(
        [
            r"\documentclass{article}",
            r"\begin{document}",
            r"\frenchspacing",
            r"\begin{center}\rule{0.5\linewidth}{0.5pt}\end{center}",
            "",
            f"title: ``{title}'' profile: ``{profile}'' source-commit: ``{commit}'' ---",
            "",
            "% CM-INTEGRATED-SHELL PART part-i-world",
            r"\CMIntegratedPart{I}{The World of Cybermancy}{player}{part-i-world}",
            r"\end{document}",
            "",
        ]
    )


class Stage160ProvenanceCleanupTests(unittest.TestCase):
    def test_strips_exact_player_publication_residue_from_compile_copy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "player.tex"
            path.write_text(
                _tex_with_residue("Cybermancy Player Guide", "player-guide"),
                encoding="utf-8",
            )
            result = strip_publication_provenance_residue(path, "player-guide")
            self.assertEqual(result["status"], "PASS", result)
            self.assertTrue(result["stripped"])
            rendered = path.read_text(encoding="utf-8")
            self.assertNotIn("source-commit:", rendered)
            self.assertNotIn(r"\rule{0.5\linewidth}{0.5pt}", rendered)
            self.assertIn("% CM-INTEGRATED-SHELL PART part-i-world", rendered)

    def test_strips_exact_complete_publication_residue_from_compile_copy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "complete.tex"
            path.write_text(
                _tex_with_residue(
                    "Cybermancy Complete Rulebook", "complete-rulebook", "b" * 40
                ),
                encoding="utf-8",
            )
            result = strip_publication_provenance_residue(
                path, "complete-rulebook"
            )
            self.assertEqual(result["status"], "PASS", result)
            self.assertTrue(result["stripped"])
            self.assertEqual(result["sourceCommit"], "b" * 40)

    def test_rejects_profile_mismatch_without_mutating_tex(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "book.tex"
            original = _tex_with_residue(
                "Cybermancy Complete Rulebook", "complete-rulebook"
            )
            path.write_text(original, encoding="utf-8")
            result = strip_publication_provenance_residue(path, "player-guide")
            self.assertEqual(result["status"], "FAIL", result)
            self.assertFalse(result["stripped"])
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_noop_when_generated_residue_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "book.tex"
            original = "\n".join(
                [
                    r"\documentclass{article}",
                    r"\begin{document}",
                    r"\frenchspacing",
                    "% CM-INTEGRATED-SHELL PART part-i-world",
                    r"\end{document}",
                    "",
                ]
            )
            path.write_text(original, encoding="utf-8")
            result = strip_publication_provenance_residue(path, "player-guide")
            self.assertEqual(result["status"], "PASS", result)
            self.assertFalse(result["stripped"])
            self.assertEqual(path.read_text(encoding="utf-8"), original)


class Stage160DiagnosticPolicyTests(unittest.TestCase):
    def test_output_routine_vbox_is_retained_but_deferred_to_stage170(self) -> None:
        diagnostic = (
            r"Overfull \vbox (21.933pt too high) has occurred while \output is active"
        )
        report = classify_latex_diagnostics(diagnostic)
        self.assertEqual(report["blockingCount"], 0, report)
        self.assertEqual(report["blockingOverfull"], [])
        self.assertEqual(report["outputRoutineVboxes"], [diagnostic])
        self.assertEqual(report["renderedLayoutWarningCount"], 1)

    def test_overfull_hbox_remains_blocking(self) -> None:
        diagnostic = r"Overfull \hbox (5.0pt too wide) in paragraph at lines 10--11"
        report = classify_latex_diagnostics(diagnostic)
        self.assertEqual(report["blockingCount"], 1)
        self.assertEqual(report["blockingOverfull"], [diagnostic])

    def test_non_output_routine_vbox_remains_blocking(self) -> None:
        diagnostic = r"Overfull \vbox (5.0pt too high) detected at line 10"
        report = classify_latex_diagnostics(diagnostic)
        self.assertEqual(report["blockingCount"], 1)
        self.assertEqual(report["blockingOverfull"], [diagnostic])

    def test_compile_passes_with_only_output_routine_vbox_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            tex = work / "book.tex"
            tex.write_text("test", encoding="utf-8")

            def runner(command: list[str], cwd: Path):
                (cwd / "book.pdf").write_bytes(b"%PDF-1.7\nsynthetic\n")
                return _completed(
                    command,
                    0,
                    stdout=(
                        r"Overfull \vbox (21.933pt too high) has occurred while \output is active"
                        + "\n"
                    ),
                )

            report = compile_unified_lualatex_stage160(
                tex, "lualatex", work, passes=2, runner=runner
            )
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["diagnostics"]["blockingCount"], 0)
            self.assertEqual(
                len(report["diagnostics"]["outputRoutineVboxes"]), 1
            )

    def test_compile_still_fails_on_material_overfull_hbox(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            tex = work / "book.tex"
            tex.write_text("test", encoding="utf-8")

            def runner(command: list[str], cwd: Path):
                (cwd / "book.pdf").write_bytes(b"%PDF-1.7\nsynthetic\n")
                return _completed(
                    command,
                    0,
                    stdout=(
                        r"Overfull \hbox (4.0pt too wide) in paragraph at lines 10--11"
                        + "\n"
                    ),
                )

            report = compile_unified_lualatex_stage160(
                tex, "lualatex", work, passes=2, runner=runner
            )
            self.assertEqual(report["status"], "FAIL", report)
            self.assertEqual(report["diagnostics"]["blockingCount"], 1)


if __name__ == "__main__":
    unittest.main()
