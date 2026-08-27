# Step 6 DomainPackage prototype

This directory defines the **G.3 DomainPackage design proof** for Chapter 14, *Domains and Domain Cards*.

Maker is the default regression fixture. The semantic composition contract is accepted; the current milestone adds a **standalone visual prototype** so the publication grammar can be reviewed before it is generalized to Bullet/Circuit or integrated into the full Chapter 14/Pandoc pipeline.

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

It does **not** read canonical Foundry JSON, generated MkDocs pages, Foundry folder organization, or runtime asset paths. Foundry Domain folders remain a Step 4 validation cross-check only.

## Semantic view

The composer emits `cybermancy-step6-domain-package-view-v1.0`:

```text
domain
    key
    name
    artwork.image
    artwork.mask
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

Step 4 owns deterministic ordering: **level -> case-insensitive name -> stable source ID**. The composer validates package membership, level buckets, card count, ordering, Domain/Level agreement, normalized mechanics, staged artwork, and source-reference leakage.

No Domain description is invented.

## Provisional Maker visual grammar

The standalone renderer currently uses this review grammar:

1. A compact Domain identity opener contains the Chapter/Part label, Domain name, derived card/level count, and staged Domain PNG artwork.
2. The staged SVG mask remains part of the semantic identity contract but is not required for the first visual rendering pass.
3. Level groups are full-width semantic dividers in ascending order.
4. Cards flow in two balanced publication columns beneath each Level divider.
5. Each card entry keeps its image, name, Level, Recall Cost, optional `IN VAULT` marker, and rules text together when practical.
6. The default `ability` card classification is not repeated visually. The normalized `cardType` remains in the view model and is displayed only when a future card uses a non-default classification.
7. Card body text is 9 pt with 11.3 pt configured leading; card names are 12.4 pt. These are prototype values subject to visual review.
8. Level groups request enough remaining page space to avoid beginning a card pair immediately above a page break. A Level may still continue naturally onto the next page when its cards require more space.
9. No per-card special casing is permitted; the same renderer must eventually work for every DomainPackage.

This visual grammar is **not accepted/frozen yet**. Maker PDF review is the acceptance gate.

## Rendered regression

A successful `build` requires:

- LuaLaTeX compilation;
- no overfull `hbox` or `vbox` warnings;
- every card heading rendered exactly once;
- every Level heading rendered exactly once and in view order;
- each card heading associated with nearby Level/Recall Cost metadata;
- two distinct card-column start positions;
- configured body leading within tolerance when `pdftotext` can measure wrapped descriptions;
- no intermediate PDF page between the first and last card page with zero card headings.

If `pdftotext` is unavailable, geometry/content regression is reported as a warning rather than silently skipped.

## Maker commands

```powershell
python build\rulebook\scripts\build-rulebook-domain-package.py inspect
python build\rulebook\scripts\build-rulebook-domain-package.py validate
python build\rulebook\scripts\build-rulebook-domain-package.py build
```

Use `--verbose` anywhere for the complete report. `build --tex-only` writes the view model and LaTeX without invoking LuaLaTeX. Another Domain can be selected with `--domain-key`, but Maker remains the only visual-acceptance fixture at this stage.

Default prototype output:

```text
build/rulebook/layout/domain-package-prototype/
    maker-domain-package-view.json
    Cybermancy_Chapter14_Maker_DomainPackage_Step6.tex
    Cybermancy_Chapter14_Maker_DomainPackage_Step6.pdf
```

Validation report:

```text
build/rulebook/layout/reports/domain-package-maker.json
```

## Current boundary

The immediate acceptance task is **Maker visual review**. Do not generalize to all Domains and do not replace Chapter 14 in the full rulebook until the Maker grammar is visually accepted. Once accepted, freeze DomainPackage v1, add all-Domain regression, and only then perform Chapter 14/Pandoc integration.
