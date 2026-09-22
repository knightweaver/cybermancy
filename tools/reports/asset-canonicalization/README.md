# Asset Canonicalization Inventory

Generated from Git tree `03d35b63113087b2ca11124a8983a8c325912f7f`.

This inventory is read-only evidence for the next cleanup step. It does not change
or delete any artwork.

## Redundant tracked docs copies

`redundant-doc-copies.csv` lists documentation artwork whose Git blob is
byte-identical to at least one canonical repository `/assets` file.

- Redundant docs files: **919**
- Redundant working-tree bytes: **381853285**
- Player docs media inspected: **854**
- GM docs media inspected: **496**
- Canonical root media inspected: **1026**

These are safe candidates for removal from tracked audience docs asset trees once
the staged MkDocs build and Step 4 rulebook asset resolution are qualified.

## Docs-only shared art

`docs-only-shared-art.csv` lists byte-identical artwork present in both Player
and GM documentation trees that has **no byte-identical canonical root /assets
copy**.

- Shared-content groups: **17**
- Unique shared-content bytes: **2409620**

The `suggested_shared_path` column is a proposed consolidation target under
`docs/_shared/assets`. When the existing Player and GM logical paths differ,
the suggested target uses a neutral `icons/shared` or `images/shared` path;
source references should be updated before deleting the audience copies.

Existing files already under `docs/_shared/assets` are reported separately in
the CSV and should be preferred when they already represent the intended shared
source.
