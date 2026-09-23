# Cybermancy Seattle Lore Art Manifest Schema v0.1

**Status:** Working production schema

**Source:** Canonical GM Seattle Atlas GeoJSON, with GM-only notes excluded from prompts

**Expected enabled rows:** 51

## Purpose

This manifest is the deterministic production boundary between the Seattle Atlas canon and generated lore artwork. It records stable source linkage, prompt text, request parameters, output filenames, and parent geography. Image generation itself remains nondeterministic.

## Coverage

| Source layer | Required rows | Preset family |
|---|---:|---|
| Regions | 5 | `regionEnvironment` |
| Districts | 11 | `districtEnvironment` |
| Point and event POIs | 29 | `locationEnvironment` or `eventEnvironment` |
| Routes and corridors | 6 | `routeEnvironment` |

## Core fields

- `record_id`: stable `{layer}-{feature_id}-{slug}` identifier.
- `family`: atlas layer or context category.
- `preset_family`: request and composition preset resolved by the batch generator.
- `parent_id` / `parent_name`: containing district or region where one authoritative parent exists.
- `source_dataset` / `source_feature_id`: exact GeoJSON provenance.
- `source_summary`: player-visible canonical atlas properties only.
- `subject_brief`: feature-specific visual composition.
- `prompt`: frozen full prompt used exactly by the generator.
- `negative_notes`: feature-specific canon and spoiler exclusions.
- `output_filename`: namespaced stable WebP filename.

Additional columns follow the Edgeheart manifest conventions and are ignored safely by the generator where not required.

## Validation rules

1. Exactly 51 enabled rows: 5 regions, 11 districts, 29 point/event POIs, and 6 routes.
2. Each GM atlas feature appears exactly once and matches the player atlas by ID and name.
3. `record_id` and `output_filename` values are unique.
4. Every row resolves to a declared preset family and approved substyle.
5. Every row uses `3:2`, `1536x1024`, opaque WebP output.
6. Prompts use player-visible properties and never include `gm_notes`.
7. Silicon Wilds geography remains strictly east of Lake Washington; Mercer Island remains separate.
8. Memorial prompts remain non-graphic and do not reenact the violence.
9. Wild and Resonance prompts do not establish rumored entities or explanations as fact.

## Generator command

```powershell
python batch-image-generation-on-OpenAI-v2.py `
  --input art-production/seattle-lore/cybermancy-seattle-lore-art-manifest-v0.1.csv `
  --presets art-production/seattle-lore/cybermancy-seattle-lore-art-presets-v0.1.json `
  --outdir generated-art/seattle-lore `
  --dry-run
```

Remove `--dry-run` only after reviewing the generation ledger and approving a representative pilot.
