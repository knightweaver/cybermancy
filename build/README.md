# Cybermancy Rulebook Step 4 — Manifest-Integrated Implementation (r3)

This is the third engineering revision of the Step 4 normalization implementation.

## What changed in r3

The v1.1 assembly manifest introduced an explicit GM-section front-matter placement:

- `bookStructure[*].openerRefs`
- `gmDivider.afterDividerFrontMatterRefs`

The r2 validator only counted `chapter.contentRefs` as primary authored placements. That made the valid `auth.gm-guide-index` opener appear to be missing.

r3 corrects that behavior:

- `part.openerRefs` now count as primary assembly placements.
- `gmDivider.afterDividerFrontMatterRefs` is treated as a routing/order assertion, not a second primary placement.
- The validator checks that the divider front-matter refs exactly match the `openerRefs` on `gmDivider.beforePart` when either field is used.
- The assembler renders part opener fragments after the GM spoiler divider and before the GM part heading.
- Two regression tests were added for front-matter primary placement and divider-routing consistency.
- Test suite: 14 tests PASS.

## Why this is the correct interpretation

The v1.1 manifest places `auth.gm-guide-index` at `gm-front-matter`, lists it in the GM part's `openerRefs`, and repeats it under `gmDivider.afterDividerFrontMatterRefs` to establish ordering immediately after the spoiler divider. The divider reference is therefore not a duplicate canonical placement.

## Commands

Validate the v1.1 manifests:

```bash
python pyCybermancy/build-rulebook-source.py validate \
  --publication-manifest cybermancy-rulebook-publication-manifest-v1.1.json \
  --assembly-manifest cybermancy-rulebook-assembly-manifest-v1.1.json \
  --config cybermancy-rulebook-normalization-config-v1.0.json \
  --repo-root . \
  --output-root build/rulebook
```

If validation returns `PASS`, run the production build:

```bash
python pyCybermancy/build-rulebook-source.py build \
  --publication-manifest cybermancy-rulebook-publication-manifest-v1.1.json \
  --assembly-manifest cybermancy-rulebook-assembly-manifest-v1.1.json \
  --config cybermancy-rulebook-normalization-config-v1.0.json \
  --repo-root . \
  --output-root build/rulebook
```

The build performs a complete materialization and a second clean materialization for deterministic-output verification.

## Expected contract checks after this correction

The prior `AUTHORED_PRIMARY_PLACEMENT` failure for `auth.gm-guide-index` should become `PASS`. A new check, `GM_FRONT_MATTER_ROUTING`, should also return `PASS` when the v1.1 manifest fields agree as shown by the diagnostic output.

Any later validation failure should be treated as a newly exposed Step 4 issue rather than bypassed.
