# Cybermancy v0.2.0 — Step 4 Foundry 14 / Daggerheart 2 sheet migration result

Status: **PASS — legacy custom sheets retired**  
Branch: `migration/v0.2.0-f14-dh2`  
Foundry qualification target: **14.368**  
Daggerheart qualification target: **2.10.5**

This step resolves the custom-sheet migration boundary. It does not constitute
clean-world runtime qualification and does not authorize release or merge.

## Decision: retire rather than port

Cybermancy v0.1.x registered two optional custom sheets:

- `CybermancyRunnerSheet` extending legacy global `ActorSheet`
- `CybermancyWeaponSheet` extending legacy global `ItemSheet`

Both referenced empty Handlebars templates. The Weapon sheet also implemented
a manual `1d20 + agility + attack proficiency` workflow using legacy field
paths and directly mutated Cybermancy Edge flags. That path is not compatible
with Daggerheart 2's native Action workflow and would bypass the system's
attack/damage handling.

Daggerheart 2.10.5 already registers its native Character and Weapon sheets as
the defaults, using Foundry ApplicationV2 sheet classes. Its native Weapon data
model exposes `system.attack` as an ActionField, and the native Character
sheet invokes item/action `use(...)` workflows for attacks and damage.

Cybermancy therefore retires both custom sheets instead of porting prototype
UI behavior that duplicates or bypasses Daggerheart 2.

## Runtime changes

Removed from active source/runtime:

- `scripts/sheets/CybermancyRunnerSheet.js`
- `scripts/sheets/CybermancyWeaponSheet.js`
- `templates/actor-runner-sheet.hbs`
- `templates/item-weapon-sheet.hbs`
- `styles/cybermancy.css`

`scripts/main.js` no longer imports or registers Cybermancy Actor/Item sheets.

The obsolete `enableSmartlink` world setting was also removed. It existed
only to control the retired Weapon-sheet manual-roll behavior.

`module.json` now declares no module stylesheet, and its description no longer
claims custom sheets.

`tools/build-runtime-package.py` no longer packages retired sheet files,
templates, or stylesheet.

Sheet-only localization labels were removed from `lang/en.json`; the
Cybermancy Edge label was retained for the still-active runtime hook boundary.

## Gameplay preservation

No canonical Compendium document uses the retired custom-sheet flags:

- `flags.cybermancy.weapon.smartlink`
- `flags.cybermancy.weapon.burst`
- `flags.cybermancy.weapon.cybergrade`

The validator scans all canonical `src/packs` JSON for these legacy runtime
flags and fails if they appear.

Cybermancy weapon mechanics remain in native Daggerheart Item data. All 47
canonical Weapon documents have a native `system.attack` action.

Representative regression fixture:

- **Smartpistol** — `41U5oyL5z2gAkerd`
  - retains native `system.attack.type = "attack"`;
  - retains Finesse as its attack trait;
  - retains its canonical Cybermancy **Smartlink** action in
    `system.actions`.

Therefore retiring the sheet prototype does not remove canonical Smartlink
content or replace it with an inferred mechanic.

## Validation tooling

Added `tools/validate-runtime-sheets.mjs` and
`npm run validate:runtime-sheets`.

The validator requires:

- no legacy ActorSheet/ItemSheet implementation files;
- no empty custom sheet templates/style;
- no Cybermancy Actor/Item sheet registration;
- no manual `1d20` attack workflow;
- no legacy Daggerheart agility/proficiency field paths;
- no retired Smartlink/burst/cybergrade runtime flags in canonical packs;
- all 47 Weapon documents retain native Daggerheart `system.attack`;
- the Smartpistol native attack and Smartlink action remain present.

The validator is now part of `validate:release`, the migration workflow, and
future release-candidate CI.

## Validation run

Successful workflow: **36069138264**

Step 4-specific results:

- legacy ActorSheet/ItemSheet classes: PASS — retired
- empty custom sheet templates/style: PASS — retired
- custom sheet registration: PASS — absent
- manual d20 attack workflow: PASS — absent
- retired custom weapon flags in canonical packs: PASS — absent
- native Daggerheart Weapon documents checked: **47**
- Smartpistol native attack + canonical Smartlink action: PASS

The full migration workflow also passed:

- v0.2.0 release-manifest validation
- deterministic v0.1.14 -> DH2 source projection
- 774 source entries / 675 documents / 99 folders
- Circuit, Maker, Bullet registration tests
- strict asset validation
- all 15 Compendia compile/re-extract
- 774 source -> 774 re-extracted records
- embedded Actor Item identity/forms/actions
- targeted rulebook semantic regression suite

Step 4 structural runtime package:

- archive: `cybermancy-v0.2.0.zip`
- SHA-256: `bd6b587b8dfea62c2084b1520b33e417636821fea35fc812966ea5a329f03d85`
- runtime files: **1,138**
- compiled Compendia: **15**

The runtime file count fell by five because the two legacy sheet scripts, two
empty templates, and one sheet-only stylesheet were removed.

## Remaining runtime boundary

The remaining pre-qualification runtime concern is Step 5:
`scripts/hooks.js` still uses the legacy chat-context hook to spend Cybermancy
Edge. Its semantics must be preserved, but the UI integration should change
only if Foundry 14 proves the existing hook unavailable.

After Step 5, build the clean-world v0.2.0 qualification candidate for Foundry
14.368 / Daggerheart 2.10.5. Do not publish or merge before that qualification
gate passes.
