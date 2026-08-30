# Part VI Encounter Toolkit - Frozen publication grammars

This package owns the approved Step 6 publication grammar for Chapters 30-32:

- Chapter 30 - Adversaries
- Chapter 31 - Environments
- Chapter 32 - Adversary Feature Reference

The renderer consumes `build/rulebook/source/metadata/structured-entities.json` after Step 4 encounter enrichment. It does not parse raw Foundry actors or Package Builder PDFs.

## Final Step 6 acceptance

**Part VI is frozen and accepted for standalone Step 6 production as of 2026-08-29.**

The final full-corpus regression build passed all three production contracts:

- Chapter 30: **106 / 106 Adversaries**, AdversaryPackage **v1.1**
- Chapter 31: **8 / 8 Environments**, EnvironmentPackage **v1.0**
- Chapter 32: **344 / 344 publication Feature representatives**, Adversary Feature Reference **v1.0**, derived from **419 canonical standalone Features**

The **106 Adversaries** and **8 Environments** above are reference-corpus counts from that dated acceptance run. They are not permanent production-count constants. Current Chapter 30 and 31 expected counts come from the selected publication manifest and must reconcile exactly with the Step 4 structured sidecar before rendering.

The final reports also confirmed successful render-asset preparation with no missing or unsupported publication assets, the Chapter 31 opener merge, Chapter 30 multicolumn flow protection, and Chapter 32 consumption of the approved Step 4 publication-equivalence projection (`publicationStatus=APPLIED`).

The remaining `encounterSemantics` status of `WARNING` is non-blocking canonical content debt already governed by the missing-content policy; Step 6 does not invent or repair absent canonical fields.

No further standalone Part VI layout work is required. Integration of Chapters 30-32 into the Complete Rulebook belongs to the Step 6 Architecture Reconciliation & Complete Rulebook Integration stage.

## Frozen production rules

- Chapter 30 AdversaryPackage is frozen as **v1.1** after the approved Phase C layout revision on 2026-08-28.
- Chapter 31 EnvironmentPackage and Chapter 32 Adversary Feature Reference remain frozen as **v1.0**.
- Adversaries use a two-column body beneath a full-width chapter opener; the first Adversary shares page 1 with the chapter title.
- Adversary publication art is a compact identity thumbnail capped to approximately the height of the Type/Tier + Name + statistics header block.
- Environments remain one-column and retain their approved distinct interior grammar.
- Adversaries and Environments share the Encounter Toolkit shell but use distinct interior grammars.
- Chapters 30 and 31 are inline-complete: embedded Features remain with their owning entity.
- Chapter 32 is an independent reference corpus. Its canonical source family still contains **419** standalone Features, but the approved Step 4 publication-equivalence layer reduces those to **344** Chapter 32 publication representatives without deleting or altering canonical Foundry identities.
- Exact duplicates are consolidated for Chapter 32. Approved Feature-Library-backed families are consolidated only when mechanically meaningful parameters match; actor/adversary-name substitution alone is not mechanically meaningful.
- Mechanically distinct same-name variants remain separate. In particular, `Group Attack` variants remain distinct where `groupName` or `damagePerMinion` differ, and the mechanically distinct `Split` variant remains separate.
- Feature-Library-backed representative entries use reader-neutral rules text such as `this adversary` rather than inheriting an arbitrary source adversary name.
- Adversaries and Environments use deterministic Tier -> Classification -> Name -> semantic ID ordering. Chapter 32 uses normalized publication name -> semantic ID.
- Fast Play is rendered only from structured `publicationData.fastPlay` and is never reconstructed from Description.
- Missing legacy descriptions, classifications, impulses, Fast Play, or artwork remain absent. Step 6 does not invent canonical content.
- Publication artwork is optional for legacy entities and is loaded only from staged Step 4 paths. LuaLaTeX-incompatible raster formats are converted into caller-owned temporary render assets without mutating Step 4 source assets.
- Chapter 30 and 31 production builds fail closed unless the selected publication-manifest counts and semantic corpus reconcile exactly with the Step 4 sidecar. The dated 106/8 acceptance counts do not freeze future corpus size.
- The Chapter 32 publication projection remains frozen at **344** representatives derived from **419** canonical standalone Features unless separately authorized.

## Chapter 32 publication equivalence

The initial Step 4 audit remains available as diagnostic evidence:

- `build/rulebook/source/metadata/adversary-feature-equivalence-audit.json`
- `build/rulebook/source/metadata/adversary-feature-equivalence-review.md`

The approved decisions are frozen in:

- `build/rulebook/scripts/data/adversary-feature-equivalence-decisions-v1.json`

A normal Step 4 build now runs three Part VI stages in sequence:

1. encounter semantic enrichment;
2. Feature equivalence audit;
3. approved Feature publication-equivalence application.

The application stage preserves all 419 canonical Feature entities, marks one deterministic representative per approved publication group, supplies reader-neutral Feature-Library-backed reference text where appropriate, and writes:

- `build/rulebook/source/metadata/adversary-feature-publication-selection.json`

The frozen result is **344 Chapter 32 representatives** and **75 excluded redundant publication entries** across **29 approved groups**.

The standalone audit command remains useful for inspecting equivalence candidates but does not itself apply publication selection:

```powershell
python build\rulebook\scripts\audit-adversary-feature-equivalence.py
```

To apply the approved decisions, rerun Step 4 normally:

```powershell
python build\rulebook\scripts\build-rulebook-source.py validate
python build\rulebook\scripts\build-rulebook-source.py build
```

## Approved Phase C proofs

The approved proof selections are retained under `build/rulebook/layout/encounters/proof/` for visual regression. The Chapter 30 proof exercises the v1.1 two-column grammar; Chapters 31-32 retain their approved v1.0 proof grammars.

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

The production command injects the complete publication selection from Step 4, validates the manifest-authoritative Chapter 30/31 counts and package versions, enforces deterministic publication ordering, and blocks Chapter 32 unless the frozen **419-to-344** Step 4 Feature publication-equivalence projection reports `publicationStatus=APPLIED`.

After these three standalone full-corpus builds pass, the next stage is AST integration of Chapters 30-32 into the Complete Rulebook Part VI publication build, following the same semantic replacement discipline already used by Chapter 29 ICE Reference.
