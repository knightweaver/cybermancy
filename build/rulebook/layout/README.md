# Cybermancy Rulebook Step 6 — Equipment & Technology Layout

Step 6 is the publication-layout layer. It consumes normalized Step 4 outputs
and never reads canonical Foundry pack JSON directly.

## Architecture

The Equipment & Technology workflow is configuration-driven:

```text
canonical Foundry data
        ↓
Step 4 normalization
        ↓
assembled Markdown + structured-entities.json
        ↓
family-specific Step 6 configuration
        ↓
shared Equipment Catalog / reference primitives
        ↓
family chapter artifact + semantic AST replacement
```

Each family receives its own publication contract. A later family must not
silently inherit the Weapons schema merely because both are equipment.

Current configs:

```text
build/rulebook/layout/equipment/weapons-v1.json  # Chapter 16
build/rulebook/layout/equipment/ammo-v1.json     # Chapter 17
```

## Generic family commands

The preferred interface for Equipment & Technology chapters is:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py inspect-equipment --family <family>
python build\rulebook\scripts\build-rulebook-layout.py validate-equipment --family <family>
python build\rulebook\scripts\build-rulebook-layout.py build-equipment --family <family>
```

For example, Chapter 17 Ammunition:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py inspect-equipment --family ammo
python build\rulebook\scripts\build-rulebook-layout.py validate-equipment --family ammo
python build\rulebook\scripts\build-rulebook-layout.py build-equipment --family ammo
```

`ammunition` is accepted as an alias for `ammo`.

The existing Chapter 16 commands remain supported:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py validate-chapter16
python build\rulebook\scripts\build-rulebook-layout.py build-chapter16
```

The generic interface also accepts `--family weapons` and routes it through the
specialized Chapter 16 validation/reference contract.

## Shared catalog behavior

The reusable Equipment Catalog primitive supports:

- config-driven columns and widths;
- deterministic source-sidecar sorting;
- optional grouping rather than synthetic group bands;
- humanized code-style labels where configured;
- normalized plain-text descriptions from Step 4;
- config-driven table typography;
- `longtable` pagination with repeated column headers;
- family/tier continuation labels on continuation pages;
- semantic Pandoc-AST replacement of `family:<family>`.

## Chapter 16 — Weapons

Weapons retain their approved nine-column contract:

```text
Name | Tier | Trait | Range | Burden | Damage | Action | Critical Effect | Description
```

Weapons sort by Tier → Trait → Name, use Trait bands, combine Weapon Features
and Actions for the Action column, and publish separate Weapon Actions and
Critical Effects reference sections. The complete Weapons chapter uses flowing
pagination rather than one forced table per page.

## Chapter 17 — Ammunition

The canonical Ammunition pack currently contains 13 records. Those records do
not carry canonical Tier values, so Step 6 does not invent tiers or tier groups.
The initial Chapter 17 publication contract is:

```text
Name | Effect
```

`Effect` is the Step 4 normalized plain-text entity description. Entries sort
alphabetically by Name. If the catalog crosses a page boundary, the continuation
page repeats the Ammunition continuation label and the table header.

Expected outputs are written to:

```text
build/rulebook/layout/chapter17/
    Cybermancy_Chapter17_Ammunition_Step6.tex
    Cybermancy_Chapter17_Ammunition_Step6.pdf
    ammo-family-step6.tex
    ammo-rows.json
    player-guide-step6-ammo.ast.json
```

The validation report is:

```text
build/rulebook/layout/reports/equipment-ammo.json
```

## Scope boundary

This stage generalizes individual Equipment family chapters. It does not yet
build the entire Equipment & Technology section in one pass. A section-level
aggregator should be added only after additional family configs have been audited
and accepted, so the section builder composes proven family contracts rather
than guessing their schemas.
