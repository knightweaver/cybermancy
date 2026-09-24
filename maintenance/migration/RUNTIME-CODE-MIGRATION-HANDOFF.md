# Cybermancy v0.2.0 — runtime-code migration handoff

Data migration is complete on `migration/v0.2.0-f14-dh2` through source commit
`0821096791282db8ba8398a235efe6d3cfb812bd`.

Target runtime remains Foundry 14.368 / Daggerheart 2.10.5. Do not publish or
merge from this handoff.

## Completed source boundary

- All 15 declared Compendia retain 774 entries: 675 documents + 99 folders.
- Stable top-level IDs, `_key` values, folder topology, names, artwork paths,
  sort values, and stable Cybermancy Compendium UUIDs were validated against
  frozen `v0.1.14`.
- Five Class `system.subclasses` arrays (10 references) were removed; all ten
  Subclass `system.linkedClass` UUIDs remain unchanged.
- 382 Feature records/items had empty legacy origin metadata normalized and an
  explicit DH2 `featureForm` added: 216 action, 136 passive, 30 reaction.
- 136 embedded Actor Features were validated; the Environment subset remains
  exactly 28 Features with stable IDs, `_key` values, actions, text and order.
- Six nonportable world `Actor.*` references in two Environment groups were
  not guessed. Their Actor UUID arrays are empty and the exact legacy world
  references are retained under `flags.cybermancy.migration` as unresolved
  evidence. The source contains no demonstrable names or canonical Actor
  identities for those three world IDs.
- The three existing Corporate Office Cybermancy adversary Compendium UUIDs
  remain unchanged and resolve.
- Daggerheart-authored `_stats` metadata was updated to Foundry 14.368 /
  Daggerheart 2.10.5 on 980 source/embedded metadata objects.
- Armor `baseScore` / `marks` and legacy Action `damage.parts` were
  deliberately preserved. Daggerheart 2.10.5 explicitly migrates those shapes;
  runtime qualification must prove the official migration before any
  Cybermancy-owned rewrite is considered.

Validation workflow run `36065031319` passed source preservation, Domain
validation, strict asset validation, compilation/re-extraction of all 15
Compendia, embedded Actor Item integrity, and targeted rulebook semantic tests.

The rulebook read-only baseline characterization still reports the pre-existing
selected inventory/freeze hash mismatch. No inventory freeze, publication
manifest, frozen Step 6 grammar, or publication corpus was refreshed by this
migration.

## Next runtime-code work

1. Migrate `module.json` to Cybermancy 0.2.0 with Foundry major 14 and
   Daggerheart major 2 compatibility while keeping 14.368 / 2.10.5 as the
   qualification target.
2. Reconcile manifest pack-path semantics with Foundry 14 and update
   `compile-packs.mjs`, release-manifest validation, runtime packaging, and
   release preparation atomically. Preserve source directory topology and all
   stable Compendium identities.
3. Audit `scripts/main.js` activation against Daggerheart 2.10.5. Preserve
   Circuit, Maker and Bullet registration through the native Homebrew setting;
   prove GM/non-GM behavior and reload idempotence.
4. Retire or port `CybermancyRunnerSheet` and `CybermancyWeaponSheet`.
   The current classes extend legacy sheet APIs; the Weapon sheet also uses
   legacy Daggerheart field paths and a manual d20 attack workflow. Do not
   emulate DH2 combat outside its Action API.
5. Runtime-test the Edge-spend chat hook. Preserve Edge semantics; change the
   hook/UI integration only if Foundry 14 proves the existing context hook no
   longer fires.
6. Build a deterministic v0.2.0 candidate and install it in a clean Foundry
   14.368 / Daggerheart 2.10.5 world. Open every Compendium and exercise the
   frozen migration fixtures, including Armor and Action damage migrations.
7. Record clean-world qualification separately from copied-world upgrade
   qualification. Only after clean-world PASS should a copied v0.1.14 campaign
   world be opened under DH2's historical migration chain.
8. Do not create release control with `publish=true`, publish v0.2.0, move
   legacy tags, or alter the frozen v0.1.14 / F13-DH1 releases during runtime
   migration.

## Runtime stop conditions

Stop rather than infer if DH2 model instantiation changes a formula, damage
type, resource target, Armor slot value, stable UUID, embedded Item identity,
Domain availability, or Feature behavior; if a custom sheet requires bypassing
the native DH2 Action model; or if a rulebook normalization change would alter
the accepted Step 4 semantic corpus rather than merely ignore implementation
metadata.
