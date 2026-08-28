# Step H3 — ICEReferencePackage v1

This directory contains the **full-corpus Chapter 29 candidate** for the GM-only ICE Reference.

H2/H2.3 established and visually accepted the publication grammar. H3 does not redesign that grammar; it promotes the same treatment from the six-entry representative proof to the complete Step 4 ICE corpus.

## Scope

ICEReferencePackage consumes only the Step 4 normalized corpus:

```text
build/rulebook/source/metadata/structured-entities.json
build/rulebook/source/assets/...
```

It does not read canonical Foundry Feature JSON, generated MkDocs Feature pages, Feature folders, or runtime action/image metadata during Step 6 composition.

Step 4 remains responsible for determining which Feature entities are ICE and for exposing normalized reader-facing ICE semantics. Resolvable ICE artwork is staged as `publicationData.image`. Artwork remains non-blocking: when an ICE has no valid staged publication image, Step 6 records a warning and renders a neutral blank identity block rather than failing the package. ICE entities remain GM-only and are excluded from the Player Guide.

Foundry `system.resource` state remains normalized for semantic completeness, but unlabeled resource internals are explicitly non-reader-facing and are omitted from the ICEReferencePackage view.

## H3 full corpus

The canonical package no longer contains a `prototype.semanticIds` subset. With `prototype.mode = "full-corpus"`, the composer consumes every semantic ID exposed by Step 4 `iceSemantics`.

The H3 contract requires exactly:

```text
13 ICE total
6 Sentry ICE
7 Wall ICE
```

Within each group, entries are ordered by case-insensitive name with stable source ID as the deterministic tie-break.

## Publication grammar

```text
Chapter 29 — ICE Reference
    Cybermancy GM chapter shell
    Sentry ICE
        two-column flowing reference entries
    Wall ICE
        two-column flowing reference entries
```

Each entry renders:

```text
[ICE IMAGE]  ICE NAME
             SENTRY ICE | WALL ICE

rules text at full column width

ACTIONS
Action Name [non-default type only]
action-specific rules text only
Cost / Range / constrained Target / reader-facing Damage / Uses
```

If artwork is unavailable, `[ICE IMAGE]` becomes a neutral blank block of the same dimensions. The image or fallback participates only in the compact identity row. Once that identity row ends, rules and action text return to the full reference-column width.

Empty optional fields are omitted. The default Foundry action classification `action`, generic `Target: any`, raw damage targets such as `hitPoints`, Foundry IDs, folder IDs, source paths, action IDs, runtime image paths, and implementation-only action wiring are prohibited from the reader-facing view.

When an action repeats its parent ICE rules exactly, the duplicate action prose is suppressed. When the action begins with the complete parent rules and then adds action-specific text, only that exact trailing remainder is published. This remains deterministic exact/prefix/block equality only; no fuzzy rewriting is permitted.

## Accepted visual rules

H3 carries forward the accepted H2.3 visual grammar unchanged:

- warm `F9F9F7` paper;
- Lato display typography and Noto Serif rules text;
- dark full-width chapter title band;
- GM-violet chapter/running marker;
- `CYBERMANCY // ICE REFERENCE` running header and `GM MATERIAL` marker;
- Step 6 / ICEReferencePackage running footer with outer page number;
- full-width Sentry/Wall group headers;
- two-column natural page flow for entries;
- minimum entry text size 10.5 pt;
- compact staged ICE image to the left of Name + ICE Type only;
- missing or invalid artwork uses a neutral `CMSoft` blank block;
- image/fallback defaults to a 0.38-inch square bounding box with a 0.07-inch gap;
- rules and actions resume at full column width below the identity row;
- title/type/first content protected from orphaning with `needspace`;
- action label/first content protected similarly;
- long entries may break naturally across columns/pages;
- nested Step 4 Markdown lists are preserved as nested LaTeX lists;
- no card boxes and no ICE-specific layout exceptions.

LuaLaTeX cannot consume the current WebP ICE artwork directly. The builder reuses the shared Step 6 render-asset pipeline: staged WebP/GIF/BMP/TIFF publication assets are deterministically converted to PNG beneath the output tree, while PNG/JPEG/PDF assets are consumed directly. Blank fallbacks require no render asset.

## Commands

H3 is a Step 6 promotion. If the current Step 4 corpus already reports 13 ICE (6 Sentry / 7 Wall), no Step 4 rebuild is required merely to remove the H2 subset.

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -v
python build\rulebook\scripts\build-rulebook-ice-reference.py inspect --verbose
python build\rulebook\scripts\build-rulebook-ice-reference.py validate
python build\rulebook\scripts\build-rulebook-ice-reference.py build
```

`inspect --verbose` must report `entryCount: 13`, with 6 Sentry entries and 7 Wall entries.

The standalone candidate currently retains the existing output paths while H3 is under review:

```text
build/rulebook/layout/ice-reference-prototype/
    ice-reference-package-view.json
    Cybermancy_Chapter29_ICE_Reference_H2.tex
    Cybermancy_Chapter29_ICE_Reference_H2.pdf
    _render-assets/ice/...

build/rulebook/layout/reports/
    ice-reference-package-h2.json
```

The legacy `H2` artifact filename is intentionally left unchanged during H3 candidate review so existing local commands and regressions are not disrupted. The final integration/freeze pass should replace proof/candidate naming with the production Chapter 29 artifact name.

## H3 acceptance gate

H3 is ready to freeze when:

- Step 4 ICE rules semantics are `PASS`;
- the complete Step 4 ICE corpus reconciles to exactly 13 entries: 6 Sentry / 7 Wall;
- the package config is `full-corpus` and contains no semantic-ID subset;
- all 13 Step 4 ICE semantic IDs resolve to publication-complete entries;
- every entry has reader-facing rules in prose and/or normalized action semantics;
- every entry has either a staged publication image or the approved blank-block fallback;
- incomplete publication-image coverage is warning-only;
- nested list markers remain attached to their text;
- duplicate parent/action prose is absent;
- generic `Target: any`, raw `hitPoints`, and unlabeled `Resource: simple; value ...` text are absent;
- each image/fallback is restricted to Name + ICE Type and body text returns to full column width below it;
- the PDF uses the accepted Cybermancy GM chapter shell, Lato/Noto typography, and warm paper treatment;
- LuaLaTeX reports no overfull boxes;
- rendered text contains both group headings and all 13 ICE headings in deterministic order.

After the full-corpus PDF passes visual review, ICEReferencePackage v1 should be frozen and Chapter 29 integrated into the Complete Rulebook production path.
