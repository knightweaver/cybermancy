# Step H2 — ICEReferencePackage v1

This directory contains the **prototype Chapter 29 publication grammar** for the GM-only ICE Reference.

## Scope

ICEReferencePackage consumes only the Step 4 normalized corpus:

```text
build/rulebook/source/metadata/structured-entities.json
build/rulebook/source/assets/...
```

It does not read canonical Foundry Feature JSON, generated MkDocs Feature pages, Feature folders, or runtime action/image metadata during Step 6 composition.

Step 4 remains responsible for determining which Feature entities are ICE and for exposing normalized reader-facing ICE semantics. H2.2 promotes resolvable ICE artwork into staged `publicationData.image` paths. H2.3 makes artwork non-blocking: when an ICE has no valid staged publication image, Step 6 records a warning and renders a neutral blank identity block rather than failing the package. The ICE entities remain GM-only and are excluded from the Player Guide.

Foundry `system.resource` state remains normalized for semantic completeness, but unlabeled resource internals are explicitly non-reader-facing and are omitted from the ICEReferencePackage view.

## H2 proof corpus

The prototype contract selects six representative ICE entries by stable semantic ID:

- Tar Pit
- Heaven's Gate
- Black ICE
- Wall of Static
- Sleaze Gate
- Wall of No!

The proof deliberately covers compact prose, long prose, list-rich rules, action-rich rules, action-only/action-dominant rules, and the repaired Wall of No! source path.

The selection is a design-proof fixture only. If `prototype.semanticIds` is removed from the config, the composer can consume the complete Step 4 ICE corpus for H3.

## Publication grammar

```text
Chapter 29 — ICE Reference
    Cybermancy GM chapter shell
    Sentry ICE
        two-column flowing reference entries
    Wall ICE
        two-column flowing reference entries
```

Within each group, entries are ordered by case-insensitive name with stable source ID as the deterministic tie-break.

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

If artwork is unavailable, `[ICE IMAGE]` becomes a neutral blank block of the same dimensions. The image or fallback participates only in the compact identity row. Its bounding box is sized to approximately the combined vertical height of the Name and ICE Type lines; once that identity row ends, rules and action text return to the full reference-column width. The image never creates a persistent narrow text rail beside the body copy.

Empty optional fields are omitted. The default Foundry action classification `action`, generic `Target: any`, raw damage targets such as `hitPoints`, Foundry IDs, folder IDs, source paths, action IDs, runtime image paths, and implementation-only action wiring are prohibited from the reader-facing view.

When an action repeats its parent ICE rules exactly, the duplicate action prose is suppressed. When the action begins with the complete parent rules and then adds action-specific text, only that exact trailing remainder is published. This is deterministic exact/prefix/block equality only; no fuzzy rewriting is permitted.

## Step 4 publication cleanup

H2.1/H2.2 targeted normalization includes:

- Foundry `<li><p>...</p></li>` structures are repaired after generic HTML conversion so list markers remain attached to their text and nested indentation is preserved.
- `target={type:any, amount:null}` is recognized as default runtime targeting and is omitted from reader semantics.
- normalized damage retains machine semantics for validation while adding reader labels (`hitPoints` -> `HP`, `stress` -> `Stress`, `physical` -> `Physical`). Step 6 publishes only the reader-safe projection.
- unlabeled `system.resource` state is retained with `readerFacing: false`; it is not printed until an authoritative reader-facing label/meaning exists.
- resolvable ICE canonical images are mapped through the Step 4 Foundry-runtime asset mapping, resolved against checked-in publication artwork, staged into the self-contained Step 4 source corpus, and exposed only as `publicationData.image`.

## H2.3 visual rules

The compact structured-reference interior sits inside the accepted Cybermancy rulebook shell:

- warm `F9F9F7` paper;
- Lato display typography and Noto Serif rules text;
- dark full-width chapter title band;
- GM-violet chapter/running marker;
- `CYBERMANCY // ICE REFERENCE` running header and `GM MATERIAL` marker;
- Step 6 / ICEReferencePackage running footer with outer page number;
- full-width Sentry/Wall group headers;
- two-column natural page flow for entries;
- minimum entry text size 10.5 pt;
- a compact staged ICE image appears to the left of Name + ICE Type only;
- missing or invalid artwork uses a neutral `CMSoft` blank block rather than failing validation;
- the image/fallback defaults to a 0.38-inch square bounding box with a 0.07-inch gap to the identity text;
- rules and actions resume at full column width below the identity row;
- title/type/first content protected from orphaning with `needspace`;
- action label/first content protected similarly;
- long entries may break naturally across columns/pages;
- nested Step 4 Markdown lists are preserved as nested LaTeX lists;
- no card boxes and no ICE-specific layout exceptions.

LuaLaTeX cannot consume the current WebP ICE artwork directly. The builder therefore reuses the shared Step 6 render-asset pipeline: staged WebP/GIF/BMP/TIFF publication assets are deterministically converted to PNG beneath the proof output tree, while PNG/JPEG/PDF assets are consumed directly. The normalized Step 4 image path remains unchanged in the view model. Blank fallbacks require no render asset.

## Commands

H2.3 is a Step 6 policy/layout change. If your Step 4 corpus has already been rebuilt for H2.2, you can pull the change and resume directly at the ICE builder:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -v
python build\rulebook\scripts\build-rulebook-ice-reference.py inspect --verbose
python build\rulebook\scripts\build-rulebook-ice-reference.py validate
python build\rulebook\scripts\build-rulebook-ice-reference.py build
```

For a render-input-only proof:

```powershell
python build\rulebook\scripts\build-rulebook-ice-reference.py build --tex-only
```

Default proof output:

```text
build/rulebook/layout/ice-reference-prototype/
    ice-reference-package-view.json
    Cybermancy_Chapter29_ICE_Reference_H2.tex
    Cybermancy_Chapter29_ICE_Reference_H2.pdf
    _render-assets/ice/...
```

Validation report:

```text
build/rulebook/layout/reports/ice-reference-package-h2.json
```

## H2 acceptance gate

H2 is ready for the next visual review when:

- Step 4 ICE rules semantics are `PASS`;
- the complete Step 4 ICE corpus reconciles to 13 entries: 6 Sentry / 7 Wall;
- all six proof entries resolve from the Step 4 ICE semantic ID set;
- every proof entry has reader-facing rules in prose and/or normalized action semantics;
- every proof ICE has either a staged publication image or the approved blank-block fallback;
- incomplete Step 4 publication-image coverage is reported as a warning rather than a rules/publication failure;
- nested list markers remain attached to their text;
- duplicate parent/action prose is absent;
- generic `Target: any`, raw `hitPoints`, and unlabeled `Resource: simple; value ...` text are absent;
- each proof ICE shows its image/fallback only beside Name + ICE Type and body text returns to full column width below it;
- the PDF uses the accepted Cybermancy GM chapter shell, Lato/Noto typography, and warm paper treatment;
- LuaLaTeX reports no overfull boxes;
- rendered text contains every group and proof entry heading, with first occurrences in view order.

The config remains `prototype` until the revised rendered proof is visually accepted. H3 should promote the accepted grammar to all 13 ICE entries and only then freeze ICEReferencePackage v1.
