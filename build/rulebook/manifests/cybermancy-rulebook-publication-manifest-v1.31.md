# Cybermancy Rulebook Publication Manifest v1.31

**Status:** FROZEN

Repository commit: `2c0fe6452f3984c8d7ff6eb552314e3c62c15b8a`

## Decision summary

| Metric | Count |
|---|---:|
| Authored publication inputs | 18 |
| Structured publication families | 15 |
| Structured publication entities | 1085 |

## Structured publication families

| Family | Entities | Folders | Generated page slugs | Slug collisions | Digest |
|---|---:|---:|---:|---:|---|
| `adversaries` | 107 | 26 | 107 | 0 | `c387c4d179212b73506428ae41aa862cf7ce56bc339ab8742158c39ce2c916cf` |
| `adversaries-features` | 419 | 10 | 323 | 32 | `3c53efdf3376e51d2a8f4fcb18a885a1cedba27f644a273b2a1e33eaebdf1f39` |
| `environments` | 8 | 2 | 8 | 0 | `a825584dbfa39c1d839426220df57b36850a919226e831b1a246db4baa2a8ee7` |
| `ammo` | 13 | 0 | 13 | 0 | `77e12640a7ca2346d10204d650128206abbf91758cc3a364fb4717a0bdbeba63` |
| `armors` | 36 | 4 | 36 | 0 | `802898b99526194240ad13590306d1c98fef55359e296c919fc37aa36f02880b` |
| `classes` | 5 | 0 | 5 | 0 | `a1269813be20e8f752990f12965f080e1d50bde226980d34a9aa484df21545c6` |
| `consumables` | 59 | 4 | 59 | 0 | `beeb282a4fc0ff3dce5d366c2c220ed9a1bc2be38596dc58a0e7a67227babfde` |
| `cybernetics` | 103 | 4 | 103 | 0 | `45649ebd6af4844f757498224da37ddd628e6205829d1dcca1e7c8ea20572fcc` |
| `domains` | 74 | 29 | 73 | 1 | `1fc1d59fbbf1fc85356f0c1c7bf48910254abf132b2b391d16b65ae8910193d3` |
| `drones-devices` | 19 | 3 | 19 | 0 | `02f4491233ff21d0153d86260cde2db77302a4a36613210f8db2754b3b88339f` |
| `features` | 105 | 19 | 102 | 3 | `455525eb076fbbb3e000278006c7713b77928521dd6d74654cb269a8618328a9` |
| `loot` | 60 | 4 | 60 | 0 | `483960ae9daa7a808eef979d78a717cebf15218c475271bf929ad421d31b8202` |
| `mods` | 20 | 0 | 20 | 0 | `045c84fd8b3c33bc155fa53daf0affe61fad1361a4633320abf62b253d09cfd6` |
| `subclasses` | 10 | 0 | 10 | 0 | `55938af0e8fcbc7d215e932e4f4c9bb8ffdc4ce12932676a2384130d9eabfb33` |
| `weapons` | 47 | 4 | 47 | 0 | `315fcf44cfbb76be03f3cabc5c1917702d0069b1a48ee2dbcd3ec7241e1709b5` |

## Validation

**Manifest validation:** PASS

- Canonical structured entity counts use stable Foundry/source IDs.
- Same-name source records remain distinct canonical entities.
- Generated-page slug collisions are presentation diagnostics, not deduplication.
- Every structured family digest was recomputed with shared digest v4.
- Foundry folder records participate in the digest without becoming publication entities.
- Structured family counts were cross-checked against the selected inventory.

The JSON manifest is the normative machine-readable freeze artifact.
