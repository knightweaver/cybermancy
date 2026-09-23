# Seattle Lore Art Production

This directory contains the source-backed image-generation manifest for every named feature currently displayed by the Seattle Atlas.

## Files

- `cybermancy-seattle-lore-art-manifest-v0.1.csv`: primary input for the batch generator.
- `cybermancy-seattle-lore-art-manifest-v0.1.json`: equivalent machine-readable manifest using the generator-compatible `items` key.
- `cybermancy-seattle-lore-art-presets-v0.1.json`: Cybermancy environment-art presets required by manifest mode.
- `cybermancy-seattle-lore-art-manifest-schema-v0.1.md`: field definitions, coverage, validation rules, and dry-run command.

The prompts are frozen in each row. Preset metadata still controls request defaults and remains mandatory because the batch generator validates every `preset_family`.

## Rebuild

```powershell
python tools/build-seattle-lore-art-manifest.py
```

The builder fails if atlas coverage, player/GM feature identity, parent links, preset keys, substyles, or stable filenames drift.
