# Stage 150 — Integrated LaTeX Generation

Status: **IMPLEMENTED — real-corpus proof required before acceptance**

Stage 150 consumes the accepted Stage 140 validated Pandoc AST and produces one body-complete LaTeX document for the selected publication profile. It does **not** invoke LuaLaTeX; compilation remains Stage 160.

## Authority and non-goals

Stage 150 does not redesign any frozen chapter grammar. The accepted Prose, Rules, Character Origins, ClassPackage, DomainPackage, Equipment, ICE Reference, Adversary, Environment, and Adversary Feature Reference bodies are already present in the Stage 140 AST.

Stage 150 owns only the document-level integration concerns that cannot be expressed independently by those frozen packages:

- exactly one document class and one document boundary;
- one shared package/dependency surface;
- definitions for the Stage 130 publication-shell macros;
- accepted Rules and Character Origins document-level macro extensions;
- local font/palette wrappers for structured package families;
- deterministic geometry transitions between publication lanes;
- a single self-contained graphics root for Stage 160;
- body-only Pandoc lowering of the validated generation AST.

The accepted Stage 140 AST is never mutated. Stage 150 operates on a deep-copy generation AST and treats both the generation AST and final TeX as noncanonical outputs.

## Input

Default inputs are:

```text
build/rulebook/layout/integration/output/
  player-guide-stage140-validated.ast.json
  complete-rulebook-stage140-validated.ast.json
```

Stage 140 is re-run against the loaded AST immediately before generation. A failed Stage 140 revalidation blocks Stage 150.

The accepted layout contracts loaded for the one-document shell are:

```text
build/rulebook/layout/prose/prose-layout-v1.json
build/rulebook/layout/character-origins/character-origins-layout-v1.json
build/rulebook/layout/classes/class-package-v1.json
build/rulebook/layout/domains/domain-package-v1.json
build/rulebook/layout/equipment/equipment-section-v1.json
build/rulebook/layout/equipment/*-v1.json
build/rulebook/layout/ice/ice-reference-package-v1.json
```

The accepted Long-Form Prose `document_preamble()` remains the document-shell base. Stage 150 extends it rather than creating an unrelated second style system.

## Geometry lanes

Frozen packages were designed at different horizontal page geometries. Stage 150 preserves those requirements through deterministic lane transitions:

| Lane | Chapters | Left/Right margin |
|---|---|---:|
| Long-Form Prose / Rules / Character Origins | 1–11, 23–28 | 0.78 in |
| ClassPackage / DomainPackage | 12, 14 | 0.55 in |
| Equipment & Technology | 15–22 | 0.46 in |
| ICE / Encounter Toolkit | 29–32 | 0.55 in |

The Equipment margin is intentionally preserved because the accepted Equipment tables use the wider full-page width. Geometry changes happen only when a lane changes rather than redundantly at every chapter.

The accepted recto policy remains `preserve-current-clearpage`; Stage 150 does not add recto forcing.

## Publication-shell definitions

Stage 130 emits these stable calls:

```latex
\CMIntegratedPart{roman}{title}{audience}{part-id}
\CMIntegratedChapter{number}{title}{audience}{chapter-id}
\CMIntegratedGMDivider{GM MATERIAL — SPOILERS BEYOND THIS POINT}
```

Stage 150 defines them once in the integrated preamble.

`\CMIntegratedPart` delegates to the accepted Prose `\CMPartPage` grammar after selecting the appropriate geometry lane.

`\CMIntegratedChapter` delegates to the accepted Prose `\CMChapterBanner` grammar. Chapters 4–9 also switch to the accepted Rules standard-image cap and ordered-list grammar; all other generic chapters restore the accepted Prose treatment.

`\CMIntegratedGMDivider` produces the single Complete Rulebook GM warning page. It is absent from the Player Guide by profile contract.

## Frozen grammar extensions

### Rules

Stage 150 defines the accepted Rules v1.0 document-level primitives:

```text
CMRulesQuote
CMRulesTable
CMRulesStandardImage
```

The Rules standard image treatment is activated only for Chapters 4–9. It does not globally replace the Long-Form Prose standard-image treatment.

### Character Origins

Stage 150 defines the accepted Character Origins v1.0 document-level primitives from the frozen Character Origins and Prose configs:

```text
CMOriginEntryRule
CMOriginIdentityImage
CMOriginIdentityMissing
CMOriginIdentity
CMOriginFeatureLabel
CMOriginFeature
```

`wrapfig` is loaded once for the whole document.

## Structured-family wrappers

Stage 140 still retains semantic `family:*` Div containers because they are useful validation landmarks. Stage 150 no longer needs those semantic containers, so a deep-copy generation AST flattens each validated family to its exact accepted raw-LaTeX body.

Local wrappers preserve package-specific palettes and font choices without forcing a false global compromise between otherwise frozen designs:

- Classes: accepted ClassPackage colors + Arial;
- Domains: accepted DomainPackage colors + Arial;
- Equipment: each family’s accepted table colors + Arial;
- ICE: accepted ICE palette with the integrated Arial `CMDisplay` font command;
- Encounter Toolkit: accepted Encounter palette + Arial;

`family:subclasses` remains a marker-only body because Subclasses are already rendered inside `family:classes` by the accepted Chapter 12 ClassPackage grammar.

For Chapters 29–32, Stage 140 proves that the package-owned chapter header immediately precedes its family body. Stage 150 wraps that header and body together so the package-specific palette applies to both. No generic second chapter banner is introduced.

## One graphics root

The independently proven chapter lanes generated graphics paths relative to their own proof work directories. Those paths cannot be carried unchanged into one Stage 160 compile working directory.

Stage 150 therefore resolves every reachable `\includegraphics`/`\detokenize{...}` reference against the known accepted integration work roots, copies the asset into:

```text
build/rulebook/layout/integration/output/stage150/<profile>/assets/
```

and rewrites the generation AST to use only `assets/...` paths.

PNG, JPEG, and PDF assets are copied directly. WebP/GIF/BMP/TIFF assets are deterministically converted to PNG through Pillow. Multiple resolution candidates are accepted only when their content hashes are identical; conflicting candidates fail closed.

The final integrated TeX therefore contains no dependence on the user’s absolute repository path or on the Stage 130 proof working directory.

## Pandoc boundary

After family flattening and asset staging, Stage 150 writes a diagnostic generation AST and invokes Pandoc once:

```text
pandoc --from=json --to=latex --wrap=none <generation.ast.json>
```

No standalone Pandoc document shell is requested. The resulting body stream is then placed between the single integrated preamble/document boundary.

## Fail-closed validation

Stage 150 blocks output when any of the following is false:

- integration contract Stage 150 is order 150;
- Stage 140 revalidation passes;
- every expected family can be flattened exactly;
- all graphics references resolve and stage;
- body-only Pandoc lowering succeeds;
- no nested `documentclass` / `begin{document}` / `end{document}` enters the body;
- the final document contains exactly one document class and one document boundary;
- every `CM*` command or `CM*/cm*` environment referenced by the body is defined in the integrated preamble;
- profile Part/Chapter/GM-divider call counts remain exact;
- the source Stage 140 AST hash remains unchanged.

Stage 150 deliberately does not validate rendered page geometry, overflow, fonts, or PDF semantics. Those require LuaLaTeX and belong to Stages 160–170.

## Outputs

Player Guide:

```text
build/rulebook/layout/integration/output/stage150/player-guide/
  Cybermancy_Player_Guide_Step6_Integrated.tex
  assets/
```

Complete Rulebook:

```text
build/rulebook/layout/integration/output/stage150/complete-rulebook/
  Cybermancy_Complete_Rulebook_Step6_Integrated.tex
  assets/
```

Diagnostic generation artifacts are written beneath:

```text
build/rulebook/layout/integration/work/stage150/<profile>/
```

Reports are written to:

```text
build/rulebook/layout/integration/reports/
  player-guide-stage150-integrated-latex.json
  complete-rulebook-stage150-integrated-latex.json
```

All of these are generated/noncanonical outputs.

## Proof commands

From repository root:

```powershell
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_integrated_latex.py" -v
python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_*.py" -v

python build\rulebook\scripts\build-rulebook-step6-integrated-latex.py --profile player-guide --verbose
python build\rulebook\scripts\build-rulebook-step6-integrated-latex.py --profile complete-rulebook --verbose
```

A clean real-corpus proof is required before Stage 150 is accepted and before Stage 160 LuaLaTeX compilation begins.
