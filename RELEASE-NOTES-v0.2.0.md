# Cybermancy v0.2.0

## Compatibility

- Foundry VTT 14 (clean-world qualification on 14.368)
- Daggerheart 2.x (clean-world qualification on 2.10.5)

## Changes from v0.1.14

- Migrates the 15 Cybermancy Compendia to the Daggerheart 2 source shape and Foundry 14 LevelDB runtime packaging.
- Updates the Cybermancy runtime integration, including Daggerheart 2 sheets, Domains, hooks, and artwork references.
- Corrects the system relationship to allow Daggerheart 2.x point releases. An earlier candidate with `maximum: "2"` could not activate on Daggerheart 2.10.5 and has been superseded.

The exact ZIP qualified by the full clean-world checklist is from [workflow run 36134465097](https://github.com/knightweaver/cybermancy/actions/runs/36134465097), SHA-256 `08c394d072af001c9cdfcd0e952d71cacb50e13e6048dc80367716ee7e1915b7`.

Existing-world upgrades have not been separately qualified. Back up an existing world before migrating it to Foundry 14 and Daggerheart 2.
