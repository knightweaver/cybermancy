#!/usr/bin/env bash
set -euo pipefail

if ! command -v pmtiles >/dev/null 2>&1; then
  echo "pmtiles CLI is required: https://docs.protomaps.com/pmtiles/cli" >&2
  exit 2
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 SOURCE_PMTILES_URL [OUTPUT_FILE]" >&2
  exit 2
fi

source_archive="$1"
output_archive="${2:-docs/player-facing/assets/atlas/seattle-region-z14.pmtiles}"
maximum_bytes=$((50 * 1024 * 1024))

mkdir -p "$(dirname "$output_archive")"

# Player-atlas extent: Tacoma through Everett, Puget Sound through the western
# Cascade approaches. Zoom 14 is the accepted initial release target.
pmtiles extract \
  "$source_archive" \
  "$output_archive" \
  --bbox=-122.75,47.05,-121.35,48.15 \
  --maxzoom=14

pmtiles verify "$output_archive"

archive_bytes="$(wc -c < "$output_archive" | tr -d ' ')"
archive_mib="$(awk -v bytes="$archive_bytes" 'BEGIN { printf "%.2f", bytes / 1048576 }')"

echo "Created $output_archive ($archive_mib MiB)"

if (( archive_bytes > maximum_bytes )); then
  echo "Size gate failed: archive exceeds 50 MiB; leave it uncommitted and use object storage or reduce the extent/detail." >&2
  exit 1
fi

echo "Size gate passed. The archive remains gitignored until its hosting decision is explicit."
