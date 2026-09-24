# Cybermancy v0.2.0 — data-migration handoff

Start from branch migration/v0.2.0-f14-dh2 after the audit commit. Do not touch v0.1.14, F13-DH1, either published release, or the historical alias control.

## Objective

Produce a deterministic DH2-native projection of Cybermancy canonical source while preserving stable IDs, mechanics, references, assets and the rulebook publication boundary. Target Foundry 14.368 / Daggerheart 2.10.5. Do not publish.

## Execution sequence

1. Add a deterministic migration/projection script and tests before bulk edits. It must consume the v0.1.14-shaped src/packs records and emit/validate DH2-shaped records without changing stable top-level IDs, Folder IDs or embedded Item identities.
2. Implement only confirmed B transformations from f14-dh2-audit.md: Class subclass-array removal; Feature-field normalization with a stop condition for populated legacy origin metadata; Environment world-UUID resolution with unresolved values failing rather than guessing; explicit resolution of The Eternal Night's missing Environment type; v14/DH2 _stats; and any additional source field proven incompatible by schema validation.
3. Treat Armor and damage.parts as official A migrations first. Build fixtures that instantiate the legacy shape through DH2 models and compare the result with the deterministic source projection. Preserve formulas, damage types and resource targets exactly.
4. Migrate manifest/build tooling atomically: v0.2.0 compatibility, F14 pack-path convention, compile/re-extract validation, runtime packaging and release-manifest validation. Add release-control scaffolding only with publish disabled.
5. Update validate-domain-registration.mjs to the DH2.10.5 core Domain set, including Dread. Keep Circuit/Maker/Bullet registration through Daggerheart Homebrew settings; qualify it in runtime.
6. Resolve custom runtime code. The current Weapon sheet's legacy field paths/manual d20 roll are not a DH2 action integration. Either remove custom sheet registration or port against DH2 actions. Treat the Runner sheet similarly. Keep Edge-spend chat behavior unchanged unless Foundry 14 proves the old context hook unavailable.
7. Before changing any src/packs field consumed by the rulebook, add dual-read/update logic in the structured-source normalization layer. Compare pre/post Step 4 normalized semantics and preserve the accepted Step 6 transform order/grammars.
8. Compile all 15 packs, re-extract, run ID/reference/asset/domain validators, and produce a deterministic runtime candidate. Do not create a GitHub release.
9. Run the clean-world Foundry 14.368 / Daggerheart 2.10.5 checklist. Only after PASS should a copied v0.1.14 world be tested through Daggerheart's migration chain. Record those as separate qualification states.

## Stop conditions

Stop rather than infer when a populated Feature origin field has no deterministic DH2 granter mapping; a world Actor.* UUID cannot be tied to a canonical Cybermancy adversary; an Environment type is absent/ambiguous; an Action loses formula/type/target/cost semantics; an ID or Folder relationship changes; or the Step 4 normalized publication corpus changes mechanically/editorially.

The next commit should be the deterministic data projection + schema tests, not runtime release publication.
