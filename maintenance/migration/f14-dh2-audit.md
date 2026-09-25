# Cybermancy v0.2.0 — Foundry 14 / Daggerheart 2 migration audit

Target: Foundry 14.368 and Daggerheart 2.10.5. Daggerheart tag 2.10.5 resolves to commit 6bf4b69f983139107bd0d2207a5b2897e8c44cc1; its system.json declares Foundry minimum 14.364, verified 14.368, maximum 14.

Legacy source: Cybermancy v0.1.14 at 92d3fa98b04a87b619b6aa63fb52d841d2859406. Historical v0.1.14 and F13-DH1 are frozen; this audit changes neither.

Classification: A = Daggerheart has an explicit source/data-model migration for the legacy shape. B = Cybermancy must change canonical source, runtime, validators, packaging, or publication tooling. C = preserve until a Foundry 14.368 / Daggerheart 2.10.5 runtime test establishes behavior.

## Baseline

The machine-readable baseline is maintenance/baseline-v0.2.0.json.

The 15 declared Compendia contain 774 source entries: 675 documents + 99 Folder records. The undeclared reference family src/packs/system/adversaries-features adds 429 entries: 419 documents + 10 Folders, for 1,203 total src/packs JSON records. Stable 16-character IDs are retained by filename and no duplicate filename-derived IDs were found in the v0.1.14 tree.

The v0.1.14 repository contains 1,027 canonical /assets files totaling 418,762,145 bytes. The baseline records every asset path/blob SHA and every declared source entry with ID, kind, blob SHA, size, and recognized inventory references.

Cybermancy has eight Environment Actor records. Seven contain 28 embedded Feature Items; Neon Diner currently contains none. This differs from the Edgeheart migration: Cybermancy does not need an Environment system.features[] to embedded-items[] conversion.

## Field and API audit

| Area | Legacy/current difference | Class | Required treatment |
| --- | --- | :---: | --- |
| Armor | Cybermancy Armor uses system.baseScore + system.marks.value; DH2 uses system.armor.max/current. | A | DH2 module/data/item/armor.mjs migrateDocumentData maps both when system.armor is absent. Do not invent slot values. Regression-test the result. |
| Action damage | Legacy actions use damage.parts[]; DH2 uses damage.main + damage.resources. | A | DH2 module/data/action/baseAction.mjs migrateData keys old parts by applyTo and promotes HP/non-healing damage to main. Preserve custom formulas, types and result-based semantics. |
| Action value data | DH2 uses DHActionDiceData multiplier/flatMultiplier/dice/bonus/custom and removes valueAlt when not result-based. | A/C | Let model migration normalize it, then runtime-test flat custom and ordinary dice damage. |
| Adversary attack | DH2 expects an ActionField standard attack and normalizes a missing attack type to attack. | A/C | Preserve attacks; validate post-model attack/damage behavior. Cascade Burrowtail is the flat custom-formula fixture. |
| Class to Subclass | DH2 Class schema has no system.subclasses; discovery is by Subclass system.linkedClass. | B | Remove five Class subclass arrays (10 refs) in the v0.2.0 projection. All ten Cybermancy Subclasses already have linkedClass; preserve them. Do not rely on DH's historical 1.1.1 world migration for newly distributed source. |
| Subclass | linkedClass, spellcastingTrait, features, featureState and isMulticlass remain DH2 concepts. | C | Preserve and validate Character Builder acquisition/linking. |
| Domain Card | DH2 still uses system.domain, level, recallCost, type and action/resource fields; choices come from CONFIG.DH.DOMAIN.allDomains(). | C | Preserve cards and runtime-test Circuit/Maker/Bullet registration before card acquisition/use. |
| Homebrew Domains | scripts/domains.js writes Daggerheart's Homebrew setting. DH2.10.5 still exposes Homebrew domains and allDomains(). | B/C | Update validator assumptions to the DH2 core set, which includes Dread. Preserve the supported setting model and qualify it in runtime. |
| Standalone Feature | Legacy source carries originItemType/multiclassOrigin conventions; DH2 Feature uses granter, featureForm and actorResources. | B/C | Normalize obsolete empty defaults. Any populated legacy origin metadata is a stop-and-map case, not data to discard. Preserve/derive feature form from actual semantics. |
| Embedded Feature | Environment/adversary Features are already embedded Items with stable IDs/_keys. | B/C | Preserve embedded identity/order; normalize only fields/actions proven incompatible. |
| Environment impulses | Cybermancy already stores impulses as a string, matching DH2. | C | No shape migration; runtime validation only. |
| Environment potential adversaries | DH2 requires keyed groups with Actor UUID arrays. Cybermancy already uses that shape. | B/C | Keep the shape. Corporate Office has three Cybermancy Compendium UUIDs. Abraxas Ritual Cave and Cascadia Mountain Valley have six occurrences of nonportable world Actor.* UUIDs that require explicit resolution. Never guess their target. |
| Environment type | DH2 Environment type is schema-controlled. | B | The Eternal Night omits system.type. Resolve from canonical design intent before migration; no silent default. |
| Environment embedded Features | Seven of eight Environment Actors contain 28 embedded Features. | C | No Edgeheart-style feature lifting. Preserve Neon Diner's zero embedded Features unless content design separately changes it. |
| _stats metadata | v0.1.14 records were authored under Foundry 13.351 / DH 1.2.7. | B | v0.2.0 projected source/build metadata should identify 14.368 / 2.10.5 where metadata is emitted. Metadata is not qualification evidence. |
| Manifest versions | module.json is v0.1.14, Foundry 13, DH 1.2–1.9. | B | Later migration commit must set v0.2.0 with Foundry major 14 and DH major 2. Exact 14.368/2.10.5 remains the qualification target. |
| Manifest pack paths | Current Cybermancy tooling expects LevelDB directory paths without .db; the accepted Edgeheart F14 implementation uses manifest .db paths and strips the suffix for source/build directories. | B | Change manifest/compiler/validator/runtime-package handling atomically; do not edit only module.json. |
| Pack compiler/validator | compile-packs, compiled-pack validation and runtime packaging are coupled to current pack-path semantics. | B | Update as one change set and round-trip all 15 Compendia, stable IDs/Folders and embedded IDs. |
| Release validator | validate-release-manifest.mjs hardcodes Foundry 13 + DH 1.2–1.9. | B | Add v0.2.0 rules without weakening historical v0.1.14 evidence. |
| Release preparation | prepare-release.py hardcodes Foundry major 13 / DH major 1 targets. | B | Introduce v0.2.0-specific expectations only after runtime qualification. |
| Publish workflow | publish-release.yml defaults to release-control/v0.1.14.json. | B | Do not run it for v0.2.0 until a new control record and qualified digest exist. |
| Custom Runner sheet | CybermancyRunnerSheet extends legacy global ActorSheet, uses the legacy lifecycle, and points at an empty HBS template. | B/C | Do not assume F14 compatibility. Retire registration or port deliberately to ActorSheetV2, then runtime-test. |
| Custom Weapon sheet | CybermancyWeaponSheet extends legacy ItemSheet, uses jQuery listeners, a blank template, legacy DH paths, and a manual 1d20 attack roll. | B | It is not a valid DH2 action workflow. Retire or rewrite against DH2 actions; preserve Smartlink/Edge intent only through a supported integration. |
| Sheet registration API | DH2.10.5 itself still calls Actors.registerSheet / Items.registerSheet, but with modern sheet classes. | C | Registration entry points exist; Cybermancy sheet class compatibility is the issue. |
| Edge chat hook | scripts/hooks.js uses getChatLogEntryContext plus Actor flags to spend Edge; DH2 uses modern chat rendering hooks internally. | C | Preserve behavior pending F14 test. If the context hook no longer fires, port the UI surface without changing Edge semantics. |
| Activation order | main.js registers settings/sheets at init and hooks/domains at ready. | C | Verify domain registration, hooks, GM/non-GM behavior and reload idempotence in a clean world. |
| Assets | Canonical assets live under /assets; runtime JSON should use modules/cybermancy/assets/... . | B/C | Keep validate:assets -- --strict-prefix as a migration gate. No bulk art change is part of this audit. |
| Rulebook source boundary | Rulebook production consumes src/packs; Step 4 normalized publication corpus is the frozen downstream boundary. | B | Update structured-source readers atomically or dual-read both shapes. Regression must prove normalized semantics/order do not drift. |
| Rulebook encounter grammar | Accepted Step 6 Adversary order is identity → description → attack → motives → experiences → Fast Play → actions → features; Environment order is identity → description → impulses → potential adversaries → Fast Play → actions → features. | B/C | Preserve frozen publication grammars and the accepted whole-book transform order. Schema migration must not become an editorial rewrite. |

## Daggerheart migration boundary

Daggerheart's historical migration chain is evidence, not a substitute for natively coherent v0.2.0 Compendium source. New Cybermancy packs must validate under DH2 even in a clean world with no legacy migration history. A-class transformations are still regression-tested against Daggerheart's model behavior.

Recent DH2.10.x migration handlers primarily cover settings, Dice So Nice state, ancestry/community refresh and weapon refresh behavior; they do not replace the Cybermancy-specific work above.

## Rulebook impact

Keep deterministic game-data transformation separate from publication transformation. src/packs remains a canonical structured input and the accepted Step 4 normalized publication corpus remains the downstream publication boundary. Before changing a source field used by publication, add a parser fixture and compare normalized semantic output before/after. Do not alter Step 6 layout grammar merely to accommodate a Foundry schema change.

## Gate status

This commit is audit/baseline only. No Foundry 14 clean-world test has run, no copied-world migration has run, module.json remains the v0.1.14 production manifest, and v0.2.0 is not publishable.
