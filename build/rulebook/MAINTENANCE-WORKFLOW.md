# Cybermancy Rulebook Maintenance Workflow

This is the maintainer-facing workflow for the current Rulebook Step 4 freeze and Step 7 production renderer. It documents the supported path; it does not redefine publication authority, chapter architecture, layout grammar, production stages, or release names.

## 1. Code/freeze baseline

From the repository root, before maintenance work:

```powershell
python build\rulebook\scripts\build-rulebook.py baseline-check
```

Use `--verbose` for the JSON report. This check is read-only and intentionally does not require `build/rulebook/source/`, Pandoc, LuaLaTeX, or the PDF utilities. It verifies the accepted production contract, frozen Step 6 hashes, selected freeze artifacts, profile/release identity, chapter topology, and production-stage tail.

## 2. Structured-content maintenance sequence

1. Import or edit the structured content in Foundry.
2. Export the canonical Foundry JSON.
3. Place the exported JSON in the appropriate canonical `src/packs/...` family. Place required art under the repository `assets/` tree at the canonical path referenced by the entity.
4. Commit the canonical source and asset changes **before** generating the new inventory. The current publication-manifest generator requires `inventory.repository.git_commit` to equal repository `HEAD`.
5. Rebuild the strict inventory:

   ```powershell
   python build\rulebook\scripts\build-rulebook-inventory.py --strict
   ```

6. Rebuild the publication manifest. By default the launcher selects the highest current publication manifest as its base and creates the next minor version; the explicit inventory path below binds it to the inventory just generated:

   ```powershell
   python build\rulebook\scripts\rebuild-rulebook-publication-manifest.py --inventory-json build\rulebook\inventory\rulebook-inventory.json
   ```

7. Rebuild the compatible assembly manifest. The current CLI selects the highest publication manifest when no override is supplied:

   ```powershell
   python build\rulebook\scripts\build-rulebook-assembly-manifest.py
   ```

8. Rebuild the compatible normalization configuration and standard. The current CLI selects the highest compatible publication/assembly inputs when no overrides are supplied:

   ```powershell
   python build\rulebook\scripts\build-rulebook-normalization-artifacts.py
   ```

9. Commit the regenerated `build/rulebook/inventory/` files and new versioned manifest/configuration artifacts. Production preflight requires the selected freeze artifacts to be tracked by Git. Do not commit generated Step 4 `build/rulebook/source/` output.
10. Rebuild the Step 4 normalized publication source:

    ```powershell
    python build\rulebook\scripts\build-rulebook-source.py build
    ```

11. Run production preflight:

    ```powershell
    python build\rulebook\scripts\build-rulebook.py preflight
    ```

12. Build the required publication profile:

    ```powershell
    python build\rulebook\scripts\build-rulebook.py build --profile complete-rulebook
    python build\rulebook\scripts\build-rulebook.py build --profile player-guide
    ```

    The accepted release filenames remain `Cybermancy_Core_Rulebook.pdf` and `Cybermancy_Player_Guide.pdf`.
13. At release checkpoints only, run the two-clean-build semantic/render reproducibility check for the profile being released:

    ```powershell
    python build\rulebook\scripts\build-rulebook.py reproducibility --profile complete-rulebook
    python build\rulebook\scripts\build-rulebook.py reproducibility --profile player-guide
    ```

## 3. Supported rulebook unit suite

Run the supported Python unit suite from the repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_*.py" -v
```

`unittest` prints the number of tests run and reports failures, errors, and skips; a failing suite exits nonzero. Do not suppress that exit status. These tests exercise code plus checked-in contracts, manifests, canonical source fixtures, and checked-in assets. A genuinely missing checked-in source or asset is a real test failure and must not be fabricated.

The ignored/generated Step 4 corpus under `build/rulebook/source/` is a separate production-readiness layer. Its absence is not by itself a unit-test failure. `build-rulebook.py preflight`, profile builds, and reproducibility are the commands that require current generated Step 4 output and the external production toolchain.

## 4. Active production path

The official Step 7 production entrypoint is:

`build/rulebook/scripts/build-rulebook.py`

Its active imported implementation is `build/rulebook/scripts/rulebook_production/`, principally `contract.py`, `preflight.py`, `orchestrator.py`, `publication_shell.py`, `reproducibility.py`, `reporting.py`, and `workspace.py`. `baseline.py` is the read-only maintenance guard and is not part of rendering.

The production entrypoint first runs `rulebook_production.preflight.run_preflight`. Production rendering then uses `rulebook_production.orchestrator.stage_commands` to invoke the accepted Step 6 launchers in this exact tail order:

| Order | Production stage | Launcher | Active implementation role |
|---:|---|---|---|
| 130 | publication-shell-lowering | `build-rulebook-step6-publication-shell.py` | Step 6 shell lowering in `rulebook_layout.publication_shell`, with Step 7 publication-shell preparation |
| 140 | post-transform-validation | `build-rulebook-step6-post-transform-validation.py` | `rulebook_layout.post_transform_validation` |
| 150 | integrated-latex | `build-rulebook-step6-integrated-latex.py` | integrated LaTeX generation plus `rulebook_production.publication_shell` |
| 160 | lualatex | `build-rulebook-step6-lualatex.py` | `rulebook_layout.unified_lualatex` |
| 170 | rendered-regression | `build-rulebook-step6-rendered-regression.py` | `rulebook_layout.rendered_regression` plus production publication-shell rendered validation |

The Step 6 integration authority for those stages remains `build/rulebook/layout/integration/step6-integration-v1.json`. The Step 7 authority remains `build/rulebook/production/production-renderer-v1.json`; reader-facing names remain in `build/rulebook/production/publication-metadata-v1.json`.

## 5. Step 2–4 maintenance entrypoints and compatibility launchers

The supported maintenance launchers are the public `.py` files in `build/rulebook/scripts/`. Several delegate through `rulebook_cli.py` to a sibling `.py.impl` implementation so older invocation paths remain compatible. In particular:

| Function | Supported launcher | Active implementation |
|---|---|---|
| Strict inventory | `build-rulebook-inventory.py` | `build-rulebook-inventory.py.impl` |
| Publication freeze | `rebuild-rulebook-publication-manifest.py` (also the compatible `build-rulebook-publication-manifest.py`) | `build-rulebook-publication-manifest.py.impl` |
| Assembly freeze | `build-rulebook-assembly-manifest.py` | `build-rulebook-assembly-manifest.py.impl` |
| Normalization config/standard | `build-rulebook-normalization-artifacts.py` | `build-rulebook-normalization-artifacts.py.impl` |
| Step 4 normalized source | `build-rulebook-source.py` | `build-rulebook-source.py.impl` |

`rulebook_cli.py` and `rulebook_layout_cli_compat.py` are compatibility infrastructure, not alternate publication authorities.

## 6. Standalone prototypes, design proofs, tests, and historical artifacts

The numerous package builders and `build-rulebook-step6-*-integrated.py` scripts remain useful standalone Step 3–6 package/design-proof/regression tools, but they are not the official Step 7 top-level production entrypoint unless `rulebook_production.orchestrator.stage_commands` invokes them. Examples include `build-rulebook-step6-integrated.py`, the prose/rules/character-origin/encounter integrated builders, `build-rulebook-layout.py`, `build-rulebook-pdf.py`, and family package builders.

`build/rulebook/scripts/tests/test_*.py` is the supported rulebook unit/regression suite. Layout-package README files and JSON contracts under `build/rulebook/layout/` document/freeze the accepted package grammars.

Potentially historical or suspicious artifacts should be investigated before any later cleanup and are deliberately retained in this transaction. These include compatibility aliases such as `rebuild-rulebook-publication-manifest-v2.py`, the dormant-looking `rebuild-rulebook-publication-manifest.py.impl` beside the currently targeted implementation, `scratch_5.py`, and the captured `test-results.txt`. Their presence does not make them production entrypoints.

## 7. Generated versus tracked artifacts

`build/rulebook/inventory/` and the selected versioned freeze artifacts under `build/rulebook/manifests/` are tracked maintenance inputs to production preflight. `build/rulebook/source/` is generated by Step 4, ignored/untracked, and validated in place by production preflight; the Step 7 build does not regenerate it automatically.

Do not edit normalized Step 4 output as a source of truth. Canonical authored Markdown and structured `src/packs/...` inputs remain upstream authority; generated PDF/work/report/output trees remain production outputs.
