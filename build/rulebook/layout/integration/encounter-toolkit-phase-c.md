# Phase C Encounter Toolkit integration proof

This increment binds the frozen standalone Encounter Toolkit publication grammars to the Complete Rulebook Pandoc AST without redesigning Chapters 30-32.

## Scope

The proof covers the three Complete-Rulebook-only transforms already reserved by `step6-integration-v1.json`:

```text
100  Chapter 30  Adversaries                 family:adversaries
110  Chapter 31  Environments                family:environments
120  Chapter 32  Adversary Feature Reference family:adversaries-features
```

The standalone Encounter Toolkit producer remains the visual-production authority. The integration composer invokes `build-rulebook-encounters.py build --family all --tex-only`, validates the frozen production reports, and extracts only the accepted chapter opener plus package body from each emitted TeX document. Local `documentclass`, `usepackage`, `begin{document}`, and `end{document}` shell material is rejected rather than inserted into the book AST.

Frozen corpus anchors remain:

- AdversaryPackage v1.1: 106 entries;
- EnvironmentPackage v1.0: 8 entries;
- Adversary Feature Reference v1.0: 344 publication representatives derived from 419 canonical standalone Features.

The composer additionally verifies the accepted Chapter 30 two-column/multicol-safe flow grammar, the Chapter 31 opener sharing its page with the first Environment, and the Chapter 32 two-column reference grammar.

## Transaction and idempotency

Each chapter adapter replaces exactly one semantic chapter heading and exactly one structured family body. Chapters 30-32 are then committed as a single staged transaction: any failure discards all three staged mutations. Reapplying a successfully integrated stage must make all three adapters idempotent and leave the canonical AST SHA-256 unchanged.

The proof uses the existing Step 6 base-AST loader and structural preflight, so it still generates exactly one base Pandoc AST for the Complete Rulebook profile.

## Proof commands

Run the focused regression first:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_encounters.py" -v
```

Then run the current Step 6 integration regression suite:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v
```

Finally run the real-corpus proof:

```powershell
python build\rulebook\scripts\build-rulebook-step6-encounter-integrated.py --profile complete-rulebook --verbose
```

A successful real-corpus proof must report PASS for structural preflight, Encounter Toolkit composition, all three chapter adapters, the combined transactional stage, combined idempotency, and integrated AST output.

Generated proof artifacts remain noncanonical beneath the existing integration `work/`, `reports/`, and `output/` directories. The default integrated proof AST is:

```text
build/rulebook/layout/integration/output/complete-rulebook-phase-c-encounters.ast.json
```

This increment does not yet perform publication-shell lowering, unified LaTeX generation, LuaLaTeX compilation, or rendered whole-book regression.
