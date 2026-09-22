# Cybermancy Rulebook Source Inventory

Schema: `cybermancy-rulebook-inventory-v0.2.4`  
Scanner: `0.2.4`  
Git commit: `e4f4b107625e31cb02b34991d5e68fc21a24a7f6`

## Scope

This is a read-only corpus inventory. It identifies source types, publication audiences,
generated content, MkDocs-specific constructs, dependencies, and generator/source drift.
It does **not** decide canonical authority or rulebook inclusion; those are Phase 2 decisions.

## Summary

| Metric | Count |
|---|---:|
| Files scanned | 4429 |
| Documents | 1066 |
| Player-site documents | 590 |
| GM-site documents | 462 |
| Player nav entries | 21 |
| GM nav entries | 17 |
| Generated documents | 1000 |
| Hand-authored/source documents | 66 |
| Dynamic MkDocs documents | 18 |
| Documents requiring normalization | 1034 |
| Stub documents | 4 |
| Foundry folder records | 109 |
| Organizational files/pages | 123 |
| Files with known exceptions | 139 |
| Files with review flags | 678 |
| Files with unresolved local dependencies | 670 |
| Duplicate-content groups | 110 |

## Files by source family

| Metric | Count |
|---|---:|
| asset | 1027 |
| config | 4 |
| data | 15 |
| generator | 69 |
| gm | 817 |
| player | 608 |
| repository | 38 |
| shared-docs | 21 |
| structured-source | 1830 |

## Files by audience

| Metric | Count |
|---|---:|
| developer | 73 |
| gm | 817 |
| player | 608 |
| shared | 1866 |
| unknown | 1065 |

## Files by content scope

| Metric | Count |
|---|---:|
| campaign | 283 |
| developer | 90 |
| setting | 17 |
| system | 2158 |
| unknown | 1881 |

## Files by kind

| Metric | Count |
|---|---:|
| asset | 1421 |
| code | 48 |
| config | 6 |
| data | 1862 |
| document | 1066 |
| other | 15 |
| presentation | 11 |

## Files by authorship/source status

| Metric | Count |
|---|---:|
| generated | 1026 |
| hand-authored-or-source | 1967 |
| unknown | 1436 |

## MkDocs sites

- **player** — docs_dir `docs/player-facing`, nav entries 21
- **gm** — docs_dir `docs/gm-facing`, nav entries 17

## MkDocs / normalization features

| Metric | Count |
|---|---:|
| attribute-list | 33 |
| include-markdown | 1 |
| jinja-expression | 17 |
| jinja-statement | 17 |
| load-csv | 16 |
| raw-html | 1037 |

## Print-normalization flags

| Metric | Count |
|---|---:|
| attribute-list | 33 |
| html-heavy | 340 |
| include-markdown | 1 |
| jinja-expression | 17 |
| jinja-statement | 17 |
| load-csv | 16 |
| raw-html | 1037 |

## Generator reconciliation

| Audience | Type | Source entities | Foundry folders | Generated pages | Missing | Organizational | Orphan |
|---|---|---:|---:|---:|---:|---:|---:|
| gm | adversaries | 107 | 12 | 107 | 0 | 0 | 0 |
| gm | adversaries-features | 419 | 10 | 323 | 0 | 0 | 0 |
| player | ammo | 13 | 0 | 13 | 0 | 0 | 0 |
| player | armors | 36 | 4 | 36 | 0 | 0 | 0 |
| player | classes | 5 | 0 | 5 | 0 | 0 | 0 |
| player | consumables | 59 | 4 | 59 | 0 | 0 | 0 |
| player | cybernetics | 103 | 4 | 103 | 0 | 0 | 0 |
| player | domains | 74 | 13 | 73 | 0 | 0 | 0 |
| player | drones-devices | 19 | 3 | 19 | 0 | 0 | 0 |
| gm | environments | 8 | 2 | 8 | 0 | 0 | 0 |
| player | features | 105 | 19 | 116 | 0 | 14 | 0 |
| player | loot | 60 | 4 | 60 | 0 | 0 | 0 |
| player | mods | 20 | 0 | 20 | 0 | 0 | 0 |
| player | subclasses | 10 | 0 | 10 | 0 | 0 | 0 |
| player | weapons | 47 | 4 | 47 | 0 | 0 | 0 |

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
| stub-document | 4 |
| title-collision-candidate | 16 |
| unresolved-local-dependency:../../../assets/icons/adversaries/ar-projector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/augmented-street-performer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/auto-targeting-sniper-node.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/automated-barricade-deployment-system.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/adversaries/automated-machinegun-turret.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/adversaries/autonomous-combat-drone-aerial.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/autonomous-combat-drone-ground.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/autonomous-guard-bot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/awakened-kid.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/body-mod-enthusiast.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/burned-out-decker.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/ceiling-drop-restraint-mesh.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/chemical-mist-neutralizer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/choir-of-glass-knifer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/conspiracy-vlogger.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/corp-intern-with-tablet.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/corp-spec-guard-android.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/corporate-courier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/desk-console.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/diner-regular-with-backpack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/dockworker-with-grease-stains.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/down-on-his-luck-corporate-drone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/drunk-salaryman.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/echo-runner.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/elderly-shopkeeper.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/electro-pulse-mine.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/electronic-lock.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/emergency-beacon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/entrapment-foam-ejector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/environmental-sensor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/ex-gang-member-trying-to-stay-clean.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/ex-military-veteran.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/explosive-decoy-crate.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/fixers-messenger.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/glassmask-lookout.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/adversaries/guardrail-jackpot-trap.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/heat-seeking-micro-rocket-turret.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/high-voltage-security-door.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/holo-terminal.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/hostile-intruder-spray-unit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/illegal-cybertech-dealer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/laser-tripwire-grid.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/late-shift-worker-eating-breakfast.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/local-courier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/matrix-relay.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/medical-scanner.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/micro-camera.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/micro-missile-sentry-pod.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/adversaries/microdrone-swarm-dispenser.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/monofilament-perimeter-wire.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/neon-sign-controller.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/off-duty-prostitute-sipping-coffee.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/off-duty-security-guard.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/pattern-touched-beggar.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/payment-terminal.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/personal-drone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/quiet-ganger.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/rail-slug-wall-cannon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/rave-enforcer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/remote-triggered-nanoshard-mine.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/runner-doing-fixer-errands.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/security-drone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/security-mech-frame.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/security-ripper-drone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/service-bot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/shock-floor-conduction-plates.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/silent-alarm.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/sleep-deprived-student.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/smart-appliance.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/smart-claymore-charge.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/smartphone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/sonic-disruption-cannon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/street-kid-with-scavenged-cyberware.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/street-medic.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/synthetic-food-vendor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/taser-web-launcher.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/thermal-motion-detector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/tired-paramedic-on-break.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/undercity-preacher.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/vehicle-interface-node.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/washed-up-mage.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/adversaries/wearable-tech.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/armor-piercing-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/breeching-shells.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/cryo-slugs.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/data-spike-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/emp-shells.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/nanite-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/reactive-shrapnel-shells.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/smart-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/sonic-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/thermobaric-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/toxic-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/tracer-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/ammo/tracker-rounds.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/advanced-slash-resistant-jacket.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/assault-carapace.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/auto-heal-laminate.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/bare-bones.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/bellamoi-fine-armor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/caster-s-conduit-harness.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/ceramsteel-chest-rig.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/composite-riot-carapace.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/double-buffer-plating.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/elundrian-chain-mail.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/emberguard-mantle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/enhanced-riot-carapace.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/failsafe-exo-plate.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/ghoststep-weave.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/hope-bank-vest.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/impact-padded-street-vest.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/kevflex-jacket-mk-ii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/kevflex-jacket.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/kevflex-trench.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/kevlar-shirt.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/kinetic-only-bulwark.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/kinetic-shift-harness.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/legendary-assault-carapace.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/legendary-gel-suit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/legendary-kevflex-trench.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/legendary-polymer-coat.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/monett-s-cloak.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/pain-route-harness.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/razor-stud-carapace.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/reinforced-street-vest.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/savior-polymer-aegis.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/slash-resistant-polymer-coat.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/slash-resistant-polymer-jacket.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/tactical-gel-suit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/timeslip-silks.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/armors/truthlight-carapace.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/classes/cybermancer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/classes/netrunner.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/classes/razz-hacker.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/classes/rigger.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/classes/street-samurai.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/agility-booster-nanoshot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/agility-booster-plus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/arc-resonance-powder.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/armor-nanite-repair-kit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/assassin-s-neurotoxin.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/biomimetic-mask-gel.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/cognitive-overclock-pill.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/cognitive-overclock-plus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/combat-regen-inhalant.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/data-clone-chip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/deep-sleep-capsule.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/flashbang-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/focus-amp-tabs.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/grav-damp-chip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/grav-lift-harness.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/grim-contact-toxin.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/hyper-corrosive-edge-coating.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/improved-plasma-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/industrial-adhesive-gel.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/instinct-amplifier-chip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/instinct-amplifier-plus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/kinetic-leg-booster.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/liquid-focus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/macro-size-serum.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/major-adrenaline-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/major-health-stimpack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/major-plasma-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/memory-transfer-crystal.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/mental-fatigue-override.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/micro-size-serum.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/minor-adrenaline-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/minor-health-stimpack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/morale-beacon-flare.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/morbid-contact-toxin.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/muscle-overdrive-plus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/muscle-overdrive-serum.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/nanowire-bridge-pod.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/neural-reset-drink.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/neural-toxin-ampule.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/night-vision-eye-drops.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/null-field-generator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/orbital-strike-beacon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/persona-enhancement-dose.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/persona-enhancement-plus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/phase-shift-serum.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/precision-sync-injector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/precision-sync-plus.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/pyro-core-injector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/quantum-flux-serum.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/reactive-deflection-matrix.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/reactive-evasion-smoke.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/respirator-gel.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/sonic-disruption-jar.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/soothing-med-gel.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/spell-cache-drive.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/standard-adrenaline-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/standard-health-stimpack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/unstable-plasma-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/consumables/wall-melt-gel.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/adrenal-surge-regulator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/adv-nanite-trauma-mesh.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/arc-resonator-node.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-base-unit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-cpu-implant.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-cyberdeck.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-drone-control.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-intuit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-know-it-all.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-mirror-neuron-amplifier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-signal-amplifier-array.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-skilz.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/caracal-ears.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/chemical-hazard-sensor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/claws.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cognitive-filter-array.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cognitive-manifold-core.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cognitive-overclock-node.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/combat-reflex-core.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cortisol-modulator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-all-access.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-arsenal.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-base-unit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-combat-limbs.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-digital-uplink.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-holdall.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-hydraulic-actuator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-monowhip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-shock-servo-enhancer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-stiletto.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-widow-spine.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-i.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-ii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-iii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-iv.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/dreamweaver-chip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/dynamic-tattoo.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/elite-nanite-trauma-mesh.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/emotive-pulse-regulator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/empathic-feedback-loop.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/endosteel-frame.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/etheric-amplifier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/etheric-dampening-core.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-i.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-ii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-iii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-iv.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/gorilla-arms-mk-i.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/gorilla-arms-mk-ii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/gorilla-arms-mk-iii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/gyroscopic-stabilizer-frame.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/kinetic-absorber-matrix.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/limbic-nullifier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/mana-projector-coil.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/meditative-reflex-chip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/modular-hardpoint-interface.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/motion-prediction-gyro.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/myomer-muscle-weave.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/nanite-medigel-reservoir.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/nanite-trauma-mesh.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/nerve-lattice-fingertips.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/neural-firewall.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/neural-precision-co-processor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/neuro-spinal-load-balancer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-allure-eye.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-base-unit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-eagle-eye.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-inspecter.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-palette.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-spectra.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-witch-eye.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/parallel-synapse-array.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/phase-interference-skin.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/predictive-motion-processor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/psi-focus-amplifier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/reactive-gel-layer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/reflex-loop-accelerator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/regenerative-stemware.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/rem-compression-routine.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/shock-dispersion-skeleton.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/skilljack-neural-matrix.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-armor-analyzer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-ballistics.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-cpu-implant.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-headshot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-targeting-core.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-targeting-reticle-implant.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-weapon-mount.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/speed-feet-rollerblades.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-nanoweave-mki.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-i.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-ii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-iii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-iv.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/tactical-subcortex.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/thaumic-nullifier-implant.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/trauma-suppression-cortex.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/vox-resonance-enhancer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-base-unit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-dual-targeting-suite.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-kinetic-feedback-enhancer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-neural-balancer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-servo-wrist-reinforcement.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/assess-weapon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/body-shield.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/bullet-time.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/burst-fire.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/full-automatic.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/gun-trainer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/gunsmith.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/improvised-weapon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/intimidation.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/knee-slide.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/marksman.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/pistol-whip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/quick-reload.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/quick-shot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/rapid-fire.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/ricochet.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/shoot-around-corners.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/situational-awareness.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/snapshot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/sniper-shot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/suppressing-fire.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/targeted-shot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/bullet/trick-shot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/all-quiet-here-how-are-you.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/creative-coding.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/cybernetics-syndrome.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/cyberware-malfunction.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/deep-fake.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/deep-search.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/digital-recon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/elevate-permission.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/feedback-spike.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/field-experience.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/ghost-protocol.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/ghost-signal.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/matrix-mind.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/neural-sync.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/overload.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/patience-young-padawan.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/quick-hack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/reality-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/short-circuit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/signal-boost.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/smartwire-reflex.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/static-veil.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/strobe-effect.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/circuit/synchronized-uplink.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/air-support.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/analyst.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/armorer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/assess-equipment.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/chinook.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/drone-control.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/drone-maneuver.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/drone-swarm.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/engineer-solution.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/expert-driver.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/explosive-detonation.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/fixer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/flying-drone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/getaway-vehicle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/good-maintenance.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/improvise-equipment.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/improvised-mod.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/micromissle-barrage.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/multitalented.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/patch-job.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/plant-tracker.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/power-boost.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/project-manager.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/quick-change.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/stealth-drone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/domains/maker/urban-assault-vehicle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/chemical-analysis-tool.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/digger.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/electronic-surveillance-kit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/extra-armor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/extra-weapon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/grappling-device.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/lock-kit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/melee-weapon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/night-vision.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/portable-barrier.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/primary-drone-base-armor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/rocket-launcher.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/signal-booster.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/signal-jammer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/stealth-shield.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/storage-locker.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/submersible.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/drones-devices/telescope.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/arcane-debugging.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/ash-cloud.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/battle-bonded.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/become-one-with-the-matrix.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/black-ice.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/boom-baby.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/brainstorm.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/breach-and-clear.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/built-in-smgs.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/calm-in-the-storm.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/chaos-wave.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/coding-reality.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/coming-through.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/daemon-host.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/data-hound.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/destructive-interference.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/detect-anomaly.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/digital-awareness.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/digital-wasteland.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/digital-whisp.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/disorientation.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/don-t-worry-that-was-just-a-glitch.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/driving-expert.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/drone-control.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/dual-wielding.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/eclipse-wall.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/entangle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/expert-maneuver.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/fade-to-black.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/fast-car.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/feedback-loop.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/field-collapse.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/firewall-hydra.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/focused-aggression.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/fractal-surge.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/frostline.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/get-behind-me.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/grinder.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/gun-trainer.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/hacking-insight.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/hardened.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/harmonic-reversion.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/heaven-s-gate.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/heavy-ordinance.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/i-ve-driven-this-before.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/i-ve-seen-this-model-before.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/inspired-driving.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/interference.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/joined-at-the-hip.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/kick-open-the-front-door.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/kraken-ice.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/lethal-combo.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/living-conductor.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/lock-on.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/mana-encryption-wave.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/mana-phase-change-circuit.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/merge-with-the-matrix.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/mirror-maze.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/need-for-speed.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/neural-ripper.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/neuromancy-protocol.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/now-you-see-me-now-you-don-t.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/overseer-protocol.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/pawning-the-past.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/pea-gun.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/power-up.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-1-mod.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-additional-upgrade.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-dmg-threshold-and-upgrade.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-evasion-12.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-evasion-14.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/primary-drone.webp | 3 |
| unresolved-local-dependency:../../../assets/icons/features/protection-assignment.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/quantum-casting.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/quantum-lattice.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/quick-hack.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/quick-reflexes.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/rail-gun.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/reality-fissure.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/reboot.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/reprogram-reality.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/resolve.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/resonant-overdrive.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/reverb.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/ride-the-wave.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/schlieren-patterns.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/scrambler-field.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/siren.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/situational-awareness.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/sleaze-gate.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/soulcatcher.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/sphere-of-control.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/stabilizing-influence.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/stillpoint.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/tar-pit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/the-right-drone-for-the-job.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/two-foci.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/wall-of-no.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/features/whirlwind.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/you-re-in-my-sights.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/features/zero-mirror.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/adrenaline-patch-geneartor-mk-1.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/arc-empty-chest-module.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/arc-greatstone-relay.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/arc-intrusion-key.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/arc-memory-stone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/arc-resonance-powder-generator.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/arc-stride-relic-shard.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/black-glider-beacon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/chrome-fire-jar-beacon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/chrome-flickerfly-pendant-driver.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/chrome-haptics.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/chrome-homing-compasses-beacon.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/cipher-arc-torch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/cipher-calming-pendant-lens.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/cipher-luck-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/cipher-shard-of-node.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/electro-magnetic-flux-rod.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/flux-bolster-relic-relay.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/flux-circuit-ring.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/flux-speaking-orbs-key.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/focusing-brain-implant.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/ghost-attune-relic-mask.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/ghost-clay-companion-relay.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/ghost-control-relic-injector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/ghost-ghostweave-cloak.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/ghost-hopekeeper-locket-node.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/ghost-luck-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/grid-arcane-prism-lens.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/grid-valorstone-injector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/grid-vial-of-driver.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/lakestrider-boots.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/localized-dampening-field-ring.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/mirror-circuit-ring.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/mirror-corrector-sprite-mask.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/mirror-nanoshot.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/nano-cache-pack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/nano-lorekeeper-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/nano-woven-net-module.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neo-dual-flask.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-agility.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-finesse.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-instinct.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-knowledge.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-prescence.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-strength.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/opti-bloodstone.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/opti-companion-case.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/quantum-cache.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/quantum-charging-quiver-module.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/quantum-piper-whistle-injector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/reactive-nanites-pack.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/schrodinger-matter-box.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/street-paragons-chain-injector.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/street-portal-seed-seal.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/synth-enlighten-relic-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/synth-manacles-spike.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/synth-premium-bedroll-key.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/synth-utility-belt.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/zero-piercing-arrows-patch.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/loot/zero-quantum-amulet.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/adaptive-ballistics-computer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/aim-assist.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/armor-piercing-slug-rail.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/ballistic-enhancement-barrel.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/ballistic-servo-sight.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/bayonette.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/caseless-high-cap-mag.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/flash-diverter-strobe-muzzle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/foldable-stock.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/gauss-coil-retrofit.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/gyro-stabilizer.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/holo-displacer-camo.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/laser-sight.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/reactive-ammo-loader.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/reactive-shrapnel-shells.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/shock-damping-frame.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/smart-safety-override.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/smartlink-mod.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/subsonic-suppressor.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/mods/telescopic-sight.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/subclasses/amplifier.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/bodyguard.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/dampener.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/ghost-in-the-machine.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/jack-of-all-trades.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/mercenary.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/speed-racer.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/walkers.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/weavers.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/subclasses/wrecking-ball.webp | 2 |
| unresolved-local-dependency:../../../assets/icons/weapons/adv-emp-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/adv-fragmentation-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/advanced-assault-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/advanced-smg.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/annihilation-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/anti-materiel-sniper.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/assault-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/cluster-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/combat-vibro-blade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/compact-smg.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/corporate-mono-whip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/cyber-spur.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/diamond-cyber-spurs.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/emp-cascade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/emp-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/emp-singularity.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/fragmentation-grenade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/gauss-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/heavy-semi-auto-pistol.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/heavy-shock-baton.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/improved-cyber-spur.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/improved-monofilament-whip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/improved-shock-baton.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/improved-vibro-knife.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/legendary-monofilament-whip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/light-semi-auto-pistol.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/military-assault-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/monofilament-whip.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/nano-vibro-blade.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/orbital-sniper-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/plasma-shotgun.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/prototype-smg.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/riot-shotgun.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/scoped-sniper-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/shock-baton.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/shotgun.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/smartpistol-elite.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/smartpistol-mk-ii.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/smartpistol-omega.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/smartpistol.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/smg-machine-pistol.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/sniper-rifle.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/street-sweeper-shotgun.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/throwing-knives.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/thunder-baton.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/titanium-cyber-spurs.webp | 1 |
| unresolved-local-dependency:../../../assets/icons/weapons/vibro-knife.webp | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/abraxas-cult-leader.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/abraxas-cultist.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/abraxas-modified-deer.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/aggressive-librarian.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/altered-coyote.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/altered-raven.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/altered-threshold-cougar.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/bella-in-transport-tank.webp | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/cascade-burrowtail.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/cavelor-finn.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/clevermask.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/healers-folly.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/liminal-research-drone.png | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/mireborn-thrall-enforcer.webp | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/mireborn-thrall-group.webp | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/pierjaw-crab.webp | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/raz-eel-pack.webp | 1 |
| unresolved-local-dependency:../../../assets/images/adversaries/sewerjaw-gator.png | 1 |
| unresolved-local-dependency:../../../assets/images/environments/neon-diner.png | 1 |
| unresolved-local-dependency:../../assets/images/environments/neon-diner.png | 3 |
| unresolved-local-dependency:../../assets/images/npcs/cassiel-cass-kincaid.png | 1 |
| unresolved-local-dependency:../../assets/images/npcs/kade-stonewall-harrow.png | 1 |
| unresolved-local-dependency:../../assets/images/npcs/lira-slipstream-calder.png | 1 |
| unresolved-local-dependency:../../assets/images/npcs/lyra-kincaid.png | 1 |
| unresolved-local-dependency:../../assets/images/npcs/mara-ma-kuroda.png | 2 |
| unresolved-local-dependency:../../assets/images/npcs/nox-phantomware-kade.png | 1 |
| unresolved-local-dependency:../../assets/images/npcs/rex-ghostwire-mendez.png | 1 |
| unresolved-local-dependency:../../assets/images/npcs/sera-brightline-vance.png | 1 |
| unresolved-local-dependency:../assets/icons/corps/astravail-technologies.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/black-helix-security.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/chimeragene-solutions.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/dominion-systems.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/helion-dynamics.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/helios-biotech.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/kirin-logistics.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/neuracore-industries.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/omnitrine-communications.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/verdant-biomech.webp | 1 |
| unresolved-local-dependency:../assets/icons/corps/vesper-syndicate.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/clank.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/drakona.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/dwarf.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/elf.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/faerie.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/faun.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/firbolg.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/fungril.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/galapa.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/giant.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/goblin.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/halfling.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/human.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/infernis.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/katari.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/orc.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/ribbet.webp | 1 |
| unresolved-local-dependency:../assets/images/ancestory/simiah.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/currentborn.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/databorne.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/directiveborn.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/executiveborn.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/greenborn.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/nomadborn.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/skyborne.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/streetborn.webp | 1 |
| unresolved-local-dependency:../assets/images/communities/substrataborn.webp | 1 |
| unresolved-local-dependency:../assets/images/npcs/abraxas-lord-of-the-threshold.png | 2 |
| unresolved-local-dependency:../assets/images/npcs/dr-aurelia-vale.png | 2 |
| unresolved-local-dependency:../assets/images/npcs/triune-sigil.png | 1 |
| unresolved-local-dependency:../assets/images/npcs/vai-volitional-autonomous-intelligence.png | 2 |
| unresolved-local-dependency:assets/art/275637-Female%20Halfing%20Commoner%20C%20.png.webp | 1 |
| unresolved-local-dependency:assets/images/world/the-razz.png | 1 |
| unresolved-local-dependency:stella-brownwalk.html | 1 |
| unresolved-local-dependency:worlds/cybermancer/assets/images/SelkaToken_sm.png | 1 |

## Files requiring review

| Path | Audience | Scope | Authorship | Flags |
|---|---|---|---|---|
| `docs/gm-facing/adventures/adversaries/abraxas-cult-leader/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/abraxas-cult-leader.png` |
| `docs/gm-facing/adventures/adversaries/abraxas-cultist/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/abraxas-cultist.png` |
| `docs/gm-facing/adventures/adversaries/abraxas-modified-deer/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/abraxas-modified-deer.png` |
| `docs/gm-facing/adventures/adversaries/aggressive-librarian/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/aggressive-librarian.png` |
| `docs/gm-facing/adventures/adversaries/altered-coyote/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/altered-coyote.png` |
| `docs/gm-facing/adventures/adversaries/altered-raven/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/altered-raven.png` |
| `docs/gm-facing/adventures/adversaries/altered-threshold-cougar/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/altered-threshold-cougar.png` |
| `docs/gm-facing/adventures/adversaries/ar-projector/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/ar-projector.webp` |
| `docs/gm-facing/adventures/adversaries/augmented-street-performer/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/augmented-street-performer.webp` |
| `docs/gm-facing/adventures/adversaries/auto-targeting-sniper-node/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/auto-targeting-sniper-node.webp` |
| `docs/gm-facing/adventures/adversaries/automated-barricade-deployment-system/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/automated-barricade-deployment-system.webp` |
| `docs/gm-facing/adventures/adversaries/automated-machinegun-turret-mk-i/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/automated-machinegun-turret.webp` |
| `docs/gm-facing/adventures/adversaries/automated-machinegun-turret-mk-ii/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/automated-machinegun-turret.webp` |
| `docs/gm-facing/adventures/adversaries/autonomous-combat-drone-aerial/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/autonomous-combat-drone-aerial.webp` |
| `docs/gm-facing/adventures/adversaries/autonomous-combat-drone-ground/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/autonomous-combat-drone-ground.webp` |
| `docs/gm-facing/adventures/adversaries/autonomous-guard-bot/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/autonomous-guard-bot.webp` |
| `docs/gm-facing/adventures/adversaries/awakened-kid/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/awakened-kid.webp` |
| `docs/gm-facing/adventures/adversaries/bella/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/bella-in-transport-tank.webp` |
| `docs/gm-facing/adventures/adversaries/body-mod-enthusiast/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/body-mod-enthusiast.webp` |
| `docs/gm-facing/adventures/adversaries/burned-out-decker/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/burned-out-decker.webp` |
| `docs/gm-facing/adventures/adversaries/cascade-burrowtail/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/cascade-burrowtail.png` |
| `docs/gm-facing/adventures/adversaries/cavelor-finn/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/cavelor-finn.png` |
| `docs/gm-facing/adventures/adversaries/ceiling-drop-restraint-mesh/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/ceiling-drop-restraint-mesh.webp` |
| `docs/gm-facing/adventures/adversaries/chemical-mist-neutralizer/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/chemical-mist-neutralizer.webp` |
| `docs/gm-facing/adventures/adversaries/choir-of-glass-knifer/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/choir-of-glass-knifer.webp` |
| `docs/gm-facing/adventures/adversaries/clevermask/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/clevermask.png` |
| `docs/gm-facing/adventures/adversaries/conspiracy-vlogger/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/conspiracy-vlogger.webp` |
| `docs/gm-facing/adventures/adversaries/corp-intern-with-tablet/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/corp-intern-with-tablet.webp` |
| `docs/gm-facing/adventures/adversaries/corp-spec-guard-android/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/corp-spec-guard-android.webp` |
| `docs/gm-facing/adventures/adversaries/corporate-courier/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/corporate-courier.webp` |
| `docs/gm-facing/adventures/adversaries/desk-console/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/desk-console.webp` |
| `docs/gm-facing/adventures/adversaries/diner-regular-with-backpack/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/diner-regular-with-backpack.webp` |
| `docs/gm-facing/adventures/adversaries/dockworker-with-grease-stains/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/dockworker-with-grease-stains.webp` |
| `docs/gm-facing/adventures/adversaries/down-on-his-luck-corporate-drone/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/down-on-his-luck-corporate-drone.webp` |
| `docs/gm-facing/adventures/adversaries/drunk-salaryman/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/drunk-salaryman.webp` |
| `docs/gm-facing/adventures/adversaries/echo-runner/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/echo-runner.webp` |
| `docs/gm-facing/adventures/adversaries/elderly-shopkeeper/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/elderly-shopkeeper.webp` |
| `docs/gm-facing/adventures/adversaries/electro-pulse-mine/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/electro-pulse-mine.webp` |
| `docs/gm-facing/adventures/adversaries/electronic-door-lock/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/electronic-lock.webp` |
| `docs/gm-facing/adventures/adversaries/emergency-call-beacon/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/emergency-beacon.webp` |
| `docs/gm-facing/adventures/adversaries/entrapment-foam-ejector/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/entrapment-foam-ejector.webp` |
| `docs/gm-facing/adventures/adversaries/environmental-sensor/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/environmental-sensor.webp` |
| `docs/gm-facing/adventures/adversaries/ex-gang-member-trying-to-stay-clean/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/ex-gang-member-trying-to-stay-clean.webp` |
| `docs/gm-facing/adventures/adversaries/ex-military-veteran/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/ex-military-veteran.webp` |
| `docs/gm-facing/adventures/adversaries/explosive-decoy-crate/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/explosive-decoy-crate.webp` |
| `docs/gm-facing/adventures/adversaries/fixer-s-messenger/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/fixers-messenger.webp` |
| `docs/gm-facing/adventures/adversaries/glassmask-lookout/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/glassmask-lookout.webp` |
| `docs/gm-facing/adventures/adversaries/glassmask-sniper/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/glassmask-lookout.webp` |
| `docs/gm-facing/adventures/adversaries/guardrail-jackpot-trap/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/guardrail-jackpot-trap.webp` |
| `docs/gm-facing/adventures/adversaries/healer-s-folly/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/healers-folly.png` |
| `docs/gm-facing/adventures/adversaries/heat-seeking-micro-rocket-turret/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/heat-seeking-micro-rocket-turret.webp` |
| `docs/gm-facing/adventures/adversaries/high-voltage-security-door/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/high-voltage-security-door.webp` |
| `docs/gm-facing/adventures/adversaries/holo-terminal/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/holo-terminal.webp` |
| `docs/gm-facing/adventures/adversaries/hostile-intruder-spray-unit/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/hostile-intruder-spray-unit.webp` |
| `docs/gm-facing/adventures/adversaries/illegal-cybertech-dealer/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/illegal-cybertech-dealer.webp` |
| `docs/gm-facing/adventures/adversaries/laser-tripwire-grid/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/laser-tripwire-grid.webp` |
| `docs/gm-facing/adventures/adversaries/late-shift-worker-eating-breakfast/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/late-shift-worker-eating-breakfast.webp` |
| `docs/gm-facing/adventures/adversaries/liminal-research-drone/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/liminal-research-drone.png` |
| `docs/gm-facing/adventures/adversaries/local-courier/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/local-courier.webp` |
| `docs/gm-facing/adventures/adversaries/matrix-relay-node/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/matrix-relay.webp` |
| `docs/gm-facing/adventures/adversaries/medical-scanner/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/medical-scanner.webp` |
| `docs/gm-facing/adventures/adversaries/micro-camera/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/micro-camera.webp` |
| `docs/gm-facing/adventures/adversaries/micro-missile-sentry-pod-mk-i/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/micro-missile-sentry-pod.webp` |
| `docs/gm-facing/adventures/adversaries/micro-missile-sentry-pod-mk-ii/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/micro-missile-sentry-pod.webp` |
| `docs/gm-facing/adventures/adversaries/microdrone-swarm-dispenser/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/microdrone-swarm-dispenser.webp` |
| `docs/gm-facing/adventures/adversaries/mireborn-thrall-foreman/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/mireborn-thrall-enforcer.webp` |
| `docs/gm-facing/adventures/adversaries/monofilament-perimeter-wire/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/monofilament-perimeter-wire.webp` |
| `docs/gm-facing/adventures/adversaries/moreborn-thrall/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/mireborn-thrall-group.webp` |
| `docs/gm-facing/adventures/adversaries/neon-sign-controller/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/neon-sign-controller.webp` |
| `docs/gm-facing/adventures/adversaries/off-duty-prostitute-sipping-coffee/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/off-duty-prostitute-sipping-coffee.webp` |
| `docs/gm-facing/adventures/adversaries/off-duty-security-guard/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/off-duty-security-guard.webp` |
| `docs/gm-facing/adventures/adversaries/pattern-touched-beggar/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/pattern-touched-beggar.webp` |
| `docs/gm-facing/adventures/adversaries/payment-terminal/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/payment-terminal.webp` |
| `docs/gm-facing/adventures/adversaries/personal-drone/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/personal-drone.webp` |
| `docs/gm-facing/adventures/adversaries/pierjaw-crab/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/pierjaw-crab.webp` |
| `docs/gm-facing/adventures/adversaries/portable-auto-barricade/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/automated-barricade-deployment-system.webp` |
| `docs/gm-facing/adventures/adversaries/public-service-bot/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/service-bot.webp` |
| `docs/gm-facing/adventures/adversaries/quiet-ganger/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/quiet-ganger.webp` |
| `docs/gm-facing/adventures/adversaries/rail-slug-wall-cannon/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/rail-slug-wall-cannon.webp` |
| `docs/gm-facing/adventures/adversaries/rave-enforcer/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/rave-enforcer.webp` |
| `docs/gm-facing/adventures/adversaries/raz-eels/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/raz-eel-pack.webp` |
| `docs/gm-facing/adventures/adversaries/remote-triggered-nanoshard-mine/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/remote-triggered-nanoshard-mine.webp` |
| `docs/gm-facing/adventures/adversaries/runner-doing-fixer-errands/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/runner-doing-fixer-errands.webp` |
| `docs/gm-facing/adventures/adversaries/security-drone/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/security-drone.webp` |
| `docs/gm-facing/adventures/adversaries/security-mech-frame/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/security-mech-frame.webp` |
| `docs/gm-facing/adventures/adversaries/security-ripper-drone/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/security-ripper-drone.webp` |
| `docs/gm-facing/adventures/adversaries/sewerjaw-gator/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/adversaries/sewerjaw-gator.png` |
| `docs/gm-facing/adventures/adversaries/shock-floor-conduction-plates/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/shock-floor-conduction-plates.webp` |
| `docs/gm-facing/adventures/adversaries/silent-alarm/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/silent-alarm.webp` |
| `docs/gm-facing/adventures/adversaries/sleep-deprived-student/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/sleep-deprived-student.webp` |
| `docs/gm-facing/adventures/adversaries/smart-appliance/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/smart-appliance.webp` |
| `docs/gm-facing/adventures/adversaries/smart-claymore-charge/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/smart-claymore-charge.webp` |
| `docs/gm-facing/adventures/adversaries/smartphone-commlink/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/smartphone.webp` |
| `docs/gm-facing/adventures/adversaries/sonic-disruption-cannon/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/sonic-disruption-cannon.webp` |
| `docs/gm-facing/adventures/adversaries/street-kid-with-scavenged-cyberware/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/street-kid-with-scavenged-cyberware.webp` |
| `docs/gm-facing/adventures/adversaries/street-medic/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/street-medic.webp` |
| `docs/gm-facing/adventures/adversaries/synthetic-food-vendor/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/synthetic-food-vendor.webp` |
| `docs/gm-facing/adventures/adversaries/taser-web-launcher/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/taser-web-launcher.webp` |
| `docs/gm-facing/adventures/adversaries/thermal-motion-detector/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/thermal-motion-detector.webp` |
| `docs/gm-facing/adventures/adversaries/tired-paramedic-on-break/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/tired-paramedic-on-break.webp` |
| `docs/gm-facing/adventures/adversaries/undercity-preacher/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/undercity-preacher.webp` |
| `docs/gm-facing/adventures/adversaries/vehicle-node-interface/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/vehicle-interface-node.webp` |
| `docs/gm-facing/adventures/adversaries/washed-up-mage/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/washed-up-mage.webp` |
| `docs/gm-facing/adventures/adversaries/wearable-tech/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/icons/adversaries/wearable-tech.webp` |
| `docs/gm-facing/adventures/environments/neon-diner-environment/index.md` | gm | campaign | generated | `unresolved-local-dependency:../../../assets/images/environments/neon-diner.png` |
| `docs/gm-facing/adventures/npc-actors.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:../assets/images/npcs/abraxas-lord-of-the-threshold.png`, `unresolved-local-dependency:../assets/images/npcs/dr-aurelia-vale.png`, `unresolved-local-dependency:../assets/images/npcs/vai-volitional-autonomous-intelligence.png` |
| `docs/gm-facing/adventures/npcs/cass-kincaid.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/cassiel-cass-kincaid.png` |
| `docs/gm-facing/adventures/npcs/lyra-kincaid.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/lyra-kincaid.png` |
| `docs/gm-facing/adventures/npcs/mara-ma-kuroda.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/environments/neon-diner.png`, `unresolved-local-dependency:../../assets/images/npcs/mara-ma-kuroda.png` |
| `docs/gm-facing/adventures/npcs/rex-ghostwire-mendez.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/rex-ghostwire-mendez.png` |
| `docs/gm-facing/adventures/pc-actors.md` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:stella-brownwalk.html` |
| `docs/gm-facing/adventures/pcs/selka-rivineuve.html` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:worlds/cybermancer/assets/images/SelkaToken_sm.png` |
| `docs/gm-facing/adventures/pcs/stella-brownwalk.html` | gm | campaign | hand-authored-or-source | `unresolved-local-dependency:assets/art/275637-Female%20Halfing%20Commoner%20C%20.png.webp` |
| `docs/gm-facing/meta/etl-pipeline.md` | gm | developer | hand-authored-or-source | `stub-document` |
| `docs/gm-facing/system/adversaries-features.md` | gm | system | hand-authored-or-source | `title-collision-candidate` |
| `docs/gm-facing/system/adversaries-features/overload/index.md` | gm | system | generated | `title-collision-candidate` |
| `docs/gm-facing/system/adversaries-features/whirlwind/index.md` | gm | system | generated | `title-collision-candidate` |
| `docs/gm-facing/world/the-cabal.md` | gm | setting | hand-authored-or-source | `unresolved-local-dependency:../assets/images/npcs/abraxas-lord-of-the-threshold.png`, `unresolved-local-dependency:../assets/images/npcs/dr-aurelia-vale.png`, `unresolved-local-dependency:../assets/images/npcs/triune-sigil.png`, `unresolved-local-dependency:../assets/images/npcs/vai-volitional-autonomous-intelligence.png` |
| `docs/gm-facing/world/the-council-projects.md` | gm | setting | hand-authored-or-source | `stub-document` |
| `docs/player-facing/adventures/locations.md` | player | campaign | hand-authored-or-source | `stub-document` |
| `docs/player-facing/adventures/locations/neon-diner.md` | player | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/environments/neon-diner.png` |
| `docs/player-facing/adventures/npcs.md` | player | campaign | hand-authored-or-source | `stub-document` |
| `docs/player-facing/adventures/npcs/mara-ma-kuroda.md` | player | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/environments/neon-diner.png`, `unresolved-local-dependency:../../assets/images/npcs/mara-ma-kuroda.png` |
| `docs/player-facing/adventures/pcs/kade-stonewall-harrow.html` | player | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/kade-stonewall-harrow.png` |
| `docs/player-facing/adventures/pcs/lira-slipstream-calder.html` | player | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/lira-slipstream-calder.png` |
| `docs/player-facing/adventures/pcs/nox-phantomware-kade.html` | player | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/nox-phantomware-kade.png` |
| `docs/player-facing/adventures/pcs/sera-brightline-vance.html` | player | campaign | hand-authored-or-source | `unresolved-local-dependency:../../assets/images/npcs/sera-brightline-vance.png` |
| `docs/player-facing/index.md` | player | unknown | hand-authored-or-source | `unresolved-local-dependency:assets/images/world/the-razz.png` |
| `docs/player-facing/items/ammo/armor-piercing-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/armor-piercing-rounds.webp` |
| `docs/player-facing/items/ammo/breeching-shells/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/breeching-shells.webp` |
| `docs/player-facing/items/ammo/cryo-slugs/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/cryo-slugs.webp` |
| `docs/player-facing/items/ammo/data-spike-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/data-spike-rounds.webp` |
| `docs/player-facing/items/ammo/emp-shells/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/emp-shells.webp` |
| `docs/player-facing/items/ammo/nanite-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/nanite-rounds.webp` |
| `docs/player-facing/items/ammo/reactive-shrapnel-shells/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/ammo/reactive-shrapnel-shells.webp` |
| `docs/player-facing/items/ammo/smart-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/smart-rounds.webp` |
| `docs/player-facing/items/ammo/sonic-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/sonic-rounds.webp` |
| `docs/player-facing/items/ammo/thermobaric-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/thermobaric-rounds.webp` |
| `docs/player-facing/items/ammo/toxic-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/toxic-rounds.webp` |
| `docs/player-facing/items/ammo/tracer-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/tracer-rounds.webp` |
| `docs/player-facing/items/ammo/tracker-rounds/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/ammo/tracker-rounds.webp` |
| `docs/player-facing/items/armors/advanced-slash-resistant-jacket/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/advanced-slash-resistant-jacket.webp` |
| `docs/player-facing/items/armors/assault-carapace/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/assault-carapace.webp` |
| `docs/player-facing/items/armors/auto-heal-laminate/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/auto-heal-laminate.webp` |
| `docs/player-facing/items/armors/bare-bones/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/bare-bones.webp` |
| `docs/player-facing/items/armors/bellamoi-fine-armor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/bellamoi-fine-armor.webp` |
| `docs/player-facing/items/armors/caster-s-conduit-harness/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/caster-s-conduit-harness.webp` |
| `docs/player-facing/items/armors/ceramsteel-chest-rig/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/ceramsteel-chest-rig.webp` |
| `docs/player-facing/items/armors/composite-riot-carapace/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/composite-riot-carapace.webp` |
| `docs/player-facing/items/armors/double-buffer-plating/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/double-buffer-plating.webp` |
| `docs/player-facing/items/armors/elundrian-chain-mail/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/elundrian-chain-mail.webp` |
| `docs/player-facing/items/armors/emberguard-mantle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/emberguard-mantle.webp` |
| `docs/player-facing/items/armors/enhanced-riot-carapace/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/enhanced-riot-carapace.webp` |
| `docs/player-facing/items/armors/failsafe-exo-plate/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/failsafe-exo-plate.webp` |
| `docs/player-facing/items/armors/ghoststep-weave/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/ghoststep-weave.webp` |
| `docs/player-facing/items/armors/hope-bank-vest/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/hope-bank-vest.webp` |
| `docs/player-facing/items/armors/impact-padded-street-vest/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/impact-padded-street-vest.webp` |
| `docs/player-facing/items/armors/kevflex-jacket-mk-ii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/kevflex-jacket-mk-ii.webp` |
| `docs/player-facing/items/armors/kevflex-jacket/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/kevflex-jacket.webp` |
| `docs/player-facing/items/armors/kevflex-trench/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/kevflex-trench.webp` |
| `docs/player-facing/items/armors/kevlar-shirt/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/kevlar-shirt.webp` |
| `docs/player-facing/items/armors/kinetic-only-bulwark/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/kinetic-only-bulwark.webp` |
| `docs/player-facing/items/armors/kinetic-shift-harness/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/kinetic-shift-harness.webp` |
| `docs/player-facing/items/armors/legendary-assault-carapace/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/legendary-assault-carapace.webp` |
| `docs/player-facing/items/armors/legendary-gel-suit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/legendary-gel-suit.webp` |
| `docs/player-facing/items/armors/legendary-kevflex-trench/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/legendary-kevflex-trench.webp` |
| `docs/player-facing/items/armors/legendary-polymer-coat/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/legendary-polymer-coat.webp` |
| `docs/player-facing/items/armors/monett-s-cloak/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/monett-s-cloak.webp` |
| `docs/player-facing/items/armors/pain-route-harness/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/pain-route-harness.webp` |
| `docs/player-facing/items/armors/razor-stud-carapace/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/razor-stud-carapace.webp` |
| `docs/player-facing/items/armors/reinforced-street-vest/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/reinforced-street-vest.webp` |
| `docs/player-facing/items/armors/savior-polymer-aegis/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/savior-polymer-aegis.webp` |
| `docs/player-facing/items/armors/slash-resistant-polymer-coat/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/slash-resistant-polymer-coat.webp` |
| `docs/player-facing/items/armors/slash-resistant-polymer-jacket/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/slash-resistant-polymer-jacket.webp` |
| `docs/player-facing/items/armors/tactical-gel-suit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/tactical-gel-suit.webp` |
| `docs/player-facing/items/armors/timeslip-silks/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/timeslip-silks.webp` |
| `docs/player-facing/items/armors/truthlight-carapace/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/armors/truthlight-carapace.webp` |
| `docs/player-facing/items/consumables/agility-booster-nanoshot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/agility-booster-nanoshot.webp` |
| `docs/player-facing/items/consumables/agility-booster-plus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/agility-booster-plus.webp` |
| `docs/player-facing/items/consumables/arc-resonance-powder/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/arc-resonance-powder.webp` |
| `docs/player-facing/items/consumables/armor-nanite-repair-kit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/armor-nanite-repair-kit.webp` |
| `docs/player-facing/items/consumables/assassin-s-neurotoxin/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/assassin-s-neurotoxin.webp` |
| `docs/player-facing/items/consumables/biomimetic-mask-gel/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/biomimetic-mask-gel.webp` |
| `docs/player-facing/items/consumables/cognitive-overclock-pill/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/cognitive-overclock-pill.webp` |
| `docs/player-facing/items/consumables/cognitive-overclock-plus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/cognitive-overclock-plus.webp` |
| `docs/player-facing/items/consumables/combat-regen-inhalant/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/combat-regen-inhalant.webp` |
| `docs/player-facing/items/consumables/data-clone-chip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/data-clone-chip.webp` |
| `docs/player-facing/items/consumables/deep-sleep-capsule/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/deep-sleep-capsule.webp` |
| `docs/player-facing/items/consumables/flashbang-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/flashbang-grenade.webp` |
| `docs/player-facing/items/consumables/focus-amp-tabs/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/focus-amp-tabs.webp` |
| `docs/player-facing/items/consumables/grav-damp-chip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/grav-damp-chip.webp` |
| `docs/player-facing/items/consumables/grav-lift-harness/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/grav-lift-harness.webp` |
| `docs/player-facing/items/consumables/grim-contact-toxin/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/grim-contact-toxin.webp` |
| `docs/player-facing/items/consumables/hyper-corrosive-edge-coating/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/hyper-corrosive-edge-coating.webp` |
| `docs/player-facing/items/consumables/improved-plasma-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/improved-plasma-grenade.webp` |
| `docs/player-facing/items/consumables/industrial-adhesive-gel/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/industrial-adhesive-gel.webp` |
| `docs/player-facing/items/consumables/instinct-amplifier-chip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/instinct-amplifier-chip.webp` |
| `docs/player-facing/items/consumables/instinct-amplifier-plus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/instinct-amplifier-plus.webp` |
| `docs/player-facing/items/consumables/kinetic-leg-booster/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/kinetic-leg-booster.webp` |
| `docs/player-facing/items/consumables/liquid-focus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/liquid-focus.webp` |
| `docs/player-facing/items/consumables/macro-size-serum/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/macro-size-serum.webp` |
| `docs/player-facing/items/consumables/major-adrenaline-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/major-adrenaline-patch.webp` |
| `docs/player-facing/items/consumables/major-health-stimpack/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/major-health-stimpack.webp` |
| `docs/player-facing/items/consumables/major-plasma-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/major-plasma-grenade.webp` |
| `docs/player-facing/items/consumables/memory-transfer-crystal/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/memory-transfer-crystal.webp` |
| `docs/player-facing/items/consumables/mental-fatigue-override/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/mental-fatigue-override.webp` |
| `docs/player-facing/items/consumables/micro-size-serum/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/micro-size-serum.webp` |
| `docs/player-facing/items/consumables/minor-adrenaline-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/minor-adrenaline-patch.webp` |
| `docs/player-facing/items/consumables/minor-health-stimpack/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/minor-health-stimpack.webp` |
| `docs/player-facing/items/consumables/morale-beacon-flare/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/morale-beacon-flare.webp` |
| `docs/player-facing/items/consumables/morbid-contact-toxin/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/morbid-contact-toxin.webp` |
| `docs/player-facing/items/consumables/muscle-overdrive-plus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/muscle-overdrive-plus.webp` |
| `docs/player-facing/items/consumables/muscle-overdrive-serum/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/muscle-overdrive-serum.webp` |
| `docs/player-facing/items/consumables/nanowire-bridge-pod/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/nanowire-bridge-pod.webp` |
| `docs/player-facing/items/consumables/neural-reset-drink/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/neural-reset-drink.webp` |
| `docs/player-facing/items/consumables/neural-toxin-ampule/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/neural-toxin-ampule.webp` |
| `docs/player-facing/items/consumables/night-vision-eye-drops/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/night-vision-eye-drops.webp` |
| `docs/player-facing/items/consumables/null-field-generator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/null-field-generator.webp` |
| `docs/player-facing/items/consumables/orbital-strike-beacon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/orbital-strike-beacon.webp` |
| `docs/player-facing/items/consumables/persona-enhancement-dose/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/persona-enhancement-dose.webp` |
| `docs/player-facing/items/consumables/persona-enhancement-plus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/persona-enhancement-plus.webp` |
| `docs/player-facing/items/consumables/phase-shift-serum/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/phase-shift-serum.webp` |
| `docs/player-facing/items/consumables/precision-sync-injector/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/precision-sync-injector.webp` |
| `docs/player-facing/items/consumables/precision-sync-plus/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/precision-sync-plus.webp` |
| `docs/player-facing/items/consumables/pyro-core-injector/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/pyro-core-injector.webp` |
| `docs/player-facing/items/consumables/quantum-flux-serum/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/quantum-flux-serum.webp` |
| `docs/player-facing/items/consumables/reactive-deflection-matrix/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/reactive-deflection-matrix.webp` |
| `docs/player-facing/items/consumables/reactive-evasion-smoke/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/reactive-evasion-smoke.webp` |
| `docs/player-facing/items/consumables/respirator-gel/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/respirator-gel.webp` |
| `docs/player-facing/items/consumables/sonic-disruption-jar/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/sonic-disruption-jar.webp` |
| `docs/player-facing/items/consumables/soothing-med-gel/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/soothing-med-gel.webp` |
| `docs/player-facing/items/consumables/spell-cache-drive/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/spell-cache-drive.webp` |
| `docs/player-facing/items/consumables/standard-adrenaline-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/standard-adrenaline-patch.webp` |
| `docs/player-facing/items/consumables/standard-health-stimpack/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/standard-health-stimpack.webp` |
| `docs/player-facing/items/consumables/unstable-plasma-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/unstable-plasma-grenade.webp` |
| `docs/player-facing/items/consumables/wall-melt-gel/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/consumables/wall-melt-gel.webp` |
| `docs/player-facing/items/cybernetics/adrenal-surge-regulator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/adrenal-surge-regulator.webp` |
| `docs/player-facing/items/cybernetics/adv-nanite-trauma-mesh/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/adv-nanite-trauma-mesh.webp` |
| `docs/player-facing/items/cybernetics/arc-resonator-node/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/arc-resonator-node.webp` |
| `docs/player-facing/items/cybernetics/brainiac-base-unit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-base-unit.webp` |
| `docs/player-facing/items/cybernetics/brainiac-cpu-implant/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-cpu-implant.webp` |
| `docs/player-facing/items/cybernetics/brainiac-cyberdeck/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-cyberdeck.webp` |
| `docs/player-facing/items/cybernetics/brainiac-drone-control/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-drone-control.webp` |
| `docs/player-facing/items/cybernetics/brainiac-intuit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-intuit.webp` |
| `docs/player-facing/items/cybernetics/brainiac-know-it-all/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-know-it-all.webp` |
| `docs/player-facing/items/cybernetics/brainiac-mirror-neuron-amplifier/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-mirror-neuron-amplifier.webp` |
| `docs/player-facing/items/cybernetics/brainiac-signal-amplifier-array/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-signal-amplifier-array.webp` |
| `docs/player-facing/items/cybernetics/brainiac-skilz/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/brainiac-skilz.webp` |
| `docs/player-facing/items/cybernetics/caracal-ears/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/caracal-ears.webp` |
| `docs/player-facing/items/cybernetics/chemical-hazard-sensor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/chemical-hazard-sensor.webp` |
| `docs/player-facing/items/cybernetics/claws/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/claws.webp` |
| `docs/player-facing/items/cybernetics/cognitive-filter-array/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cognitive-filter-array.webp` |
| `docs/player-facing/items/cybernetics/cognitive-manifold-core/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cognitive-manifold-core.webp` |
| `docs/player-facing/items/cybernetics/cognitive-overclock-node/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cognitive-overclock-node.webp` |
| `docs/player-facing/items/cybernetics/combat-reflex-core/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/combat-reflex-core.webp` |
| `docs/player-facing/items/cybernetics/cortisol-modulator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cortisol-modulator.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-all-access/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-all-access.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-arsenal/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-arsenal.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-base-unit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-base-unit.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-combat-limbs/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-combat-limbs.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-digital-uplink/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-digital-uplink.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-holdall/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-holdall.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-hydraulic-actuator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-hydraulic-actuator.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-monowhip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-monowhip.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-shock-servo-enhancer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-shock-servo-enhancer.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-stiletto/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-stiletto.webp` |
| `docs/player-facing/items/cybernetics/cyberarm-widow-spine/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/cyberarm-widow-spine.webp` |
| `docs/player-facing/items/cybernetics/dermal-plating-mk-i/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-i.webp` |
| `docs/player-facing/items/cybernetics/dermal-plating-mk-ii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-ii.webp` |
| `docs/player-facing/items/cybernetics/dermal-plating-mk-iii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-iii.webp` |
| `docs/player-facing/items/cybernetics/dermal-plating-mk-iv/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/dermal-plating-mk-iv.webp` |
| `docs/player-facing/items/cybernetics/dreamweaver-chip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/dreamweaver-chip.webp` |
| `docs/player-facing/items/cybernetics/dynamic-tattoo/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/dynamic-tattoo.webp` |
| `docs/player-facing/items/cybernetics/elite-nanite-trauma-mesh/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/elite-nanite-trauma-mesh.webp` |
| `docs/player-facing/items/cybernetics/emotive-pulse-regulator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/emotive-pulse-regulator.webp` |
| `docs/player-facing/items/cybernetics/empathic-feedback-loop/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/empathic-feedback-loop.webp` |
| `docs/player-facing/items/cybernetics/endosteel-frame/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/endosteel-frame.webp` |
| `docs/player-facing/items/cybernetics/etheric-amplifier/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/etheric-amplifier.webp` |
| `docs/player-facing/items/cybernetics/etheric-dampening-core/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/etheric-dampening-core.webp` |
| `docs/player-facing/items/cybernetics/feline-feet-mk-i/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-i.webp` |
| `docs/player-facing/items/cybernetics/feline-feet-mk-ii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-ii.webp` |
| `docs/player-facing/items/cybernetics/feline-feet-mk-iii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-iii.webp` |
| `docs/player-facing/items/cybernetics/feline-feet-mk-iv/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/feline-feet-mk-iv.webp` |
| `docs/player-facing/items/cybernetics/gorilla-arms-mk-i/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/gorilla-arms-mk-i.webp` |
| `docs/player-facing/items/cybernetics/gorilla-arms-mk-ii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/gorilla-arms-mk-ii.webp` |
| `docs/player-facing/items/cybernetics/gorilla-arms-mk-iii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/gorilla-arms-mk-iii.webp` |
| `docs/player-facing/items/cybernetics/gyroscopic-stabilizer-frame/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/gyroscopic-stabilizer-frame.webp` |
| `docs/player-facing/items/cybernetics/kinetic-absorber-matrix/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/kinetic-absorber-matrix.webp` |
| `docs/player-facing/items/cybernetics/limbic-nullifier/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/limbic-nullifier.webp` |
| `docs/player-facing/items/cybernetics/mana-projector-coil/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/mana-projector-coil.webp` |
| `docs/player-facing/items/cybernetics/meditative-reflex-chip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/meditative-reflex-chip.webp` |
| `docs/player-facing/items/cybernetics/modular-hardpoint-interface/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/modular-hardpoint-interface.webp` |
| `docs/player-facing/items/cybernetics/motion-prediction-gyro/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/motion-prediction-gyro.webp` |
| `docs/player-facing/items/cybernetics/myomer-muscle-weave/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/myomer-muscle-weave.webp` |
| `docs/player-facing/items/cybernetics/nanite-medigel-reservoir/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/nanite-medigel-reservoir.webp` |
| `docs/player-facing/items/cybernetics/nanite-trauma-mesh/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/nanite-trauma-mesh.webp` |
| `docs/player-facing/items/cybernetics/nerve-lattice-fingertips/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/nerve-lattice-fingertips.webp` |
| `docs/player-facing/items/cybernetics/neural-firewall/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/neural-firewall.webp` |
| `docs/player-facing/items/cybernetics/neural-precision-co-processor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/neural-precision-co-processor.webp` |
| `docs/player-facing/items/cybernetics/neuro-spinal-load-balancer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/neuro-spinal-load-balancer.webp` |
| `docs/player-facing/items/cybernetics/oculus-allure-eye/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-allure-eye.webp` |
| `docs/player-facing/items/cybernetics/oculus-base-unit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-base-unit.webp` |
| `docs/player-facing/items/cybernetics/oculus-eagle-eye/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-eagle-eye.webp` |
| `docs/player-facing/items/cybernetics/oculus-inspecter/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-inspecter.webp` |
| `docs/player-facing/items/cybernetics/oculus-palette/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-palette.webp` |
| `docs/player-facing/items/cybernetics/oculus-spectra/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-spectra.webp` |
| `docs/player-facing/items/cybernetics/oculus-witch-eye/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/oculus-witch-eye.webp` |
| `docs/player-facing/items/cybernetics/parallel-synapse-array/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/parallel-synapse-array.webp` |
| `docs/player-facing/items/cybernetics/phase-interference-skin/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/phase-interference-skin.webp` |
| `docs/player-facing/items/cybernetics/predictive-motion-processor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/predictive-motion-processor.webp` |
| `docs/player-facing/items/cybernetics/psi-focus-amplifier/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/psi-focus-amplifier.webp` |
| `docs/player-facing/items/cybernetics/reactive-gel-layer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/reactive-gel-layer.webp` |
| `docs/player-facing/items/cybernetics/reflex-loop-accelerator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/reflex-loop-accelerator.webp` |
| `docs/player-facing/items/cybernetics/regenerative-stemware/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/regenerative-stemware.webp` |
| `docs/player-facing/items/cybernetics/rem-compression-routine/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/rem-compression-routine.webp` |
| `docs/player-facing/items/cybernetics/shock-dispersion-skeleton/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/shock-dispersion-skeleton.webp` |
| `docs/player-facing/items/cybernetics/skilljack-neural-matrix/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/skilljack-neural-matrix.webp` |
| `docs/player-facing/items/cybernetics/smartlink-armor-analyzer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-armor-analyzer.webp` |
| `docs/player-facing/items/cybernetics/smartlink-ballistics/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-ballistics.webp` |
| `docs/player-facing/items/cybernetics/smartlink-cpu-implant/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-cpu-implant.webp` |
| `docs/player-facing/items/cybernetics/smartlink-headshot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-headshot.webp` |
| `docs/player-facing/items/cybernetics/smartlink-targeting-core/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-targeting-core.webp` |
| `docs/player-facing/items/cybernetics/smartlink-targeting-reticle-implant/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-targeting-reticle-implant.webp` |
| `docs/player-facing/items/cybernetics/smartlink-weapon-mount/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/smartlink-weapon-mount.webp` |
| `docs/player-facing/items/cybernetics/speed-feet-rollerblades/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/speed-feet-rollerblades.webp` |
| `docs/player-facing/items/cybernetics/subdermal-nanoweave-mki/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-nanoweave-mki.webp` |
| `docs/player-facing/items/cybernetics/subdermal-weave-mk-i/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-i.webp` |
| `docs/player-facing/items/cybernetics/subdermal-weave-mk-ii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-ii.webp` |
| `docs/player-facing/items/cybernetics/subdermal-weave-mk-iii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-iii.webp` |
| `docs/player-facing/items/cybernetics/subdermal-weave-mk-iv/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/subdermal-weave-mk-iv.webp` |
| `docs/player-facing/items/cybernetics/tactical-subcortex/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/tactical-subcortex.webp` |
| `docs/player-facing/items/cybernetics/thaumic-nullifier-implant/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/thaumic-nullifier-implant.webp` |
| `docs/player-facing/items/cybernetics/trauma-suppression-cortex/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/trauma-suppression-cortex.webp` |
| `docs/player-facing/items/cybernetics/vox-resonance-enhancer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/vox-resonance-enhancer.webp` |
| `docs/player-facing/items/cybernetics/wakizashi-base-unit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-base-unit.webp` |
| `docs/player-facing/items/cybernetics/wakizashi-dual-targeting-suite/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-dual-targeting-suite.webp` |
| `docs/player-facing/items/cybernetics/wakizashi-kinetic-feedback-enhancer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-kinetic-feedback-enhancer.webp` |
| `docs/player-facing/items/cybernetics/wakizashi-neural-balancer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-neural-balancer.webp` |
| `docs/player-facing/items/cybernetics/wakizashi-servo-wrist-reinforcement/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/cybernetics/wakizashi-servo-wrist-reinforcement.webp` |
| `docs/player-facing/items/drones-devices/chemical-analysis-tool/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/chemical-analysis-tool.webp` |
| `docs/player-facing/items/drones-devices/digger/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/digger.webp` |
| `docs/player-facing/items/drones-devices/electronic-surveillance-kit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/electronic-surveillance-kit.webp` |
| `docs/player-facing/items/drones-devices/extra-armor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/extra-armor.webp` |
| `docs/player-facing/items/drones-devices/extra-weapon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/extra-weapon.webp` |
| `docs/player-facing/items/drones-devices/grappling-device/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/grappling-device.webp` |
| `docs/player-facing/items/drones-devices/grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/grenade.webp` |
| `docs/player-facing/items/drones-devices/lock-kit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/lock-kit.webp` |
| `docs/player-facing/items/drones-devices/melee-weapon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/melee-weapon.webp` |
| `docs/player-facing/items/drones-devices/night-vision/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/night-vision.webp` |
| `docs/player-facing/items/drones-devices/portable-barrier/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/portable-barrier.webp` |
| `docs/player-facing/items/drones-devices/primary-drone-base-armor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/primary-drone-base-armor.webp` |
| `docs/player-facing/items/drones-devices/rocket-launcher/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/rocket-launcher.webp` |
| `docs/player-facing/items/drones-devices/signal-booster/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/signal-booster.webp` |
| `docs/player-facing/items/drones-devices/signal-jammer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/signal-jammer.webp` |
| `docs/player-facing/items/drones-devices/stealth-shield/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/stealth-shield.webp` |
| `docs/player-facing/items/drones-devices/storage-locker/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/storage-locker.webp` |
| `docs/player-facing/items/drones-devices/submersible/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/submersible.webp` |
| `docs/player-facing/items/drones-devices/telescope/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/drones-devices/telescope.webp` |
| `docs/player-facing/items/loot/adrenaline-patch-geneartor-mk-1/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/adrenaline-patch-geneartor-mk-1.webp` |
| `docs/player-facing/items/loot/arc-empty-chest-module/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/arc-empty-chest-module.webp` |
| `docs/player-facing/items/loot/arc-greatstone-relay/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/arc-greatstone-relay.webp` |
| `docs/player-facing/items/loot/arc-intrusion-key/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/arc-intrusion-key.webp` |
| `docs/player-facing/items/loot/arc-memory-stone/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/arc-memory-stone.webp` |
| `docs/player-facing/items/loot/arc-resonance-powder-generator/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/arc-resonance-powder-generator.webp` |
| `docs/player-facing/items/loot/arc-stride-relic-shard/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/arc-stride-relic-shard.webp` |
| `docs/player-facing/items/loot/black-glider-beacon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/black-glider-beacon.webp` |
| `docs/player-facing/items/loot/chrome-fire-jar-beacon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/chrome-fire-jar-beacon.webp` |
| `docs/player-facing/items/loot/chrome-flickerfly-pendant-driver/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/chrome-flickerfly-pendant-driver.webp` |
| `docs/player-facing/items/loot/chrome-haptics/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/chrome-haptics.webp` |
| `docs/player-facing/items/loot/chrome-homing-compasses-beacon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/chrome-homing-compasses-beacon.webp` |
| `docs/player-facing/items/loot/cipher-arc-torch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/cipher-arc-torch.webp` |
| `docs/player-facing/items/loot/cipher-calming-pendant-lens/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/cipher-calming-pendant-lens.webp` |
| `docs/player-facing/items/loot/cipher-luck-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/cipher-luck-patch.webp` |
| `docs/player-facing/items/loot/cipher-shard-of-node/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/cipher-shard-of-node.webp` |
| `docs/player-facing/items/loot/electro-magnetic-flux-rod/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/electro-magnetic-flux-rod.webp` |
| `docs/player-facing/items/loot/flux-bolster-relic-relay/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/flux-bolster-relic-relay.webp` |
| `docs/player-facing/items/loot/flux-circuit-ring/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/flux-circuit-ring.webp` |
| `docs/player-facing/items/loot/flux-speaking-orbs-key/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/flux-speaking-orbs-key.webp` |
| `docs/player-facing/items/loot/focusing-brain-implant/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/focusing-brain-implant.webp` |
| `docs/player-facing/items/loot/ghost-attune-relic-mask/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/ghost-attune-relic-mask.webp` |
| `docs/player-facing/items/loot/ghost-clay-companion-relay/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/ghost-clay-companion-relay.webp` |
| `docs/player-facing/items/loot/ghost-control-relic-injector/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/ghost-control-relic-injector.webp` |
| `docs/player-facing/items/loot/ghost-ghostweave-cloak/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/ghost-ghostweave-cloak.webp` |
| `docs/player-facing/items/loot/ghost-hopekeeper-locket-node/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/ghost-hopekeeper-locket-node.webp` |
| `docs/player-facing/items/loot/ghost-luck-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/ghost-luck-patch.webp` |
| `docs/player-facing/items/loot/grid-arcane-prism-lens/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/grid-arcane-prism-lens.webp` |
| `docs/player-facing/items/loot/grid-valorstone-injector/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/grid-valorstone-injector.webp` |
| `docs/player-facing/items/loot/grid-vial-of-driver/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/grid-vial-of-driver.webp` |
| `docs/player-facing/items/loot/lakestrider-boots/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/lakestrider-boots.webp` |
| `docs/player-facing/items/loot/localized-dampening-field-ring/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/localized-dampening-field-ring.webp` |
| `docs/player-facing/items/loot/mirror-circuit-ring/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/mirror-circuit-ring.webp` |
| `docs/player-facing/items/loot/mirror-corrector-sprite-mask/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/mirror-corrector-sprite-mask.webp` |
| `docs/player-facing/items/loot/mirror-nanoshot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/mirror-nanoshot.webp` |
| `docs/player-facing/items/loot/nano-cache-pack/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/nano-cache-pack.webp` |
| `docs/player-facing/items/loot/nano-lorekeeper-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/nano-lorekeeper-patch.webp` |
| `docs/player-facing/items/loot/nano-woven-net-module/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/nano-woven-net-module.webp` |
| `docs/player-facing/items/loot/neo-dual-flask/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neo-dual-flask.webp` |
| `docs/player-facing/items/loot/neuro-muscular-telemetry-agility/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-agility.webp` |
| `docs/player-facing/items/loot/neuro-muscular-telemetry-finesse/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-finesse.webp` |
| `docs/player-facing/items/loot/neuro-muscular-telemetry-instinct/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-instinct.webp` |
| `docs/player-facing/items/loot/neuro-muscular-telemetry-knowledge/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-knowledge.webp` |
| `docs/player-facing/items/loot/neuro-muscular-telemetry-prescence/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-prescence.webp` |
| `docs/player-facing/items/loot/neuro-muscular-telemetry-strength/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/neuro-muscular-telemetry-strength.webp` |
| `docs/player-facing/items/loot/opti-bloodstone/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/opti-bloodstone.webp` |
| `docs/player-facing/items/loot/opti-companion-case/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/opti-companion-case.webp` |
| `docs/player-facing/items/loot/quantum-cache/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/quantum-cache.webp` |
| `docs/player-facing/items/loot/quantum-charging-quiver-module/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/quantum-charging-quiver-module.webp` |
| `docs/player-facing/items/loot/quantum-piper-whistle-injector/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/quantum-piper-whistle-injector.webp` |
| `docs/player-facing/items/loot/reactive-nanites-pack/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/reactive-nanites-pack.webp` |
| `docs/player-facing/items/loot/schrodinger-matter-box/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/schrodinger-matter-box.webp` |
| `docs/player-facing/items/loot/street-paragons-chain-injector/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/street-paragons-chain-injector.webp` |
| `docs/player-facing/items/loot/street-portal-seed-seal/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/street-portal-seed-seal.webp` |
| `docs/player-facing/items/loot/synth-enlighten-relic-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/synth-enlighten-relic-patch.webp` |
| `docs/player-facing/items/loot/synth-manacles-spike/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/synth-manacles-spike.webp` |
| `docs/player-facing/items/loot/synth-premium-bedroll-key/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/synth-premium-bedroll-key.webp` |
| `docs/player-facing/items/loot/synth-utility-belt/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/synth-utility-belt.webp` |
| `docs/player-facing/items/loot/zero-piercing-arrows-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/zero-piercing-arrows-patch.webp` |
| `docs/player-facing/items/loot/zero-quantum-amulet/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/loot/zero-quantum-amulet.webp` |
| `docs/player-facing/items/mods/adaptive-ballistics-computer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/adaptive-ballistics-computer.webp` |
| `docs/player-facing/items/mods/aim-assist/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/aim-assist.webp` |
| `docs/player-facing/items/mods/armor-piercing-slug-rail/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/armor-piercing-slug-rail.webp` |
| `docs/player-facing/items/mods/ballistic-enhancement-barrel/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/ballistic-enhancement-barrel.webp` |
| `docs/player-facing/items/mods/ballistic-servo-sight/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/ballistic-servo-sight.webp` |
| `docs/player-facing/items/mods/bayonette/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/bayonette.webp` |
| `docs/player-facing/items/mods/caseless-high-cap-mag/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/caseless-high-cap-mag.webp` |
| `docs/player-facing/items/mods/flash-diverter-strobe-muzzle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/flash-diverter-strobe-muzzle.webp` |
| `docs/player-facing/items/mods/foldable-stock/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/foldable-stock.webp` |
| `docs/player-facing/items/mods/gauss-coil-retrofit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/gauss-coil-retrofit.webp` |
| `docs/player-facing/items/mods/gyro-stabilizer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/gyro-stabilizer.webp` |
| `docs/player-facing/items/mods/holo-displacer-camo/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/holo-displacer-camo.webp` |
| `docs/player-facing/items/mods/laser-sight/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/laser-sight.webp` |
| `docs/player-facing/items/mods/reactive-ammo-loader/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/reactive-ammo-loader.webp` |
| `docs/player-facing/items/mods/reactive-shrapnel-shells/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/mods/reactive-shrapnel-shells.webp` |
| `docs/player-facing/items/mods/shock-damping-frame/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/shock-damping-frame.webp` |
| `docs/player-facing/items/mods/smart-safety-override/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/smart-safety-override.webp` |
| `docs/player-facing/items/mods/smartlink-mod/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/smartlink-mod.webp` |
| `docs/player-facing/items/mods/subsonic-suppressor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/subsonic-suppressor.webp` |
| `docs/player-facing/items/mods/telescopic-sight/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/mods/telescopic-sight.webp` |
| `docs/player-facing/items/weapons/adv-emp-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/adv-emp-grenade.webp` |
| `docs/player-facing/items/weapons/adv-fragmentation-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/adv-fragmentation-grenade.webp` |
| `docs/player-facing/items/weapons/advanced-assault-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/advanced-assault-rifle.webp` |
| `docs/player-facing/items/weapons/advanced-smg/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/advanced-smg.webp` |
| `docs/player-facing/items/weapons/annihilation-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/annihilation-grenade.webp` |
| `docs/player-facing/items/weapons/anti-materiel-sniper/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/anti-materiel-sniper.webp` |
| `docs/player-facing/items/weapons/assault-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/assault-rifle.webp` |
| `docs/player-facing/items/weapons/cluster-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/cluster-grenade.webp` |
| `docs/player-facing/items/weapons/combat-vibro-blade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/combat-vibro-blade.webp` |
| `docs/player-facing/items/weapons/compact-smg/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/compact-smg.webp` |
| `docs/player-facing/items/weapons/corporate-mono-whip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/corporate-mono-whip.webp` |
| `docs/player-facing/items/weapons/cyber-spur/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/cyber-spur.webp` |
| `docs/player-facing/items/weapons/diamond-cyber-spurs/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/diamond-cyber-spurs.webp` |
| `docs/player-facing/items/weapons/emp-cascade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/emp-cascade.webp` |
| `docs/player-facing/items/weapons/emp-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/emp-grenade.webp` |
| `docs/player-facing/items/weapons/emp-singularity/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/emp-singularity.webp` |
| `docs/player-facing/items/weapons/fragmentation-grenade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/fragmentation-grenade.webp` |
| `docs/player-facing/items/weapons/gauss-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/gauss-rifle.webp` |
| `docs/player-facing/items/weapons/heavy-semi-auto-pistol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/heavy-semi-auto-pistol.webp` |
| `docs/player-facing/items/weapons/heavy-shock-baton/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/heavy-shock-baton.webp` |
| `docs/player-facing/items/weapons/improved-cyber-spur/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/improved-cyber-spur.webp` |
| `docs/player-facing/items/weapons/improved-monofilament-whip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/improved-monofilament-whip.webp` |
| `docs/player-facing/items/weapons/improved-shock-baton/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/improved-shock-baton.webp` |
| `docs/player-facing/items/weapons/improved-vibro-knife/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/improved-vibro-knife.webp` |
| `docs/player-facing/items/weapons/legendary-monofilament-whip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/legendary-monofilament-whip.webp` |
| `docs/player-facing/items/weapons/light-semi-auto-pistol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/light-semi-auto-pistol.webp` |
| `docs/player-facing/items/weapons/military-assault-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/military-assault-rifle.webp` |
| `docs/player-facing/items/weapons/monofilament-whip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/monofilament-whip.webp` |
| `docs/player-facing/items/weapons/nano-vibro-blade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/nano-vibro-blade.webp` |
| `docs/player-facing/items/weapons/orbital-sniper-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/orbital-sniper-rifle.webp` |
| `docs/player-facing/items/weapons/plasma-shotgun/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/plasma-shotgun.webp` |
| `docs/player-facing/items/weapons/prototype-smg/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/prototype-smg.webp` |
| `docs/player-facing/items/weapons/riot-shotgun/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/riot-shotgun.webp` |
| `docs/player-facing/items/weapons/scoped-sniper-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/scoped-sniper-rifle.webp` |
| `docs/player-facing/items/weapons/shock-baton/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/shock-baton.webp` |
| `docs/player-facing/items/weapons/shotgun/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/shotgun.webp` |
| `docs/player-facing/items/weapons/smartpistol-elite/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/smartpistol-elite.webp` |
| `docs/player-facing/items/weapons/smartpistol-mk-ii/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/smartpistol-mk-ii.webp` |
| `docs/player-facing/items/weapons/smartpistol-omega/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/smartpistol-omega.webp` |
| `docs/player-facing/items/weapons/smartpistol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/smartpistol.webp` |
| `docs/player-facing/items/weapons/smg-machine-pistol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/smg-machine-pistol.webp` |
| `docs/player-facing/items/weapons/sniper-rifle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/sniper-rifle.webp` |
| `docs/player-facing/items/weapons/street-sweeper-shotgun/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/street-sweeper-shotgun.webp` |
| `docs/player-facing/items/weapons/throwing-knives/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/throwing-knives.webp` |
| `docs/player-facing/items/weapons/thunder-baton/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/thunder-baton.webp` |
| `docs/player-facing/items/weapons/titanium-cyber-spurs/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/titanium-cyber-spurs.webp` |
| `docs/player-facing/items/weapons/vibro-knife/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/weapons/vibro-knife.webp` |
| `docs/player-facing/system/classes/cybermancer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/classes/cybermancer.webp`, `unresolved-local-dependency:../../../assets/icons/features/detect-anomaly.webp`, `unresolved-local-dependency:../../../assets/icons/features/feedback-loop.webp`, `unresolved-local-dependency:../../../assets/icons/features/fractal-surge.webp`, `unresolved-local-dependency:../../../assets/icons/features/ride-the-wave.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/amplifier.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/dampener.webp` |
| `docs/player-facing/system/classes/netrunner/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/classes/netrunner.webp`, `unresolved-local-dependency:../../../assets/icons/features/digital-awareness.webp`, `unresolved-local-dependency:../../../assets/icons/features/hacking-insight.webp`, `unresolved-local-dependency:../../../assets/icons/features/interference.webp`, `unresolved-local-dependency:../../../assets/icons/features/quick-hack.webp`, `unresolved-local-dependency:../../../assets/icons/features/reboot.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/ghost-in-the-machine.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/wrecking-ball.webp` |
| `docs/player-facing/system/classes/razz-hacker/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/classes/razz-hacker.webp`, `unresolved-local-dependency:../../../assets/icons/features/living-conductor.webp`, `unresolved-local-dependency:../../../assets/icons/features/mana-encryption-wave.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/walkers.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/weavers.webp` |
| `docs/player-facing/system/classes/rigger/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/classes/rigger.webp`, `unresolved-local-dependency:../../../assets/icons/features/driving-expert.webp`, `unresolved-local-dependency:../../../assets/icons/features/drone-control.webp`, `unresolved-local-dependency:../../../assets/icons/features/power-up.webp`, `unresolved-local-dependency:../../../assets/icons/features/primary-drone.webp`, `unresolved-local-dependency:../../../assets/icons/features/the-right-drone-for-the-job.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/jack-of-all-trades.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/speed-racer.webp` |
| `docs/player-facing/system/classes/street-samurai/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/classes/street-samurai.webp`, `unresolved-local-dependency:../../../assets/icons/features/dual-wielding.webp`, `unresolved-local-dependency:../../../assets/icons/features/focused-aggression.webp`, `unresolved-local-dependency:../../../assets/icons/features/quick-reflexes.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/bodyguard.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/mercenary.webp` |
| `docs/player-facing/system/domains/air-support/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/air-support.webp` |
| `docs/player-facing/system/domains/all-quiet-here-how-are-you/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/all-quiet-here-how-are-you.webp` |
| `docs/player-facing/system/domains/analyst/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/analyst.webp` |
| `docs/player-facing/system/domains/armorer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/armorer.webp` |
| `docs/player-facing/system/domains/assess-equipment/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/assess-equipment.webp` |
| `docs/player-facing/system/domains/assess-weapon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/assess-weapon.webp` |
| `docs/player-facing/system/domains/body-shield/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/body-shield.webp` |
| `docs/player-facing/system/domains/bullet-time/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/bullet-time.webp` |
| `docs/player-facing/system/domains/burst-fire/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/burst-fire.webp` |
| `docs/player-facing/system/domains/chinook/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/chinook.webp` |
| `docs/player-facing/system/domains/creative-coding/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/creative-coding.webp` |
| `docs/player-facing/system/domains/cybernetics-syndrome/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/cybernetics-syndrome.webp` |
| `docs/player-facing/system/domains/cyberware-malfunction/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/cyberware-malfunction.webp` |
| `docs/player-facing/system/domains/deep-fake/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/deep-fake.webp` |
| `docs/player-facing/system/domains/deep-search/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/deep-search.webp` |
| `docs/player-facing/system/domains/digital-recon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/digital-recon.webp` |
| `docs/player-facing/system/domains/drone-control/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/domains/maker/drone-control.webp` |
| `docs/player-facing/system/domains/drone-maneuver/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/drone-maneuver.webp` |
| `docs/player-facing/system/domains/drone-swarm/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/drone-swarm.webp` |
| `docs/player-facing/system/domains/elevate-permission/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/elevate-permission.webp` |
| `docs/player-facing/system/domains/engineer-solution/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/engineer-solution.webp` |
| `docs/player-facing/system/domains/expert-driver/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/expert-driver.webp` |
| `docs/player-facing/system/domains/explosive-detonation/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/explosive-detonation.webp` |
| `docs/player-facing/system/domains/feedback-spike/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/feedback-spike.webp` |
| `docs/player-facing/system/domains/field-experience/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/field-experience.webp` |
| `docs/player-facing/system/domains/fixer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/fixer.webp` |
| `docs/player-facing/system/domains/flying-drone/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/flying-drone.webp` |
| `docs/player-facing/system/domains/full-automatic/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/full-automatic.webp` |
| `docs/player-facing/system/domains/getaway-vehicle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/getaway-vehicle.webp` |
| `docs/player-facing/system/domains/ghost-protocol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/ghost-protocol.webp` |
| `docs/player-facing/system/domains/ghost-signal/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/ghost-signal.webp` |
| `docs/player-facing/system/domains/good-maintenance/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/good-maintenance.webp` |
| `docs/player-facing/system/domains/gun-trainer/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/domains/bullet/gun-trainer.webp` |
| `docs/player-facing/system/domains/gunsmith/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/gunsmith.webp` |
| `docs/player-facing/system/domains/improvise-equipment/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/improvise-equipment.webp` |
| `docs/player-facing/system/domains/improvised-mod/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/improvised-mod.webp` |
| `docs/player-facing/system/domains/improvised-weapon/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/improvised-weapon.webp` |
| `docs/player-facing/system/domains/intimidation/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/intimidation.webp` |
| `docs/player-facing/system/domains/knee-slide/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/knee-slide.webp` |
| `docs/player-facing/system/domains/marksman/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/marksman.webp` |
| `docs/player-facing/system/domains/matrix-mind/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/matrix-mind.webp` |
| `docs/player-facing/system/domains/micromissle-barrage/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/micromissle-barrage.webp` |
| `docs/player-facing/system/domains/multitalented/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/multitalented.webp` |
| `docs/player-facing/system/domains/neural-sync/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/neural-sync.webp` |
| `docs/player-facing/system/domains/overload/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/domains/circuit/overload.webp` |
| `docs/player-facing/system/domains/patch-job/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/patch-job.webp` |
| `docs/player-facing/system/domains/patience-young-padawan/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/patience-young-padawan.webp` |
| `docs/player-facing/system/domains/pistol-whip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/pistol-whip.webp` |
| `docs/player-facing/system/domains/plant-tracker/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/plant-tracker.webp` |
| `docs/player-facing/system/domains/power-boost/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/power-boost.webp` |
| `docs/player-facing/system/domains/project-manager/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/project-manager.webp` |
| `docs/player-facing/system/domains/quick-change/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/quick-change.webp` |
| `docs/player-facing/system/domains/quick-hack/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/domains/circuit/quick-hack.webp` |
| `docs/player-facing/system/domains/quick-reload/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/quick-reload.webp` |
| `docs/player-facing/system/domains/quick-shot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/quick-shot.webp` |
| `docs/player-facing/system/domains/rapid-fire/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/rapid-fire.webp` |
| `docs/player-facing/system/domains/reality-patch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/reality-patch.webp` |
| `docs/player-facing/system/domains/ricochet/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/ricochet.webp` |
| `docs/player-facing/system/domains/shoot-around-corners/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/shoot-around-corners.webp` |
| `docs/player-facing/system/domains/short-circuit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/short-circuit.webp` |
| `docs/player-facing/system/domains/signal-boost/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/signal-boost.webp` |
| `docs/player-facing/system/domains/situational-awareness/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/domains/bullet/situational-awareness.webp` |
| `docs/player-facing/system/domains/smartwire-reflex/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/smartwire-reflex.webp` |
| `docs/player-facing/system/domains/snapshot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/snapshot.webp` |
| `docs/player-facing/system/domains/sniper-shot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/sniper-shot.webp` |
| `docs/player-facing/system/domains/static-veil/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/static-veil.webp` |
| `docs/player-facing/system/domains/stealth-drone/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/stealth-drone.webp` |
| `docs/player-facing/system/domains/strobe-effect/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/strobe-effect.webp` |
| `docs/player-facing/system/domains/suppressing-fire/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/suppressing-fire.webp` |
| `docs/player-facing/system/domains/synchronized-uplink/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/circuit/synchronized-uplink.webp` |
| `docs/player-facing/system/domains/targeted-shot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/targeted-shot.webp` |
| `docs/player-facing/system/domains/trick-shot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/bullet/trick-shot.webp` |
| `docs/player-facing/system/domains/urban-assault-vehicle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/domains/maker/urban-assault-vehicle.webp` |
| `docs/player-facing/system/features.md` | player | system | hand-authored-or-source | `title-collision-candidate` |
| `docs/player-facing/system/features/arcane-debugging/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/arcane-debugging.webp` |
| `docs/player-facing/system/features/ash-cloud/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/ash-cloud.webp` |
| `docs/player-facing/system/features/battle-bonded/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/battle-bonded.webp` |
| `docs/player-facing/system/features/become-one-with-the-matrix/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/become-one-with-the-matrix.webp` |
| `docs/player-facing/system/features/black-ice/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/black-ice.webp` |
| `docs/player-facing/system/features/boom-baby/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/boom-baby.webp` |
| `docs/player-facing/system/features/brainstorm/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/brainstorm.webp` |
| `docs/player-facing/system/features/breach-and-clear/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/breach-and-clear.webp` |
| `docs/player-facing/system/features/built-in-smgs/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/built-in-smgs.webp` |
| `docs/player-facing/system/features/calm-in-the-storm/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/calm-in-the-storm.webp` |
| `docs/player-facing/system/features/chaos-wave/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/chaos-wave.webp` |
| `docs/player-facing/system/features/coding-reality/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/coding-reality.webp` |
| `docs/player-facing/system/features/coming-through/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/coming-through.webp` |
| `docs/player-facing/system/features/daemon-host/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/daemon-host.webp` |
| `docs/player-facing/system/features/data-hound/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/data-hound.webp` |
| `docs/player-facing/system/features/destructive-interference/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/destructive-interference.webp` |
| `docs/player-facing/system/features/detect-anomaly/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/detect-anomaly.webp` |
| `docs/player-facing/system/features/digital-awareness/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/digital-awareness.webp` |
| `docs/player-facing/system/features/digital-wasteland/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/digital-wasteland.webp` |
| `docs/player-facing/system/features/digital-whisp/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/digital-whisp.webp` |
| `docs/player-facing/system/features/disorientation/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/disorientation.webp` |
| `docs/player-facing/system/features/don-t-worry-that-was-just-a-glitch/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/don-t-worry-that-was-just-a-glitch.webp` |
| `docs/player-facing/system/features/driving-expert/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/driving-expert.webp` |
| `docs/player-facing/system/features/drone-control/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/features/drone-control.webp` |
| `docs/player-facing/system/features/dual-wielding/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/dual-wielding.webp` |
| `docs/player-facing/system/features/eclipse-wall/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/eclipse-wall.webp` |
| `docs/player-facing/system/features/entangle/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/entangle.webp` |
| `docs/player-facing/system/features/expert-maneuver/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/expert-maneuver.webp` |
| `docs/player-facing/system/features/fade-to-black/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/fade-to-black.webp` |
| `docs/player-facing/system/features/fast-car/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/fast-car.webp` |
| `docs/player-facing/system/features/feedback-loop/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/feedback-loop.webp` |
| `docs/player-facing/system/features/field-collapse/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/field-collapse.webp` |
| `docs/player-facing/system/features/firewall-hydra/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/firewall-hydra.webp` |
| `docs/player-facing/system/features/focused-aggression/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/focused-aggression.webp` |
| `docs/player-facing/system/features/fractal-surge/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/fractal-surge.webp` |
| `docs/player-facing/system/features/frostline/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/frostline.webp` |
| `docs/player-facing/system/features/get-behind-me/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/get-behind-me.webp` |
| `docs/player-facing/system/features/grinder/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/grinder.webp` |
| `docs/player-facing/system/features/gun-trainer/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/features/gun-trainer.webp` |
| `docs/player-facing/system/features/hacking-insight/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/hacking-insight.webp` |
| `docs/player-facing/system/features/hardened/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/hardened.webp` |
| `docs/player-facing/system/features/harmonic-reversion/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/harmonic-reversion.webp` |
| `docs/player-facing/system/features/heaven-s-gate/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/heaven-s-gate.webp` |
| `docs/player-facing/system/features/heavy-ordinance/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/heavy-ordinance.webp` |
| `docs/player-facing/system/features/i-ve-driven-this-before/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/i-ve-driven-this-before.webp` |
| `docs/player-facing/system/features/i-ve-seen-this-model-before/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/i-ve-seen-this-model-before.webp` |
| `docs/player-facing/system/features/inspired-driving/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/inspired-driving.webp` |
| `docs/player-facing/system/features/interference/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/interference.webp` |
| `docs/player-facing/system/features/joined-at-the-hip/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/joined-at-the-hip.webp` |
| `docs/player-facing/system/features/kick-open-the-front-door/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/kick-open-the-front-door.webp` |
| `docs/player-facing/system/features/kraken-ice/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/kraken-ice.webp` |
| `docs/player-facing/system/features/lethal-combo/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/lethal-combo.webp` |
| `docs/player-facing/system/features/living-conductor/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/living-conductor.webp` |
| `docs/player-facing/system/features/lock-on/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/lock-on.webp` |
| `docs/player-facing/system/features/mana-encryption-wave/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/mana-encryption-wave.webp` |
| `docs/player-facing/system/features/mana-phase-change-circuit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/mana-phase-change-circuit.webp` |
| `docs/player-facing/system/features/merge-with-the-matrix/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/merge-with-the-matrix.webp` |
| `docs/player-facing/system/features/mirror-maze/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/mirror-maze.webp` |
| `docs/player-facing/system/features/need-for-speed/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/need-for-speed.webp` |
| `docs/player-facing/system/features/neural-ripper/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/neural-ripper.webp` |
| `docs/player-facing/system/features/neuromancy-protocol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/neuromancy-protocol.webp` |
| `docs/player-facing/system/features/now-you-see-me-now-you-don-t/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/now-you-see-me-now-you-don-t.webp` |
| `docs/player-facing/system/features/overseer-protocol/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/overseer-protocol.webp` |
| `docs/player-facing/system/features/pawning-the-past/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/pawning-the-past.webp` |
| `docs/player-facing/system/features/pea-gun/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/pea-gun.webp` |
| `docs/player-facing/system/features/power-up/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/power-up.webp` |
| `docs/player-facing/system/features/primary-drone-upgrade-1-mod/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-1-mod.webp` |
| `docs/player-facing/system/features/primary-drone-upgrade-additional-upgrade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-additional-upgrade.webp` |
| `docs/player-facing/system/features/primary-drone-upgrade-dmg-threshold-and-upgrade/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-dmg-threshold-and-upgrade.webp` |
| `docs/player-facing/system/features/primary-drone-upgrade-evasion-12/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-evasion-12.webp` |
| `docs/player-facing/system/features/primary-drone-upgrade-evasion-14/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-evasion-14.webp` |
| `docs/player-facing/system/features/primary-drone/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/primary-drone.webp` |
| `docs/player-facing/system/features/protection-assignment/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/protection-assignment.webp` |
| `docs/player-facing/system/features/quantum-casting/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/quantum-casting.webp` |
| `docs/player-facing/system/features/quantum-lattice/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/quantum-lattice.webp` |
| `docs/player-facing/system/features/quick-hack/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/features/quick-hack.webp` |
| `docs/player-facing/system/features/quick-reflexes/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/quick-reflexes.webp` |
| `docs/player-facing/system/features/rail-gun/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/rail-gun.webp` |
| `docs/player-facing/system/features/reality-fissure/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/reality-fissure.webp` |
| `docs/player-facing/system/features/reboot/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/reboot.webp` |
| `docs/player-facing/system/features/reprogram-reality/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/reprogram-reality.webp` |
| `docs/player-facing/system/features/resolve/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/resolve.webp` |
| `docs/player-facing/system/features/resonant-overdrive/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/resonant-overdrive.webp` |
| `docs/player-facing/system/features/reverb/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/reverb.webp` |
| `docs/player-facing/system/features/ride-the-wave/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/ride-the-wave.webp` |
| `docs/player-facing/system/features/schlieren-patterns/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/schlieren-patterns.webp` |
| `docs/player-facing/system/features/scrambler-field/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/scrambler-field.webp` |
| `docs/player-facing/system/features/siren/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/siren.webp` |
| `docs/player-facing/system/features/situational-awareness/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/features/situational-awareness.webp` |
| `docs/player-facing/system/features/sleaze-gate/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/sleaze-gate.webp` |
| `docs/player-facing/system/features/soulcatcher/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/soulcatcher.webp` |
| `docs/player-facing/system/features/sphere-of-control/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/sphere-of-control.webp` |
| `docs/player-facing/system/features/stabilizing-influence/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/stabilizing-influence.webp` |
| `docs/player-facing/system/features/stillpoint/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/stillpoint.webp` |
| `docs/player-facing/system/features/tar-pit/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/tar-pit.webp` |
| `docs/player-facing/system/features/the-right-drone-for-the-job/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/the-right-drone-for-the-job.webp` |
| `docs/player-facing/system/features/two-foci/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/two-foci.webp` |
| `docs/player-facing/system/features/wall-of-no/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/wall-of-no.webp` |
| `docs/player-facing/system/features/whirlwind/index.md` | player | system | generated | `title-collision-candidate`, `unresolved-local-dependency:../../../assets/icons/features/whirlwind.webp` |
| `docs/player-facing/system/features/you-re-in-my-sights/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/you-re-in-my-sights.webp` |
| `docs/player-facing/system/features/zero-mirror/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/zero-mirror.webp` |
| `docs/player-facing/system/subclasses/amplifier/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/chaos-wave.webp`, `unresolved-local-dependency:../../../assets/icons/features/disorientation.webp`, `unresolved-local-dependency:../../../assets/icons/features/reality-fissure.webp`, `unresolved-local-dependency:../../../assets/icons/features/reprogram-reality.webp`, `unresolved-local-dependency:../../../assets/icons/features/resonant-overdrive.webp`, `unresolved-local-dependency:../../../assets/icons/features/reverb.webp`, `unresolved-local-dependency:../../../assets/icons/features/schlieren-patterns.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/amplifier.webp` |
| `docs/player-facing/system/subclasses/bodyguard/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/calm-in-the-storm.webp`, `unresolved-local-dependency:../../../assets/icons/features/get-behind-me.webp`, `unresolved-local-dependency:../../../assets/icons/features/protection-assignment.webp`, `unresolved-local-dependency:../../../assets/icons/features/situational-awareness.webp`, `unresolved-local-dependency:../../../assets/icons/features/sphere-of-control.webp`, `unresolved-local-dependency:../../../assets/icons/features/two-foci.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/bodyguard.webp` |
| `docs/player-facing/system/subclasses/dampener/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/destructive-interference.webp`, `unresolved-local-dependency:../../../assets/icons/features/field-collapse.webp`, `unresolved-local-dependency:../../../assets/icons/features/harmonic-reversion.webp`, `unresolved-local-dependency:../../../assets/icons/features/quantum-lattice.webp`, `unresolved-local-dependency:../../../assets/icons/features/stabilizing-influence.webp`, `unresolved-local-dependency:../../../assets/icons/features/stillpoint.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/dampener.webp` |
| `docs/player-facing/system/subclasses/ghost-in-the-machine/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/become-one-with-the-matrix.webp`, `unresolved-local-dependency:../../../assets/icons/features/don-t-worry-that-was-just-a-glitch.webp`, `unresolved-local-dependency:../../../assets/icons/features/i-ve-seen-this-model-before.webp`, `unresolved-local-dependency:../../../assets/icons/features/now-you-see-me-now-you-don-t.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/ghost-in-the-machine.webp` |
| `docs/player-facing/system/subclasses/jack-of-all-trades/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/battle-bonded.webp`, `unresolved-local-dependency:../../../assets/icons/features/joined-at-the-hip.webp`, `unresolved-local-dependency:../../../assets/icons/features/lethal-combo.webp`, `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-1-mod.webp`, `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-additional-upgrade.webp`, `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-dmg-threshold-and-upgrade.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/jack-of-all-trades.webp` |
| `docs/player-facing/system/subclasses/mercenary/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/gun-trainer.webp`, `unresolved-local-dependency:../../../assets/icons/features/heavy-ordinance.webp`, `unresolved-local-dependency:../../../assets/icons/features/resolve.webp`, `unresolved-local-dependency:../../../assets/icons/features/whirlwind.webp`, `unresolved-local-dependency:../../../assets/icons/features/you-re-in-my-sights.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/mercenary.webp` |
| `docs/player-facing/system/subclasses/speed-racer/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/expert-maneuver.webp`, `unresolved-local-dependency:../../../assets/icons/features/fast-car.webp`, `unresolved-local-dependency:../../../assets/icons/features/i-ve-driven-this-before.webp`, `unresolved-local-dependency:../../../assets/icons/features/inspired-driving.webp`, `unresolved-local-dependency:../../../assets/icons/features/need-for-speed.webp`, `unresolved-local-dependency:../../../assets/icons/features/primary-drone-upgrade-evasion-12.webp`, `unresolved-local-dependency:../../../assets/icons/features/primary-drone.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/speed-racer.webp` |
| `docs/player-facing/system/subclasses/walkers/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/arcane-debugging.webp`, `unresolved-local-dependency:../../../assets/icons/features/mana-phase-change-circuit.webp`, `unresolved-local-dependency:../../../assets/icons/features/pawning-the-past.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/walkers.webp` |
| `docs/player-facing/system/subclasses/weavers/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/coding-reality.webp`, `unresolved-local-dependency:../../../assets/icons/features/neuromancy-protocol.webp`, `unresolved-local-dependency:../../../assets/icons/features/quantum-casting.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/weavers.webp` |
| `docs/player-facing/system/subclasses/wrecking-ball/index.md` | player | system | generated | `unresolved-local-dependency:../../../assets/icons/features/boom-baby.webp`, `unresolved-local-dependency:../../../assets/icons/features/coming-through.webp`, `unresolved-local-dependency:../../../assets/icons/features/digital-wasteland.webp`, `unresolved-local-dependency:../../../assets/icons/features/kick-open-the-front-door.webp`, `unresolved-local-dependency:../../../assets/icons/subclasses/wrecking-ball.webp` |
| `docs/player-facing/world/ancestories.md` | player | setting | hand-authored-or-source | `unresolved-local-dependency:../assets/images/ancestory/clank.webp`, `unresolved-local-dependency:../assets/images/ancestory/drakona.webp`, `unresolved-local-dependency:../assets/images/ancestory/dwarf.webp`, `unresolved-local-dependency:../assets/images/ancestory/elf.webp`, `unresolved-local-dependency:../assets/images/ancestory/faerie.webp`, `unresolved-local-dependency:../assets/images/ancestory/faun.webp`, `unresolved-local-dependency:../assets/images/ancestory/firbolg.webp`, `unresolved-local-dependency:../assets/images/ancestory/fungril.webp`, `unresolved-local-dependency:../assets/images/ancestory/galapa.webp`, `unresolved-local-dependency:../assets/images/ancestory/giant.webp`, `unresolved-local-dependency:../assets/images/ancestory/goblin.webp`, `unresolved-local-dependency:../assets/images/ancestory/halfling.webp`, `unresolved-local-dependency:../assets/images/ancestory/human.webp`, `unresolved-local-dependency:../assets/images/ancestory/infernis.webp`, `unresolved-local-dependency:../assets/images/ancestory/katari.webp`, `unresolved-local-dependency:../assets/images/ancestory/orc.webp`, `unresolved-local-dependency:../assets/images/ancestory/ribbet.webp`, `unresolved-local-dependency:../assets/images/ancestory/simiah.webp` |
| `docs/player-facing/world/communities.md` | player | setting | hand-authored-or-source | `unresolved-local-dependency:../assets/images/communities/currentborn.webp`, `unresolved-local-dependency:../assets/images/communities/databorne.webp`, `unresolved-local-dependency:../assets/images/communities/directiveborn.webp`, `unresolved-local-dependency:../assets/images/communities/executiveborn.webp`, `unresolved-local-dependency:../assets/images/communities/greenborn.webp`, `unresolved-local-dependency:../assets/images/communities/nomadborn.webp`, `unresolved-local-dependency:../assets/images/communities/skyborne.webp`, `unresolved-local-dependency:../assets/images/communities/streetborn.webp`, `unresolved-local-dependency:../assets/images/communities/substrataborn.webp` |
| `docs/player-facing/world/corps.md` | player | setting | hand-authored-or-source | `unresolved-local-dependency:../assets/icons/corps/astravail-technologies.webp`, `unresolved-local-dependency:../assets/icons/corps/black-helix-security.webp`, `unresolved-local-dependency:../assets/icons/corps/chimeragene-solutions.webp`, `unresolved-local-dependency:../assets/icons/corps/dominion-systems.webp`, `unresolved-local-dependency:../assets/icons/corps/helion-dynamics.webp`, `unresolved-local-dependency:../assets/icons/corps/helios-biotech.webp`, `unresolved-local-dependency:../assets/icons/corps/kirin-logistics.webp`, `unresolved-local-dependency:../assets/icons/corps/neuracore-industries.webp`, `unresolved-local-dependency:../assets/icons/corps/omnitrine-communications.webp`, `unresolved-local-dependency:../assets/icons/corps/verdant-biomech.webp`, `unresolved-local-dependency:../assets/icons/corps/vesper-syndicate.webp` |

## Phase 2 handoff

Use this inventory to assign authority and publication disposition separately.
Recommended disposition values remain `INCLUDE`, `EXCLUDE`, `REVIEW`, `GENERATE`,
and `SUPERSEDED`.
