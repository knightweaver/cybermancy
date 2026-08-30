# Cybermancy rulebook scripts

This directory contains the maintained Rulebook Step 2–7 tooling. Routine work
should begin with the repository maintenance runbook:

- `build/rulebook/MAINTENANCE-WORKFLOW.md`
- `python build/rulebook/scripts/maintain-rulebook.py status`

## Supported maintenance entrypoints

The supported top-level workflow is `maintain-rulebook.py`:

- `status` — read-only repository/freeze/Step 4 readiness report;
- `prepare` — strict inventory plus compatible Step 2–4 freeze artifacts;
- `build` — Step 4 validation/materialization, production preflight, and selected profile build;
- `release` — the build sequence followed by the existing reproducibility check.

The accepted production renderer remains `build-rulebook.py`, with
`baseline-check`, `preflight`, `build`, and `reproducibility` commands.

The underlying Step 2–4 launchers remain independently supported for diagnostics
and recovery:

| Function | Supported launcher | Active implementation |
|---|---|---|
| Strict inventory | `build-rulebook-inventory.py` | `build-rulebook-inventory.py.impl` |
| Publication freeze | `build-rulebook-publication-manifest.py` and supported `rebuild-rulebook-publication-manifest.py` alias | `build-rulebook-publication-manifest.py.impl` |
| Assembly freeze | `build-rulebook-assembly-manifest.py` | `build-rulebook-assembly-manifest.py.impl` |
| Normalization config/standard | `build-rulebook-normalization-artifacts.py` | `build-rulebook-normalization-artifacts.py.impl` |
| Step 4 normalized source | `build-rulebook-source.py` | `build-rulebook-source.py.impl` |
| Production renderer | `build-rulebook.py` | `rulebook_production/` |

Public wrapper scripts that use `rulebook_cli.py` deliberately delegate to their
named `.py.impl` implementation while preserving the public launcher path. The
implementation files are source code, not separate user-facing commands.

## Active implementation packages

- `rulebook_normalize/` implements the accepted Step 4 normalization/materialization behavior.
- `rulebook_layout/` implements the accepted Step 6 publication/layout transforms and validation.
- `rulebook_production/` implements Step 7 preflight, orchestration, reporting, publication shell, and reproducibility.
- `rulebook_step3_architecture.py` and the `rulebook_step4_*.py` modules provide reviewed extensions used by the supported Step 3/4 launchers.

The production path and frozen contracts are defined by the repository contracts,
not by the presence of other scripts in this directory.

## Standalone proof and package tools

Family package builders, layout proof commands, and intermediate Step 6
integration drivers remain available for manual engineering/regression work.
They are not the top-level production renderer unless the accepted production
orchestrator invokes them.

In particular, retain the intermediate prose, rules, character-origins, and
encounter `build-rulebook-step6-*-integrated.py` proof drivers. They may be run
manually even when no production subprocess statically calls them. The umbrella
`build-rulebook-step6-integrated.py` proof driver is also retained.

## Historical and removed tools

Repository-hygiene work removes obsolete duplicate launchers, superseded
one-time upgrade helpers, the superseded Step 5 content-only PDF prototype, and
scratch/test-transcript residue once repository-wide reference checks confirm
they have no supported caller. These historical tools are not publication
authority and are not part of the accepted Step 7 production path.

Do not infer authority from an old script name or an archived implementation.
Use `MAINTENANCE-WORKFLOW.md`, the production contracts, and the active launchers
above when deciding which command is supported.
