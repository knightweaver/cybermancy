# Atlas Publishing Workflow

The GM atlas is the authoritative workspace for public and secret map content. The player atlas is generated from the subset explicitly marked for publication.

## Preparing a feature

Add the feature to the appropriate file under `docs/gm-facing/assets/atlas/` with a stable numeric or string `id`.

Use one of these audience values:

- `"audience": "gm"` — visible only in the GM atlas.
- `"audience": "player"` — eligible for both the GM and player atlases.

Context features may use these categories:

- `landmark`
- `transit`
- `corporate`
- `hazard`
- `settlement`
- `event`
- `route`

Player-safe panel fields are `name`, `code`, `description`, `status`, `known_for`, and `access`.

Private planning fields may be recorded as `gm_notes`, `adventure_hooks`, or `events`. Any property whose name begins with `gm_` is also treated as private.

## Revealing a feature

1. Review every player-safe field for spoilers.
2. Change `audience` from `gm` to `player`.
3. Run:

```powershell
npm run atlas:sync
npm run atlas:check
mkdocs build -f mkdocs.player.yml --strict
mkdocs build -f mkdocs.gm.yml --strict
```

The sync operation copies player-visible features to the player atlas and removes all GM-only planning fields. The GM feature remains in place, including its private notes.

Do not edit player atlas GeoJSON directly. Those files are publication outputs derived from the GM source.
