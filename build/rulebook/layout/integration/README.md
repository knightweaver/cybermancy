# Step 6 integration contract

This directory contains the accepted whole-book integration contract and proof documentation for Cybermancy Rulebook Step 6.

`step6-integration-v1.json` does **not** replace the Step 3 assembly/book manifest. Step 3 remains authoritative for book architecture, chapter identity, audience, ordering, and the reserved Chapter 13 slot. The Step 6 contract binds frozen publication grammars to those semantic targets and records deterministic transform order and regression expectations.

## Profiles

The integration layer supports exactly two publication profiles:

- `complete-rulebook`: Chapters 1–12 and 14–32, shared/player/GM material, exactly one GM spoiler divider.
- `player-guide`: Chapters 1–12 and 14–22, shared/player material only, no GM spoiler divider.

Chapter 13 remains reserved and has no chapter node or placeholder.

## Deterministic transform order

One base Pandoc JSON AST is created per profile and transformed in this order:

```text
10   structural preflight
20   Player Prose, Chapters 1–3
30   Rules, Chapters 4–9
40   Character Origins, Chapters 10–11
50   ClassPackage, Chapter 12
60   DomainPackage, Chapter 14
70   Equipment, Chapters 15–22
80   GM Prose, Chapters 23–28                 Complete Rulebook only
90   ICE Reference, Chapter 29                Complete Rulebook only
100  Adversaries, Chapter 30                  Complete Rulebook only
110  Environments, Chapter 31                 Complete Rulebook only
120  Adversary Feature Reference, Chapter 32  Complete Rulebook only
130  publication-shell lowering
140  post-transform semantic validation
150  integrated LaTeX generation
160  LuaLaTeX
170  rendered-output regression
```

Semantic replacement occurs before publication-shell lowering while chapter/family semantics remain available.

## Current accepted integration state

All Phase C chapter-layout transforms have been individually proven against the real Step 4 corpus and accepted:

```text
20   Chapters 1–3     Long-Form Player Prose
30   Chapters 4–9     Rules
40   Chapters 10–11   Character Origins
50   Chapter 12       Classes + Subclasses
60   Chapter 14       Domains + Domain Cards
70   Chapters 15–22   Equipment & Technology
80   Chapters 23–28   Long-Form GM Prose
90   Chapter 29       ICE Reference
100  Chapter 30       Adversaries
110  Chapter 31       Environments
120  Chapter 32       Adversary Feature Reference
```

Stage **130 publication-shell lowering is accepted** after cumulative Player Guide and Complete Rulebook proofs passed against one deterministic AST per profile.

Stage **140 post-transform semantic validation is implemented and awaiting real-corpus acceptance**. It consumes the deterministic Stage 130 AST without mutation and emits a byte-identical validated AST for Stage 150.

See:

```text
prose-phase-c.md
rules-phase-c.md
character-origins-phase-c.md
encounter-toolkit-phase-c.md
publication-shell-stage130.md
post-transform-validation-stage140.md
```

## Cumulative integration corrections discovered at Stage 130

The first cumulative assembly exposed a boundary defect that isolated chapter proofs could not reveal. The original prose/rules body adapters used the next Chapter H2 as the only body boundary, so the last chapter of a Part could cross and consume the intervening Part H1.

The corrected integration boundary is the earliest of:

- the next authoritative Chapter H2; or
- an intervening top-level Part H1.

This protects the Part boundaries after Chapters 3, 9, and 28 without changing any accepted chapter grammar or rulebook content.

Stage 130 also established that semantic H2 display text is not itself the publication-title authority. Exact semantic chapter ID/order and audience remain routing preconditions; Stage 130 canonicalizes the visible integrated Chapter title from the accepted Step 6 integration contract.

## Structured package targets

The accepted structured replacements are:

```text
Chapter 12  family:classes + family:subclasses
Chapter 14  family:domains
Chapter 15  family:weapons
Chapter 16  family:ammo
Chapter 17  family:armors
Chapter 18  family:cybernetics
Chapter 19  family:drones-devices
Chapter 20  family:consumables
Chapter 21  family:mods
Chapter 22  family:loot
Chapter 29  family:features
Chapter 30  family:adversaries
Chapter 31  family:environments
Chapter 32  family:adversaries-features
```

Chapters 29–32 are Complete Rulebook only.

## Fail-closed runtime

The structural preflight verifies, before semantic replacement:

- exact profile chapter identity and order;
- exactly one required chapter node;
- no Chapter 13 node;
- authoritative `data-audience` markers;
- required `family:*` targets exactly once;
- Complete Rulebook has exactly one `GM MATERIAL — SPOILERS BEYOND THIS POINT` divider;
- Player Guide has no GM divider or GM chapter targets.

Common exact adapters stage mutations on a deep copy and commit only after exact postconditions pass. Reapplying an integrated stage must be a byte-stable no-op.

Stage 130 adds a cumulative readiness gate requiring all Part boundaries to survive orders 20–120, all generic prose/rules/origin bodies to be exact accepted LaTeX fragments, all applicable structured family bodies to be exact accepted LaTeX fragments, and package-owned Chapter 29–32 headers to have already been lowered.

Stage 140 then verifies the fully lowered cumulative AST without changing it. Validation includes exact shell counts, canonical landmark order, absence of semantic Part/Chapter residue, Chapter 13 exclusion, structured-family integrity, package-owned header preservation, multicolumn balance, profile audience separation, and absence of standalone LaTeX document-shell leakage.

## Publication-shell lowering

Stage 130 lowers the remaining semantic publication nodes to stable intermediate macros:

```text
\CMIntegratedPart{roman}{title}{audience}{part-id}
\CMIntegratedChapter{number}{title}{audience}{chapter-id}
\CMIntegratedGMDivider{GM MATERIAL — SPOILERS BEYOND THIS POINT}
```

It establishes the shared outer two-column context required by accepted prose/rules/Character Origins fragments in Chapters 1–11 and, for the Complete Rulebook, Chapters 23–28.

It does not create a second standalone document shell and does not replace the frozen package-owned headers already emitted for Chapters 29–32. The final whole-book macro definitions and preamble belong to Stage 150.

The accepted recto policy remains `preserve-current-clearpage`.

## Regression anchors

The integration contract records these current corpus expectations:

- Character Origins: 18 Ancestories, 9 Communities, 27 staged artwork items.
- Classes/Subclasses: 5 Classes, 10 Subclasses.
- Domains: 3 Domains, 73 Domain Cards.
- Equipment: 47 Weapons, 13 Ammunition, 36 Armor, 103 Cybernetics, 19 Drones/Devices, 59 Consumables, 20 Mods, 60 Loot.
- ICE Reference: 13 entries.
- Adversaries: 106 entries.
- Environments: 8 entries.
- Adversary Feature Reference: 344 published representatives from 419 canonical source entries.

## Stage 140 proof commands

From repository root, after the accepted Stage 130 outputs exist:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_post_transform_validation.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-post-transform-validation.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-post-transform-validation.py --profile complete-rulebook --verbose
```

Generated ASTs, work files, render-only assets, and reports remain noncanonical outputs beneath `build/rulebook/layout/integration/{output,work,reports}/`.
