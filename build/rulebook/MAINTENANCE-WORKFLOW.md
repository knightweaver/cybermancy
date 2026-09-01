# Cybermancy Content Creation through Rulebook Maintenance Workflow

This is the end-to-end workflow that is used for:
 * Generating new content (mostly Adversaries and Environments) in ChatGPT using the Package Pipeline
 * Importing that content into Foundry via a macro
 * Exporting content from Foundry via fvtt
 * Updating the Cybermancy project in GitHub
 * Running the maintenance steps in a command line to rebuild the rulebooks, both the Player Handbook and the GM Guide

## 1. Generating new content in ChatGPT

In the Cybermancy - World & Campaign project we have built up an Adversary and Environment pipeline that will generate content from a prompt shaped like this:

```angular2html
BUILD ADVERSARY
Name: <name>
Tier: <1-4>
Role: <Solo|Leader|Bruiser|Standard|Minion|Horde|Ranged|Skulk|Support|Social>
    or
Type: <Exploration|Traversal|Social|Event>    
Concept: <1-3 sentences>
```
That prompt should generate a full zip file that can be loaded into Foundry.  (NOTE: the preserved artifacts for the pipeline are located E:\Documents\Daniel\role-gaming\Cybermancy Adversary and Environment Generator in case they are ever needed)

## 2. Import into Foundry

### Unzip the file generated from 1 and it will contain a structure like:
```text
<adversary-environment name>/
├── assets/
│   ├── images/
│   │   └── adversaries/
│   │   │   └── <stub-name.png> 
│   ├── tokens
│   │   └── adversaries
│   │   │   └── <token-stub-name.png> 
├── foundry/
│   └── <stub-name.json>
├── print/
│   └── <stub-name.pdf>
└── source/  -- you will likely never need the files in this directory
```
### Use Foundry macro **Direct Import Cybermancy Actor JSON** to import the <stub-name.json> into Foundry
### Copy the assets to these 3 folder locations:
   * **E:\FoundryVTT\Data\modules\cybermancy**  --> this is the image location so the images show up in the Compendium
   * **E:\FoundryVTT\Data\worlds\cybermancer**  --> this is the image location so the images show up when these are made into Actors (yes, I should have given the campaign in Foundry a better name)
   * The appropriate docs directory:
     * **E:\Documents\Daniel\role-gaming\Cybermancy module development\cybermancy\docs\player-facing**
     * **E:\Documents\Daniel\role-gaming\Cybermancy module development\cybermancy\docs\gm-facing**

I may try to figure out a better option for the images that copying into 3 locations, but that's what we've got at the moment.

## 3. Export from Foundry Compendia to src/packs and regenerate the docs

### Use the fvtt command-line commands to export the Compendia packs, examples:

 * System: 
```powershell
fvtt package unpack -n "system/classes" --outputDirectory "src/packs/system/classes"
```
 * Adventure:
```powershell
fvtt package unpack -n "adventures/adversaries" --outputDirectory "src/packs/adventures/adversaries"
```
 * Items:
```powershell
fvtt package unpack -n "items/loot" --outputDirectory "src/packs/items/loot"
```

### Run generate-docs.py
 * GM facing:
```powershell
python pyCybermancy/generate-docs.py --audience gm-facing --types adversaries,environments --repo-root .
```
 * Player facing:
```powershell
python pyCybermancy/generate-docs.py --audience player-facing --types weapons,loot --repo-root .
```
 * Alternately, you can test out the Cybermancy web documentation locally buy running:
```powershell
python -m mkdocs serve --config-file mkdocs.player.yml --dev-addr 127.0.0.1:8001
```

## 4. Checkin all the changes to the cybermancy project on Github directly into main

## 5. Rebuild rulebooks

### a). Check the baseline

From the repository root, before maintenance work:

```powershell
python build\rulebook\scripts\build-rulebook.py baseline-check
```
Use `--verbose` for the JSON report if there are issues.

If needed the unit test suite:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_*.py" -v
```
### (b. Optional) Check the Status

```powershell
python build\rulebook\scripts\maintain-rulebook.py status
```
`status` is read-only. It reports the state of readiness for the rulebook rebuild. Use `--verbose` for structured JSON.

### c). Prepare a new freeze snapshot

Run `prepare` only **after the intended canonical source and asset changes have been committed**:

```powershell
python build\rulebook\scripts\maintain-rulebook.py prepare
```
> **Generated freeze artifacts must be _committed_ and pushed to main before production build.**

### d). Routine build

After the refreshed inventory and versioned freeze artifacts have been reviewed and **committed**:

```powershell
python build\rulebook\scripts\maintain-rulebook.py build --profile complete-rulebook
python build\rulebook\scripts\maintain-rulebook.py build --profile player-guide
python build\rulebook\scripts\maintain-rulebook.py build --profile all
```
### (Optional and if desired) Dry-run

`prepare`, `build`, and `release` accept `--dry-run`:

```powershell
python build\rulebook\scripts\maintain-rulebook.py prepare --dry-run
python build\rulebook\scripts\maintain-rulebook.py build --profile complete-rulebook --dry-run
python build\rulebook\scripts\maintain-rulebook.py release --profile all --dry-run
```
---

## Full documentation on the Rulebook Maintenance scritps

### Continuous integration

`.github/workflows/rulebook-maintenance.yml` runs the same read-only maintenance validation on pull requests and pushes to `main` when rulebook, source, documentation, asset, manifest, or workflow paths change. It uses a full checkout with Python 3.12, performs compile/import smoke checks, then runs `baseline-check --verbose`, `maintain-rulebook.py status --verbose`, and the complete supported unit suite. The workflow installs no publishing toolchain, regenerates no freeze artifacts, and does not render or deploy PDFs.

## 2. Official routine maintenance CLI

`build/rulebook/scripts/maintain-rulebook.py` is a thin safety/orchestration layer over the existing Step 2–4 and Step 7 commands. It does not replace or reimplement them, and it never runs Git add/commit/push, Foundry pack compilation, Foundry export ingestion, tagging, or GitHub Release creation.

### Status

```powershell
python build\rulebook\scripts\maintain-rulebook.py status
```

`status` is read-only. It reports repository HEAD and working-tree state, changed canonical-source paths, the current inventory snapshot, selected publication/assembly/normalization freezes, compatibility/tracking, generated Step 4 freshness, production-preflight eligibility, and the recommended next action. Use `--verbose` for structured JSON.

### Prepare a new freeze snapshot

Run `prepare` only **after the intended canonical source and asset changes have been committed**:

```powershell
python build\rulebook\scripts\maintain-rulebook.py prepare
```

The command requires a clean working tree at startup, records HEAD, runs the strict inventory, verifies that the generated inventory records that same HEAD, generates the next publication manifest from the latest accepted publication freeze, generates the compatible assembly manifest and normalization artifacts, validates their compatibility, then stops. It does **not** materialize Step 4 and does **not** render a PDF.

Review every generated inventory/manifest/configuration artifact and commit it before building. Until that commit exists, `status` reports:

> Generated freeze artifacts must be committed before production build.

### Routine build

After the refreshed inventory and versioned freeze artifacts have been reviewed and committed:

```powershell
python build\rulebook\scripts\maintain-rulebook.py build --profile complete-rulebook
python build\rulebook\scripts\maintain-rulebook.py build --profile player-guide
python build\rulebook\scripts\maintain-rulebook.py build --profile all
```

`build` requires a clean working tree and tracked compatible freeze inputs. Its non-dry-run child sequence is deliberately only:

1. Step 4 `build`.
2. Production `build` for the explicitly requested profile.

The separate Step 4 `validate` subprocess is not repeated because Step 4 `build` performs the same authoritative repository/manifest preflight before materialization. The separate production `preflight` subprocess is not repeated because production `build` always runs production preflight before any rendering stage. A nested preflight failure therefore still stops the wrapper immediately with the child return code, diagnostics, and relevant report paths. `build` does not run reproducibility automatically and does not infer a profile from changed filenames.

For adversary or environment maintenance, use:

```powershell
python build\rulebook\scripts\maintain-rulebook.py build --profile complete-rulebook
```

### Release checkpoint

At a release checkpoint only:

```powershell
python build\rulebook\scripts\maintain-rulebook.py release --profile all
```

`release` performs the same safety checks, then runs Step 4 `build`, the requested production `build`, and production `reproducibility`, in that order. The ordinary production build is intentionally retained at release checkpoints. Production `build` performs its own production preflight, and production `reproducibility` also performs production preflight before either of its two reproducibility builds. Reproducibility runs only after the ordinary production build succeeds. The wrapper reports the final release filenames and relevant report locations. It does not package, tag, push, or create a GitHub Release.

### Dry-run

`prepare`, `build`, and `release` accept `--dry-run`:

```powershell
python build\rulebook\scripts\maintain-rulebook.py prepare --dry-run
python build\rulebook\scripts\maintain-rulebook.py build --profile complete-rulebook --dry-run
python build\rulebook\scripts\maintain-rulebook.py release --profile all --dry-run
```

Dry-run performs read-only discovery and safety validation and creates/deletes no files. For build/release it runs the existing read-only Step 4 `validate` command so current canonical-source compatibility is checked without materialization. The `PLAN:` output then lists the exact mutating commands a corresponding real invocation would run; the read-only validation probe is recorded in child diagnostics but is not represented as a mutating planned command. Dry-run does not invoke a separate production preflight because it performs no production rendering.

All maintenance commands use argument-list subprocesses rather than shell command chaining, so paths with Windows spaces are supported.

## 3. Adversary/environment update workflow

1. Build and validate the entity package using the current Cybermancy Adversary/Environment production pipeline.
2. Import it into Foundry and inspect it.
3. Export the Foundry Actor JSON.
4. Place the JSON under `src/packs/adventures/adversaries` or `src/packs/adventures/environments` as appropriate.
5. Place required art under the canonical repository asset paths referenced by the entity.
6. Commit the canonical source and asset changes.
7. Run `python build\rulebook\scripts\maintain-rulebook.py prepare`.
8. Review and commit the generated `build/rulebook/inventory/` outputs and new versioned publication/assembly/normalization artifacts.
9. Run `python build\rulebook\scripts\maintain-rulebook.py build --profile complete-rulebook`.

The publication manifest remains the frozen expected canonical corpus authority. `prepare` does not bypass the requirement that inventory provenance match committed HEAD, and `build` does not bypass Step 4 or production preflight; those validations are enforced inside the authoritative build commands.

## 4. Git and freeze boundaries

The maintenance CLI intentionally preserves the existing transaction boundaries:

- Canonical authored Markdown, structured `src/packs/...` JSON, and required canonical assets must be committed before strict inventory generation.
- The publication-manifest refresh fails unless `inventory.repository.git_commit` equals repository `HEAD`.
- `prepare` deliberately leaves its generated inventory and versioned freeze artifacts uncommitted for human review.
- Production build/release requires the selected inventory, publication manifest, assembly manifest, and normalization config to be tracked, and requires a clean working tree.
- `build/rulebook/source/` remains ignored/generated Step 4 output and is never committed as canonical input.

A current inventory file may have been generated at a different repository commit than an older still-selected publication freeze; that fact alone is not a production error. The selected publication/assembly/normalization set remains the authority until a new compatible set is generated, reviewed, and committed.

## 5. Individual maintenance commands remain supported

The wrapper is conservative convenience, not a replacement. The existing commands remain independently usable:

| Function | Supported launcher | Active implementation |
|---|---|---|
| Strict inventory | `build-rulebook-inventory.py` | `build-rulebook-inventory.py.impl` |
| Publication freeze | `rebuild-rulebook-publication-manifest.py` (also compatible `build-rulebook-publication-manifest.py`) | `build-rulebook-publication-manifest.py.impl` |
| Assembly freeze | `build-rulebook-assembly-manifest.py` | `build-rulebook-assembly-manifest.py.impl` |
| Normalization config/standard | `build-rulebook-normalization-artifacts.py` | `build-rulebook-normalization-artifacts.py.impl` |
| Step 4 normalized source | `build-rulebook-source.py` | `build-rulebook-source.py.impl` |
| Production renderer | `build-rulebook.py` | `rulebook_production/` |

The equivalent manual refresh sequence remains:

```powershell
python build\rulebook\scripts\build-rulebook-inventory.py --strict
python build\rulebook\scripts\rebuild-rulebook-publication-manifest.py --inventory-json build\rulebook\inventory\rulebook-inventory.json
python build\rulebook\scripts\build-rulebook-assembly-manifest.py
python build\rulebook\scripts\build-rulebook-normalization-artifacts.py
```

After reviewing and committing those generated freeze artifacts, the equivalent optimized manual build sequence is:

```powershell
python build\rulebook\scripts\build-rulebook-source.py build
python build\rulebook\scripts\build-rulebook.py build --profile complete-rulebook
```

The standalone `build-rulebook-source.py validate` and `build-rulebook.py preflight` commands remain supported for explicit read-only diagnostics. They are simply redundant when invoked immediately before their corresponding authoritative `build` commands, which enforce those validations internally.

`rulebook_cli.py` and `rulebook_layout_cli_compat.py` remain compatibility infrastructure, not alternate publication authorities.

## 6. Active production path

The official Step 7 production entrypoint remains `build/rulebook/scripts/build-rulebook.py`. The maintenance CLI does not alter it.

Its active imported implementation is `build/rulebook/scripts/rulebook_production/`, principally `contract.py`, `preflight.py`, `orchestrator.py`, `publication_shell.py`, `reproducibility.py`, `reporting.py`, and `workspace.py`. `baseline.py` is the read-only maintenance guard and is not part of rendering.

Production rendering continues to invoke the accepted Step 6 tail in this exact order:

| Order | Production stage | Launcher | Active implementation role |
|---:|---|---|---|
| 130 | publication-shell-lowering | `build-rulebook-step6-publication-shell.py` | Step 6 shell lowering in `rulebook_layout.publication_shell`, with Step 7 publication-shell preparation |
| 140 | post-transform-validation | `build-rulebook-step6-post-transform-validation.py` | `rulebook_layout.post_transform_validation` |
| 150 | integrated-latex | `build-rulebook-step6-integrated-latex.py` | integrated LaTeX generation plus `rulebook_production.publication_shell` |
| 160 | lualatex | `build-rulebook-step6-lualatex.py` | `rulebook_layout.unified_lualatex` |
| 170 | rendered-regression | `build-rulebook-step6-rendered-regression.py` | `rulebook_layout.rendered_regression` plus production publication-shell rendered validation |

The Step 6 integration authority remains `build/rulebook/layout/integration/step6-integration-v1.json`. The Step 7 authority remains `build/rulebook/production/production-renderer-v1.json`; reader-facing names remain in `build/rulebook/production/publication-metadata-v1.json`. Accepted release filenames remain `Cybermancy_Core_Rulebook.pdf` and `Cybermancy_Player_Guide.pdf`.

## 7. Generated versus tracked artifacts

`build/rulebook/inventory/` and the selected versioned freeze artifacts under `build/rulebook/manifests/` are tracked maintenance inputs to production. `build/rulebook/source/` is generated by Step 4, ignored/untracked, and validated in place by production preflight.

Do not edit normalized Step 4 output as a source of truth. Generated PDF/work/report/output trees remain production outputs. Standalone package builders, design proofs, compatibility aliases, and historical artifacts remain available but are not promoted to top-level production authority by the maintenance CLI.
