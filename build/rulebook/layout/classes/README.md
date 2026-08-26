# Step 6 ClassPackage prototype

This directory contains the first Chapter 12 publication-design proof for Cybermancy Classes and Subclasses.

The prototype is deliberately isolated from the accepted Equipment layout grammar. It consumes only the Step 4 normalized corpus:

- `build/rulebook/source/metadata/structured-entities.json`
- staged publication images below `build/rulebook/source/assets/`

It does **not** read canonical Foundry JSON, generated MkDocs pages, or `docs/...` artwork directly. Step 4 owns those source interpretations and exposes only normalized semantic IDs, publication data, and staged publication assets to Step 6.

## Prototype target

`class-package-v1.json` currently selects the Razz Hacker Class entity as the design proof. The composition is generic: the renderer follows the Class semantic relationships to its Class/Hope Features, linked Subclasses, each Subclass progression group, and referenced starting equipment.

The current compact prototype grammar is:

1. Class identity, domains, and full-height Class art establish the opening.
2. HP and Evasion begin at the top of the text column, aligned with the top of the Class art; Class lead text follows them.
3. Hope Features begin immediately below the Class-art row, followed directly by Class Features.
4. Starting package, character-guide recommendations, Background Questions, and Connections follow when present.
5. The linked Subclasses begin together on a new page and are paired in parallel half-page columns when two are available.
6. Each Subclass uses artwork at roughly half the original page footprint, with Spellcast Trait and lead text aligned to the top of the artwork.
7. Foundation, Specialization, and Mastery Feature groups begin immediately below the Subclass identity/art row and preserve variable-length progression arrays.
8. If a Class eventually has more Subclasses than fit the configured column count, additional pairs continue on subsequent pages without changing the Class/Subclass semantic model.

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
