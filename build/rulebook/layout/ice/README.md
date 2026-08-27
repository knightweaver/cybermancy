# Step H2 — ICEReferencePackage v1

This directory contains the **prototype Chapter 29 publication grammar** for the GM-only ICE Reference.

## Scope

ICEReferencePackage consumes only the Step 4 normalized corpus:

```text
build/rulebook/source/metadata/structured-entities.json
```

It does not read canonical Foundry Feature JSON, generated MkDocs Feature pages, Feature folders, or runtime action metadata during Step 6 composition.

Step 4 remains responsible for determining which Feature entities are ICE and for exposing normalized reader-facing ICE semantics. Step 6 consumes `iceSemantics`, `publicationData.featureCategory`, `publicationData.iceType`, `rulesMarkdown`, normalized actions, and normalized resource data.

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
    full-width chapter opener
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
Action Name — type
rules text
Cost / Range / Target / Damage / Uses

Resource: ...
```

Empty optional fields are omitted. Foundry IDs, folder IDs, source paths, action IDs, runtime image paths, and implementation-only action wiring are prohibited from the reader-facing view.

## H2 visual rules

- full-width chapter and group headers;
- two-column natural page flow for entries;
- minimum entry text size 10.5 pt;
- title/type/first content protected from orphaning with `needspace`;
- action label/first content protected similarly;
- long entries may break naturally across columns/pages;
- nested Step 4 Markdown lists are preserved as nested LaTeX lists;
- no card boxes and no entry-specific layout exceptions;
- no artwork requirement for H2.

## Commands

From the repository root:

```powershell
python build\rulebook\scripts\build-rulebook-ice-reference.py inspect
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

H2 is ready for visual review when:

- Step 4 ICE semantics are `PASS`;
- the complete Step 4 ICE corpus reconciles to 13 entries: 6 Sentry / 7 Wall;
- all six proof entries resolve from the Step 4 ICE semantic ID set;
- every proof entry has reader-facing rules in prose and/or normalized action semantics;
- the view contains no raw source/runtime references;
- LuaLaTeX reports no overfull boxes;
- rendered text contains each group and proof entry exactly once and in view order.

The config remains `prototype` until the rendered proof is visually accepted. H3 should promote the accepted grammar to all 13 ICE entries and only then freeze ICEReferencePackage v1.
