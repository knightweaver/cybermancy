# Part VI Encounter Toolkit - Frozen v1

This package owns the approved Step 6 publication grammar for Chapters 30-32:

- Chapter 30 - Adversaries
- Chapter 31 - Environments
- Chapter 32 - Adversary Feature Reference

The renderer consumes `build/rulebook/source/metadata/structured-entities.json` after Step 4 encounter enrichment. It does not parse raw Foundry actors or Package Builder PDFs.

## Frozen production rules

- Phase C visual proof was approved on 2026-08-28; the production contracts are frozen as v1.0.
- Adversaries and Environments share the Encounter Toolkit shell but use distinct interior grammars.
- Chapters 30 and 31 are inline-complete: embedded Features remain with their owning entity.
- Chapter 32 is an independent reference corpus. Same-name Features are not deduplicated; stable ordering is normalized name then semantic ID.
- Adversaries and Environments use deterministic Tier -> Classification -> Name -> semantic ID ordering.
- Fast Play is rendered only from structured `publicationData.fastPlay` and is never reconstructed from Description.
- Missing legacy descriptions, classifications, impulses, Fast Play, or artwork remain absent. Step 6 does not invent canonical content.
- Publication artwork is optional for legacy entities and is loaded only from staged Step 4 paths.
- Production builds fail closed if the Step 4 corpus count drifts from the frozen contract: 106 Adversaries, 8 Environments, 419 standalone Adversary Features.

## Approved Phase C proofs

The approved proof selections are retained under `build/rulebook/layout/encounters/proof/` for visual regression.

```powershell
python build\rulebook\scripts\build-rulebook-encounters.py proof --family all
```

Proof output defaults to `build/rulebook/layout/encounters/proof-output/`.

## Full-corpus Chapter 30-32 build

Run against the current Step 4 sidecar and staged publication assets:

```powershell
python build\rulebook\scripts\build-rulebook-encounters.py build --family all
```

Production output defaults to `build/rulebook/layout/encounters/chapter-output/` and produces:

- `Cybermancy_Chapter30_Adversaries_Step6.pdf`
- `Cybermancy_Chapter31_Environments_Step6.pdf`
- `Cybermancy_Chapter32_Adversary_Feature_Reference_Step6.pdf`
- matching `.tex` files and `.report.json` validation reports

The production command injects the complete family selection from Step 4, validates the frozen expected count, enforces deterministic publication ordering, and blocks the build if encounter semantics are in a FAIL state.

After these three standalone full-corpus builds pass, the next stage is AST integration of Chapters 30-32 into the Complete Rulebook Part VI publication build, following the same semantic replacement discipline already used by Chapter 29 ICE Reference.
