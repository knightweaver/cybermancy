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

The authoritative section contract is:

```text
build/rulebook/layout/equipment/equipment-section-v1.json
```

It defines the complete Equipment & Technology sequence:

```text
16  weapons
17  ammo
18  armors
19  cybernetics
20  drones-devices
21  consumables
22  mods
23  loot
```

Family configs are implemented separately, for example:

```text
build/rulebook/layout/equipment/weapons-v1.json  # Chapter 16
build/rulebook/layout/equipment/ammo-v1.json     # Chapter 17
```

## Generic family commands

The preferred interface for a single Equipment & Technology chapter is:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py inspect-equipment --family <family>
python build\rulebook\scripts\build-rulebook-layout.py init-equipment --family <family>
python build\rulebook\scripts\build-rulebook-layout.py validate-equipment --family <family>
python build\rulebook\scripts\build-rulebook-layout.py build-equipment --family <family>
```

For example, Chapter 18 Armor:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py inspect-equipment --family armors
python build\rulebook\scripts\build-rulebook-layout.py init-equipment --family armors
python build\rulebook\scripts\build-rulebook-layout.py validate-equipment --family armors
python build\rulebook\scripts\build-rulebook-layout.py build-equipment --family armors
```

`ammunition` is accepted as an alias for `ammo`; `armor` is accepted as an alias
for the canonical `armors` family.

### Bootstrap inspection before a family config exists

`inspect-equipment` does not require a Step 6 family config. If the expected
`<family>-v1.json` file is missing, inspection switches to bootstrap mode and
uses the Equipment section registry plus Step 4 normalized inputs to report:

- chapter number and title from `equipment-section-v1.json`;
- entity count and semantic identity integrity;
- `family:<family>` manuscript alignment;
- every available `publicationData.*` field path;
- populated/missing counts and coverage for each field;
- up to three representative values per field; and
- up to five representative normalized entities.

For example, before `armors-v1.json` has been initialized:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py inspect-equipment --family armors
```

returns a successful bootstrap inspection with `configStatus: NOT_IMPLEMENTED`
rather than failing `CONFIG_PRESENT`. This output exposes the Step 4 semantics
available to the family without inventing a publication contract.

### Initializing a family config

`init-equipment` converts the bootstrap inspection into a conservative, usable
first-pass Step 6 family config at the exact path owned by the section registry.
For Armor this creates:

```text
build/rulebook/layout/equipment/armors-v1.json
```

The initializer is deliberately limited to normalized fields that are already
present in Step 4. It always publishes `Name` and may additionally publish these
safe common fields when they contain data:

```text
publicationData.tier         → Tier
publicationData.range        → Range
publicationData.burden       → Burden
publicationData.description  → Description
```

It derives the chapter/title, entity count, tier mode, sort order, required-field
coverage, column widths, continuation label, output stem, and standard Equipment
visual style deterministically. Other discovered `publicationData.*` fields stay
visible in bootstrap inspection but are not automatically turned into columns;
family-specific mechanics still require an explicit semantic/layout decision.

Initialization never overwrites an existing config. Re-running a family whose
config already exists reports `EXISTS` and preserves the file unchanged.
Initialization reports are written to:

```text
build/rulebook/layout/reports/equipment-init-<family>.json
```

The complete initialization pass is:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py init-equipment --all
```

`--all` walks Chapters 16–23 in section order, preserves existing configs such
as Weapons and Ammunition, and creates only missing family configs whose bootstrap
inspection passes. Its aggregate report is:

```text
build/rulebook/layout/reports/equipment-init-all.json
```

After initialization, `validate-equipment` and `build-equipment` remain
fail-closed in the normal way. A generated first-pass config is therefore a
repeatable starting contract, not permission to bypass semantic review; validation
must still pass and the rendered chapter should still be reviewed before the
family contract is treated as final.

The existing Chapter 16 commands remain supported:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py validate-chapter16
python build\rulebook\scripts\build-rulebook-layout.py build-chapter16
```

The generic interface also accepts `--family weapons` and routes it through the
specialized Chapter 16 validation/reference contract.

## Batch commands

Use `--all` to process the complete Equipment & Technology section contract:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py inspect-equipment --all
python build\rulebook\scripts\build-rulebook-layout.py init-equipment --all
python build\rulebook\scripts\build-rulebook-layout.py validate-equipment --all
python build\rulebook\scripts\build-rulebook-layout.py build-equipment --all
```

Batch validation/build mode reads `equipment-section-v1.json`, reports every
required Chapter 16–23 family, and marks a family whose config does not exist as
`BLOCKED`. Missing configs therefore remain visible rather than being silently
omitted.

Validation and build batch operations write:

```text
build/rulebook/layout/reports/equipment-all.json
```

The aggregate report records the section registry, chapter order, every required
family, its implementation/config status, and the child validation/build result.
Individual family reports remain unchanged.

`build-equipment --all` has two fail-closed rules:

1. If any **implemented** family fails validation preflight, no implemented
   chapter builds begin.
2. If an implemented family fails during rendering, later implemented families
   are marked `BLOCKED` and are not built.

A family whose config has not yet been implemented is also reported as `BLOCKED`,
but it does not prevent already implemented families from being validated or
built. Until every required Chapter 16–23 config exists, the aggregate command
still exits non-zero and `equipment-all.json` remains `FAIL` because the section
is incomplete. This allows progressive implementation without falsely reporting
that the complete Equipment section is finished.

Batch child Python processes are forced to UTF-8 (`PYTHONIOENCODING=utf-8` and
`PYTHONUTF8=1`) so reader-facing Unicode such as `→` and `—` can be emitted in
JSON reports on Windows consoles that otherwise default to cp1252.

If `--output-dir` is supplied with `build-equipment --all`, it is treated as a
base output directory and each implemented family is written beneath its own
`chapterNN` subdirectory. `--config` cannot be combined with the validation/build
`--all` flow because the section contract owns config discovery.

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

The section registry defines which chapters must ultimately exist. Initialization
can create deterministic first-pass configs from normalized Step 4 fields, but it
does not invent family-specific mechanics. Armor, Cybernetics, Drones and Devices,
Consumables, Mods, and Loot may still require Step 4 semantic enrichment or manual
config refinement after their generated first-pass layouts are inspected.
