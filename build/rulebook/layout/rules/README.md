# Cybermancy Rulebook Step 6 — Part II Rules Layout v1 Prototype

**Status:** PROTOTYPE  
**Scope:** Part II — Cybermancy Rules, Chapters 4–9  
**Design proof:** Chapters 4, 6, 8, and 9

This lane extends the accepted **Long-Form Prose Layout v1.0** rather than creating a separate publication stack. It uses the same Pandoc + LuaLaTeX engine, page geometry, typography, two-column body flow, chapter banners, source-order pagination, and staged Step 4 assets.

## Source contract

Primary normalized input:

```text
build/rulebook/source/assembled/player-guide.md
```

Cross-profile regression input:

```text
build/rulebook/source/assembled/complete-rulebook.md
```

Assets:

```text
build/rulebook/source/assets/**
```

The builder verifies that Chapters 4–9 exist in the player profile and, when the complete-rulebook profile is present, requires the normalized Part II chapter content to match between profiles.

Step 6 does not read canonical authored Markdown or Foundry data directly and does not rewrite rule text.

## Prototype grammar

The prototype adds only the approved rules-specific structures:

```text
Long-Form Prose v1.0
    + compact accented ordered-list procedures
    + full-width rules reference tables
    + neutral rules blockquotes
```

### Procedure

Ordered lists are treated consistently as compact rules sequences. The renderer does not inspect the words in the list to decide whether it is a procedure subtype.

### Rules Reference Table

Pandoc tables use the accepted full-width prose-table infrastructure with repeated-header longtable behavior. This lane does **not** use or depend on the Equipment Catalog primitive.

### Neutral rules blockquote

Part II blockquotes are not automatically interpreted as quotations, examples, formulas, warnings, or principles. They receive a restrained neutral treatment until explicit publication semantics justify subtype-specific rendering.

## Deliberately deferred semantics

The prototype must not infer these from source wording, filenames, or chapter-specific rules:

```text
rulesCallout.kind
imageRole = chapter-lead
stateTrack.label + stateTrack.states
```

Accordingly:

- Chapter 5–7 artwork remains in source order with inherited standard image treatment.
- Netrunning state tracks remain faithful source text rather than automatically generated horizontal widgets.
- Examples and principles compose from existing prose/list/table/blockquote structures.

If visual review demonstrates a material reader benefit, these become explicit Step 4 semantic proposals before richer Step 6 components are implemented.

## Design-proof corpus

The initial PDF renders:

```text
Part II opener
Chapter 4 — Cybermancy Frame Rules
Chapter 6 — Flashbacks
Chapter 8 — Driving and Chases
Chapter 9 — Netrunning and Device Intrusion
```

This combination tests the ordinary-prose baseline, source-order artwork, ordered procedures, nested rules, dense mechanical prose, decision/reference tables, numeric matrices, blockquotes, consequence tracks, Fear-spend tables, and quick-reference material.

Chapters 5 and 7 remain required in the normalized Part II corpus even though they are not included in this first design-proof PDF.

## Commands

From repository root:

```powershell
python build\rulebook\scripts\build-rulebook-rules.py validate
python build\rulebook\scripts\build-rulebook-rules.py build
```

The default command is `build`:

```powershell
python build\rulebook\scripts\build-rulebook-rules.py
```

Expected PDF:

```text
build/rulebook/layout/rules/output/
    Cybermancy_Part_II_Rules_Design_Proof_v1.pdf
```

Validation report:

```text
build/rulebook/layout/rules/reports/
    rules-design-proof-v1.json
```

Intermediate Markdown, Pandoc-generated LaTeX, staged raster conversions, and LuaLaTeX diagnostics are isolated beneath:

```text
build/rulebook/layout/rules/work/pandoc-lualatex-v1/
```

## Acceptance gate for the next phase

The prototype is ready for visual review when:

- the Rules Layout v1 prototype config validates;
- all Chapters 4–9 exist in the primary player profile;
- the complete-rulebook Part II corpus matches when that profile is available;
- Chapters 4, 6, 8, and 9 route into the proof;
- Step 4 contains no image/heading adjacency defects;
- Pandoc and LuaLaTeX complete successfully;
- no material clipping, overfull content, broken glyphs, or table failures remain;
- visual review confirms that procedures, tables, and neutral blockquotes are sufficiently distinct without over-componentizing the rules.

Only after that review should the contract be promoted from `PROTOTYPE` toward an accepted Part II Rules Layout v1.0.

## Ownership boundary

This lane owns:

```text
build/rulebook/layout/rules/**
build/rulebook/scripts/build-rulebook-rules.py
```

It does not modify:

```text
build/rulebook/layout/prose/**
build/rulebook/layout/equipment/**
build/rulebook/layout/classes/**
build/rulebook/layout/domains/**
build/rulebook/layout/ice/**
build/rulebook/scripts/rulebook_normalize/**
```
