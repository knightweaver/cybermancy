# Step 6 integration contract

This directory contains the accepted whole-book integration contract for Cybermancy Rulebook Step 6.

`step6-integration-v1.json` does not replace the Step 3 assembly/book manifest. Step 3 remains authoritative for book architecture, chapter identity, audience, ordering, and the reserved Chapter 13 slot. The Step 6 integration contract binds accepted Step 6 publication grammars to those semantic chapter targets and records deterministic transformation order and regression expectations.

## Profiles

The integration layer supports exactly two publication profiles:

- `complete-rulebook`: Chapters 1–12 and 14–32, with shared/player/GM material and exactly one GM spoiler divider.
- `player-guide`: Chapters 1–12 and 14–22, with shared/player material only and no GM spoiler divider.

Chapter 13 remains reserved. It has no chapter node and no placeholder.

The contract carries the explicit chapter ID/title/audience map used by Phase C structural preflight. This is a runtime binding of the accepted Step 3 architecture, not a second book-architecture authority.

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

## Deterministic transformation order

Step 6 integration is defined as one base Pandoc JSON AST per profile followed by ordered transforms:

```text
10   structural preflight
20   player prose, Chapters 1–3
30   rules, Chapters 4–9
40   character origins, Chapters 10–11
50   ClassPackage, Chapter 12
60   DomainPackage, Chapter 14
70   Equipment, Chapters 15–22
80   GM prose, Chapters 23–28                 Complete Rulebook only
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

Semantic replacement occurs before publication-shell lowering while chapter/family semantics remain intact.

## Phase C runtime

The Phase C runtime is implemented by:

```text
build/rulebook/scripts/build-rulebook-step6-integrated.py
build/rulebook/scripts/rulebook_layout/integration.py
build/rulebook/scripts/rulebook_layout/integration_ast.py
build/rulebook/scripts/rulebook_layout/character_options_integration.py
build/rulebook/scripts/rulebook_layout/character_options_adapters.py
build/rulebook/scripts/rulebook_layout/equipment_integration.py
build/rulebook/scripts/rulebook_layout/equipment_adapters.py
```

The structural preflight is fail-closed. Before any package adapter runs it verifies:

- the exact profile chapter ID sequence;
- exactly one chapter node for every required chapter;
- Chapter 13 remains absent;
- chapter `data-audience` markers match the accepted map;
- every structured `family:*` target required by the profile appears exactly once;
- Complete Rulebook contains exactly one `GM MATERIAL — SPOILERS BEYOND THIS POINT` divider;
- Player Guide contains no divider and no GM chapter targets.

The common exact-adapter runtime records `expected`, `found`, `replaced`, `remaining`, and integrated-postcondition counts. Mutations are staged on a deep copy and committed only after all postconditions pass, so a failed adapter does not leave a partially modified AST. Reapplying an already integrated adapter must be a byte-stable no-op.

### Character Options proof — Chapters 12 and 14

The order-50/60 Character Options stage integrates the already accepted all-Class ClassPackage grammar and all-Domain DomainPackage grammar without introducing a second layout implementation or standalone document shell.

Chapter 12 consumes exactly the current frozen **5 Classes and 10 Subclasses** from the Step 4 semantic corpus. Each Class is composed through the existing ClassPackage semantic composer, including linked Subclasses, Class/Subclass Features, staged publication artwork, Starting Package data, and Character Guide references. The accepted refined ClassPackage body helpers are reused directly. Standalone `documentclass`, geometry, font setup, color definitions, and `\begin{document}`/`\end{document}` are not inserted into the whole-book AST.

The `family:classes` body contains the complete deterministic sequence of ClassPackages. Because Subclasses are already rendered inside their owning ClassPackage, the independent `family:subclasses` body is replaced with an exact raw-LaTeX marker rather than rendering the same Subclasses a second time. The semantic wrapper remains present for deterministic postconditions and source-family traceability. Coverage validation requires every Class and every Subclass to be consumed exactly once.

Chapter 14 consumes the frozen **3 Domains / 73 Domain Cards** from Step 4 `domainPackages` and `domainSemantics`. The existing accepted DomainPackage identity, level-group, card, and artwork grammar is reused as body-only LaTeX, with LuaLaTeX-safe render assets staged beneath the integration work directory. No standalone DomainPackage shell is introduced.

Orders 50 and 60 form one transaction for this proof. The runtime deep-copies the base AST once, applies the Chapter 12 adapter, then the Chapter 14 adapter. If Chapter 14 fails after Chapter 12 has staged successfully, both mutations are discarded. A second successful application must report both adapters idempotent and leave the AST SHA-256 unchanged.

Character Options applies to both `player-guide` and `complete-rulebook`.

### Equipment proof — Chapters 15–22

Equipment is the accepted order-70 Phase C production proof. The integration composer consumes the current Step 4 `cybermancy-step4-structured-entities-v1.3` sidecar, the accepted Equipment registry, and the eight accepted family configs. It validates the frozen corpus counts and config contracts, then renders only the accepted family-body grammar—never the standalone Equipment document shell.

The order-70 Equipment stage targets exactly:

```text
15  family:weapons
16  family:ammo
17  family:armors
18  family:cybernetics
19  family:drones-devices
20  family:consumables
21  family:mods
22  family:loot
```

Weapons reuse the accepted four-Tier catalog plus Weapon Actions and Critical Effects reference grammar. The remaining families reuse the accepted generic catalog grammar. No local `documentclass`, geometry, font setup, chapter wrapper, or other standalone shell is inserted into the integrated AST.

The eight replacements are transactional as one stage: all changes occur on a staged AST copy. If a later Equipment family is missing, duplicated, invalid, or fails its postconditions, earlier staged replacements are discarded and the original AST remains untouched. A second successful application of the entire Equipment stage must be a byte-stable no-op.

Equipment applies to both `player-guide` and `complete-rulebook`.

### Chapter 29 ICE proof

Chapter 29 is the accepted first Complete-only package proof. It reuses the frozen ICEReferencePackage v1 composer and integration fragments, requires the complete 13-entry ICE corpus, and replaces exactly the Chapter 29 semantic heading plus the `family:features` body.

Default proof commands consume the current Step 4 assembled manuscript and generate one Pandoc JSON AST for the selected profile:

```powershell
python build\rulebook\scripts\build-rulebook-step6-integrated.py preflight --profile player-guide
python build\rulebook\scripts\build-rulebook-step6-integrated.py preflight --profile complete-rulebook
python build\rulebook\scripts\build-rulebook-step6-integrated.py integrate-character-options --profile player-guide
python build\rulebook\scripts\build-rulebook-step6-integrated.py integrate-character-options --profile complete-rulebook
python build\rulebook\scripts\build-rulebook-step6-integrated.py integrate-equipment --profile player-guide
python build\rulebook\scripts\build-rulebook-step6-integrated.py integrate-equipment --profile complete-rulebook
python build\rulebook\scripts\build-rulebook-step6-integrated.py integrate-ice --profile complete-rulebook
```

An existing Pandoc AST can instead be supplied with `--ast-input`. Use `--verbose` for the full machine-readable report.

Generated Phase C ASTs, work files, render-only assets, and reports remain noncanonical outputs beneath the integration `output/`, `work/`, and `reports/` directories.

## Current boundary

This milestone implements structural preflight, Character Options Chapters 12 and 14, Equipment Chapters 15–22, and Chapter 29 as isolated package-integration stages. Chapters 12/14 still require real-corpus Player Guide and Complete Rulebook proof runs before they are accepted as completed integration proofs.

It does **not** yet apply Chapters 1–11 other than Chapter 12, Chapters 23–28 layout transforms, Chapters 30–32 encounter adapters, publication-shell lowering, the unified LuaLaTeX shell, or final PDFs. Those remain subsequent Phase C/Phase D work.

Frozen package grammars remain authoritative and must not be silently redesigned during integration. Local standalone package shells, geometry, preambles, and temporary render directories are not whole-book architecture.

The accepted recto policy for this integration baseline is `preserve-current-clearpage`. Stronger recto-opening behavior is deferred unless explicitly approved as a later design change.

## Regression anchors

The integration contract records current accepted corpus expectations so whole-book integration can fail closed on silent omissions or duplication:

- Character Origins: 18 Ancestories, 9 Communities, 27 staged artwork items.
- Classes and Subclasses: 5 Classes, 10 Subclasses.
- Domains: 3 Domains, 73 Domain Cards.
- Equipment: 47 Weapons, 13 Ammunition, 36 Armor, 103 Cybernetics, 19 Drones/Devices, 59 Consumables, 20 Mods, 60 Loot.
- ICE Reference: 13 entries.
- Adversaries: 106 entries.
- Environments: 8 entries.
- Adversary Feature Reference: 344 published representatives from 419 canonical source entries.

`build/rulebook/scripts/tests/test_step6_integration_contract.py` validates the static contract. `test_step6_integration_runtime.py` validates structural preflight, common exact-adapter behavior, profile gating, and Chapter 29 idempotency. `test_step6_integration_character_options.py` validates the Chapter 12/14 exact replacements, cross-stage rollback, both-profile gating, frozen Class/Subclass counts, and combined idempotency. `test_step6_integration_equipment.py` validates Equipment composition, atomic stage rollback, both-profile gating, and Equipment idempotency.
