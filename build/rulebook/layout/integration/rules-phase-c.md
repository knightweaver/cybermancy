# Phase C — Rules Chapters 4–9 Integration

**Status:** IMPLEMENTED — real-corpus proof required before acceptance  
**Transform order:** 30  
**Profiles:** Player Guide and Complete Rulebook  
**Frozen layout authority:** `build/rulebook/layout/rules/rules-layout-v1.json`

This increment binds the accepted **Part II Rules Layout v1.0** to the whole-book Pandoc AST without changing the frozen standalone Rules grammar.

## Accepted source/layout contract

The Rules lane remains an extension of **Long-Form Prose v1.0**. It preserves the accepted Part II treatments for:

- ordinary two-column rules prose;
- suppression of only the first normalized H3 chapter-root heading;
- compact accented ordered-list procedures;
- full-width repeated-header rules reference tables;
- neutral flowable rules blockquotes;
- compact source-order rules artwork capped at `0.20\textheight`;
- deterministic directional-arrow LaTeX rendering.

No new semantic inference is introduced. The deferred Rules semantics remain deferred:

```text
rulesCallout.kind
imageRole=chapter-lead
stateTrack.label+states
```

## Whole-book target

Order 30 replaces only the bodies of these semantic chapter nodes:

```text
4  ch04-frame-rules
5  ch05-item-loadouts
6  ch06-flashbacks
7  ch07-bennies
8  ch08-driving-chases
9  ch09-netrunning
```

The H2 chapter nodes are preserved for later publication-shell lowering. Chapter 10 is the closing boundary for Chapter 9 and is not modified by this stage.

## Composition

`rulebook_layout/rules_integration.py` loads the accepted `build-rulebook-rules.py` producer and uses its inherited Long-Form Prose runtime for the same preprocessing used by the standalone accepted lane:

1. extract all six Part II chapters from both Step 4 publication profiles;
2. require byte-equivalent title/audience/Markdown content between profiles;
3. require the accepted Rules v1.0 config and the integration contract's order-30 chapter map;
4. remove only known MkDocs-only `div` wrapper lines using the inherited prose sanitizer;
5. fail closed on Step 4 image/heading adjacency defects;
6. stage source-order artwork using the inherited prose asset resolver/stager;
7. run each chapter through the accepted `rules.lua` filter with the accepted Markdown reader;
8. reject standalone-shell/chapter-banner leakage from each integrated body fragment.

Unlike the standalone design proof, integration consumes **all Chapters 4–9**, not only proof Chapters 4, 6, 8, and 9. Chapters 5 and 7 therefore receive the same accepted lane grammar before the order-30 stage can pass.

## Adapter transaction

`rulebook_layout/rules_adapters.py` treats all six chapter-body replacements as one `ExactAdapterSpec`:

```text
name     rules
order    30
profiles complete-rulebook, player-guide
```

All mutation occurs on the common exact-adapter staged copy. The adapter works backwards from Chapter 9 to Chapter 4 so replacement cannot invalidate later chapter-boundary indices. If any chapter boundary is missing, duplicated, out of order, or fails an integrated postcondition, the caller AST remains unchanged.

A second successful application must report idempotent and leave the canonical AST SHA-256 unchanged.

## Regression proof

Focused tests:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_rules.py" -v
```

Broader integration suite:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v
```

Real-corpus proofs:

```powershell
python build\rulebook\scripts\build-rulebook-step6-rules-integrated.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-rules-integrated.py --profile complete-rulebook --verbose
```

Expected top-level checks:

```text
INTEGRATION_CONTRACT       PASS
BASE_AST_GENERATION        PASS
STRUCTURAL_PREFLIGHT       PASS
RULES_STAGE_COMPOSITION    PASS
RULES_STAGE_ADAPTER        PASS
RULES_STAGE_IDEMPOTENCY    PASS
INTEGRATED_AST_OUTPUT      PASS
```

Expected AST outputs:

```text
build/rulebook/layout/integration/output/player-guide-phase-c-rules.ast.json
build/rulebook/layout/integration/output/complete-rulebook-phase-c-rules.ast.json
```

Generated ASTs, staged assets, work files, and reports remain noncanonical outputs.

## Acceptance boundary

This implementation is not an acceptance claim. Chapters 4–9 become an accepted Phase C integration proof only after the focused regression test, broader Step 6 integration regressions, and both real-corpus profile runs are clean.
