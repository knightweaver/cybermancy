# Cybermancy v0.2.0 — Step 2 Foundry 14 pack-path migration result

Status: **PASS — structural/build qualification only**  
Branch: `migration/v0.2.0-f14-dh2`  
Foundry qualification target: **14.368**  
Daggerheart qualification target: **2.10.5**

This step does not constitute Foundry runtime qualification and does not authorize
publication.

## Implemented contract

Foundry 14 manifest Compendium paths now use the `.db` representation while
the physical LevelDB and canonical source directories remain unchanged.

Example:

```text
module.json                 packs/items/weapons.db
compiled LevelDB directory  packs/items/weapons/
canonical source            src/packs/items/weapons/
```

The same mapping is applied to all 15 declared Compendia. Pack names, labels,
document types, pack-folder membership, canonical source topology and stable
Compendium names/UUID namespaces are unchanged.

## Files changed

- `module.json`
- `tools/compile-packs.mjs`
- `tools/extract-packs.mjs`
- `tools/validate-compiled-packs.mjs`
- `tools/validate-release-manifest.mjs`
- `tools/build-runtime-package.py`
- `tools/prepare-release.py`
- `tools/migrate-dh2-compendia.py`
- `tools/validate-dh2-source.py`
- `.github/workflows/migration-data-sync.yml`
- `.github/workflows/build-release-candidate.yml`

## Release safeguards

`prepare-release.py` now requires a future v0.2.0 release-control runtime target
of Foundry 14.368 / Daggerheart 2.10.5, all 15 Foundry 14 `.db` manifest paths,
and a runtime-package report proving those mappings. Existing release control
still requires `publish=true`; no v0.2.0 release-control record was created by
this step.

## Validation

Successful workflow run: **36067302264**

- release manifest validation: PASS
- all 15 manifest paths end in exactly one `.db`: PASS
- canonical source projection from frozen v0.1.14: PASS
- source preservation validation: PASS
- Domain and strict asset validation: PASS
- compile all 15 Compendia: PASS
- re-extract all 15 Compendia: PASS
- 774 source entries -> 774 re-extracted entries: PASS
- embedded Actor Item identity/forms/actions: PASS
- deterministic Foundry 14 runtime package build: PASS
- runtime package mapping metadata: PASS
- targeted rulebook semantic regressions: PASS

Structural runtime package produced in CI:

- archive: `cybermancy-v0.2.0.zip`
- SHA-256: `376af0aaa1a69fe47ac45e9d5b8634e214ef5c111be2c3ad2fea5d3fcd2f0e45`
- runtime files: 1,143
- compiled Compendia: 15

This archive hash is evidence for Step 2 packaging determinism only. It is not a
clean-world qualified release artifact.

## Corrective iteration

Workflow run **36067234620** failed because the first pack-path commit changed
the manifest to `.db` before the source-migration/validation tools were taught
to strip the suffix when locating `src/packs`. Commit
`0466708a5d1cd802ec1c9c360b7f2c59596f278d` corrected both tools. The
subsequent complete run **36067302264** passed.

## Next step

Proceed to runtime-code Step 3: audit and migrate `scripts/main.js` activation
against Daggerheart 2.10.5, preserving Circuit, Maker and Bullet registration
through the native Homebrew setting and explicitly testing GM/non-GM behavior
and reload idempotence.
