# Step 6 Stage 130 — Publication-shell lowering

**Status:** implementation ready for cumulative real-corpus proof  
**Order:** 130  
**Input:** one profile AST after all applicable orders 20–120  
**Output:** deterministic shell-lowered Pandoc JSON AST

Stage 130 is the first integration increment that is deliberately tested against a **cumulative** whole-profile AST rather than an isolated chapter/package proof.

It does not render a PDF and does not define the final LaTeX preamble. Its job is to lower the remaining Step 3/Step 4 publication-structure nodes into a stable intermediate shell interface after every chapter-layout transform has already consumed the semantics it needs.

## Fixed-order cumulative proof

`build-rulebook-step6-publication-shell.py` starts from exactly one base Pandoc AST and applies the accepted transforms in the normative order:

```text
10   structural preflight
20   Player Prose, Chapters 1–3
30   Rules, Chapters 4–9
40   Character Origins, Chapters 10–11
50   ClassPackage, Chapter 12
60   DomainPackage, Chapter 14
70   Equipment, Chapters 15–22
80   GM Prose, Chapters 23–28                 Complete only
90   ICE Reference, Chapter 29                Complete only
100  Adversaries, Chapter 30                  Complete only
110  Environments, Chapter 31                 Complete only
120  Adversary Feature Reference, Chapter 32  Complete only
130  publication-shell lowering
```

The runner reuses the already accepted composers and adapters. It does not create another implementation of any frozen chapter grammar.

## Part-boundary integration correction

Cumulative assembly exposed an integration-boundary defect that isolated chapter proofs could not reveal: the original prose/rules body adapters used only the next Chapter H2 as their body boundary. For the last chapter of a Part, that slice crossed the intervening Part H1 and could consume the next Part node.

The corrected adapters stop at the **earliest** of:

- the next authoritative Chapter H2; or
- an intervening top-level Part H1.

This specifically protects the boundaries after Chapters 3, 9, and 28 while preserving the same accepted chapter body fragments. It is an integration correction, not a frozen-layout redesign.

## Stage 130 readiness gate

Before shell lowering commits, the cumulative AST must prove:

- all expected Part H1 nodes are still present exactly once and in Step 3 order;
- all Chapter headers still owned by the generic publication shell are present exactly once with the accepted title/audience;
- Chapters 29–32 in the Complete Rulebook no longer have semantic H2 headers because orders 90–120 already lowered their frozen package headers;
- every prose/rules/Character Origins chapter body that requires the shared two-column shell is exactly one accepted LaTeX fragment;
- every applicable structured `family:*` body is exactly one accepted LaTeX fragment;
- the GM divider count still matches the profile contract.

Any failure leaves the input AST unchanged.

## Lowered shell interface

Stage 130 replaces remaining semantic publication nodes with stable intermediate LaTeX blocks:

```text
Part H1
  -> \CMIntegratedPart{roman}{title}{audience}{part-id}

Chapter H2
  -> \CMIntegratedChapter{number}{title}{audience}{chapter-id}

GM divider
  -> \CMIntegratedGMDivider{GM MATERIAL — SPOILERS BEYOND THIS POINT}
```

Stages 150–160 will own the definitions and compilation of these whole-book macros. Stage 130 therefore does not invent a second document preamble or independently restyle accepted package headers.

### Shared two-column context

The frozen Long-Form Prose, Rules, and Character Origins filters assume an outer `multicols` context because their full-width table/image primitives temporarily end and reopen it. Stage 130 establishes that outer context for:

```text
Chapters 1–11
Chapters 23–28 (Complete only)
```

It does not add the generic wrapper around ClassPackage, DomainPackage, Equipment, ICE, Adversary, Environment, or Adversary Feature bodies, whose accepted package grammars own their internal layout.

### Package-owned headers

Complete Rulebook Chapters 29–32 already carry the frozen raw-LaTeX headers emitted by their accepted package transforms. Stage 130 preserves those blocks exactly and refuses to proceed if the semantic H2 header for any of those chapters is still present.

## Preserved material

Shell lowering changes only the exact Part headers, generic Chapter headers, GM divider, and required shared-column wrappers. Other top-level blocks are retained in source order. This includes GM front matter between the Part V opener and Chapter 23.

The accepted recto policy remains `preserve-current-clearpage`; stronger recto enforcement is not introduced here.

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_publication_shell.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-publication-shell.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-publication-shell.py --profile complete-rulebook --verbose
```

Expected high-level checks include:

```text
INTEGRATION_CONTRACT         PASS
STRUCTURAL_PREFLIGHT         PASS
ORDER20_PLAYER_PROSE         PASS
ORDER30_RULES                PASS
ORDER40_CHARACTER_ORIGINS    PASS
ORDERS50_60_CHARACTER_OPTIONS PASS
ORDER70_EQUIPMENT            PASS
PHASE_C_FIXED_ORDER          PASS
STAGE130_PUBLICATION_SHELL   PASS
STAGE130_IDEMPOTENCY         PASS
STAGE130_AST_OUTPUT          PASS
```

The Complete Rulebook additionally proves orders 80, 90, and 100–120.

Generated ASTs remain noncanonical outputs:

```text
build/rulebook/layout/integration/output/
    player-guide-stage130-publication-shell.ast.json
    complete-rulebook-stage130-publication-shell.ast.json
```

Stage 130 is not accepted until both real-corpus profile runs and the integration regression suite pass cleanly.
