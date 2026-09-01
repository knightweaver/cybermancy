# Step 6 — ICEReferencePackage v1

This directory owns the **accepted and frozen Chapter 29 publication grammar** for the GM-only *ICE Reference*.

ICEReferencePackage v1 was developed through representative visual proofing and full-corpus promotion, then visually accepted against the complete current ICE corpus on 2026-08-28. The accepted corpus is **13 ICE: 6 Sentry / 7 Wall**.

## Freeze status

`ice-reference-package-v1.json` is the frozen publication contract. Its lifecycle metadata records:

- version `v1.0`;
- status `frozen`;
- semantic regression `PASS`;
- full-corpus render `PASS`;
- visual review `ACCEPTED`;
- acceptance corpus: 13 total / 6 Sentry / 7 Wall.

Future changes to the ICEReferencePackage grammar should be intentional versioned changes rather than silent edits to accepted v1 behavior.

The frozen config no longer contains proof/candidate terminology. Full-corpus selection is expressed as:

```json
"selection": {
  "mode": "full-corpus"
}
```

and publication validation is owned by `publicationPolicy`.

## Source boundary

ICEReferencePackage consumes only the Step 4 normalized corpus:

```text
build/rulebook/source/metadata/structured-entities.json
build/rulebook/source/assets/**
```

It does not read canonical Foundry Feature JSON, generated MkDocs Feature pages, Feature folders, or runtime action/image metadata during Step 6 composition.

Step 4 remains responsible for determining which Feature entities are ICE and for exposing normalized reader-facing ICE semantics. The complete Feature family remains normalized because dependent Class/Subclass mechanics consume it, but the independent rulebook collection publishes only normalized Sentry and Wall ICE.

Resolvable artwork is staged as `publicationData.image`. Missing or invalid artwork is non-blocking and renders as the accepted neutral blank identity block. Runtime image paths never pass through to the reader-facing package.

Unlabeled Foundry resource state remains normalized for semantic completeness but is not reader-facing.

## Frozen publication grammar

```text
Chapter 29 — ICE Reference
    Cybermancy GM chapter shell
    Sentry ICE
        6 entries, two-column natural flow
    Wall ICE
        7 entries, two-column natural flow
```

Within each group, entries sort by case-insensitive name with stable source ID as the deterministic tie-break.

Each entry renders:

```text
[ICE IMAGE OR BLANK]  ICE NAME
                      SENTRY ICE | WALL ICE

rules text at full column width

ACTIONS
Action Name [non-default type only]
action-specific rules text only
Cost / Range / constrained Target / reader-facing Damage / Uses
```

Accepted visual rules:

- warm `F9F9F7` paper;
- Arial display typography and Arial rules text;
- dark full-width chapter band;
- GM-violet chapter/running identity;
- `CYBERMANCY // ICE REFERENCE` running header and `GM MATERIAL` marker;
- full-width Sentry/Wall group headers;
- two-column natural entry flow;
- minimum entry text size 10.5 pt;
- image/fallback occupies only the compact Name + ICE Type row;
- image/fallback defaults to a 0.38-inch square with a 0.07-inch gap;
- body text resumes at full column width beneath the identity row;
- long entries may break naturally across columns/pages;
- nested normalized lists remain nested;
- no card boxes and no ICE-specific layout exceptions.

### Action-type presentation role

Structured reader-facing action types use the shared Feature/Action type-label role: bold uppercase text at 9.5 pt with 10.5 pt leading in the established ICE `CMAccent` teal/blue role. This replaces the former 7.8 pt muted-gray suffix and applies only to the semantic action-type label; action names, rules text, metadata, and the 10.5 pt body-text minimum are unchanged.

The label is rendered only from the normalized structured action type supplied to the publication view. Legacy prose that happens to contain words such as *Passive* or *Reaction* is not parsed or rewritten to manufacture a type label.

Reader-facing output must not expose default Foundry `action` classification, generic `Target: any`, raw `hitPoints`, unlabeled `Resource: simple`, Foundry IDs, folder IDs, source paths, runtime image paths, or implementation wiring.

Exact parent/action prose duplication is suppressed deterministically. No fuzzy rewriting is used.

## Production commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -v
python build\rulebook\scripts\build-rulebook-ice-reference.py inspect --verbose
python build\rulebook\scripts\build-rulebook-ice-reference.py validate
python build\rulebook\scripts\build-rulebook-ice-reference.py build
```

Default production output:

```text
build/rulebook/layout/ice-reference/
    ice-reference-package-view.json
    Cybermancy_Chapter29_ICE_Reference_Step6.tex
    Cybermancy_Chapter29_ICE_Reference_Step6.pdf
    ice-reference-chapter-header.tex
    ice-reference-family-features.tex
    _render-assets/ice/...
```

Validation report:

```text
build/rulebook/layout/reports/ice-reference-package-v1.json
```

## Complete Rulebook AST integration

Step 3 owns Chapter 29 placement and Step 4 emits the normalized `family:features` publication container. The production builder provides a fail-closed Pandoc AST integration command:

```powershell
python build\rulebook\scripts\build-rulebook-ice-reference.py integrate `
  --ast-input <complete-rulebook-pandoc-ast.json>
```

By default the integrated AST is written to:

```text
build/rulebook/layout/ice-reference/complete-rulebook-step6-ice-reference.ast.json
```

The integration pass requires exactly one Chapter 29 heading (`ch29-ice-reference` or `section:ch29-ice-reference`) and exactly one `family:features` Div. It replaces the chapter heading with the frozen Cybermancy chapter band and replaces only the Feature-family body with the accepted Sentry/Wall ICE reference content.

This preserves the System boundary: non-ICE Feature semantics remain normalized upstream for dependent mechanics while the Complete Rulebook receives only the approved Chapter 29 ICE subset.

## Frozen acceptance gate

Ordinary production remains fail-closed unless:

- the contract is frozen v1.0;
- Step 4 ICE rules semantics are `PASS`;
- the corpus reconciles to 13 entries: 6 Sentry / 7 Wall;
- every ICE has reader-facing rules in prose and/or normalized action semantics;
- every ICE has either a staged image or the approved blank fallback;
- implementation vocabulary is absent from the reader-facing view;
- the accepted group order and deterministic sorting are preserved;
- LuaLaTeX reports no overfull boxes;
- rendered content contains all group and entry headings in view order.

**Step H — ICE Reference is complete and accepted. ICEReferencePackage v1 is frozen for Chapter 29 production and Complete Rulebook integration.**
