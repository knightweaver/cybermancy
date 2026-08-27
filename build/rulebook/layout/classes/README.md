# Step 6 ClassPackage grammar

This directory contains the accepted Chapter 12 publication grammar for Cybermancy Classes and Subclasses.

The grammar was established and visually accepted using the Razz Hacker ClassPackage. It is deliberately separate from the Equipment layout grammar and consumes only the Step 4 normalized corpus:

- `build/rulebook/source/metadata/structured-entities.json`
- staged publication images below `build/rulebook/source/assets/`

It does **not** read canonical Foundry JSON, generated MkDocs pages, or `docs/...` artwork directly. Step 4 owns those source interpretations and exposes only normalized semantic IDs, publication data, and staged publication assets to Step 6.

## Accepted ClassPackage grammar

1. Class identity, domains, and full-height Class art establish the opening.
2. HP and Evasion begin at the top of the text column, aligned with the top of the Class art; the Class lead follows as a distinct paragraph block.
3. Hope Features begin immediately below the Class-art row, followed directly by Class Features.
4. Starting Package uses paired columns with label/value baseline alignment; character-guide recommendations, Background Questions, and Connections follow when present.
5. Linked Subclasses use the accepted parallel two-column grammar whenever a pair is present. The Subclass spread is not forced to a new page: it begins on the current page when sufficient room remains, otherwise it advances naturally.
6. The two Subclass columns are page-breakable and grow independently across as many pages as their canonical text requires. Long Subclasses never fall back to separate full-width pages merely because of estimated text length.
7. Each Subclass uses compact artwork, with Spellcast Trait and lead text aligned at the top of the identity row.
8. Foundation, Specialization, and Mastery Feature groups begin immediately below the Subclass identity/art row and preserve variable-length progression arrays. Feature descriptions may break naturally across pages while headings retain enough following space to avoid obvious orphans.
9. Description body text uses a 10.5 pt minimum; Feature names use 12 pt; Domains use 14 pt.
10. Feature separators belong to the semantic feature type, not to individual features. Hope Features and Class Features each end with one separator after their final feature. Each Subclass Foundation, Specialization, and Mastery group likewise ends with one separator after its final feature; multiple features inside the same group are separated by whitespace only. Class/Subclass identity rules are unchanged.
11. Rendered geometry validation checks description leading and Starting Package baseline alignment when `pdftotext` is available.
12. LuaLaTeX rendering requires the `paracol` package for page-breakable parallel Subclass columns. The builder preflights this dependency when `kpsewhich` or `findtexmf` is available and emits an explicit installation diagnostic if it is missing.

Blank optional content is omitted cleanly. A blank Subclass description is a warning, not a pipeline failure. Broken semantic references, wrong-family references, parent mismatches, unstaged images, unsupported Step 4 schemas, raw Foundry-reference leakage, LaTeX overflow, and rendered-geometry failures are blocking errors.

## Single-Class commands

`class-package-v1.json` retains Razz Hacker as the default single-Class regression fixture:

```powershell
python build\rulebook\scripts\build-rulebook-class-package.py inspect
python build\rulebook\scripts\build-rulebook-class-package.py validate
python build\rulebook\scripts\build-rulebook-class-package.py build
```

A different Class can be selected with `--class-id`; artifact names are derived from the resolved Class name.

## All-Class regression

The current Step 6 production stage applies the accepted grammar to every Class entity present in the Step 4 semantic corpus:

```powershell
python build\rulebook\scripts\build-rulebook-all-class-packages.py inspect
python build\rulebook\scripts\build-rulebook-all-class-packages.py validate
python build\rulebook\scripts\build-rulebook-all-class-packages.py build
```

The batch build discovers Classes dynamically from Step 4 rather than hard-coding the current count. It writes all generated ClassPackage PDFs, TeX files, and view models beneath:

```text
build/rulebook/layout/class-packages/
```

Per-Class validation reports are written beneath:

```text
build/rulebook/layout/reports/class-packages/
```

with the aggregate report at:

```text
build/rulebook/layout/reports/class-packages-all.json
```

All commands use the rulebook pipeline's terse CLI convention. Add `--verbose` anywhere for the complete aggregate report. `build --tex-only` generates every Class view model and LaTeX file without invoking LuaLaTeX.

## Current boundary

The Razz Hacker design proof is complete and the publication grammar is accepted. The current task is **all-Class regression**: confirm that the same grammar handles every Class, Class Feature set, Starting Package, Subclass pair, and variable-length progression in the canonical Step 4 corpus without reverting to alternate layouts or creating avoidable dead whitespace.

Full Chapter 12/Pandoc AST integration remains deferred until this all-Class regression is reviewed and accepted. No alternate authoring stream is introduced.
