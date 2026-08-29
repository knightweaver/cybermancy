from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.unified_lualatex import (
    STAGE_ORDER,
    apply_compile_compatibility_overlay,
    compile_unified_lualatex,
    contract_stage,
    extract_usepackages,
    parse_latex_diagnostics,
    prepare_compile_tree,
    probe_tex_packages,
    sha256_file,
    sha256_tree,
    static_graphics_references,
    validate_static_graphics,
)

CONTRACT_PATH = RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"


def _completed(command: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


class Stage160ContractTests(unittest.TestCase):
    def test_contract_places_lualatex_at_order_160(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        stage = contract_stage(contract)
        self.assertIsNotNone(stage)
        self.assertEqual(stage["stage"], "lualatex")
        self.assertEqual(int(stage["order"]), STAGE_ORDER)


class Stage160CompileTreeTests(unittest.TestCase):
    def test_prepare_compile_tree_verifies_exact_copy_before_compile_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "stage150"
            source.mkdir()
            tex = source / "book.tex"
            original = "\\documentclass{article}\n\\begin{document}x\\end{document}\n"
            tex.write_text(original, encoding="utf-8")
            assets = source / "assets"
            nested = assets / "nested"
            nested.mkdir(parents=True)
            (assets / "one.png").write_bytes(b"one")
            (nested / "two.jpg").write_bytes(b"two")

            work = root / "stage160-work"
            result = prepare_compile_tree(tex, assets, work)

            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["sourceTexSha256"], result["copiedTexSha256"])
            self.assertNotEqual(result["sourceTexSha256"], result["compileTexSha256"])
            self.assertEqual(result["sourceAssetsSha256"], result["compileAssetsSha256"])
            self.assertEqual(result["assetCount"], 2)
            self.assertEqual(tex.read_text(encoding="utf-8"), original)
            self.assertIn(r"\hfuzz=0.2pt", (work / "book.tex").read_text(encoding="utf-8"))
            self.assertEqual(sha256_tree(assets)[0], sha256_tree(work / "assets")[0])
            self.assertEqual(result["compatibilityOverlay"]["status"], "PASS")

    def test_compile_overlay_adds_strikeout_support_anchors_footer_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tex = Path(td) / "book.tex"
            tex.write_text(
                "\n".join(
                    [
                        r"\documentclass{article}",
                        r"\usepackage[hidelinks]{hyperref}",
                        r"\fancyfoot[L]{\sffamily\fontsize{7.0}{8.5}\selectfont\color{CMTeal}STEP 6 // COMPLETE RULEBOOK // INTEGRATED}",
                        r"\begin{document}",
                        r"\st{1. \textbf{World Foundations}}",
                        r"\end{document}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            first = apply_compile_compatibility_overlay(tex)
            rendered = tex.read_text(encoding="utf-8")
            second = apply_compile_compatibility_overlay(tex)

            self.assertEqual(first["status"], "PASS", first)
            self.assertEqual(
                first["patches"],
                [
                    "pandoc-strikeout-soul",
                    "hfuzz-0.2pt",
                    "profile-footer-zero-width-anchor",
                ],
            )
            self.assertIn(r"\usepackage{soul}", rendered)
            self.assertIn(r"\hfuzz=0.2pt", rendered)
            self.assertIn(r"\fancyfoot[L]{\rlap{", rendered)
            self.assertEqual(second["status"], "PASS", second)
            self.assertEqual(second["patches"], [])


class Stage160GraphicsPreflightTests(unittest.TestCase):
    def test_static_graphics_ignores_macro_placeholders_and_requires_compile_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assets = root / "assets"
            assets.mkdir()
            (assets / "present.png").write_bytes(b"image")
            tex = "\n".join(
                [
                    r"\newcommand{\CMImage}[1]{\includegraphics{#1}}",
                    r"\includegraphics{assets/present.png}",
                    r"\CMImage{\detokenize{assets/present.png}}",
                ]
            )
            refs = static_graphics_references(tex)
            self.assertEqual(refs, ["assets/present.png"])
            report = validate_static_graphics(tex, root)
            self.assertEqual(report["status"], "PASS", report)

    def test_static_graphics_rejects_missing_and_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = "\n".join(
                [
                    r"\includegraphics{assets/missing.png}",
                    r"\includegraphics{C:/outside/absolute.png}",
                ]
            )
            report = validate_static_graphics(tex, root)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("assets/missing.png", report["missing"])
            self.assertIn("C:/outside/absolute.png", report["absolute"])


class Stage160PackageProbeTests(unittest.TestCase):
    def test_extracts_multi_package_usepackage_contract(self) -> None:
        tex = "\n".join(
            [
                r"\usepackage{fontspec}",
                r"\usepackage[table]{xcolor}",
                r"\usepackage{array,booktabs}",
            ]
        )
        self.assertEqual(extract_usepackages(tex), ["array", "booktabs", "fontspec", "xcolor"])

    def test_kpsewhich_probe_reports_missing_package(self) -> None:
        def runner(command: list[str], cwd: Path):
            target = command[-1]
            if target == "missing.sty":
                return _completed(command, 1)
            return _completed(command, 0, stdout=f"/tex/{target}\n")

        tex = r"\usepackage{fontspec,missing}"
        with tempfile.TemporaryDirectory() as td:
            report = probe_tex_packages(tex, "kpsewhich", Path(td), runner=runner)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["missing"], ["missing"])
        self.assertIn("fontspec", report["resolved"])

    def test_package_probe_is_nonblocking_when_kpsewhich_unavailable(self) -> None:
        report = probe_tex_packages(r"\usepackage{fontspec}", None, Path("."))
        self.assertEqual(report["status"], "SKIPPED")
        self.assertEqual(report["packages"], ["fontspec"])


class Stage160DiagnosticsTests(unittest.TestCase):
    def test_material_diagnostics_are_classified(self) -> None:
        text = "\n".join(
            [
                "Overfull \\hbox (1.0pt too wide) in paragraph at lines 1--2",
                "Underfull \\vbox (badness 10000) has occurred while \\output is active",
                "Missing character: There is no → (U+2192) in font Test!",
                "LaTeX Warning: Label(s) may have changed.",
                "Package hyperref Warning: Token not allowed in a PDF string",
                "LaTeX Font Warning: Font shape unavailable",
            ]
        )
        report = parse_latex_diagnostics(text)
        self.assertEqual(len(report["overfull"]), 1)
        self.assertEqual(len(report["underfull"]), 1)
        self.assertEqual(len(report["missingCharacters"]), 1)
        self.assertEqual(report["blockingCount"], 2)


class Stage160CompileTests(unittest.TestCase):
    def test_two_pass_compile_produces_pdf_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            tex = work / "book.tex"
            tex.write_text("test", encoding="utf-8")
            invocations: list[list[str]] = []

            def runner(command: list[str], cwd: Path):
                invocations.append(command)
                (cwd / "book.pdf").write_bytes(b"%PDF-1.7\nsynthetic\n")
                return _completed(command, 0, stdout="Output written on book.pdf (2 pages).\n")

            report = compile_unified_lualatex(tex, "lualatex", work, passes=2, runner=runner)
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["passesCompleted"], 2)
            self.assertEqual(len(invocations), 2)
            self.assertTrue((work / "logs" / "lualatex-pass-1.txt").is_file())
            self.assertTrue((work / "logs" / "lualatex-pass-2.txt").is_file())
            self.assertTrue((work / "book.pdf").is_file())

    def test_compile_fails_closed_on_first_pass_error_with_fatal_tex_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            tex = work / "book.tex"
            tex.write_text("line one\nline two\nline three\n", encoding="utf-8")

            def runner(command: list[str], cwd: Path):
                return _completed(
                    command,
                    1,
                    stdout=(
                        "book.tex:2: Infinite glue shrinkage found in box being split\n"
                        "book.tex:3: Undefined control sequence.\n"
                        "l.3 line three\n"
                    ),
                )

            report = compile_unified_lualatex(tex, "lualatex", work, passes=2, runner=runner)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failedPass"], 1)
            self.assertIn("line three", report["passReports"][0]["texContext"])
            self.assertIn(">>     3:", report["passReports"][0]["texContext"])

    def test_compile_fails_closed_on_overfull_output_even_when_lualatex_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            tex = work / "book.tex"
            tex.write_text("\n".join(f"line {n}" for n in range(1, 13)) + "\n", encoding="utf-8")

            def runner(command: list[str], cwd: Path):
                (cwd / "book.pdf").write_bytes(b"%PDF-1.7\nsynthetic\n")
                return _completed(
                    command,
                    0,
                    stdout="Overfull \\hbox (4.0pt too wide) in paragraph at lines 10--11\n",
                )

            report = compile_unified_lualatex(tex, "lualatex", work, passes=2, runner=runner)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["diagnostics"]["blockingCount"], 1)
            self.assertEqual(report["blockingContexts"][0]["line"], 10)
            self.assertIn("line 10", report["blockingContexts"][0]["texContext"])


if __name__ == "__main__":
    unittest.main()
