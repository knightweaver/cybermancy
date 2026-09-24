# Cybermancy v0.1.14 / F13-DH1 freeze

This migration treats the published Foundry 13 / Daggerheart 1.x line as immutable historical evidence.

## Frozen release identity

| Release | Commit | Published | Qualification |
| --- | --- | --- | --- |
| v0.1.14 | 92d3fa98b04a87b619b6aa63fb52d841d2859406 | 2026-09-22 15:30:42 UTC | Foundry 13; Daggerheart 1.2–1.9 |
| F13-DH1 | 92d3fa98b04a87b619b6aa63fb52d841d2859406 | 2026-09-23 04:23:01 UTC | Compatibility alias of exactly the same qualified release |

Both releases are published, non-draft, non-prerelease releases. The alias is not a separate build.

The three published assets are byte-identical between the releases:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| cybermancy-v0.1.14.zip | 416,948,124 | 157623168893bfcc4d755b50182037e2a50d726d76cc30bf9bcd8413571f5606 |
| module.json | 5,185 | 5f2a234195d6a70876418c066b14edfa18e14dd19fad52e85d5998dfdf873a97 |
| SHA256SUMS.txt | 167 | a1856b517d3aa3ec76c6c44204cb9b5bc285efafefa4b75a85ab8f65336092b0 |

The existing compatibility-release-control/F13-DH1.json remains the authoritative alias control record. It records the final pre-migration baseline as Foundry 13 / Daggerheart major 1, with Daggerheart 1.2–1.9 support.

## Freeze rules

The v0.2.0 migration MUST NOT move or recreate either tag; edit either release, release notes, published assets, or historical hashes; reinterpret the old release as qualified on Foundry 14 or Daggerheart 2; rewrite the historical compatibility alias control record; or modify the v0.1.14 production artifact to make it look forward-compatible.

Migration work occurs only on migration/v0.2.0-f14-dh2 and later v0.2.0-specific branches/commits. The v0.1.14 tag commit remains the immutable legacy source snapshot.
