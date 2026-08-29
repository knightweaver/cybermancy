# Step 6 DomainPackage v1

This directory contains the **accepted and frozen Chapter 14 publication grammar** for *Domains and Domain Cards*.

DomainPackage v1 was established using Maker as the design-proof fixture, then applied without Domain-specific or card-specific layout exceptions to the complete current Domain corpus. The final all-Domain regression passed for **3 Domains / 73 Domain Cards**, and the resulting Bullet, Circuit, and Maker PDFs were visually accepted on 2026-08-27.

## Freeze status

`domain-package-v1.json` is the frozen DomainPackage v1 publication contract. Its lifecycle metadata records:

- version `v1.0`;
- status `frozen`;
- all-Domain regression `PASS`;
- visual review `ACCEPTED`;
- acceptance corpus: 3 Domains / 73 Domain Cards.

Future changes to the DomainPackage grammar should be intentional versioned changes rather than silent edits to the accepted v1 behavior.

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

Generated DomainPackage PDFs, TeX files, view models, converted render assets, and validation reports are reproducible outputs. They are not canonical game-content inputs.

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

## Accepted DomainPackage visual grammar

1. A compact Domain identity opener contains the Chapter/Part label, Domain name, derived card/level count, and staged Domain PNG artwork.
2. The staged SVG mask remains part of the semantic identity contract but is not required for the v1 rendering grammar.
3. Level groups are full-width semantic dividers in ascending order.
4. Cards render in **three columns** beneath each Level divider. Cards are partitioned into balanced contiguous column stacks so the first card in every active column begins at the same vertical origin.
5. There is no horizontal rule across the top of a card entry. A light bottom separator remains between successive card entries.
6. Card descriptions use the same first-line spacing treatment accepted for Classes/Subclasses: the identity row is explicitly terminated, then rules text begins in its own zero-`parskip`, zero-`parindent` paragraph group with explicit font leading. Normalized line/paragraph whitespace is collapsed into one publication paragraph before rendering.
7. Each card entry shows its image, name, Level, Recall Cost, optional `IN VAULT` marker, and rules text. Long rules text may continue naturally rather than being trapped in an unbreakable card box.
8. The default `ability` classification is not repeated visually. `cardType` remains in the semantic view and appears only for a future non-default classification.
9. **No text inside a Domain Card entry may render below 10.5 pt.** Rules text is 10.5 pt with 12.1 pt leading; Level and Recall Cost metadata are 10.5 pt; card names remain 12 pt. Level and Recall Cost are stacked on separate lines so the larger metadata remains wrap-safe in the three-column grammar.
10. The renderer retains 2 pt of bottom-page safety headroom and uses ragged-bottom page flow to avoid tiny vbox overflows without reducing the 10.5 pt minimum.
11. No Domain-specific or card-specific layout exceptions are part of DomainPackage v1.

The three-column flow uses `paracol`, matching the page-breakable parallel-column approach accepted for ClassPackage. A legacy two-column path remains only for older regression fixtures; the canonical DomainPackage configuration is three columns.

## LuaLaTeX render assets

Step 4 stages many Domain Card illustrations as WebP. LuaLaTeX/`graphicx` does not directly consume WebP, so the DomainPackage builder performs deterministic render-only conversion:

- PNG/JPEG/PDF publication assets are consumed directly from the Step 4 staged tree;
- WebP/GIF/BMP/TIFF publication assets are converted to PNG;
- converted files are written only below the DomainPackage render tree;
- Step 4 staged assets and canonical source assets are never modified;
- the composed DomainPackage view continues to contain the normalized Step 4 publication path rather than a render-specific path.

Raster conversion requires Pillow:

```powershell
python -m pip install Pillow
```

## Rendered regression

Every all-Domain `build` runs the same child validation used by Maker. A successful DomainPackage requires:

- render-asset reconciliation;
- LuaLaTeX compilation;
- no overfull `hbox` or `vbox` warnings;
- every card heading rendered exactly once, including headings that wrap across multiple PDF text lines;
- every Level heading resolved exactly once and in view order;
- each card heading associated with nearby Level/Recall Cost metadata;
- the configured three-column publication flow to produce the expected distinct column starts whenever enough cards are present;
- the first card in every active column for a Level to begin on the same page and within the configured top-alignment tolerance;
- the first-to-second description baseline to match configured 12.1 pt body leading when measurable;
- extractor-sensitive description anchors to be reported as skipped measurement samples rather than false content failures when the corpus still provides measurable leading samples;
- no intermediate PDF page between the first and last card page with zero card headings.

The PDF geometry validator is wrap-aware so long names and extractor-sensitive punctuation do not produce false failures merely because `pdftotext` splits or normalizes visible text differently.

The batch discovery layer reconciles the number of discovered packages and total cards against Step 4 `domainSemantics` when those counts are present. It discovers Domain keys dynamically from `domainPackages`; Bullet, Circuit, and Maker are not hard-coded into the batch builder.

## Single-Domain commands

```powershell
python build\rulebook\scripts\build-rulebook-domain-package.py inspect
python build\rulebook\scripts\build-rulebook-domain-package.py validate
python build\rulebook\scripts\build-rulebook-domain-package.py build
```

Another Domain may be selected with `--domain-key`.

## All-Domain commands

```powershell
python build\rulebook\scripts\build-rulebook-all-domain-packages.py inspect
python build\rulebook\scripts\build-rulebook-all-domain-packages.py validate
python build\rulebook\scripts\build-rulebook-all-domain-packages.py build
```

Use `--verbose` anywhere for the complete aggregate report. `build --tex-only` generates every Domain view model and LaTeX file but skips LuaLaTeX.

Default all-Domain output:

```text
build/rulebook/layout/domain-packages/
    <domain>-domain-package-view.json
    Cybermancy_Chapter14_<Domain>_DomainPackage_Step6.tex
    Cybermancy_Chapter14_<Domain>_DomainPackage_Step6.pdf
    _render-assets/
        <domain>/
```

Aggregate and per-Domain reports:

```text
build/rulebook/layout/reports/domain-packages-all.json
build/rulebook/layout/reports/domain-packages/<domain>.json
```

## Current boundary

**Step G — Domains and Domain Cards is complete and accepted.** DomainPackage v1 is frozen. The semantic and visual design work for Chapter 14 should not be reopened during ordinary rulebook assembly.

Chapter 14/Pandoc AST integration is now unblocked. The accepted integration target is replacement of the `family:domains` semantic container within Chapter 14 using the frozen DomainPackage v1 grammar. The former Chapter 15 all-Feature reference is obsolete; independent Feature publication is the GM-only Chapter 29 ICE Reference defined by the current Step 3 architecture.
