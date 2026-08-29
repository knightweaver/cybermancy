# Part VI Encounter Toolkit - Frozen publication grammars

This package owns the approved Step 6 publication grammar for Chapters 30-32:

- Chapter 30 - Adversaries
- Chapter 31 - Environments
- Chapter 32 - Adversary Feature Reference

The renderer consumes `build/rulebook/source/metadata/structured-entities.json` after Step 4 encounter enrichment. It does not parse raw Foundry actors or Package Builder PDFs.

## Frozen production rules

- Chapter 30 AdversaryPackage is frozen as **v1.1** after the approved Phase C layout revision on 2026-08-28.
- Chapter 31 EnvironmentPackage and Chapter 32 Adversary Feature Reference remain frozen as **v1.0**.
- Adversaries use a two-column body beneath a full-width chapter opener; the first Adversary shares page 1 with the chapter title.
- Adversary publication art is a compact identity thumbnail capped to approximately the height of the Type/Tier + Name + statistics header block.
- Environments remain one-column and retain their approved distinct interior grammar.
- Adversaries and Environments share the Encounter Toolkit shell but use distinct interior grammars.
- Chapters 30 and 31 are inline-complete: embedded Features remain with their owning entity.
- Chapter 32 is an independent reference corpus. Same-name Features are not deduplicated at Step 6; stable ordering is normalized name then semantic ID.
- Adversaries and Environments use deterministic Tier -> Classification -> Name -> semantic ID ordering.
- Fast Play is rendered only from structured `publicationData.fastPlay` and is never reconstructed from Description.
- Missing legacy descriptions, classifications, impulses, Fast Play, or artwork remain absent. Step 6 does not invent canonical content.
- Publication artwork is optional for legacy entities and is loaded only from staged Step 4 paths. LuaLaTeX-incompatible raster formats are converted into caller-owned temporary render assets without mutating Step 4 source assets.
- Production builds fail closed if the Step 4 corpus count drifts from the frozen contract: 106 Adversaries, 8 Environments, 419 standalone Adversary Features.

## Chapter 32 publication-equivalence audit

Deduplication of standalone Adversary Features is owned by Step 4 publication semantics, not the Step 6 renderer. The Step 4 pipeline now emits an advisory equivalence audit after encounter enrichment:

- `build/rulebook/source/metadata/adversary-feature-equivalence-audit.json`
- `build/rulebook/source/metadata/adversary-feature-equivalence-review.md`

The audit preserves all canonical Foundry/source entities. It identifies exact and trivial-normalization equivalence groups, recommends a deterministic publication representative, and separately identifies high-similarity same-name pairs for human review. Fuzzy candidates never auto-collapse. Until the review is approved, Chapter 32 remains unchanged at the frozen 419-entry full-corpus contract.

The audit is generated automatically by a normal Step 4 build, or it can be regenerated from an existing current Step 4 sidecar without rebuilding the rest of Step 4:

```powershell
python build\rulebook\scripts\audit-adversary-feature-equivalence.py
```

After review, the next implementation stage is to encode approved publication representative decisions in Step 4, rebuild Step 4, update Chapter 32's frozen expected count, and regenerate Chapter 32. Canonical source cleanup is a separate stronger action and should only be used when a duplicate is determined to be an erroneous canonical entity rather than merely redundant for publication.

## Approved Phase C proofs

The approved proof selections are retained under `build/rulebook/layout/encounters/proof/` for visual regression. The Chapter 30 proof now exercises the v1.1 two-column grammar; Chapters 31-32 retain their approved v1.0 proof grammars.

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

The production command injects the complete family selection from Step 4, validates the frozen expected count and package version, enforces deterministic publication ordering, and blocks the build if encounter semantics are in a FAIL state.

After these three standalone full-corpus builds pass, the next stage is AST integration of Chapters 30-32 into the Complete Rulebook Part VI publication build, following the same semantic replacement discipline already used by Chapter 29 ICE Reference.
