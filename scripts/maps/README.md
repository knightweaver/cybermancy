# Seattle atlas basemap preparation

The player atlas initially uses OpenFreeMap's hosted dark vector style, built from OpenStreetMap data. Cybermancy overlays, descriptions, and interactions are repository-owned and do not depend on that provider.

To evaluate a durable regional vector basemap, install the `pmtiles` CLI and run:

```bash
scripts/maps/extract-seattle-basemap.sh SOURCE_PMTILES_URL
```

The extraction is intentionally fixed to:

- bounding box: `-122.75,47.05,-121.35,48.15`
- maximum zoom: `14`
- repository admission threshold: `50 MiB`

The generated archive is ignored by Git. After reviewing its size and rendered detail, either:

1. deliberately remove the ignore rule and commit an archive below the threshold; or
2. upload the archive to range-request-capable object storage and configure the atlas to read it there.

Do not replace the external basemap until its attribution, browser range requests, and both desktop and mobile rendering have been verified.

## GM-to-player atlas publishing

The files in `docs/gm-facing/assets/atlas/` are the authoritative atlas overlays. Each feature must have a stable `id` and an `audience` property:

- `"audience": "gm"` keeps the feature in the GM atlas only.
- `"audience": "player"` publishes the feature to both atlases.

GM-only planning fields may be stored as `gm_notes`, `adventure_hooks`, or `events`. Properties beginning with `gm_` and the named planning fields are stripped from player output even after a feature is promoted.

To reveal a prepared feature:

1. Confirm that its player-safe `name`, `description`, `status`, `known_for`, and `access` fields contain no spoilers.
2. Change its `audience` from `gm` to `player` in the GM GeoJSON file.
3. Run `npm run atlas:sync`.
4. Run `npm run atlas:check` and build both MkDocs sites.

`atlas:check` fails if player-visible features drift from the authoritative GM data or if required IDs and audience values are invalid.
