# Phase C Character Origins integration — Chapters 10–11

This increment binds the frozen Character Origins v1.0 publication grammar to the accepted Step 6 whole-book AST architecture at transformation order 40.

## Frozen inputs

The integration composer consumes only the existing accepted production inputs:

- `build/rulebook/layout/character-origins/character-origins-layout-v1.json`
- `build/rulebook/layout/character-origins/pandoc/character-origins.lua`
- `build/rulebook/scripts/build-rulebook-character-origins.py`
- `build/rulebook/scripts/build-rulebook-prose.py`
- Step 4 Complete Rulebook and Player Guide assembled Markdown
- Step 4 staged publication assets

It does not introduce a second Character Option Entry renderer and does not read canonical Foundry or MkDocs sources.

The frozen regression contract remains:

- Chapter 10 — 18 Ancestories, exactly 2 Features each;
- Chapter 11 — 9 Communities, exactly 1 Community Feature each;
- exact accepted entry identity and order;
- byte-equivalent Complete Rulebook and Player Guide normalized chapter fragments;
- 27 staged artwork references;
- Character Origins v1.0 / frozen / accepted.

## Integration behavior

The composer reuses the frozen Character Origins parser, annotation grammar, asset staging, and Lua filter. Each annotated chapter is converted by Pandoc to a body-only LaTeX fragment. Standalone document-shell tokens (`documentclass`, `usepackage`, `begin{document}`, `end{document}`) are rejected.

The order-40 adapter preserves the semantic H2 nodes `ch10-ancestories` and `ch11-communities`. It replaces only their bodies:

```text
ch10-ancestories body  -> frozen Character Origins Chapter 10 LaTeX fragment
ch11-communities body  -> frozen Character Origins Chapter 11 LaTeX fragment
```

Chapter 12 remains the boundary after the Chapter 11 body. Preserving the Chapter 10/11 H2 nodes keeps whole-book chapter semantics available for later publication-shell lowering.

Both chapter-body replacements execute through one common exact adapter on a staged AST copy. Missing/duplicated chapter boundaries, corpus drift, profile drift, missing artwork, Pandoc failure, or postcondition failure discard the entire mutation. Reapplying the stage must be a byte-stable no-op.

Character Origins applies to both `player-guide` and `complete-rulebook`.

## Proof commands

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_character_origins.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-character-origins-integrated.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-character-origins-integrated.py --profile complete-rulebook --verbose
```

Expected top-level proof checks are:

```text
INTEGRATION_CONTRACT                    PASS
BASE_AST_GENERATION                     PASS
STRUCTURAL_PREFLIGHT                    PASS
CHARACTER_ORIGINS_STAGE_COMPOSITION     PASS
CHARACTER_ORIGINS_STAGE_ADAPTER         PASS
CHARACTER_ORIGINS_STAGE_IDEMPOTENCY     PASS
INTEGRATED_AST_OUTPUT                   PASS
```

Generated ASTs remain noncanonical outputs under `build/rulebook/layout/integration/output/`.
