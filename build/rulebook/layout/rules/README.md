# Cybermancy Rulebook Step 6 — Part II Rules Layout v1.0

**Status:** ACCEPTED  
**Accepted:** 2026-08-28  
**Scope:** Part II — Cybermancy Rules, Chapters 4–9  
**Accepted proof:** Chapters 4, 6, 8, and 9

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

The accepted visual regression snapshot corresponds to repository commit:

```text
9800f925bae0e644b6fe4670ec2fb97a984a0128
```

## Accepted Rules grammar

```text
Long-Form Prose v1.0
    + suppressed normalized chapter-root heading
    + compact accented ordered-list procedures
    + full-width rules reference tables
    + neutral flowable rules blockquotes
    + compact standard source-order rules artwork
    + deterministic directional-arrow rendering
```

### Chapter root heading

Step 4 shifts an authored document-root H1 to normalized H3. Because Step 6 already renders the authoritative chapter title in the chapter banner, the first H3 in each chapter fragment is suppressed. Later H3 headings remain normal section headings. This is structural and does not compare or infer heading text.

### Procedure

Ordered lists are treated consistently as compact rules sequences. The renderer does not inspect the words in the list to decide whether it is a procedure subtype.

### Rules Reference Table

Pandoc tables use the accepted full-width prose-table infrastructure with repeated-header longtable behavior. This lane does **not** use or depend on the Equipment Catalog primitive.

### Neutral rules blockquote

Part II blockquotes are not automatically interpreted as quotations, examples, formulas, warnings, or principles. They receive a restrained, flowable treatment until explicit publication semantics justify subtype-specific rendering. The implementation deliberately avoids `Needspace` or list-based reservation that can create artificial blank pages around full-width tables.

### Standard rules artwork

Standard source-order images are centered within the current column and capped at `0.20\textheight`, preserving aspect ratio. This denser Part II treatment prevents ordinary artwork from creating unnecessary continuation pages. Explicit wide/mark/symbolic/portrait roles remain inherited from the prose lane.

### Directional arrows

Normalized directional arrows are preserved semantically and emitted as deterministic LaTeX math arrows so rendering does not depend on installed font glyph coverage.

## Deliberately deferred semantics

The accepted v1.0 lane must not infer these from source wording, filenames, or chapter-specific rules:

```text
rulesCallout.kind
imageRole = chapter-lead
stateTrack.label + stateTrack.states
```

Accordingly:

- Chapter 5–7 artwork remains in source order with the accepted compact standard-image treatment unless explicit image-role semantics are added.
- Netrunning state tracks remain faithful source text rather than automatically generated horizontal widgets.
- Examples and principles compose from existing prose/list/table/blockquote structures.

If future visual requirements justify richer treatment, these should become explicit Step 4 publication semantics before richer Step 6 components are implemented.

## Accepted proof corpus

The accepted PDF proof renders:

```text
Part II opener
Chapter 4 — Cybermancy Frame Rules
Chapter 6 — Flashbacks
Chapter 8 — Driving and Chases
Chapter 9 — Netrunning and Device Intrusion
```

This corpus validates ordinary rules prose, source-order artwork, ordered procedures, nested rules, dense mechanical prose, decision/reference tables, numeric matrices, mechanical blockquotes, consequence tracks, Fear-spend tables, and quick-reference material.

Chapters 5 and 7 remain required in the normalized Part II corpus even though they are not part of the accepted proof fixture.

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

Intermediate Markdown, Pandoc-generated LaTeX, staged raster conversions, and LuaLaTeX diagnostics remain isolated beneath:

```text
build/rulebook/layout/rules/work/pandoc-lualatex-v1/
```

## Accepted validation gate

The v1.0 contract requires:

- all Chapters 4–9 in the primary player profile;
- Part II profile equivalence against the complete rulebook when available;
- accepted proof Chapters 4, 6, 8, and 9 route correctly;
- no Step 4 image/heading adjacency defects;
- successful Pandoc and LuaLaTeX processing;
- no material clipping, broken glyphs, table failures, or artificial blank-page flow defects;
- successful visual review.

## Known upstream content issue

Chapter 4 still contains developmental/editorial residue and obvious prose errors. These are canonical-source issues and must be corrected upstream and propagated through Step 4; Step 6 must not patch them.

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
