# Cybermancy v0.2.0 — Step 3 Daggerheart 2 activation result

Status: **PASS — activation/domain integration only**  
Branch: `migration/v0.2.0-f14-dh2`  
Foundry qualification target: **14.368**  
Daggerheart qualification target: **2.10.5**

This step validates Cybermancy activation logic and native Domain registration.
It is not the clean-world runtime qualification gate and does not authorize
release or merge. Custom sheet compatibility remains Step 4.

## Daggerheart 2.10.5 API audit

Daggerheart 2.10.5 registers its Homebrew setting as a world-scoped
`DhHomebrew` DataModel at
`CONFIG.DH.SETTINGS.gameSettings.Homebrew`. Its setting `onChange` handler
calls `DhHomebrew.handleChange()`, which replaces
`game.system.settings.homebrew` with the new model before refreshing config.

Daggerheart initializes `game.system.settings.homebrew` during `i18nInit`,
before the Foundry `ready` hook. Its Domain API defines
`CONFIG.DH.DOMAIN.allDomains()` as the merge of
`game.system.settings.homebrew.domains` and Daggerheart core Domains.

Therefore Cybermancy continues to register Circuit, Maker, and Bullet through
Daggerheart's native Homebrew setting at `ready`; it does not patch Daggerheart
configuration or replace core Domain tables.

## Changes

### scripts/domains.js

- Updated the integration contract from Daggerheart 1.2.7 to 2.10.5.
- Added `auditCybermancyRuntime()`.
- Requires:
  - system ID `daggerheart`;
  - Daggerheart major version 2;
  - initialized `CONFIG.DH`;
  - native Domain API;
  - native Homebrew setting API;
  - initialized `game.system.settings.homebrew`.
- Distinguishes the major-2 compatibility contract from the exact 2.10.5
  qualification target.
- Uses `DhHomebrew.toObject(true)` semantics when cloning the current setting.
- Registration result now explicitly reports whether the world setting was
  written.
- Existing unrelated Homebrew data remains preserved.
- Same-ID differing Homebrew Domains and core-domain collisions remain
  non-destructive failures.

### scripts/main.js

- Exposes the runtime audit through `game.modules.get("cybermancy").api`.
- Audits the Daggerheart runtime before attempting Domain registration.
- Rejects incomplete/non-DH2 runtime state.
- Allows other Daggerheart 2.x versions permitted by the major-only manifest,
  while logging that they are not the exact 2.10.5 qualification target.
- Keeps Circuit/Maker/Bullet registration on the `ready` hook.

### validation

`tools/validate-domain-registration.mjs` now exercises the registration code
against a Daggerheart-2.10.5-shaped mock of the native Homebrew DataModel
setting and Domain API.

It proves:

- initial GM registration writes the world setting exactly once;
- unrelated Homebrew Domain data is retained;
- a second registration in the same session performs no write;
- a fresh simulated reload with persisted Cybermancy Domains performs no write;
- a non-GM entering before registration performs no write and reports
  `gm-required`;
- a non-GM entering after registration performs no write and audits successfully;
- a later Daggerheart 2.x patch is structurally accepted but is not reported as
  exactly qualified;
- Daggerheart 1.x fails the v0.2.0 activation audit;
- Circuit, Maker, and Bullet remain distinct from all ten Daggerheart 2.10.5
  core Domains, including Dread.

## Validation run

Successful workflow: **36068378274**

Domain/runtime activation results:

- Circuit/Maker/Bullet definitions: PASS
- 74 Domain Cards: PASS
  - Circuit: 24
  - Maker: 26
  - Bullet: 24
- 5 Classes checked: PASS
  - Circuit referenced by 3
  - Maker referenced by 1
  - Bullet referenced by 1
- unrelated Homebrew preservation: PASS
- same-ID conflict preservation: PASS
- core-domain collision guard: PASS
- Daggerheart 2.10.5 runtime API audit: PASS
- GM first registration writes once: PASS
- same-session idempotence: PASS
- reload idempotence: PASS
- non-GM missing-domain behavior with zero writes: PASS
- non-GM registered-domain behavior with zero writes: PASS
- DH2-major vs exact-2.10.5 distinction: PASS
- Daggerheart 1.x rejection: PASS

The full migration workflow also revalidated source preservation, strict assets,
all 15 Compendia, 774 source/re-extracted records, deterministic packaging, and
the targeted rulebook semantic regression set.

The Step 3 structural runtime package was:

- `cybermancy-v0.2.0.zip`
- SHA-256: `37fe15f973bec24d4122490959e1c3506fe5a580f4184a47507c483330a7ac9f`
- runtime files: 1,143
- compiled Compendia: 15

The hash differs from Step 2 because runtime JavaScript changed in Step 3. It is
still only a structural candidate, not a clean-world qualified artifact.

## Corrective iteration

Workflow **36068195272** failed because the first Step 3 commit updated
`main.js` and the validator to import `auditCybermancyRuntime`, but
`scripts/domains.js` was accidentally committed with its prior blob. Commit
`fe989ff4a801a2db60fd720cc5df650d79592689` corrected the Domain module.
Workflow **36068378274** then passed all gates.

## Remaining runtime boundary

Step 3 does not claim that the entire module can yet activate cleanly in Foundry
14. The module still imports/registers `CybermancyRunnerSheet` and
`CybermancyWeaponSheet`, whose legacy sheet APIs are explicitly reserved for
Step 4. The Edge-spend chat hook remains reserved for Step 5.

Next: **Step 4 — retire or port the custom Runner and Weapon sheets for Foundry
14 / Daggerheart 2 without bypassing the native Daggerheart Action model.**
