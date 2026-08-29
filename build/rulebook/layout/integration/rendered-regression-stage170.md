# Stage 170 — Rendered-Output Regression

Status: **IMPLEMENTED — real-corpus proof required before acceptance**

Stage 170 is the final Step 6 integration gate. It does not rebuild the AST, regenerate LaTeX, or recompile the rulebook. It consumes only a **PASS Stage 160 PDF** and verifies the rendered publication artifact itself before publishing an exact validated copy at the deterministic Stage 170 output path.

Stage 160 is accepted after both Player Guide and Complete Rulebook unit/integration suites and real-corpus unified LuaLaTeX profiles passed locally.

## Input authority

The default inputs are:

```text
build/rulebook/layout/integration/output/stage160/player-guide/
  Cybermancy_Player_Guide_Step6_Integrated.pdf

build/rulebook/layout/integration/output/stage160/complete-rulebook/
  Cybermancy_Complete_Rulebook_Step6_Integrated.pdf
```

with the corresponding PASS Stage 160 reports:

```text
build/rulebook/layout/integration/reports/
  player-guide-stage160-lualatex.json
  complete-rulebook-stage160-lualatex.json
```

Stage 170 fails closed unless the PDF SHA-256 exactly matches the PDF SHA recorded by its Stage 160 proof report.

## Toolchain

Stage 170 reuses the existing Windows-aware Step 6 tool resolver.

Required:

- `pdfinfo` — page count and page-size metadata;
- `pdftotext` — page-preserving text extraction and rendered word bounding boxes.

Optional:

- `pdftoppm` — rasterized structural-anchor previews for human spot review.

No new external runtime is introduced by Stage 170. These tools are part of the PDF/Poppler surface already used by the existing rulebook build environment.

## Rendered regression contract

Stage 170 validates four independent aspects of the actual PDF.

### 1. PDF/page integrity

`pdfinfo`, `pdftotext -layout`, and `pdftotext -bbox-layout` must all agree on the page count.

Every page must be US Letter (`612 × 792 pt`) within a one-point renderer tolerance.

### 2. Rendered text containment

`pdftotext -bbox-layout` provides page-relative word bounding boxes. Every extracted word must remain inside its page rectangle within a 0.5-point numerical tolerance.

Words within 2 points of a physical page edge are recorded as `STAGE170_EDGE_TEXT` warnings for visual spot review. Text actually outside the page is blocking.

This closes the principal rendered-risk left by Stage 160: a successful TeX compile can still produce content outside the physical page even when the source compiler does not report a line-addressable error.

### 3. Rendered publication architecture

The extracted rendered text must preserve the accepted whole-book architecture:

- all profile-applicable Parts are present and ordered;
- all profile-applicable Chapters are present and ordered;
- Chapter 13 is absent;
- the Player Guide contains no Chapters 23–32 and no GM spoiler divider;
- the Complete Rulebook contains exactly one `GM MATERIAL — SPOILERS BEYOND THIS POINT` boundary between Chapters 22 and 23;
- the generated Step 4 publication-provenance residue removed by Stage 160 does not appear in the final rendered PDF.

The chapter titles and profile chapter membership remain sourced from `step6-integration-v1.json`; Part identity remains sourced from the accepted Step 3/Stage 130 Part map.

### 4. Stage 160 deferred output-routine vboxes

Stage 160 deliberately preserves TeX diagnostics of the form:

```text
Overfull \vbox (...) while \output is active
```

as Stage 170 inputs rather than suppressing them or treating them as equivalent to line-addressable material overflow.

Stage 170 reconciles those diagnostics against the rendered PDF by requiring:

- correct physical page geometry; and
- no rendered text bounding box outside the page.

The original diagnostics remain in the Stage 170 report for traceability.

## Structural-anchor previews

When `pdftoppm` is available, Stage 170 also rasterizes the first rendered page located for every Part, every Chapter, and the Complete Rulebook GM divider at 72 dpi by default.

These PNGs are diagnostic/noncanonical artifacts under:

```text
build/rulebook/layout/integration/work/stage170/<profile>/previews/
```

They provide a compact visual spot-review set for publication boundaries without making manual review of every page a prerequisite for the deterministic automated gate. If `pdftoppm` is unavailable, preview generation is recorded as a warning; the authoritative text/bbox checks still run.

## Generated diagnostic outputs

Each Stage 170 work root contains:

```text
build/rulebook/layout/integration/work/stage170/<profile>/
  <profile>-layout.txt
  <profile>-bbox.html
  previews/
```

These are generated/noncanonical inspection artifacts.

## Final validated artifacts

Only after every blocking Stage 170 check passes does the driver publish an exact byte-for-byte copy of the accepted Stage 160 PDF:

```text
build/rulebook/layout/integration/output/stage170/player-guide/
  Cybermancy_Player_Guide_Step6.pdf

build/rulebook/layout/integration/output/stage170/complete-rulebook/
  Cybermancy_Complete_Rulebook_Step6.pdf
```

The Stage 160 source PDF is re-hashed after all inspection work and must remain byte-stable. The Stage 170 final PDF must have the same SHA-256 as the Stage 160 input.

## Fail-closed checks

The principal Stage 170 checks are:

```text
STAGE170_CONTRACT
STAGE160_INPUTS
STAGE160_PDF_PROVENANCE
STAGE170_TOOLCHAIN
STAGE170_PDFINFO
STAGE170_LAYOUT_TEXT
STAGE170_BBOX_EXTRACTION
STAGE170_PAGE_COUNT_CONSISTENCY
STAGE170_PAGE_GEOMETRY
STAGE170_RENDERED_TEXT_BOUNDS
STAGE170_EDGE_TEXT
STAGE170_RENDERED_STRUCTURE
STAGE170_DEFERRED_VBOX_GEOMETRY
STAGE170_ANCHOR_PREVIEWS
STAGE170_STAGE160_IMMUTABILITY
STAGE170_FINAL_PDF
```

`STAGE170_EDGE_TEXT` is a warning when applicable. `STAGE170_ANCHOR_PREVIEWS` is a warning only when the optional `pdftoppm` tool is unavailable; an available tool that fails to rasterize requested anchors is treated as an error. All other checks above are blocking.

## Reports

```text
build/rulebook/layout/integration/reports/
  player-guide-stage170-rendered-regression.json
  complete-rulebook-stage170-rendered-regression.json
```

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_rendered_regression.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-rendered-regression.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-rendered-regression.py --profile complete-rulebook --verbose
```

Both real-corpus profile proofs must pass before Stage 170 is accepted. Because Stage 170 is order 170, acceptance of both rendered profiles completes the frozen Step 6 integration pipeline unless the rendered diagnostics expose a specific defect that must be corrected and reproven.
