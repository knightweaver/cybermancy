# Rulebook Step 4 — Master Thread Handoff

## Status

**Step 4 manifest integration and executable build engineering are complete. Final Step 4 acceptance is blocked by one normative Step 2 / Step 3 authored-input conflict.**

## Engineering completed

The Step 4 CLI no longer stops at `NotImplementedError`. It now implements:

- strict adapters for the actual Step 2 and Step 3 JSON schemas;
- Step 2 → Step 3 exact join enforcement;
- frozen baseline alignment checks;
- per-family count and primary-placement validation;
- frozen authored source SHA-256 verification;
- structured family source discovery and logical-entity filtering;
- direct `src/packs/...` materialization;
- authoritative Step 3 ordering and profile topology;
- authored source segmentation from Step 3 selectors;
- Pandoc-oriented Markdown normalization;
- stable `section:`, `family:`, and `entity:` semantic IDs;
- Fast Play as a separate GM-only semantic block;
- cross-reference and audience-isolation checks;
- repository asset staging and provenance;
- `complete-rulebook` and `player-guide` assembly;
- deterministic second-build verification.

A synthetic end-to-end fixture build passes, including byte-identical determinism. The unit suite now has 12 passing tests.

## Newly discovered normative conflict

The supplied manifests do not satisfy the Step 3 manifest's own exact join rule:

- **Step 2 INCLUDE / absent from Step 3:** `docs/gm-facing/world/the-alternate-chessboard.md`
- **Step 3 assembly / not Step 2 INCLUDE:** `docs/player-facing/index.md`

All other tested manifest invariants pass:

- baseline commit alignment;
- 15 structured families joining exactly;
- 980 structured entities reconciling per family;
- all 17 Step 3 authored refs placed exactly once;
- all 15 structured families placed exactly once;
- required complete/player profiles;
- required GM divider contract.

## Required authority decision

Do not silently repair this in Step 4. Resolve it by explicitly revising one upstream normative artifact:

1. **Preserve the approved Step 3 architecture:** revise the Step 2 publication scope so `docs/player-facing/index.md` is an INCLUDE publication input and `docs/gm-facing/world/the-alternate-chessboard.md` is no longer an INCLUDE input; or
2. **Preserve the frozen Step 2 authored set:** revise Step 3 so it assembles `the-alternate-chessboard.md` and does not treat `docs/player-facing/index.md` as an authored input.

Given the approved Step 3 book architecture contains **Welcome to Cybermancy** and does not place **The Alternate Chessboard**, option 1 appears to match the later approved architecture, but Step 4 must not enact that authority change without explicit approval.

## Next execution after resolution

Run `validate`. It must return PASS. Then run `build`. The build will generate both normalized manuscripts, metadata/provenance, staged assets, full validation, and deterministic reproduction. Only then freeze Step 4 and proceed to Step 5 — Content-Only PDF Prototype.

## r3 front-matter integration correction

Assembly manifest v1.1 introduced/used `part.openerRefs` for the included GM Guide front-matter source (`auth.gm-guide-index`) and `gmDivider.afterDividerFrontMatterRefs` to assert its position immediately after the spoiler divider. Step 4 r2 incorrectly counted only chapter `contentRefs` as primary placements. r3 corrects the validator and assembler: part opener refs are primary placements, divider front-matter refs are routing assertions, and GM opener content renders after the divider and before the GM part heading. Regression suite is 14/14 PASS. Repository-level validation against the user's v1.1 manifests must now be rerun before Step 4 is accepted.
