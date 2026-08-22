# Cybermancy Rulebook Step 4 — r4.2 Post-Acceptance Publication-Safety Fixes

This package contains two targeted Step 4 fixes exposed by the first real Step 5 PDF prototype:

1. Pandoc-safe body thematic breaks.
2. Self-contained Step 4 publication asset staging.

Step 4 source authority, assembly architecture, audience routing, semantic IDs,
structured-family reconciliation, digest v2 governance, HEAD/source-corpus policy,
and deterministic materialization are unchanged.

## Fix 1 — Pandoc-safe body thematic breaks

Assembled profiles still begin with their normal YAML metadata block:

```markdown
---
title: "..."
profile: "..."
source-commit: "..."
---
```

After that block, standalone body thematic breaks written as:

```markdown
---
```

are deterministically emitted as:

```markdown
***
```

Canonical authored Markdown is not edited.

New blocking validation:

```text
BODY_YAML_DELIMITER_AMBIGUITY
```

A passing assembled profile has no Pandoc-ambiguous body `---` delimiters and,
outside fenced code, only the opening YAML block uses `---`.

## Fix 2 — Self-contained publication assets

Publication-visible local images are now normalized to paths resolvable from:

```text
build/rulebook/source/assembled/*.md
```

and copied into:

```text
build/rulebook/source/assets/
```

For example:

```text
canonical source:
  docs/player-facing/assets/icons/corps/astravail-technologies.webp

assembled Markdown:
  ../assets/icons/corps/astravail-technologies.webp

staged publication file:
  build/rulebook/source/assets/icons/corps/astravail-technologies.webp
```

Reader-visible source assets already beneath a repository `assets/` directory
preserve the hierarchy below `assets/`. A reader-visible source file outside an
`assets/` tree is staged under:

```text
build/rulebook/source/assets/repository/<repo-relative-path>
```

and the Markdown target is rewritten accordingly.

Foundry runtime/action/token/feature image wiring that is not rendered into the
book remains metadata-only and is not promoted back into publication assets.

### Asset validation

The materializer now checks:

```text
PUBLICATION_ASSET_COLLISION
ASSET_STAGING
ASSET_RESOLUTION
ASSET_TREE_DETERMINISM
```

`ASSET_RESOLUTION` is now an assembled-profile invariant: every non-remote image
reference must resolve to an actual file inside `build/rulebook/source/`, and
that file must have Step 4 staging provenance.

Conflicting different source files that would map to the same normalized asset
path are blocking errors rather than silent basename substitutions.

The existing whole-build `DETERMINISM` check remains in force, and an explicit
asset-tree determinism check has been added.

## Output corpus

The resulting Step 4 publication source is now self-contained:

```text
build/rulebook/source/
├── assembled/
│   ├── complete-rulebook.md
│   └── player-guide.md
├── assets/
│   ├── icons/
│   ├── images/
│   └── repository/
└── metadata/
```

The old generated `build/rulebook/assets/` tree is removed on the next successful
Step 4 publish. Only that known legacy generated child is cleaned; `scripts/`,
`manifests/`, and unrelated later-stage outputs are not removed.

## Modified source files

Relative to Step 4 r4.1, the patch modifies exactly these implementation/test files:

```text
build-rulebook-source.py
build-rulebook-normalization-artifacts.py
rulebook_normalize/__init__.py
rulebook_normalize/assets.py
rulebook_normalize/markdown.py
rulebook_normalize/pipeline.py
tests/test_rulebook_normalization.py
```

No canonical Cybermancy prose, structured pack JSON, publication manifest, or
assembly manifest is modified by this patch.

`build-rulebook-publication-manifest.py`, `snapshot.py`, `structured.py`, and the
other package files are included unchanged so the package can be copied as a
complete Step 4 script directory.

## Existing frozen v1.5 inputs

You do **not** need to regenerate Step 2 or Step 3 for these two fixes. They are
representation/materialization corrections, not canonical-source changes.

The current v1.5 normalization config can be used directly. The normalization-
artifact generator is updated so future generated configs describe the new
`build/rulebook/source/assets` staging contract.

## Install

Copy the contents of this package into:

```text
cybermancy/build/rulebook/scripts/
```

over the current r4.1 Step 4 tooling.

## Local regression commands

From the Cybermancy repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -v
python build\rulebook\scripts\build-rulebook-source.py validate
python build\rulebook\scripts\build-rulebook-source.py build
```

The `build` command performs the full materialization validation, including the
new thematic-break and assembled-asset checks plus the existing repeated clean
materialization determinism test.

Expected new checks include:

```text
BODY_YAML_DELIMITER_AMBIGUITY  PASS
PUBLICATION_ASSET_COLLISION    PASS
ASSET_STAGING                  PASS
ASSET_RESOLUTION               PASS
ASSET_TREE_DETERMINISM         PASS
DETERMINISM                    PASS
```

You can also directly inspect the generated profiles with PowerShell:

```powershell
Select-String -Path build\rulebook\source\assembled\complete-rulebook.md -Pattern '^---$'
Select-String -Path build\rulebook\source\assembled\player-guide.md -Pattern '^---$'
```

Each should normally show only the opening and closing YAML metadata delimiters.

Then verify the staged publication tree exists:

```powershell
Get-ChildItem build\rulebook\source\assets -Recurse -File
```

After Step 4 passes, return to Step 5 and run:

```powershell
python build\rulebook\scripts\build-rulebook-pdf.py build --profile all
```

Step 5 should no longer need to reach into `docs/player-facing/assets` or any
other upstream publication/source directory.

## Upstream-source assessment

Neither defect required an upstream canonical-source correction:

- valid authored Markdown thematic breaks were ambiguous only after concatenation
  into a Pandoc publication manuscript;
- canonical asset files already existed, but the Step 4 publication corpus did
  not stage them at the paths emitted by the assembled Markdown.

The patch therefore changes only Step 4 representation/materialization behavior.
If the real repository run discovers a genuinely missing source asset or a
conflicting publication-path collision, Step 4 will now report that explicitly
rather than silently masking it.
