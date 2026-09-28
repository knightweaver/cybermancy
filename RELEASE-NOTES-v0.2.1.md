# Cybermancy v0.2.1

## Compatibility

- Foundry VTT 14 (qualification target: 14.368)
- Daggerheart 2.x (qualification target: 2.10.5)

## Changes from v0.2.0

- Adds the Tier 2 **Cascadian First Peoples Hunter** adversary, including approved
  production portrait/token artwork and Fast Play guidance.
- Adds the Tier 2 **Ballard Reach Floating Commons** social environment, including
  approved production artwork and Fast Play guidance.
- Extends compiled-Compendium validation so the frozen 774-entry v0.2.0 migration
  baseline remains intact while explicitly declared post-baseline additions are
  validated by ID, pack, source path, name, type, source count, and re-extracted
  compiled count.
- Keeps rulebook publication separate from ordinary module-content releases; no
  rulebook inventory/freeze refresh or rulebook PDF rebuild is part of this
  release.

## Qualification

Publication is gated on successful clean-install qualification of the exact
v0.2.1 runtime candidate on Foundry 14.368 / Daggerheart 2.10.5. The resulting
workflow run, artifact identity, runtime SHA-256, and qualification result are
recorded in `release-control/v0.2.1.json` before publication.
