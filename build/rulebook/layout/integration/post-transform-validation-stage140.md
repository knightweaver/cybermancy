# Stage 140 — Post-transform semantic validation

**Status:** IMPLEMENTED — pending real-corpus acceptance  
**Order:** 140  
**Input:** accepted Stage 130 shell-lowered Pandoc AST  
**Output:** byte-identical validated AST for Stage 150 integrated LaTeX generation

## Purpose

Stage 140 is the fail-closed semantic gate between AST transformation and final integrated LaTeX generation.

It does **not** render chapters, change frozen package grammar, edit game content, or mutate the Stage 130 AST. Its purpose is to prove that the cumulative output of orders 10–130 is structurally safe to hand to Stage 150.

The validator is implemented as a pure inspection function in:

```text
build/rulebook/scripts/rulebook_layout/post_transform_validation.py
```

The real-corpus proof driver is:

```text
build/rulebook/scripts/build-rulebook-step6-post-transform-validation.py
```

## Input contract

By default the proof driver consumes the deterministic Stage 130 outputs:

```text
build/rulebook/layout/integration/output/player-guide-stage130-publication-shell.ast.json
build/rulebook/layout/integration/output/complete-rulebook-stage130-publication-shell.ast.json
```

Stage 140 requires the accepted `step6-integration-v1.json` contract with transformation order 140 = `post-transform-validation`.

## Validation gates

Stage 140 validates all of the following without mutation.

### 1. Exact Stage 130 publication shell

For the selected profile, every expected integrated shell primitive must occur exactly once:

```text
\CMIntegratedPart{roman}{title}{audience}{part-id}
\CMIntegratedChapter{number}{title}{audience}{chapter-id}
\CMIntegratedGMDivider{GM MATERIAL — SPOILERS BEYOND THIS POINT}
```

Every prose/rules/Character Origins chapter that uses the shared outer two-column context must also have exactly one Stage 130 closing `\end{multicols}` block.

Malformed, duplicate-purpose, or profile-inapplicable `% CM-INTEGRATED-SHELL ...` markers are rejected.

### 2. Canonical whole-book landmark order

The validator reconstructs a profile-specific sequence of significant publication landmarks and requires exact agreement with the integration contract:

- Part boundaries;
- remaining Stage 130 chapter shells;
- structured `family:*` containers;
- the Complete Rulebook GM divider;
- package-owned Chapters 29–32 through their structured family anchors.

This makes GM-divider placement and Part/Chapter/family sequencing explicit rather than relying only on counts.

### 3. No semantic shell residue

After Stage 130 there must be no remaining:

- `rb-part` Header;
- `rb-chapter` Header;
- Header carrying a canonical Part ID;
- Header carrying a canonical Chapter ID.

Lower-level unrelated editorial headings are not rejected merely for being Headers.

### 4. Reserved Chapter 13 remains absent

No semantic identifier or integrated raw shell may contain a Chapter 13 target.

### 5. Structured family integrity

Every profile-applicable structured family must:

- occur exactly once;
- remain in canonical publication order;
- contain exactly one accepted LaTeX RawBlock body.

This covers Classes/Subclasses, Domains, Equipment, ICE, Adversaries, Environments, and the Adversary Feature Reference as applicable to the selected profile.

### 6. Package-owned header preservation

For the Complete Rulebook, Chapters 29–32 retain their frozen package-owned chapter headers from orders 90–120. Stage 140 requires one non-shell LaTeX header block immediately before each corresponding family container:

```text
29  family:features
30  family:adversaries
31  family:environments
32  family:adversaries-features
```

Stage 140 does not reinterpret or replace those frozen package headers.

### 7. Multicolumn balance

The cumulative raw LaTeX fragments must contain equal numbers of:

```text
\begin{multicols}{2}
\end{multicols}
```

and every outer two-column chapter introduced by Stage 130 must have its exact Stage 130 closing block.

This catches cross-fragment scope leakage before integrated LaTeX generation.

### 8. No standalone document-shell leakage

Frozen chapter/package fragments may not contribute:

```text
\documentclass
\begin{document}
\end{document}
```

Those responsibilities belong exclusively to Stage 150.

### 9. Profile audience boundary

The Player Guide must contain no GM shell blocks and no GM divider.

The Complete Rulebook must retain its GM shell content and exactly one GM divider.

### 10. Non-mutating proof

The canonical AST SHA-256 before and after validation must be identical.

The Stage 140 driver writes a canonical copy only after validation passes and verifies that its SHA-256 still matches the Stage 130 input.

## Outputs

Validated ASTs:

```text
build/rulebook/layout/integration/output/player-guide-stage140-validated.ast.json
build/rulebook/layout/integration/output/complete-rulebook-stage140-validated.ast.json
```

Reports:

```text
build/rulebook/layout/integration/reports/player-guide-stage140-post-transform-validation.json
build/rulebook/layout/integration/reports/complete-rulebook-stage140-post-transform-validation.json
```

These remain generated, noncanonical build artifacts.

## Regression coverage

`test_step6_integration_post_transform_validation.py` covers:

- valid Player Guide Stage 140 inspection;
- valid Complete Rulebook package-header ownership;
- non-mutating validation;
- missing Stage 130 chapter shell;
- residual semantic Chapter header;
- GM-divider misplacement;
- standalone LaTeX document-shell leakage;
- reserved Chapter 13 leakage;
- preservation of unrelated lower-level editorial Headers.

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_post_transform_validation.py" -v

python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-post-transform-validation.py --profile player-guide --verbose

python build\rulebook\scripts\build-rulebook-step6-post-transform-validation.py --profile complete-rulebook --verbose
```

If both real-corpus proofs pass, Stage 140 is ready for acceptance and the next integration increment is Stage 150 — integrated LaTeX generation.
