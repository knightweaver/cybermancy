# Step 6 integration contract

This directory contains the accepted whole-book integration contract for Cybermancy Rulebook Step 6.

`step6-integration-v1.json` does not replace the Step 3 assembly/book manifest. Step 3 remains authoritative for book architecture, chapter identity, audience, ordering, and the reserved Chapter 13 slot. The Step 6 integration contract binds accepted Step 6 publication grammars to those semantic chapter targets and records deterministic transformation order and regression expectations.

## Profiles

The integration layer supports exactly two publication profiles:

- `complete-rulebook`: Chapters 1–12 and 14–32, with shared/player/GM material and exactly one GM spoiler divider.
- `player-guide`: Chapters 1–12 and 14–22, with shared/player material only and no GM spoiler divider.

Chapter 13 remains reserved. It has no chapter node and no placeholder.

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

## Integration boundary

Phase B defines metadata and static validation only. It does not yet add the one-AST orchestrator, AST adapters, unified LaTeX shell, or final production PDFs. Those are Phase C implementation concerns.

Frozen package grammars remain authoritative and must not be silently redesigned during integration. Local standalone package shells, geometry, preambles, and temporary render directories are not whole-book architecture.

The accepted recto policy for this integration baseline is `preserve-current-clearpage`. Stronger recto-opening behavior is deferred unless explicitly approved as a later design change.

## Regression anchors

The integration contract records current accepted corpus expectations so whole-book integration can fail closed on silent omissions or duplication:

- Character Origins: 18 Ancestories, 9 Communities, 27 staged artwork items.
- Domains: 3 Domains, 73 Domain Cards.
- Equipment: 47 Weapons, 13 Ammunition, 36 Armor, 103 Cybernetics, 19 Drones/Devices, 59 Consumables, 20 Mods, 60 Loot.
- ICE Reference: 13 entries.
- Adversaries: 106 entries.
- Environments: 8 entries.
- Adversary Feature Reference: 344 published representatives from 419 canonical source entries.

`build/rulebook/scripts/tests/test_step6_integration_contract.py` validates this contract against the accepted package metadata without performing AST transformation.
