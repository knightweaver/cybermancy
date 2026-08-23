# Cybermancy Rulebook Step 6 — Equipment Catalog Table

Step 6 is the publication-layout layer. It consumes the normalized Step 4 corpus
and does not read canonical Foundry pack JSON directly.

## C implementation

The first reusable primitive is the Equipment Catalog Table, validated against
Chapter 16 / Tier 1 Weapons.

Inputs:

```text
build/rulebook/source/assembled/player-guide.md
build/rulebook/source/metadata/structured-entities.json
build/rulebook/layout/equipment/weapons-v1.json
```

The `structured-entities.json` file is a derived Step 4 sidecar containing stable
publication semantics such as Weapon Trait, Range, formula-only Damage, plain-text
Description, Weapon Features, Actions, and Critical Effects.

Build flow:

```text
canonical Foundry data
        ↓
Step 4 normalization
        ↓
assembled Markdown + structured-entities.json
        ↓
Step 5 content-only validation/rendering
        ↓
Step 6 layout projection
        ↓
Equipment Catalog Table
```

## Commands

From the repository root, rebuild Step 4 first so the sidecar exists:

```powershell
python build\rulebook\scripts\build-rulebook-source.py validate
python build\rulebook\scripts\build-rulebook-source.py build
```

Then run Step 6 C:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py validate
python build\rulebook\scripts\build-rulebook-layout.py build
```

Use `--tex-only` to generate the deterministic TeX source without invoking
LuaLaTeX:

```powershell
python build\rulebook\scripts\build-rulebook-layout.py build --tex-only
```

Generated prototype outputs are written under:

```text
build/rulebook/layout/prototype/
```

Validation reports are written under:

```text
build/rulebook/layout/reports/
```

## Weapons v1 contract

Tier 1 uses the approved columns:

```text
Name | Tier | Trait | Range | Burden | Damage | Action | Critical Effect | Description
```

Rules implemented by the configuration/primitive:

- sort by Tier → Trait → Name;
- render full-width Trait group bands;
- retain Trait as a table column;
- render Damage formula only, without damage type;
- compose Weapon Features before ordinary Actions in the Action column;
- render missing Action/Critical Effect as an em dash;
- consume already-normalized Critical Effect names without reparsing Foundry prefixes;
- consume Step 4 plain-text descriptions;
- repeat column headers when a long table crosses a page boundary;
- prevent table rows from being intentionally split by the layout code.

The catalog engine is configuration-driven. Other Equipment & Technology families
will receive their own field/grouping configurations rather than inheriting the
Weapons schema.

## Scope boundary

C validates only the Tier 1 Weapons table primitive. The layout package also
exposes semantic Pandoc-AST replacement for `family:weapons`, but the full-book
replacement is intentionally deferred until D, when all four Weapon tiers and the
Action/Critical Effect reference material are ready. This prevents C from deleting
Tiers 2–4 from the current complete manuscript merely to demonstrate the primitive.
