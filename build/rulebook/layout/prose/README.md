# Cybermancy Rulebook Step 6 - Long-Form Prose Layout v1.0

**Status:** ACCEPTED  
**Accepted:** 2026-08-27  
**Scope:** Part I - The World of Cybermancy; Part V - GM World Guide

This contract freezes the approved long-form prose grammar. The accepted production implementation is **build-rulebook-prose.py v1.0.5**, using the same PDF toolchain as the rest of the Cybermancy rulebook: **Pandoc + LuaLaTeX**.

## Source contract

Production input is exclusively the Step 4 publication corpus and staged assets:

```text
build/rulebook/source/assembled/complete-rulebook.md
build/rulebook/source/assets/**
```

The prose renderer does not independently re-read Foundry packs or generated MkDocs pages when Step 4 already represents the publication content.

## Accepted publication grammar

- US Letter.
- Light, print-friendly body pages.
- Two-column body prose with a 0.24 in gutter.
- Arial 10.3 pt / 14.2 pt body typography.
- Ragged-right (left-aligned) paragraph text throughout prose and structured publication bodies.
- Arial display hierarchy.
- Standalone dark Part openers.
- Full-width dark chapter title bands.
- H3-H5 restrained editorial hierarchy.
- Full-width prose tables outside the two-column flow.
- Wide artwork may span both columns; ordinary artwork remains column-width.
- All semantic quotation prose is italic; attribution remains roman.
- Part V uses the same light reading pages with a restrained violet `GM MATERIAL` marker.

The normative settings remain in:

```text
build/rulebook/layout/prose/prose-layout-v1.json
```

### Body-alignment authority

`typography.bodyAlignment` is the publication authority for ordinary paragraph alignment. The accepted value is `ragged-right`. Standalone and integrated renderers apply that policy at body or family scope so normal prose, class/subclass text, Chapter 14 Domain Card descriptions, equipment descriptions, ICE rules text, and encounter rules text retain a left edge without full justification.

The policy does **not** override explicit display alignment. Centered identity/stat cells, centered art, title treatments, table-column alignment, numeric roles, and deliberately right-aligned display elements remain explicit in their own publication grammars.

## Production renderer

The production renderer is:

```text
build/rulebook/scripts/build-rulebook-prose.py
```

with the prose-specific Pandoc filter:

```text
build/rulebook/layout/prose/pandoc/prose.lua
```

Pipeline:

```text
Step 4 complete-rulebook.md
        |
        v
Python: select Parts I and V + resolve staged assets
        |
        v
Pandoc Markdown -> LaTeX
        |
        v
prose.lua semantic layout transforms
        |
        v
LuaLaTeX
        |
        v
Cybermancy_Parts_I_V_Prose_Regression_v1.pdf
```

### Required toolchain

This lane intentionally introduces no separate PDF rendering stack. It relies on the same local software already required by Steps 5-6:

```text
Python
Pandoc
LuaLaTeX / existing TeX distribution
Pillow only when WebP/GIF/BMP/TIFF staged images require conversion
```

The renderer does **not** require:

```text
WeasyPrint
MSYS2
GTK
Pango
GLib
```

### Invocation

From repository root:

```powershell
python build\rulebook\scripts\build-rulebook-prose.py
```

Validation only:

```powershell
python build\rulebook\scripts\build-rulebook-prose.py validate
```

Explicit build:

```powershell
python build\rulebook\scripts\build-rulebook-prose.py build
```

Expected output:

```text
build/rulebook/layout/prose/output/
    Cybermancy_Parts_I_V_Prose_Regression_v1.pdf
```

Validation report:

```text
build/rulebook/layout/prose/reports/
    prose-regression-v1.json
```

Intermediate Markdown, Pandoc-generated LaTeX, converted raster assets, and LuaLaTeX logs are isolated beneath:

```text
build/rulebook/layout/prose/work/pandoc-lualatex-v1/
```

## Asset behavior

The renderer resolves normalized image paths against:

```text
build/rulebook/source/assets/**
```

Every resolved publication asset is staged beneath the prose work directory using a content-addressed, whitespace-safe filename before Pandoc runs. PNG/JPEG/PDF files are copied into that staging tree; WebP/GIF/BMP/TIFF assets are deterministically converted to PNG with Pillow. Temporary Markdown therefore references only relative `assets/...` paths and never leaks host-specific absolute paths into Pandoc/LaTeX.

If an asset is absent, the regression build remains fail-visible by rendering a labeled staged-asset placeholder and recording an `ASSETS` warning. A production image-QA build should resolve all assets.

## Normalization boundary

The renderer preserves source prose and source order. It does not editorially correct known content defects.

Image/heading Markdown block boundaries are owned by Step 4. The prose builder does **not** repair them. It validates the assembled Step 4 source line-by-line and fails closed if a standalone image is immediately followed by an ATX heading without an intervening blank line. Step 4 now validates this same invariant at its assembled-output boundary.

## Full regression scope

```text
Part I
  Chapter 1  Welcome to Cybermancy
  Chapter 2  The Resonance Cascade
  Chapter 3  Megacorporations

Part V
  Chapter 24 Project Helios and the Hidden History
  Chapter 25 The Council
  Chapter 26 The Cabal
  Chapter 27 Cabal Projects
  Chapter 28 The Chessboard
  Chapter 29 The Resonance: GM Interpretation
```

Known editorial/source defects remain report-only and must not be silently rewritten by Step 6. The earlier Chapter 29 duplicate `Tone and Themes` defect was resolved upstream in Step 4 section selection.

## Ownership boundary

This lane owns only prose-specific files:

```text
build/rulebook/layout/prose/**
build/rulebook/scripts/build-rulebook-prose.py
```

It does not modify Equipment, Classes, manifests, normalized source, canonical content, or shared Step 6 dispatch infrastructure.

## Implementation patch 1.0.1 — Windows-safe asset staging

The frozen Prose Layout contract remains **v1.0**. Builder patch 1.0.1 changes only temporary asset handling.

The original Pandoc/LuaLaTeX implementation emitted resolved absolute image paths into temporary Markdown. On Windows, a repository path containing spaces (for example `.../Cybermancy module development/...`) could cause Pandoc to split an image destination at the first space. The resulting LaTeX contained a truncated `\CM*Image{\detokenize{...}}` argument and LuaLaTeX failed with `File ended while scanning use of \CMMarkImage`.

Patch 1.0.1 now stages **every** resolved image into:

```text
build/rulebook/layout/prose/work/pandoc-lualatex-v1/assets/
```

using a content-addressed, whitespace-free filename. Temporary Markdown and generated LaTeX reference only relative `assets/...` paths. Unsupported raster formats are still converted to PNG with Pillow. No reader-facing layout or source content changes.

## Runtime compatibility patch 1.0.2

The production renderer remains **Pandoc → prose Lua filter → LuaLaTeX**.

Pandoc 3.8+ may emit `\def\LTcaptype{none}` for uncaptioned `longtable`
output. Recent `longtable` implementations then require a LaTeX counter named
`none`. The prose document preamble defines that counter defensively and only
when it does not already exist. This is a renderer compatibility shim; it does
not alter the frozen Prose Layout v1.0 design contract or table content.

The builder also preserves additional diagnostics under:

`build/rulebook/layout/prose/work/pandoc-lualatex-v1/logs/`

On LuaLaTeX failure the report now includes the failing pass, generated `.tex`
path, native `.log` path, and generated-TeX context around the reported line.

## Accepted implementation baseline — v1.0.5

The layout contract remains **v1.0**. The accepted renderer implementation is **v1.0.5** and incorporates the following production hardening without changing the frozen visual grammar:

- **v1.0.1 — Windows-safe asset staging:** all assets are staged to whitespace-safe relative paths before Pandoc conversion.
- **v1.0.2 — Pandoc/longtable compatibility and diagnostics:** guards Pandoc 3.8+ uncaptioned longtables and preserves detailed LuaLaTeX failure context.
- **v1.0.3 — strict Step 4 boundary ownership:** Step 6 no longer repairs image/heading boundaries and removes obsolete WeasyPrint-era HTML regression artifacts.
- **v1.0.4 — Windows tool resolution:** resolves Pandoc/LuaLaTeX through PATH and normal Windows installation locations, including Pandoc App Paths.
- **v1.0.5 — linewise boundary validation:** detects only physically adjacent image/heading lines; blank lines are no longer consumed by multiline whitespace matching.

The accepted production command remains:

```powershell
python build\rulebook\scripts\build-rulebook-prose.py
```
