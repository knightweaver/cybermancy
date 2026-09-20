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
