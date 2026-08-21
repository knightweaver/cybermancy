# Cybermancy Rulebook Source Inventory

Schema: `cybermancy-rulebook-inventory-v0.2.4`  
Scanner: `0.2.4`  
Git commit: `8d7782aff5dbe0f212910ecffa649acd2c0eb0cb`

## Scope

This is a read-only corpus inventory. It identifies source types, publication audiences,
generated content, MkDocs-specific constructs, dependencies, and generator/source drift.
It does **not** decide canonical authority or rulebook inclusion; those are Phase 2 decisions.

## Summary

| Metric | Count |
|---|---:|
| Files scanned | 4778 |
| Documents | 1056 |
| Player-site documents | 585 |
| GM-site documents | 459 |
| Player nav entries | 20 |
| GM nav entries | 15 |
| Generated documents | 994 |
| Hand-authored/source documents | 62 |
| Dynamic MkDocs documents | 18 |
| Documents requiring normalization | 1028 |
| Stub documents | 3 |
| Foundry folder records | 109 |
| Organizational files/pages | 123 |
| Files with known exceptions | 139 |
| Files with review flags | 22 |
| Files with unresolved local dependencies | 3 |
| Duplicate-content groups | 251 |

## Files by source family

| Metric | Count |
|---|---:|
| asset | 257 |
| config | 2 |
| data | 15 |
| generator | 65 |
| gm | 959 |
| player | 1445 |
| repository | 32 |
| shared-docs | 3 |
| structured-source | 2000 |

## Files by audience

| Metric | Count |
|---|---:|
| developer | 67 |
| gm | 959 |
| player | 1445 |
| shared | 2018 |
| unknown | 289 |

## Files by content scope

| Metric | Count |
|---|---:|
| campaign | 305 |
| developer | 86 |
| setting | 16 |
| system | 2286 |
| unknown | 2085 |

## Files by kind

| Metric | Count |
|---|---:|
| asset | 1631 |
| code | 40 |
| config | 4 |
| data | 1872 |
| document | 1056 |
| other | 166 |
| presentation | 9 |

## Files by authorship/source status

| Metric | Count |
|---|---:|
| generated | 1020 |
| hand-authored-or-source | 1961 |
| unknown | 1797 |

## MkDocs sites

- **player** — docs_dir `docs/player-facing`, nav entries 20
- **gm** — docs_dir `docs/gm-facing`, nav entries 15

## MkDocs / normalization features

| Metric | Count |
|---|---:|
| attribute-list | 32 |
| include-markdown | 1 |
| jinja-expression | 17 |
| jinja-statement | 17 |
| load-csv | 16 |
| raw-html | 1030 |

## Print-normalization flags

| Metric | Count |
|---|---:|
| attribute-list | 32 |
| html-heavy | 334 |
| include-markdown | 1 |
| jinja-expression | 17 |
| jinja-statement | 17 |
| load-csv | 16 |
| raw-html | 1030 |

## Generator reconciliation

| Audience | Type | Source entities | Foundry folders | Generated pages | Missing | Organizational | Orphan |
|---|---|---:|---:|---:|---:|---:|---:|
| gm | adversaries | 106 | 12 | 106 | 0 | 0 | 0 |
| gm | adversaries-features | 419 | 10 | 323 | 0 | 0 | 0 |
| player | ammo | 13 | 0 | 13 | 0 | 0 | 0 |
| player | armors | 35 | 4 | 35 | 0 | 0 | 0 |
| player | classes | 5 | 0 | 5 | 0 | 0 | 0 |
| player | consumables | 59 | 4 | 59 | 0 | 0 | 0 |
| player | cybernetics | 103 | 4 | 103 | 0 | 0 | 0 |
| player | domains | 73 | 13 | 72 | 0 | 0 | 0 |
| player | drones-devices | 19 | 3 | 19 | 0 | 0 | 0 |
| gm | environments | 8 | 2 | 8 | 0 | 0 | 0 |
| player | features | 105 | 19 | 116 | 0 | 14 | 0 |
| player | loot | 60 | 4 | 60 | 0 | 0 | 0 |
| player | mods | 20 | 0 | 20 | 0 | 0 | 0 |
| player | subclasses | 10 | 0 | 10 | 0 | 0 | 0 |
| player | weapons | 47 | 4 | 45 | 0 | 0 | 0 |

### player / features

**Foundry folder / organizational generated pages (known exceptions):**

- `bodyguard`
- `class-and-subclass-features`
- `device-features`
- `ghost-in-the-machine`
- `intrinsic-features`
- `jack-of-all-trades`
- `mercenary`
- `netrunner`
- `rigger`
- `sentry-ice`
- `speed-racer`
- `street-samuri`
- `wall-ice`
- `wrecking-ball`

## Title collisions

- ****Name:** *The Neon Diner*** — mirror: `docs/gm-facing/adventures/npcs/mara-ma-kuroda.md`, `docs/player-facing/adventures/npcs/mara-ma-kuroda.md`
- **Drone Control** — collision-candidate: `docs/player-facing/system/domains/drone-control/index.md`, `docs/player-facing/system/features/drone-control/index.md`
- **Features** — collision-candidate: `docs/gm-facing/system/adversaries-features.md`, `docs/player-facing/system/features.md`
- **Gun Trainer** — collision-candidate: `docs/player-facing/system/domains/gun-trainer/index.md`, `docs/player-facing/system/features/gun-trainer/index.md`
- **Overload** — collision-candidate: `docs/gm-facing/system/adversaries-features/overload/index.md`, `docs/player-facing/system/domains/overload/index.md`
- **Quick Hack** — collision-candidate: `docs/player-facing/system/domains/quick-hack/index.md`, `docs/player-facing/system/features/quick-hack/index.md`
- **Reactive Shrapnel Shells** — collision-candidate: `docs/player-facing/items/ammo/reactive-shrapnel-shells/index.md`, `docs/player-facing/items/mods/reactive-shrapnel-shells/index.md`
- **Situational Awareness** — collision-candidate: `docs/player-facing/system/domains/situational-awareness/index.md`, `docs/player-facing/system/features/situational-awareness/index.md`
- **Whirlwind** — collision-candidate: `docs/gm-facing/system/adversaries-features/whirlwind/index.md`, `docs/player-facing/system/features/whirlwind/index.md`

## Known exceptions

| Metric | Count |
|---|---:|
| foundry-folder-generated-page | 14 |
| foundry-folder-icon-reference | 14 |
| foundry-folder-record | 109 |
| templated-local-dependency | 16 |

## Review flags

| Metric | Count |
|---|---:|
| stub-document | 3 |
| title-collision-candidate | 16 |
| unresolved-local-dependency:assets/art/275637-Female%20Halfing%20Commoner%20C%20.png.webp | 1 |
| unresolved-local-dependency:stella-brownwalk.html | 1 |
| unresolved-local-dependency:worlds/cybermancer/assets/images/SelkaToken_sm.png | 1 |

## Files requiring review

| Path | Audience | Scope | Authorship | Flags |
|---|---|---|---|---|
| `docs/gm-facing/adventures/pc-actors.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:stella-brownwalk.html` |
| `docs/gm-facing/adventures/pcs/selka-rivineuve.html` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:worlds/cybermancer/assets/images/SelkaToken_sm.png` |
| `docs/gm-facing/adventures/pcs/stella-brownwalk.html` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:assets/art/275637-Female%20Halfing%20Commoner%20C%20.png.webp` |
| `docs/gm-facing/meta/etl-pipeline.md` | gm | developer | hand-authored-or-source | `stub-document` |
| `docs/gm-facing/system/adversaries-features.md` | gm | system | hand-authored-or-source | `title-collision-candidate` |
| `docs/gm-facing/system/adversaries-features/overload/index.md` | gm | system | generated | `title-collision-candidate` |
| `docs/gm-facing/system/adversaries-features/whirlwind/index.md` | gm | system | generated | `title-collision-candidate` |
| `docs/player-facing/adventures/locations.md` | player | campaign | hand-authored-or-source | `stub-document` |
| `docs/player-facing/adventures/npcs.md` | player | campaign | hand-authored-or-source | `stub-document` |
| `docs/player-facing/items/ammo/reactive-shrapnel-shells/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/items/mods/reactive-shrapnel-shells/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/domains/drone-control/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/domains/gun-trainer/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/domains/overload/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/domains/quick-hack/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/domains/situational-awareness/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/features.md` | player | system | hand-authored-or-source | `title-collision-candidate` |
| `docs/player-facing/system/features/drone-control/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/features/gun-trainer/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/features/quick-hack/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/features/situational-awareness/index.md` | player | system | generated | `title-collision-candidate` |
| `docs/player-facing/system/features/whirlwind/index.md` | player | system | generated | `title-collision-candidate` |

## Phase 2 handoff

Use this inventory to assign authority and publication disposition separately.
Recommended disposition values remain `INCLUDE`, `EXCLUDE`, `REVIEW`, `GENERATE`,
and `SUPERSEDED`.
