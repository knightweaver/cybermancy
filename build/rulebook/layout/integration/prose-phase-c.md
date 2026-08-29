# Phase C Long-Form Prose integration — Chapters 1–3 and 23–28

This increment binds the frozen Long-Form Prose Layout v1.0 publication grammar to the accepted Step 6 whole-book AST architecture at transformation orders 20 and 80.

## Scope

Order 20 — Player Prose:

- Chapter 1 — `ch01-welcome`
- Chapter 2 — `ch02-resonance`
- Chapter 3 — `ch03-megacorporations`
- profiles: `player-guide`, `complete-rulebook`

Order 80 — GM Prose:

- Chapter 23 — `ch23-project-helios`
- Chapter 24 — `ch24-council`
- Chapter 25 — `ch25-cabal`
- Chapter 26 — `ch26-cabal-projects`
- Chapter 27 — `ch27-chessboard`
- Chapter 28 — `ch28-gm-resonance`
- profile: `complete-rulebook` only

The current Step 6 integration contract and accepted prose config are authoritative for canonical chapter numbering. Historical standalone prose documentation that refers to the former GM numbering 24–29 is superseded by the accepted integrated 23–28 architecture.

## Frozen inputs

The integration composer consumes only the existing accepted production inputs:

- `build/rulebook/layout/prose/prose-layout-v1.json`
- `build/rulebook/layout/prose/pandoc/prose.lua`
- `build/rulebook/scripts/build-rulebook-prose.py`
- Step 4 Complete Rulebook and Player Guide assembled Markdown
- Step 4 staged publication assets

It does not introduce a second Long-Form Prose renderer and does not read canonical Foundry or MkDocs sources.

## Composition behavior

For each applicable chapter the composer:

1. validates the accepted Long-Form Prose v1.0 contract;
2. validates the Step 6 stage order and canonical chapter map;
3. requires exact Player Guide/Complete Rulebook equivalence for Chapters 1–3;
4. reads Chapters 23–28 only from the Complete Rulebook;
5. reuses the accepted prose Markdown sanitizer;
6. rejects Step 4 image/heading adjacency defects rather than repairing them;
7. reuses the accepted prose asset resolver and whitespace-safe staging runtime;
8. runs the body through the frozen `prose.lua` filter;
9. rejects standalone document-shell, Part opener, or chapter-banner leakage.

Missing production artwork is fail-closed in the integrated proof even though the standalone prose regression renderer can display fail-visible placeholders. The integrated whole-book production lane requires resolved staged assets.

## AST behavior

The adapters preserve every semantic H2 chapter node and replace only its body with the accepted prose LaTeX fragment.

Order 20 is one exact three-chapter transaction. Chapter 4 is the closing semantic boundary after Chapter 3.

Order 80 is one exact six-chapter transaction. Chapter 29 is the closing semantic boundary after Chapter 28. The GM divider before Chapter 23 is not modified by this stage.

Each adapter uses the shared `execute_exact_adapter` infrastructure. Missing/duplicated boundaries, profile violations, source/profile drift, asset failure, Pandoc failure, or postcondition failure discard the staged mutation. Reapplying either stage must be a byte-stable no-op.

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_prose.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-prose-integrated.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-prose-integrated.py --profile complete-rulebook --verbose
```

Expected Player Guide top-level checks:

```text
INTEGRATION_CONTRACT                 PASS
BASE_AST_GENERATION                  PASS
STRUCTURAL_PREFLIGHT                 PASS
PLAYER_PROSE_STAGE_COMPOSITION       PASS
PLAYER_PROSE_STAGE_ADAPTER           PASS
PLAYER_PROSE_STAGE_IDEMPOTENCY       PASS
GM_PROSE_STAGE_PROFILE_GATE          PASS
INTEGRATED_AST_OUTPUT                PASS
```

Expected Complete Rulebook checks additionally include:

```text
GM_PROSE_STAGE_COMPOSITION           PASS
GM_PROSE_STAGE_ADAPTER               PASS
GM_PROSE_STAGE_IDEMPOTENCY           PASS
```

Generated ASTs remain noncanonical outputs:

```text
build/rulebook/layout/integration/output/player-guide-phase-c-prose.ast.json
build/rulebook/layout/integration/output/complete-rulebook-phase-c-prose.ast.json
```

Reports remain noncanonical outputs:

```text
build/rulebook/layout/integration/reports/player-guide-integrate-prose.json
build/rulebook/layout/integration/reports/complete-rulebook-integrate-prose.json
```

Publication-shell lowering, integrated LaTeX generation, LuaLaTeX compilation, and rendered whole-book regression remain later stages 130–170.
