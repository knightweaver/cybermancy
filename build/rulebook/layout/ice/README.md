# Step H2 — ICEReferencePackage v1

This directory contains the **prototype Chapter 29 publication grammar** for the GM-only ICE Reference.

## Scope

ICEReferencePackage consumes only the Step 4 normalized corpus:

```text
build/rulebook/source/metadata/structured-entities.json
```

It does not read canonical Foundry Feature JSON, generated MkDocs Feature pages, Feature folders, or runtime action metadata during Step 6 composition.

Step 4 remains responsible for determining which Feature entities are ICE and for exposing normalized reader-facing ICE semantics. Step 6 consumes `iceSemantics`, `publicationData.featureCategory`, `publicationData.iceType`, `rulesMarkdown`, and normalized actions. Foundry `system.resource` state remains normalized for semantic completeness, but unlabeled resource internals are explicitly non-reader-facing and are omitted from the ICEReferencePackage view.

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
ICE NAME
SENTRY ICE | WALL ICE

rules text

ACTIONS
Action Name [non-default type only]
action-specific rules text only
Cost / Range / constrained Target / reader-facing Damage / Uses
```

Empty optional fields are omitted. The default Foundry action classification `action`, generic `Target: any`, raw damage targets such as `hitPoints`, Foundry IDs, folder IDs, source paths, action IDs, runtime image paths, and implementation-only action wiring are prohibited from the reader-facing view.

When an action repeats its parent ICE rules exactly, the duplicate action prose is suppressed. When the action begins with the complete parent rules and then adds action-specific text, only that exact trailing remainder is published. This is deterministic exact/prefix/block equality only; no fuzzy rewriting is permitted.

## Step 4 publication cleanup

H2.1 adds targeted normalization required by the first visual proof:

- Foundry `<li><p>...</p></li>` structures are repaired after generic HTML conversion so list markers remain attached to their text and nested indentation is preserved.
- `target={type:any, amount:null}` is recognized as default runtime targeting and is omitted from reader semantics.
- normalized damage retains machine semantics for validation while adding reader labels (`hitPoints` -> `HP`, `stress` -> `Stress`, `physical` -> `Physical`). Step 6 publishes only the reader-safe projection.
- unlabeled `system.resource` state is retained with `readerFacing: false`; it is not printed until an authoritative reader-facing label/meaning exists.

## H2.1 visual rules

The compact structured-reference interior is retained, but it now sits inside the accepted Cybermancy rulebook shell:

- warm `F9F9F7` paper;
- Lato display typography and Noto Serif rules text;
- dark full-width chapter title band;
- GM-violet chapter/running marker;
- `CYBERMANCY // ICE REFERENCE` running header and `GM MATERIAL` marker;
- Step 6 / ICEReferencePackage running footer with outer page number;
- full-width Sentry/Wall group headers;
- two-column natural page flow for entries;
- minimum entry text size 10.5 pt;
- title/type/first content protected from orphaning with `needspace`;
- action label/first content protected similarly;
- long entries may break naturally across columns/pages;
- nested Step 4 Markdown lists are preserved as nested LaTeX lists;
- no card boxes and no entry-specific layout exceptions;
- no artwork requirement for H2.

## Commands

Because H2.1 changes Step 4 publication semantics, rebuild Step 4 before regenerating the proof:

```powershell
python build\rulebook\scripts\build-rulebook-source.py validate
python build\rulebook\scripts\build-rulebook-source.py build
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
```

Validation report:

```text
build/rulebook/layout/reports/ice-reference-package-h2.json
```

## H2 acceptance gate

H2 is ready for the second visual review when:

- Step 4 ICE semantics are `PASS`;
- the complete Step 4 ICE corpus reconciles to 13 entries: 6 Sentry / 7 Wall;
- all six proof entries resolve from the Step 4 ICE semantic ID set;
- every proof entry has reader-facing rules in prose and/or normalized action semantics;
- nested list markers remain attached to their text;
- duplicate parent/action prose is absent;
- generic `Target: any`, raw `hitPoints`, and unlabeled `Resource: simple; value ...` text are absent;
- the PDF uses the accepted Cybermancy GM chapter shell, Lato/Noto typography, and warm paper treatment;
- LuaLaTeX reports no overfull boxes;
- rendered text contains every group and proof entry heading, with first occurrences in view order.

The config remains `prototype` until the revised rendered proof is visually accepted. H3 should promote the accepted grammar to all 13 ICE entries and only then freeze ICEReferencePackage v1.
