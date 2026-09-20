# Legacy Daggerheart patch instructions — retired

These instructions are retained only as historical documentation.

Cybermancy previously required local edits to the Daggerheart 1.2.7 system files in order to add the custom **Circuit**, **Maker**, and **Bullet** Domains. That approach is no longer supported by Cybermancy.

As of the native Homebrew Domain registration increment, Cybermancy registers these Domains through Daggerheart's supported world-scoped Homebrew setting at runtime. A stock, unmodified Daggerheart installation should be used.

The implementation is in:

- `scripts/domains.js`
- `scripts/main.js`

Validation is provided by:

```powershell
npm run validate:domains
```

The legacy patch files in this directory must **not** be copied into or used to overwrite files in the installed Daggerheart system.

## Historical patch values

The prior patch registered the following Domain identities. These values are preserved by the native registrar for compatibility with existing Cybermancy content:

- **Circuit** — `modules/cybermancy/assets/icons/domains/circuit.svg`
- **Maker** — `modules/cybermancy/assets/icons/domains/maker.svg`
- **Bullet** — `modules/cybermancy/assets/icons/domains/bullet.svg`

The descriptive text currently registered by Cybermancy is the same descriptive text that was embedded in the former Daggerheart patch. It has not been rewritten as part of this increment.
