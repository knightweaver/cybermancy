# Cybermancy Rulebook Step 4 — r4 Script Update

This package addresses the two blockers exposed by the v1.4 Step 4 build:

1. **Structured-family digest divergence** between the Step 2 publication-manifest generator and Step 4 normalizer.
2. **Foundry runtime artwork incorrectly treated as publication-required assets.**

## Install location

Copy the contents of this package into:

```text
cybermancy/
└── build/
    └── rulebook/
        └── scripts/
            ├── build-rulebook-publication-manifest.py
            ├── build-rulebook-normalization-artifacts.py
            ├── build-rulebook-source.py
            └── rulebook_normalize/
                ├── __init__.py
                ├── assemble.py
                ├── assets.py
                ├── manifest.py
                ├── markdown.py
                ├── pipeline.py
                ├── snapshot.py          # NEW shared snapshot/digest implementation
                ├── structured.py
                ├── validate.py
                └── xrefs.py
```

The launcher already prefers `build/rulebook/scripts/rulebook_normalize/` over the legacy `pyCybermancy/rulebook_normalize/` package, so these Step 4 changes can be tested without checking them into Git first.

`upgrade-build-rulebook-inventory.py` is included only for reference. If your current inventory already reports 1082 structured entities, do not rerun the upgrader.

## Shared structured-family digest v2

Step 2 and Step 4 now import the exact same implementation from:

```text
rulebook_normalize/snapshot.py
```

The v2 digest is:

```text
sha256(sorted stable-source-id<TAB>repo-path<TAB>file-sha256
       over logical publication entities)
```

Foundry folder records and actor records excluded by an explicit actor type are not part of the publication digest.

The publication manifest records the exact algorithm string and digest version. The normalization config copies that algorithm from the publication manifest. Step 4 validates that all three layers agree before materialization.

## Asset policy correction

Structured JSON may contain many `img`, `src`, and `texture` fields used only by Foundry VTT. r4 now separates them into two classes:

- `assets.json` — only images actually emitted into normalized reader-facing Markdown; these are publication assets and unresolved files remain errors.
- `runtime-assets.json` — Foundry/runtime image references retained for provenance only; these are not staged and are not build blockers unless they are actually rendered into the manuscript.

URL-encoded repository paths such as `Corporate%20Guard.png` are decoded before repository resolution.

## Tests

The package includes 18 normalization tests. They cover the existing Step 4 regression suite plus:

- same-name structured records remain distinct;
- structured digest determinism/content sensitivity;
- runtime icons do not become publication assets;
- rendered Markdown images do become publication assets.

A synthetic full materialization was also validated with:

- shared digest contract PASS;
- runtime Foundry image retained as metadata only;
- URL-encoded authored image successfully staged;
- deterministic second build PASS.

## Next run — no Git commit required

Your source snapshot remains the existing frozen Git commit. Because no canonical rulebook sources changed, **do not rerun the inventory solely for this tooling change**.

Run these commands in order:

```bash
python build/rulebook/scripts/build-rulebook-publication-manifest.py
```

This should create the next publication manifest (normally v1.5) with the new shared v2 family digests while retaining the same frozen Git commit and the 1082-entity corpus.

Then:

```bash
python build/rulebook/scripts/build-rulebook-assembly-manifest.py
```

Then:

```bash
python build/rulebook/scripts/build-rulebook-normalization-artifacts.py
```

Then validate:

```bash
python build/rulebook/scripts/build-rulebook-source.py validate
```

If validation passes, run:

```bash
python build/rulebook/scripts/build-rulebook-source.py build
```

## Expected changes in the next validation

You should see:

```text
EXPECTED_STRUCTURED_COUNT        PASS (1082)
STRUCTURED_FAMILY_COUNTS         PASS (1082)
STRUCTURED_DIGEST_CONTRACT       PASS
```

The former 12 `STRUCTURED_FAMILY_DIGEST` mismatches should disappear after regenerating the publication/assembly/config artifacts with the shared v2 digest.

The former 693 unresolved assets should also disappear as a class. If `ASSET_RESOLUTION` still fails, the remaining entries should now be actual images referenced by the normalized manuscript and therefore worth resolving individually.
