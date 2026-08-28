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

## Character Option Entry grammar

Each normalized entry is derived from the existing horizontal-rule / image / H4 / prose / Feature structure. Step 6 does not invent or rewrite game content.

1. The entry artwork, H4 entry title, and first flavor paragraph form one non-breaking identity row.
2. Artwork occupies 36% of the inherited prose column; identity text occupies 60%, with a 4% gap.
3. Additional flavor paragraphs return to ordinary Long-Form Prose flow beneath the identity row.
4. Ancestory `Features` and Community `Community Feature — <name>` markers are converted into layout-only Feature-group semantics in temporary build Markdown.
5. Feature names use the accepted Part III feature hierarchy; rules text retains inherited prose body typography.
6. Feature descriptions remain page/column breakable. Only the identity row is boxed together.
7. Entry order, prose, mechanics, emphasis, artwork relationships, and source wording remain unchanged.
8. No entry-specific layout exceptions are permitted in v1.

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
3. inspect the generated Chapters 10-11 PDF across all 27 entries;
4. adjust only the Character Option Entry delta if necessary;
5. freeze v1 only after visual acceptance.
