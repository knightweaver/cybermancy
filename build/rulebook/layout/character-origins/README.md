# Step 6 Character Origins — Outcome B Design Proof

**Status:** DRAFT  
**Scope:** Chapter 10 — Ancestories; Chapter 11 — Communities

This lane implements the approved **Outcome B: prose-derived entry grammar**. It inherits the frozen Long-Form Prose v1.0 publication shell and adds one compact Part III primitive: the **Character Option Entry**.

It is intentionally not frozen yet. Freeze requires an all-entry rendered regression and user visual acceptance.

## Source boundary

The builder consumes only the Step 4 publication corpus:

```text
build/rulebook/source/assembled/complete-rulebook.md
build/rulebook/source/assembled/player-guide.md
build/rulebook/source/assets/**
```

It does **not** read `docs/**`, Foundry JSON, generated MkDocs pages, or canonical source artwork directly. The Complete Rulebook and Player Guide representations of Chapters 10-11 must be byte-equivalent at the normalized chapter-fragment level before a build can pass.

Step 4's assembled-manuscript safety pass rewrites body `---` thematic breaks to `***` so Pandoc cannot confuse them with YAML delimiters. Character Origins accepts both `***` and `---` at its normalized-input boundary and emits `***` in temporary annotated Markdown.

## Character Option Entry grammar

Each normalized entry is derived from the existing horizontal-rule / image / H4 / prose / Feature structure. Step 6 does not invent or rewrite game content.

1. The entry artwork wraps on the left at 36% of the inherited prose column.
2. The H4 entry title and opening flavor text begin beside the artwork, aligned with its top, with an effective 4% horizontal gap.
3. When the opening flavor paragraph clears the bottom of the artwork, that same paragraph automatically expands back to the full inherited prose-column width. Additional flavor paragraphs use ordinary Long-Form Prose flow.
4. The renderer keeps enough vertical space for the artwork, entry heading, and opening wrapped lines, but does not box the complete first flavor paragraph into a fixed narrow identity row.
5. Ancestory `Features` and Community `Community Feature — <name>` markers are converted into layout-only Feature-group semantics in temporary build Markdown.
6. Feature names use the accepted Part III feature hierarchy; rules text retains inherited prose body typography.
7. Feature descriptions remain page/column breakable and return to ordinary full-column flow after the wrapped artwork has cleared.
8. Entry order, prose, mechanics, emphasis, artwork relationships, and source wording remain unchanged.
9. No entry-specific layout exceptions are permitted in v1.

The wrapped-art treatment is a Character Origins-only delta. The frozen Long-Form Prose v1.0 shell remains unchanged.

## Commands

From repository root:

```powershell
python build\rulebook\scripts\build-rulebook-character-origins.py inspect
python build\rulebook\scripts\build-rulebook-character-origins.py validate
python build\rulebook\scripts\build-rulebook-character-origins.py build
```

`inspect` performs corpus/profile validation without requiring Pandoc or LuaLaTeX. It must report exactly **18 Ancestories** and **9 Communities**, in the frozen source order encoded by the draft layout contract.

`validate` additionally preflights the existing Pandoc/LuaLaTeX toolchain and the Character Origins Lua filter.

`build` writes the regression PDF to:

```text
build/rulebook/layout/character-origins/output/
    Cybermancy_Chapters10_11_CharacterOrigins_Step6.pdf
```

The validation/inspection report is:

```text
build/rulebook/layout/character-origins/reports/
    character-origins-regression-v1.json
```

Temporary annotated Markdown, staged render assets, Pandoc fragments, generated TeX, and LuaLaTeX logs remain isolated under:

```text
build/rulebook/layout/character-origins/work/pandoc-lualatex-v1/
```

## Ownership boundary

This lane owns only:

```text
build/rulebook/layout/character-origins/**
build/rulebook/scripts/build-rulebook-character-origins.py
```

It must not modify the frozen Prose v1 contract, Step 4 normalized source, manifests, canonical Chapters 10-11, ClassPackage, DomainPackage, Equipment grammar, or unrelated build infrastructure.

## Current acceptance gate

The next required step is local regression:

1. run `inspect`;
2. run `build`;
3. inspect the generated Chapters 10-11 PDF across all 27 entries, with particular attention to wrapped artwork near column/page boundaries;
4. adjust only the Character Option Entry delta if necessary;
5. freeze v1 only after visual acceptance.
