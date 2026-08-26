#!/usr/bin/env python3
"""Generate Cybermancy Step 4 normalization configuration and standard.

Expected repository layout::

    cybermancy/
      build/
        rulebook/
          scripts/
            build-rulebook-normalization-artifacts.py
          manifests/
            cybermancy-rulebook-publication-manifest-v*.json
            cybermancy-rulebook-assembly-manifest-v*.json

The script automatically selects the highest numeric version of the Step 2
publication manifest and Step 3 assembly manifest, validates that they form a
compatible pair, then generates:

    cybermancy-rulebook-normalization-config-v<assembly-version>.json
    cybermancy-rulebook-normalization-standard-v<assembly-version>.md

Both outputs are written to build/rulebook/manifests/.

Typical usage from anywhere::

    python build/rulebook/scripts/build-rulebook-normalization-artifacts.py

Useful diagnostics::

    python build/rulebook/scripts/build-rulebook-normalization-artifacts.py --dry-run
    python build/rulebook/scripts/build-rulebook-normalization-artifacts.py \
        --publication-manifest cybermancy-rulebook-publication-manifest-v1.2.json \
        --assembly-manifest cybermancy-rulebook-assembly-manifest-v1.2.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "1.2.0"

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
MANIFEST_DIR = RULEBOOK_DIR / "manifests"
REPO_ROOT = RULEBOOK_DIR.parent.parent

PUBLICATION_PATTERN = "cybermancy-rulebook-publication-manifest-v*.json"
ASSEMBLY_PATTERN = "cybermancy-rulebook-assembly-manifest-v*.json"

_VERSION_RE = re.compile(
    r"-v(?P<version>\d+(?:\.\d+)*)(?:-r(?P<revision>\d+))?",
    re.IGNORECASE,
)


class GenerationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GenerationError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GenerationError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise GenerationError(f"Expected JSON object in {path}")
    return obj


def version_key(path: Path) -> tuple[tuple[int, ...], int]:
    m = _VERSION_RE.search(path.name)
    if not m:
        raise GenerationError(f"Could not parse version from filename: {path.name}")
    version = tuple(int(x) for x in m.group("version").split("."))
    revision = int(m.group("revision") or 0)
    return version, revision


def version_label(path: Path) -> str:
    m = _VERSION_RE.search(path.name)
    if not m:
        raise GenerationError(f"Could not parse version from filename: {path.name}")
    value = m.group("version")
    if m.group("revision"):
        value += f"-r{m.group('revision')}"
    return value


def discover_latest(directory: Path, pattern: str, label: str) -> Path:
    candidates: list[Path] = []
    for path in directory.glob(pattern):
        if not path.is_file():
            continue
        try:
            version_key(path)
        except GenerationError:
            continue
        candidates.append(path.resolve())

    if not candidates:
        raise GenerationError(
            f"No {label} found in {directory} matching {pattern}"
        )

    top_key = max(version_key(p) for p in candidates)
    top = [p for p in candidates if version_key(p) == top_key]

    if len(top) != 1:
        raise GenerationError(
            f"Ambiguous latest {label}: " + ", ".join(sorted(p.name for p in top))
        )
    return top[0]


def resolve_input(value: str | None, directory: Path, pattern: str, label: str) -> Path:
    if not value:
        return discover_latest(directory, pattern, label)
    p = Path(value).expanduser()
    if not p.is_absolute():
        candidate = directory / p
        p = candidate if candidate.exists() else p
    return p.resolve()


def require_dict(obj: dict[str, Any], key: str, where: str) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        raise GenerationError(f"Missing/invalid object {where}.{key}")
    return value


def require_list(obj: dict[str, Any], key: str, where: str) -> list[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        raise GenerationError(f"Missing/invalid array {where}.{key}")
    return value


def normalize_family_id(row: dict[str, Any]) -> str:
    for key in ("familyId", "generatorFamily"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise GenerationError(f"Structured-family record has no family ID: {row}")


def family_count(row: dict[str, Any]) -> int:
    for key in ("entityCount", "logicalEntityCount", "count"):
        if key in row:
            try:
                return int(row[key])
            except (TypeError, ValueError) as exc:
                raise GenerationError(
                    f"Invalid structured entity count {row.get(key)!r} in {row}"
                ) from exc
    raise GenerationError(f"Structured-family record has no entity count: {row}")


def assembly_source_commit(assembly: dict[str, Any]) -> str:
    authority = require_dict(assembly, "authority", "assembly")
    for key in ("sourceCommit", "repositoryCommit", "gitCommit"):
        value = authority.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise GenerationError("Assembly manifest authority has no source commit")


def publication_source_commit(publication: dict[str, Any]) -> str:
    repository = require_dict(publication, "repository", "publication")
    value = repository.get("gitCommit")
    if not isinstance(value, str) or not value.strip():
        raise GenerationError("Publication manifest repository.gitCommit is missing")
    return value.strip()


def publication_authored(publication: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = require_dict(publication, "publicationInputs", "publication")
    rows = require_list(inputs, "authoredDocuments", "publication.publicationInputs")
    return [r for r in rows if isinstance(r, dict)]


def publication_families(publication: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = require_dict(publication, "publicationInputs", "publication")
    rows = require_list(inputs, "structuredFamilies", "publication.publicationInputs")
    return [r for r in rows if isinstance(r, dict)]


def assembly_authored(assembly: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        r for r in require_list(assembly, "authoredInputs", "assembly")
        if isinstance(r, dict)
    ]


def assembly_families(assembly: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        r for r in require_list(assembly, "structuredFamilies", "assembly")
        if isinstance(r, dict)
    ]


def validate_pair(
    publication_path: Path,
    publication: dict[str, Any],
    assembly_path: Path,
    assembly: dict[str, Any],
) -> dict[str, Any]:
    pub_commit = publication_source_commit(publication)
    asm_commit = assembly_source_commit(assembly)

    if pub_commit != asm_commit:
        raise GenerationError(
            "Publication/assembly commit mismatch:\n"
            f"  publication: {pub_commit}\n"
            f"  assembly:    {asm_commit}"
        )

    authority = require_dict(assembly, "authority", "assembly")
    expected_parent = authority.get("parentPublicationManifest")
    if expected_parent and expected_parent != publication_path.name:
        raise GenerationError(
            "Latest assembly manifest does not target the selected publication manifest:\n"
            f"  assembly expects: {expected_parent}\n"
            f"  selected:         {publication_path.name}\n"
            "Regenerate Step 3 or explicitly select a compatible manifest pair."
        )

    pub_auth = publication_authored(publication)
    asm_auth = assembly_authored(assembly)
    pub_paths = {str(r.get("path", "")) for r in pub_auth}
    asm_paths = {str(r.get("path", "")) for r in asm_auth}
    if pub_paths != asm_paths:
        raise GenerationError(
            "Authored input path sets do not match between Step 2 and Step 3.\n"
            f"  publication-only: {sorted(pub_paths - asm_paths)}\n"
            f"  assembly-only:    {sorted(asm_paths - pub_paths)}"
        )

    pub_fams = {normalize_family_id(r): r for r in publication_families(publication)}
    asm_fams = {normalize_family_id(r): r for r in assembly_families(assembly)}
    if set(pub_fams) != set(asm_fams):
        raise GenerationError(
            "Structured family sets do not match between Step 2 and Step 3.\n"
            f"  publication-only: {sorted(set(pub_fams) - set(asm_fams))}\n"
            f"  assembly-only:    {sorted(set(asm_fams) - set(pub_fams))}"
        )

    count_mismatches = []
    for fid in sorted(pub_fams):
        pc = family_count(pub_fams[fid])
        ac = family_count(asm_fams[fid])
        if pc != ac:
            count_mismatches.append((fid, pc, ac))
    if count_mismatches:
        raise GenerationError(
            "Structured family counts disagree between Step 2 and Step 3: "
            + "; ".join(f"{fid}: publication={pc}, assembly={ac}"
                       for fid, pc, ac in count_mismatches)
        )

    total = sum(family_count(r) for r in pub_fams.values())

    digest_algorithms = {
        str(r.get("contentDigestAlgorithm") or "").strip()
        for r in pub_fams.values()
        if str(r.get("contentDigestAlgorithm") or "").strip()
    }
    if len(digest_algorithms) != 1:
        raise GenerationError(
            "Structured families must declare exactly one shared contentDigestAlgorithm; "
            f"found {sorted(digest_algorithms)}"
        )
    structured_digest_algorithm = next(iter(digest_algorithms))

    summary = publication.get("summary") or {}
    if isinstance(summary, dict):
        declared_auth = summary.get("authoredPublicationInputs")
        declared_fams = summary.get("structuredPublicationFamilies")
        declared_entities = summary.get("structuredPublicationEntities")
        if declared_auth is not None and int(declared_auth) != len(pub_auth):
            raise GenerationError(
                f"Publication summary authored count {declared_auth} "
                f"does not match {len(pub_auth)} authored inputs."
            )
        if declared_fams is not None and int(declared_fams) != len(pub_fams):
            raise GenerationError(
                f"Publication summary family count {declared_fams} "
                f"does not match {len(pub_fams)} structured families."
            )
        if declared_entities is not None and int(declared_entities) != total:
            raise GenerationError(
                f"Publication summary entity count {declared_entities} "
                f"does not match family total {total}."
            )

    return {
        "commit": pub_commit,
        "authoredCount": len(pub_auth),
        "familyCount": len(pub_fams),
        "entityCount": total,
        "publicationFamilies": pub_fams,
        "assemblyFamilies": asm_fams,
        "structuredDigestAlgorithm": structured_digest_algorithm,
    }


def segmentation_config(assembly: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "_authority": (
            "Step 3 assembly-manifest authoredInputs[].selector is normative. "
            "Entries below are generated from the selected assembly manifest."
        )
    }
    for row in assembly_authored(assembly):
        mode = str(row.get("assemblyMode") or "whole-document")
        if mode == "whole-document":
            continue
        path = str(row.get("path") or "")
        if not path:
            continue
        result[path] = {
            "strategy": "assembly-selector",
            "assemblyInputId": row.get("assemblyInputId"),
            "assemblyMode": mode,
            "selector": row.get("selector", {}),
        }
    return result


def audience_values(assembly: dict[str, Any]) -> list[str]:
    policy = assembly.get("audiencePolicy")
    if isinstance(policy, dict):
        audiences = policy.get("audiences")
        if isinstance(audiences, dict):
            values = [k for k in audiences if k != "developer"]
            if values:
                return values
    return ["shared", "player", "gm"]


def build_config(
    publication_path: Path,
    publication: dict[str, Any],
    assembly_path: Path,
    assembly: dict[str, Any],
    facts: dict[str, Any],
    output_version: str,
) -> dict[str, Any]:
    gm_divider = assembly.get("gmDivider") or {}
    if not isinstance(gm_divider, dict):
        gm_divider = {}
    divider_title = gm_divider.get(
        "title", "GM MATERIAL — SPOILERS BEYOND THIS POINT"
    )

    families: dict[str, Any] = {}
    for row in assembly_families(assembly):
        fid = normalize_family_id(row)
        families[fid] = {"expected": family_count(row)}

    return {
        "configVersion": output_version,
        "generatedBy": {
            "script": "build/rulebook/scripts/build-rulebook-normalization-artifacts.py",
            "scriptVersion": SCRIPT_VERSION,
        },
        "baseline": {
            "commit": facts["commit"],
            "expectedAuthoredInputs": facts["authoredCount"],
            "expectedStructuredFamilies": facts["familyCount"],
            "expectedLogicalEntities": facts["entityCount"],
        },
        "authority": {
            "publicationManifest": publication_path.name,
            "assemblyManifest": assembly_path.name,
            "publicationManifestVersion": publication.get("manifestVersion"),
            "assemblyManifestVersion": assembly.get("version"),
            "generatedMkDocsAreCanonical": False,
        },
        "manifestAdapter": {
            "mode": "strict",
            "notes": (
                "Do not duplicate Step 2/3 authority decisions here. "
                "These pointers bind the current canonical manifest schemas."
            ),
            "publication": {
                "baselineCommitPointer": "/repository/gitCommit",
                "authoredIncludeRecordsPointer": "/publicationInputs/authoredDocuments",
                "structuredFamilyRecordsPointer": "/publicationInputs/structuredFamilies",
            },
            "assembly": {
                "sectionsPointer": "/bookStructure",
                "profilesPointer": "/buildProfiles",
            },
        },
        "segmentation": segmentation_config(assembly),
        "families": families,
        "structured": {
            "familyDigestAlgorithm": facts["structuredDigestAlgorithm"],
            "stableIdPreference": ["_id", "_key"],
            "folderKeyMarker": "!folders!",
            "strictUnhandledFields": True,
            "fastPlayCandidatePaths": [
                "flags.cybermancy.fastPlay",
                "fastPlay",
            ],
        },
        "semantics": {
            "sectionPrefix": "section:",
            "familyPrefix": "family:",
            "entityPrefix": "entity:",
            "audiences": audience_values(assembly),
            "gmDivider": divider_title,
        },
        "assets": {
            "stagingRoot": "build/rulebook/source/assets",
            "assembledReferenceBase": "build/rulebook/source/assembled",
            "selfContainedPublicationCorpus": True,
            "runtimeAssetPolicy": "metadata-only-unless-rendered",
            "ambiguousBasenameFallback": False,
            "foundryRuntimeMappings": [
                {"prefix": "modules/cybermancy/", "repoPrefix": ""},
                {"prefix": "worlds/cybermancer/", "repoPrefix": ""},
            ],
        },
        "validation": {
            "unresolvedJinja": "error",
            "unresolvedCrossReference": "error",
            "audienceLeak": "error",
            "missingStableId": "error",
            "missingAsset": "error",
            "duplicateSemanticId": "error",
            "orderingAuthorityMissing": "error",
            "determinism": "error",
            "bodyYamlDelimiterAmbiguity": "error",
            "assembledAssetResolution": "error",
            "assetTreeDeterminism": "error",
        },
    }


def selector_text(selector: Any) -> str:
    if not selector:
        return "_No selector object supplied._"
    if isinstance(selector, str):
        return selector
    return "```json\n" + json.dumps(selector, indent=2, ensure_ascii=False) + "\n```"


def build_standard(
    publication_path: Path,
    publication: dict[str, Any],
    assembly_path: Path,
    assembly: dict[str, Any],
    facts: dict[str, Any],
    output_version: str,
) -> str:
    gm_divider = assembly.get("gmDivider") or {}
    if not isinstance(gm_divider, dict):
        gm_divider = {}
    divider_title = gm_divider.get(
        "title", "GM MATERIAL — SPOILERS BEYOND THIS POINT"
    )

    family_rows = []
    for row in assembly_families(assembly):
        fid = normalize_family_id(row)
        source_path = row.get("sourcePath") or facts["publicationFamilies"][fid].get("sourcePath") or "—"
        audience = row.get("audience") or facts["publicationFamilies"][fid].get("audience") or "—"
        sort = row.get("sort") or []
        sort_text = ", ".join(str(x) for x in sort) if isinstance(sort, list) else str(sort)
        family_rows.append(
            f"| `{fid}` | `{source_path}` | {family_count(row)} | {audience} | {sort_text or '—'} |"
        )

    segmented = []
    for row in assembly_authored(assembly):
        mode = str(row.get("assemblyMode") or "whole-document")
        if mode == "whole-document":
            continue
        segmented.append(
            "\n".join(
                [
                    f"### `{row.get('path')}`",
                    "",
                    f"- Assembly input: `{row.get('assemblyInputId')}`",
                    f"- Mode: `{mode}`",
                    "- Selector:",
                    "",
                    selector_text(row.get("selector")),
                ]
            )
        )
    segmentation_section = "\n\n".join(segmented) if segmented else "_No segmented authored inputs._"

    front_matter_lines = []
    for part in assembly.get("bookStructure") or []:
        if not isinstance(part, dict):
            continue
        refs = part.get("openerRefs")
        if isinstance(refs, list) and refs:
            front_matter_lines.append(
                f"- `{part.get('id')}` opener refs: " + ", ".join(f"`{x}`" for x in refs)
            )
    after_refs = gm_divider.get("afterDividerFrontMatterRefs")
    if isinstance(after_refs, list) and after_refs:
        front_matter_lines.append(
            "- GM after-divider front matter refs: " + ", ".join(f"`{x}`" for x in after_refs)
        )
    front_matter_text = "\n".join(front_matter_lines) if front_matter_lines else "- No special opener/front-matter refs declared."

    profiles = assembly.get("buildProfiles") or []
    profile_lines = []
    for p in profiles:
        if not isinstance(p, dict):
            continue
        profile_lines.append(
            f"- `{p.get('id')}` — audiences: "
            + ", ".join(str(x) for x in (p.get("includeAudiences") or []))
        )
    profiles_text = "\n".join(profile_lines) if profile_lines else "- No build profiles declared."

    return f"""# Cybermancy Rulebook Normalization Standard v{output_version}

**Status:** NORMATIVE STEP 4 SPECIFICATION  
**Scope:** Representation transformation from frozen canonical Cybermancy rulebook sources into Pandoc-ready intermediate Markdown.  
**Frozen repository baseline:** `{facts["commit"]}`  
**Generated by:** `build-rulebook-normalization-artifacts.py` v{SCRIPT_VERSION}

## 1. Authority

The Normalization Layer consumes, but does not replace, these upstream authorities:

1. `{publication_path.name}` — Step 2 source authority and publication scope.
2. `{assembly_path.name}` — Step 3 book topology, ordering, audience, placement, selectors, profiles, and structured-family placement.
3. Canonical repository content at commit `{facts["commit"]}`.

Generated MkDocs detail pages are derivative and are not canonical rulebook inputs. Structured publication content is consumed directly from the `src/packs/...` sources named by the publication manifest.

The selected publication and assembly manifests must resolve to the same repository commit and must join exactly by authored path and structured family ID before normalization may proceed.

## 2. Frozen input summary

| Input class | Count |
|---|---:|
| Authored canonical inputs | {facts["authoredCount"]} |
| Structured canonical families | {facts["familyCount"]} |
| Structured logical entities | {facts["entityCount"]} |

The publication manifest remains authoritative if these values change in a later approved snapshot.

Structured-family digest algorithm:

```text
{facts["structuredDigestAlgorithm"]}
```

All included structured families must use this same declared algorithm.

## 3. Pipeline

```text
Step 2 publication manifest
        +
Step 3 assembly manifest
        +
frozen authored Markdown
        +
frozen src/packs structured data
        ↓
manifest/source validation
        ↓
authored segmentation
        ↓
Markdown normalization + structured materialization
        ↓
semantic-reference resolution
        ↓
publication-asset staging
        ↓
profile assembly
        ↓
validation + determinism check
        ↓
build/rulebook/source/
```

No source may be selected merely because it appears in MkDocs navigation, an on-disk directory, or a generated documentation page.

## 4. Output model

```text
build/rulebook/
├── assets/
│   └── repo/
└── source/
    ├── authored/
    ├── generated/
    │   └── <family>/
    ├── assembled/
    │   ├── complete-rulebook.md
    │   └── player-guide.md
    ├── assets/
    │   ├── icons/
    │   ├── images/
    │   └── repository/        # fallback for reader-visible assets outside repo assets/ trees
    └── metadata/
        ├── provenance.json
        ├── semantic-targets.json
        ├── references.json
        ├── assets.json
        ├── runtime-assets.json
        ├── source-hashes.json
        └── validation.json
```

The normalized output is disposable and deterministic. It must never become a manually maintained canonical manuscript.

## 5. Source identity and semantic IDs

Every included source must retain provenance sufficient to identify:

- repository path;
- frozen commit;
- source SHA-256 or structured-family digest;
- source kind and audience;
- assembly owner/placement;
- transformation rule;
- normalized output path and output SHA-256.

Canonical semantic keys are:

```text
section:<section-or-chapter-id>
family:<family-id>
entity:<family-id>:<stable-source-id>
```

Structured identity preference is:

1. top-level `_id`;
2. deterministic Foundry document ID extracted from `_key`;
3. otherwise fail with `STRUCTURED_ID_MISSING`.

Display names and generated slugs must not silently replace stable source identity.

## 6. Authored Markdown normalization

For each authored input:

1. Confirm Step 2 INCLUDE authority.
2. Confirm exact Step 3 placement.
3. Apply any Step 3 selector before generic normalization.
4. Resolve only retained, assembly-owned transclusions.
5. Normalize supported MkDocs constructs.
6. Normalize heading hierarchy under assembly-owned section headings.
7. Resolve semantic references and publication assets.
8. Emit normalized Markdown and provenance.

Normalization may repair representation and rendering artifacts but may not editorially rewrite substantive rule text.

### 6.1 Current segmented authored inputs

{segmentation_section}

The assembly manifest is normative. This section is generated for visibility and must not override a later selector.

### 6.2 MkDocs-specific constructs

Recognized normalization includes:

- `include-markdown` when retained and assembly-owned;
- MkDocs admonitions to Pandoc fenced Divs;
- compatible attribute lists;
- Markdown-wrapper HTML removal while preserving content;
- lossless semantic-table conversion;
- repository-relative link and image resolution;
- recognized generated collection references to semantic family targets.

Unresolved Jinja, macros, opaque structural HTML, or non-deterministic transformations are validation errors unless explicitly whitelisted.

## 7. Structured family generation

| Family | Canonical source | Entities | Audience | Sort |
|---|---|---:|---|---|
{chr(10).join(family_rows)}
| **Total** |  | **{facts["entityCount"]}** |  |  |

Foundry folder/organizational records are hierarchy metadata, not logical publication entities. They do not receive entity semantic IDs and do not count toward the logical entity total.

Family rendering must preserve applicable mechanics rather than dump arbitrary JSON. A populated canonical field not consumed by a renderer must be explicitly classified as implementation metadata or reported as `UNHANDLED_STRUCTURED_FIELD`.

## 8. Fast Play

Fast Play remains GM-only structured data. When present under `flags.cybermancy.fastPlay` (or another explicitly supported canonical path), it is rendered as a separate semantic Fast Play block rather than flattened into Description or ordinary Features.

Non-rendered feature references remain available in metadata for consistency validation.

## 9. Audience and profile rules

Audiences are `shared`, `player`, and `gm`; developer material is never reader-facing.

Player/shared content MUST NOT reference GM-only semantic targets. GM content MAY reference player/shared content.

Declared build profiles:

{profiles_text}

The complete rulebook must contain the exact divider:

```text
{divider_title}
```

before GM-only material.

Special opener/front-matter routing declared by Step 3:

{front_matter_text}

## 10. Assets

Step 4 distinguishes publication assets from Foundry/runtime references.

- Assets actually emitted into normalized Markdown must resolve and be staged under `build/rulebook/source/assets/`.
- Local image targets are rewritten deterministically to publication-relative paths that resolve from `source/assembled/*.md` without consulting upstream source trees.
- Structured entity art deliberately selected for publication must resolve and be staged.
- Foundry runtime/action/token/embedded-feature image references that are not rendered in the book may be retained in metadata without becoming publication blockers.
- Remote HTTP(S)/data assets remain external; any non-remote image emitted into an assembled profile is a local publication dependency and must resolve inside `build/rulebook/source/`.
- Every staged publication asset must retain source-path and SHA-256 provenance.
- Basename-only fallback is prohibited when ambiguous; conflicting sources mapping to the same publication path are errors.

Unresolved publication-visible assets are errors. The Step 4 publication corpus must be self-contained for Step 5.

## 10.1 Pandoc-safe thematic breaks

Assembled profiles begin with one YAML metadata block delimited by standalone `---` lines. After that opening block, standalone body `---` thematic breaks are normalized to `***` so Pandoc cannot misinterpret them as a second YAML metadata block. Canonical authored prose is not edited; this is a deterministic publication-normalization transform.

## 11. Cross-references

Semantic references must resolve inside the selected build profile. Page numbers are render-time products and are never source-of-truth cross-references.

References to Daggerheart material remain external semantic dependencies unless Cybermancy explicitly contains the rule text as an included source.

## 12. Validation requirements

A successful Step 4 build must validate at minimum:

- publication and assembly manifests present and compatible;
- frozen commit alignment;
- authored paths join exactly;
- structured family IDs and counts join exactly;
- all authored primary placements are unique;
- all structured family placements are unique;
- source hashes/digests reconcile to the frozen snapshot;
- logical entity counts reconcile to {facts["entityCount"]};
- semantic IDs are unique;
- cross-references resolve within audience/profile constraints;
- Fast Play remains separately identifiable and GM-only;
- publication-visible assets resolve inside `build/rulebook/source/` and retain source provenance;
- each assembled profile contains no Pandoc-ambiguous body `---` YAML delimiters;
- the staged publication asset tree is deterministic across clean materializations;
- complete and player profiles are generated from the same normalized corpus;
- the GM divider contract is satisfied;
- a second clean build is byte-for-byte deterministic.

## 13. Reproducibility

The Step 4 configuration is generated from the selected Step 2/Step 3 manifests by:

```text
build/rulebook/scripts/build-rulebook-normalization-artifacts.py
```

The source normalizer then consumes the latest compatible generated configuration via:

```text
build/rulebook/scripts/build-rulebook-source.py
```

Changing canonical repository content requires a new frozen Step 2 manifest and corresponding Step 3 assembly manifest before Step 4 artifacts are regenerated. The normalization generator must not silently bless a dirty working tree or rewrite upstream authority.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the Step 4 normalization config and normalization standard "
            "from the latest compatible Step 2 and Step 3 manifests."
        )
    )
    parser.add_argument(
        "--manifest-dir",
        default=str(MANIFEST_DIR),
        help="Manifest directory (default: build/rulebook/manifests beside this script).",
    )
    parser.add_argument(
        "--publication-manifest",
        help="Optional publication manifest filename/path; latest version is auto-selected.",
    )
    parser.add_argument(
        "--assembly-manifest",
        help="Optional assembly manifest filename/path; latest version is auto-selected.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print planned outputs without writing files.",
    )
    args = parser.parse_args(argv)

    manifest_dir = Path(args.manifest_dir).expanduser().resolve()
    if not manifest_dir.is_dir():
        raise GenerationError(f"Manifest directory does not exist: {manifest_dir}")

    pub_path = resolve_input(
        args.publication_manifest, manifest_dir, PUBLICATION_PATTERN, "publication manifest"
    )
    asm_path = resolve_input(
        args.assembly_manifest, manifest_dir, ASSEMBLY_PATTERN, "assembly manifest"
    )

    publication = load_json(pub_path)
    assembly = load_json(asm_path)
    facts = validate_pair(pub_path, publication, asm_path, assembly)

    output_version = version_label(asm_path)
    config_name = f"cybermancy-rulebook-normalization-config-v{output_version}.json"
    standard_name = f"cybermancy-rulebook-normalization-standard-v{output_version}.md"
    config_path = manifest_dir / config_name
    standard_path = manifest_dir / standard_name

    config = build_config(
        pub_path, publication, asm_path, assembly, facts, output_version
    )
    standard = build_standard(
        pub_path, publication, asm_path, assembly, facts, output_version
    )

    summary = {
        "status": "PASS",
        "generatorVersion": SCRIPT_VERSION,
        "selectedInputs": {
            "publicationManifest": pub_path.name,
            "assemblyManifest": asm_path.name,
            "repositoryCommit": facts["commit"],
        },
        "baseline": {
            "authoredInputs": facts["authoredCount"],
            "structuredFamilies": facts["familyCount"],
            "logicalEntities": facts["entityCount"],
        },
        "outputs": {
            "normalizationConfig": str(config_path),
            "normalizationStandard": str(standard_path),
        },
        "dryRun": bool(args.dry_run),
    }

    if not args.dry_run:
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        standard_path.write_text(standard, encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GenerationError as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
