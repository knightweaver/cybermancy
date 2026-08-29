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

Stage 160 refuses to accept a Stage 150 TeX handoff whose SHA-256 differs from the SHA recorded by the successful Stage 150 proof.

## Isolated compile root

Stage 160 does not compile directly inside the Stage 150 output tree. It creates an isolated compile root:

```text
build/rulebook/layout/integration/work/stage160/<profile>/
```

The exact Stage 150 TeX and complete `assets/` tree are copied into that root and verified by SHA-256 before any compiler-specific compatibility handling occurs. This preserves Stage 150 as an immutable generated handoff while allowing LuaLaTeX to create `.aux`, `.log`, `.out`, and PDF files freely in the Stage 160 work directory.

The Stage 150 TeX and asset tree are hashed again after compilation. Any mutation of the Stage 150 source handoff fails Stage 160.

## Stage 160 compile compatibility overlay

The first real unified compilations exposed three issues that do not change rulebook content or any frozen chapter grammar but do affect the LuaLaTeX compile copy:

1. The Complete Rulebook body contains Pandoc strikeout output using `\st{...}`. The standalone Prose-derived shell did not include Pandoc's normal strikeout dependency, causing an `Undefined control sequence` failure. When the generated body actually uses `\st`, Stage 160 now adds `\usepackage{soul}` to the isolated compile copy before package preflight.
2. The Stage 150 profile footer is a long left `fancyhdr` field. In the integrated geometry lanes it generated a large false field-width overrun even though the footer text itself is short enough to render safely. Stage 160 anchors that left footer with `\rlap{...}` in the isolated compile copy so it no longer contributes spurious width to the `fancyhdr` alignment box.
3. Five shared package boxes produced numerical overfull diagnostics between approximately 0.10 and 0.12 pt. These are sub-hairline TeX rounding artifacts rather than materially out-of-bounds content. The isolated compile copy therefore sets `\hfuzz=0.2pt`. Any overfull box larger than 0.2 pt is still emitted by TeX and remains fully blocking.

This compatibility overlay is deterministic and idempotent. Its patch names and before/after compile-copy SHA-256 values are recorded beneath `compileTree.compatibilityOverlay` in the Stage 160 report.

The overlay applies **only** to the isolated Stage 160 compile copy. It never edits the accepted Stage 150 TeX, staged assets, Stage 140 AST, canonical rulebook content, or frozen package implementations.

## Toolchain

Stage 160 uses the accepted Long-Form Prose runtime's Windows-aware tool resolver for:

- `lualatex` — required;
- `kpsewhich` — optional package preflight;
- `pdfinfo` — optional page-count reporting.

The same resolver already supports environment overrides, PATH, Windows App Paths, and normal MiKTeX installation locations.

## LaTeX package preflight

The compile-copy TeX is inspected for every `\usepackage{...}` dependency after the compatibility overlay is applied. If `kpsewhich` is available, Stage 160 verifies that each corresponding `.sty` file is resolvable before compilation.

This means `soul.sty` is required only for a profile whose body actually contains Pandoc strikeout output.

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
- generated-TeX source context around the most relevant fatal file/line diagnostic when available.

When LuaLaTeX exits successfully but Stage 160 blocks on an overfull diagnostic, the report also includes `blockingContexts` with generated-TeX context for each unique reported overfull line. This avoids requiring another diagnostic build simply to identify the corresponding generated source.

The `--passes` option exists for diagnostic use and accepts 1–4 passes, but two passes are the production default.

## Blocking compiler diagnostics

A zero LuaLaTeX exit code is necessary but not sufficient for Stage 160 acceptance.

The following are blocking:

- every `Overfull \hbox` or `Overfull \vbox` that LuaLaTeX emits after the explicit `\hfuzz=0.2pt` numerical tolerance;
- any `Missing character:` diagnostic;
- failure to create a non-empty PDF.

Thus Stage 160 still fails closed on material overflow. The 0.2 pt `\hfuzz` setting exists only to prevent sub-hairline engine rounding noise from masquerading as a visible layout defect.

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

All Stage 160 work files, logs, compatibility-overlaid compile copies, and PDFs remain generated/noncanonical outputs.

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_lualatex.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-lualatex.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-lualatex.py --profile complete-rulebook --verbose
```

The existing accepted Stage 150 outputs do not need to be regenerated for this correction because the compatibility changes are applied only after Stage 150 provenance is verified in the isolated Stage 160 compile root.

Both real-corpus profile compilations must pass before Stage 160 is accepted and before Stage 170 rendered-output regression begins.
