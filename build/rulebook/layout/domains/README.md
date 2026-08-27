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
4. The accepted refinement prototype uses **three card columns** beneath each Level divider. Cards are partitioned into balanced contiguous column stacks so the first card in every active column begins at the same vertical origin.
5. The previous horizontal rule across the top of every card entry has been removed. The light bottom separator remains between successive card entries.
6. Card descriptions use the same first-line spacing fix accepted for Classes/Subclasses: the card identity row is explicitly terminated, then rules text begins in its own zero-`parskip`, zero-`parindent` paragraph group with explicit font leading. Normalized line/paragraph whitespace is collapsed into one publication paragraph before LaTeX rendering.
7. Each card entry keeps its image, name, Level, Recall Cost, optional `IN VAULT` marker, and the start of its rules text together when practical. Long rules text may continue naturally across a column/page boundary rather than producing an overfull card box.
8. The default `ability` card classification is not repeated visually. The normalized `cardType` remains in the view model and is displayed only when a future card uses a non-default classification.
9. Card body text is 9 pt with 11.3 pt configured leading; card names are 12 pt. These remain prototype values subject to visual review.
10. Level groups request enough remaining page space to avoid opening immediately above a page break. A Level may still continue naturally onto the next page when its cards require more space.
11. No per-card special casing is permitted; the same renderer must eventually work for every DomainPackage.

The three-column flow uses `paracol`, matching the page-breakable parallel-column approach already accepted for ClassPackage. A legacy two-column prototype mode remains available only for regression fixtures; the canonical Maker config is three columns.

This visual grammar is **not accepted/frozen yet**. Maker PDF review remains the acceptance gate.

## LuaLaTeX render assets

Step 4 currently stages many Domain Card illustrations as WebP. LuaLaTeX/`graphicx` does not directly consume WebP, so the DomainPackage builder performs the same kind of deterministic render-only conversion already used by the rulebook PDF pipeline:

- PNG/JPEG/PDF publication assets are consumed directly from the Step 4 staged tree;
- WebP/GIF/BMP/TIFF publication assets are converted to PNG;
- converted files are written only below the DomainPackage prototype render tree;
- Step 4 staged assets and canonical source assets are never modified;
- the composed DomainPackage view continues to contain the normalized Step 4 publication path rather than a render-specific path.

Derived Maker render assets are written beneath:

```text
build/rulebook/layout/domain-package-prototype/_render-assets/maker/
```

Raster conversion requires Pillow. If it is not installed, install it with:

```powershell
python -m pip install Pillow
```

The build report records direct, converted, missing, and unsupported render assets under `DOMAIN_PACKAGE_RENDER_ASSETS`.

## Rendered regression

A successful `build` requires:

- render-asset preparation to reconcile every publication image used by the visual prototype;
- LuaLaTeX compilation;
- no overfull `hbox` or `vbox` warnings;
- every card heading rendered exactly once;
- every Level heading rendered exactly once and in view order;
- each card heading associated with nearby Level/Recall Cost metadata;
- the configured three-column publication flow to produce the expected distinct column starts whenever enough cards are present;
- the first card in every active column for a Level to begin on the same page and within the configured top-alignment tolerance;
- the **first-to-second description baseline** to match configured body leading when `pdftotext` can measure it;
- no intermediate PDF page between the first and last card page with zero card headings.

If `pdftotext` is unavailable, geometry/content regression is reported as a warning rather than silently skipped.

## Maker commands

```powershell
python build\rulebook\scripts\build-rulebook-domain-package.py inspect
python build\rulebook\scripts\build-rulebook-domain-package.py validate
python build\rulebook\scripts\build-rulebook-domain-package.py build
```

Use `--verbose` anywhere for the complete report. `build --tex-only` prepares render assets and writes the view model and LaTeX without invoking LuaLaTeX. Another Domain can be selected with `--domain-key`, but Maker remains the only visual-acceptance fixture at this stage.

Default prototype output:

```text
build/rulebook/layout/domain-package-prototype/
    maker-domain-package-view.json
    Cybermancy_Chapter14_Maker_DomainPackage_Step6.tex
    Cybermancy_Chapter14_Maker_DomainPackage_Step6.pdf
    _render-assets/
        maker/
```

Validation report:

```text
build/rulebook/layout/reports/domain-package-maker.json
```

## Current boundary

The immediate acceptance task is **Maker visual review**. Do not generalize to all Domains and do not replace Chapter 14 in the full rulebook until the Maker grammar is visually accepted. Once accepted, freeze DomainPackage v1, add all-Domain regression, and only then perform Chapter 14/Pandoc integration.