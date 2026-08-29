# Stage 160 — Unified LuaLaTeX Compilation

Status: **IMPLEMENTED — real-corpus proof required before acceptance**

Stage 160 performs the first single-document LuaLaTeX compilation of the complete Cybermancy Player Guide and Complete Rulebook.

It consumes only the body-complete, self-contained Stage 150 output. Stage 160 does not rebuild the Pandoc AST, alter any frozen chapter grammar, restage source content, or perform rendered-content regression. Rendered semantic and page-level regression remains Stage 170.

## Input authority

The default Stage 160 inputs are:

```text
build/rulebook/layout/integration/output/stage150/player-guide/
  Cybermancy_Player_Guide_Step6_Integrated.tex
  assets/

build/rulebook/layout/integration/output/stage150/complete-rulebook/
  Cybermancy_Complete_Rulebook_Step6_Integrated.tex
  assets/
```

Each profile also requires its successful Stage 150 proof report:

```text
build/rulebook/layout/integration/reports/
  player-guide-stage150-integrated-latex.json
  complete-rulebook-stage150-integrated-latex.json
```

Stage 160 refuses to compile a TeX file whose SHA-256 differs from the SHA recorded by the successful Stage 150 proof.

## Isolated compile root

Stage 160 does not compile directly inside the Stage 150 output tree. It creates an isolated compile root:

```text
build/rulebook/layout/integration/work/stage160/<profile>/
```

The exact Stage 150 TeX and complete `assets/` tree are copied into that root and verified by SHA-256 before compilation begins. This preserves Stage 150 as an immutable generated handoff while allowing LuaLaTeX to create `.aux`, `.log`, `.out`, and PDF files freely in the Stage 160 work directory.

The Stage 150 TeX and asset tree are hashed again after compilation. Any mutation fails Stage 160.

## Toolchain

Stage 160 uses the accepted Long-Form Prose runtime's Windows-aware tool resolver for:

- `lualatex` — required;
- `kpsewhich` — optional package preflight;
- `pdfinfo` — optional page-count reporting.

The same resolver already supports environment overrides, PATH, Windows App Paths, and normal MiKTeX installation locations.

## LaTeX package preflight

The integrated TeX is inspected for every `\usepackage{...}` dependency. If `kpsewhich` is available, Stage 160 verifies that each corresponding `.sty` file is resolvable before compilation.

A missing package fails closed with the exact package names. If `kpsewhich` is not available, this check is recorded as skipped and LuaLaTeX itself remains authoritative for dependency resolution.

## Graphics preflight

Every concrete graphics path in the integrated TeX must:

- be relative rather than absolute;
- remain inside the isolated compile root;
- resolve to an existing staged file.

Macro placeholders such as `\includegraphics{#1}` are ignored by this static check. Actual Stage 150 image paths are expected to resolve beneath `assets/`.

## Compilation contract

The default Stage 160 compile is two LuaLaTeX passes:

```text
lualatex
  -interaction=nonstopmode
  -halt-on-error
  -file-line-error
  <integrated-profile>.tex
```

Both passes execute from the isolated profile compile root. Their complete stdout/stderr streams are retained at:

```text
build/rulebook/layout/integration/work/stage160/<profile>/logs/
  lualatex-pass-1.txt
  lualatex-pass-2.txt
```

If LuaLaTeX returns nonzero, Stage 160 stops immediately and reports:

- failed pass number;
- command-log path;
- native `.log` path when present;
- the last compiler output lines;
- generated-TeX source context around the first file/line diagnostic when available.

The `--passes` option exists for diagnostic use and accepts 1–4 passes, but two passes are the production default.

## Blocking compiler diagnostics

A zero LuaLaTeX exit code is necessary but not sufficient for Stage 160 acceptance.

The following are blocking:

- any `Overfull \hbox`;
- any `Overfull \vbox`;
- any `Missing character:` diagnostic;
- failure to create a non-empty PDF.

This preserves the accepted Step 6 package-production policy that overflow and missing glyphs are not silently accepted merely because TeX returned success.

Underfull boxes are recorded in the detailed compiler diagnostics but do not block Stage 160.

Ordinary LaTeX, package, and font warnings are retained as non-blocking warnings for Stage 170 review. Stage 170 will decide whether any of those warnings correspond to rendered-output defects.

## Output

Successful Stage 160 PDFs are written to:

```text
build/rulebook/layout/integration/output/stage160/player-guide/
  Cybermancy_Player_Guide_Step6_Integrated.pdf

build/rulebook/layout/integration/output/stage160/complete-rulebook/
  Cybermancy_Complete_Rulebook_Step6_Integrated.pdf
```

The output is validated for:

- existence and nonzero size;
- PDF file signature;
- deterministic SHA-256 reporting.

Page count is reported when `pdfinfo` is available, with a binary fallback when practical. Stage 160 does **not** assert an expected page count; that is a rendered-regression concern for Stage 170.

## Fail-closed checks

The Stage 160 proof reports these principal gates:

```text
STAGE160_CONTRACT
STAGE150_INPUTS
STAGE150_PROVENANCE
STAGE160_LUALATEX_AVAILABLE
STAGE160_COMPILE_TREE
STAGE160_GRAPHICS_PREFLIGHT
STAGE160_TEX_DEPENDENCIES
STAGE160_LUALATEX
STAGE160_OVERFULL_BOXES
STAGE160_MISSING_CHARACTERS
STAGE160_MATERIAL_WARNINGS
STAGE160_PDF_OUTPUT
STAGE160_PAGE_COUNT
STAGE160_STAGE150_IMMUTABILITY
```

`STAGE160_MATERIAL_WARNINGS` and an unavailable page count may be warnings without making the stage fail. All other structural/compiler gates are blocking.

## Reports

```text
build/rulebook/layout/integration/reports/
  player-guide-stage160-lualatex.json
  complete-rulebook-stage160-lualatex.json
```

All Stage 160 work files, logs, and PDFs remain generated/noncanonical outputs.

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_lualatex.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-lualatex.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-lualatex.py --profile complete-rulebook --verbose
```

Both real-corpus profile compilations must pass before Stage 160 is accepted and before Stage 170 rendered-output regression begins.
