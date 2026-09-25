# Cybermancy v0.2.0 — Step 5 Foundry 14 Edge-spend chat hook migration

Status: **STRUCTURAL PASS — clean-world runtime verification still required**  
Branch: `migration/v0.2.0-f14-dh2`  
Foundry qualification target: **14.368**  
Daggerheart qualification target: **2.10.5**

This step migrates the remaining legacy chat-context integration while preserving
the existing Cybermancy Edge-spend semantics. It does not authorize merge or
release; the next boundary is clean-world qualification.

## Finding

The v0.1.x runtime registered `getChatLogEntryContext`. Foundry replaced the
legacy ApplicationV1/jQuery context-menu hook family in v13. ChatMessage context
options now use `getChatMessageContextOptions(application, menuItems)`, with
context callbacks receiving an `HTMLElement` rather than a jQuery object.

The Cybermancy callback never depended on the selected chat-message element, so
no message lookup or DOM migration is required. Only the hook integration needs
to move to the current document-context API.

## Preserved gameplay semantics

The context option remains **Spend 1 Edge** and is available when the current
user has an assigned character.

Activation:

1. reads `flags.cybermancy.edge`, defaulting to 0;
2. refuses to spend when the value is 0 or lower and shows
   `No Edge to spend.`;
3. otherwise decrements the flag by exactly 1;
4. creates the same public chat announcement:
   `<actor name> spends 1 Edge.`

The selected ChatMessage remains intentionally irrelevant to the spend.

## Runtime implementation

`scripts/hooks.js` now registers:

```text
getChatMessageContextOptions
```

The Edge read/spend operation is factored into small exported functions so its
semantics can be validated independently of the context-menu registration.
There is no legacy jQuery access and no dependency on a chat-message DOM shape.

## Validation

Added `tools/validate-runtime-hooks.mjs` and:

```text
npm run validate:runtime-hooks
```

The validator requires the Foundry 14 hook, rejects
`getChatLogEntryContext`, and protects the assigned-character target,
`flags.cybermancy.edge` read/decrement, zero-Edge guard, warning, and chat
announcement.

The validator is included in `validate:release` and the migration workflow.
The migration workflow also watches changes to `scripts/hooks.js` and the new
validator.

## Remaining qualification boundary

Structural migration is complete after this step. The next gate is a clean
Foundry **14.368** / Daggerheart **2.10.5** world using the built v0.2.0
candidate.

Runtime qualification must explicitly verify:

- Cybermancy enables without initialization errors;
- all 15 Compendia load;
- native Character and Weapon sheets remain active;
- right-clicking a chat message exposes **Spend 1 Edge** for a user with an
  assigned character;
- spending with Edge > 0 decrements exactly one Edge and posts the announcement;
- spending at Edge = 0 leaves Edge unchanged and shows the warning;
- Domain registration and representative Cybermancy content remain functional.

Do not merge or publish `v0.2.0` until that clean-world gate passes.
