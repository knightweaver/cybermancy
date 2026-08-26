# Step 6 ClassPackage prototype

This directory contains the first Chapter 12 publication-design proof for Cybermancy Classes and Subclasses.

The prototype is deliberately isolated from the accepted Equipment layout grammar. It consumes only the Step 4 normalized corpus:

- `build/rulebook/source/metadata/structured-entities.json`
- staged publication images below `build/rulebook/source/assets/`

It does **not** read canonical Foundry JSON, generated MkDocs pages, or `docs/...` artwork directly. Step 4 owns those source interpretations and exposes only normalized semantic IDs, publication data, and staged publication assets to Step 6.

## Prototype target

`class-package-v1.json` currently selects the Razz Hacker Class entity as the design proof. The composition is generic: the renderer follows the Class semantic relationships to its Class/Hope Features, linked Subclasses, each Subclass progression group, and referenced starting equipment.

The prototype grammar is:

1. Class identity, art, domains, HP, and Evasion.
2. Class lead text.
3. Hope and Class Feature definitions.
4. Starting package and character-guide recommendations when present.
5. Optional Background Questions and Connections when present.
6. Every linked Subclass as part of the same ClassPackage.
7. Subclass identity/art, optional Spellcast Trait and lead text.
8. Foundation, Specialization, and Mastery Feature groups using variable-length progression arrays.

Blank optional content is omitted cleanly. A blank Subclass description is a warning, not a pipeline failure. Broken semantic references, wrong-family references, parent mismatches, unstaged images, unsupported Step 4 schemas, and raw Foundry-reference leakage are blocking errors.

## Commands

From the repository root:

```powershell
python build\rulebook\scripts\build-rulebook-class-package.py inspect
python build\rulebook\scripts\build-rulebook-class-package.py validate
python build\rulebook\scripts\build-rulebook-class-package.py build
```

All commands use the rulebook pipeline's terse CLI convention. Add `--verbose` anywhere for the complete JSON report:

```powershell
python build\rulebook\scripts\build-rulebook-class-package.py build --tex-only --verbose
```

`build` writes generated prototype artifacts beneath `build/rulebook/layout/class-package-prototype/` and the validation report beneath `build/rulebook/layout/reports/`.

## D boundary

This is a **standalone Step 6 design prototype**. It intentionally does not yet replace Chapter 12 inside the full Pandoc AST or full-book PDF build. That integration is deferred until the ClassPackage publication grammar is reviewed and accepted. Once the grammar is accepted, the same semantic composer can be applied to all five Classes and integrated into the chapter-level Step 6 AST transformation without creating a duplicate authoring stream.
