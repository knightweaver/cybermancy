# Part VI Encounter Toolkit - Phase C

This package owns the Step 6 publication grammar for Chapters 30-32:

- Chapter 30 - Adversaries
- Chapter 31 - Environments
- Chapter 32 - Adversary Feature Reference

The renderer consumes `build/rulebook/source/metadata/structured-entities.json` after Step 4 encounter enrichment. It does not parse raw Foundry actors or Package Builder PDFs.

## Production rules

- Adversaries and Environments share the Encounter Toolkit shell but use distinct interior grammars.
- Chapters 30 and 31 are inline-complete: embedded Features remain with their owning entity.
- Chapter 32 is an independent reference corpus. Same-name Features are not deduplicated; stable ordering is normalized name then semantic ID.
- Fast Play is rendered only from structured `publicationData.fastPlay` and is never reconstructed from Description.
- Missing legacy descriptions, classifications, impulses, Fast Play, or artwork remain absent. Step 6 does not invent canonical content.
- Publication artwork is optional for legacy entities and is loaded only from staged Step 4 paths.

## Phase C proof

```powershell
python build\rulebook\scripts\build-rulebook-encounters.py proof --family all
```

The default proof selections are frozen in the three v1 config files in this directory. After proof approval, the same renderer can be invoked with full-corpus configs for deterministic Chapter 30-32 generation.
