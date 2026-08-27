# Step 6 DomainPackage semantic contract

This directory defines the **G.3 DomainPackage design proof** for Chapter 14, *Domains and Domain Cards*.

The current implementation is intentionally limited to **semantic composition and validation**. It does not yet define or render the final visual grammar. Maker is the default prototype fixture.

## Publication unit

Chapter 14 publishes Domain Cards as Domain-native packages rather than as one flat structured-family list:

```text
Chapter 14 — Domains and Domain Cards
    DomainPackage
        Domain identity
        Level 1
            Domain Cards
        Level 2
            Domain Cards
        ...
        Level 10
            Domain Cards
```

The Step 4 `domainPackages` structure is the authoritative publication grouping for Step 6. Step 6 does not reconstruct Domain membership from filesystem paths or Foundry folder hierarchy.

## Source boundary

DomainPackage consumes only the Step 4 normalized corpus:

```text
build/rulebook/source/metadata/structured-entities.json
build/rulebook/source/assets/...
```

It does **not** read:

- canonical Foundry JSON under `src/packs/...`;
- generated MkDocs pages under `docs/...`;
- Foundry folder names, hierarchy, colors, or UUIDs;
- Foundry runtime asset paths such as `modules/...` or `worlds/...`.

Foundry Domain folders remain a Step 4 validation cross-check only. Intrinsic Domain Card semantics normalized by Step 4 are authoritative.

## Step 4 contract consumed

The composer requires:

- sidecar schema `cybermancy-step4-structured-entities-v1.3`;
- Domain semantics schema `cybermancy-step4-domain-semantics-v1.0` with status `PASS`;
- a unique `domainPackages[]` row for the requested Domain;
- Domain identity `artwork.image` and `artwork.mask` staged below `build/rulebook/source/assets/`;
- every referenced card to resolve to family `domains`;
- card `publicationData` containing:
  - `domainKey`;
  - `level`;
  - `recallCost`;
  - `cardType`;
  - `inVault`;
  - normalized `description`;
  - staged `image`.

No Domain description is invented. The Domain identity view contains only normalized identity and artwork supplied by Step 4.

## DomainPackage view

The semantic composer emits:

```text
schema
chapter
title
domain
    key
    name
    artwork
        image
        mask
    cardCount
levels[]
    level
    cards[]
        semanticId
        name
        domainKey
        level
        recallCost
        cardType
        inVault
        description
        image
```

The current view schema is:

```text
cybermancy-step6-domain-package-view-v1.0
```

## Ordering contract

Step 4 owns deterministic card order:

```text
level → case-insensitive name → stable source ID
```

The DomainPackage composer validates that:

1. the package `cards` array follows this order;
2. `levels` are ascending;
3. flattening `levels[].cards` reproduces the package card order exactly;
4. every card appears exactly once;
5. each level bucket agrees with the card's normalized `publicationData.level`.

Step 6 does not silently reorder a malformed Step 4 package.

## Blocking validation

The semantic prototype fails closed on:

- unsupported Step 4 sidecar or Domain-semantics schema;
- Domain semantics status other than `PASS`;
- duplicate semantic IDs or duplicate DomainPackage keys;
- missing or wrong-family card references;
- package card-count mismatches;
- duplicate card membership;
- malformed/out-of-order level groups;
- level-bucket/card-level disagreement;
- card Domain mismatch;
- invalid Recall Cost, card type, or `inVault` semantics;
- missing normalized card description;
- unstaged or non-normalized Domain/card artwork;
- raw Foundry, MkDocs, or canonical source-tree references leaking into the Step 6 view.

## Maker prototype commands

Maker is selected by default in `domain-package-v1.json`.

```powershell
python build\rulebook\scripts\build-rulebook-domain-package.py inspect
python build\rulebook\scripts\build-rulebook-domain-package.py validate
```

Use `--verbose` anywhere to print the complete validation report. Another Domain can be selected with `--domain-key`.

The validation report defaults to:

```text
build/rulebook/layout/reports/domain-package-maker.json
```

## Current boundary

This milestone freezes the **DomainPackage semantic composition contract**, not the visual grammar.

The next implementation task is the Maker visual prototype: define the Chapter 14 Domain identity treatment, level dividers, page-breakable card-entry grammar, LuaLaTeX renderer, and rendered geometry/content regression. Only after Maker is visually accepted should the grammar be generalized to every Domain and later integrated into the full Chapter 14/Pandoc pipeline.
