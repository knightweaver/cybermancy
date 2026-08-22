#!/usr/bin/env python3
"""
Build the normative Cybermancy Rulebook Step 3 assembly/book manifest.

This script consumes the frozen Rulebook Step 2 publication manifest and
deterministically applies the approved Step 3 Book Information Architecture.

Expected repository layout:

cybermancy/
└─ build/
   └─ rulebook/
      ├─ scripts/
      │  └─ build-rulebook-assembly-manifest.py
      └─ manifests/
         ├─ cybermancy-rulebook-publication-manifest-vX.Y.json
         ├─ cybermancy-rulebook-assembly-manifest-vX.Y.json
         └─ cybermancy-rulebook-assembly-manifest-vX.Y.md

Important behavior:
- Uses only INCLUDE publication inputs from the frozen Step 2 manifest.
- Reads structured-family counts, digests, paths, and generated-output metadata
  from Step 2 rather than hard-coding repository inventory data.
- Applies the approved Step 3 topology/order/audience mapping.
- Fails closed if the included authored-source set or structured-family set
  changes in a way not represented by the approved Step 3 architecture.
- Writes both normative JSON and a human-readable Markdown companion.
- Does NOT perform Markdown/HTML/Jinja normalization.

Standard-library only; no third-party packages required.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SCRIPT_NAME = "build-rulebook-assembly-manifest.py"
ASSEMBLY_SCHEMA_PREFIX = "cybermancy-rulebook-assembly-manifest-v"
PUBLICATION_SCHEMA_PREFIX = "cybermancy-rulebook-publication-manifest-v"


# ---------------------------------------------------------------------------
# Approved Step 3 information architecture
# ---------------------------------------------------------------------------

# Authored sources are mapped by exact repository path. If Step 2 changes the
# included set, this script deliberately fails until this mapping is reviewed.
AUTHORED_ARCHITECTURE: dict[str, dict[str, Any]] = {
    "docs/player-facing/index.md": {
        "assemblyInputId": "auth.welcome",
        "placement": "ch01-welcome",
        "title": "Cybermancy Player Introduction",
        "assemblyMode": "segment",
        "selector": {
            "include": "content before heading 'The Event: The Resonance Cascade'",
            "exclude": (
                "the duplicated Resonance Cascade section; canonical Resonance "
                "text is assembled from docs/_shared/world/the-resonance.md"
            ),
        },
    },
    "docs/_shared/world/the-resonance.md": {
        "assemblyInputId": "auth.resonance",
        "placement": "ch02-resonance",
        "title": "The Event: The Resonance Cascade",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/world/corps.md": {
        "assemblyInputId": "auth.corps",
        "placement": "ch03-megacorporations",
        "title": "Megacorporations",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/rules/index.md": {
        "assemblyInputId": "auth.frame-rules",
        "placement": "ch04-frame-rules",
        "title": "Cybermancy Frame Rules",
        "assemblyMode": "segment",
        "selector": {
            "include": [
                "document lead",
                "heading 'Critical Fails' and its descendant headings",
            ],
            "exclude": (
                "linked summary sections whose complete rules are assembled "
                "from their dedicated authored files"
            ),
        },
    },
    "docs/player-facing/rules/item-loadout.md": {
        "assemblyInputId": "auth.loadouts",
        "placement": "ch05-item-loadouts",
        "title": "Item Loadouts",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/rules/flashbacks.md": {
        "assemblyInputId": "auth.flashbacks",
        "placement": "ch06-flashbacks",
        "title": "Flashbacks",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/rules/bennies.md": {
        "assemblyInputId": "auth.bennies",
        "placement": "ch07-bennies",
        "title": "Bennies",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/rules/driving-and-chases.md": {
        "assemblyInputId": "auth.driving",
        "placement": "ch08-driving-chases",
        "title": "Driving and Chases",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/rules/netrunner-hacking.md": {
        "assemblyInputId": "auth.netrunning",
        "placement": "ch09-netrunning",
        "title": "Netrunning and Device Intrusion",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/world/ancestories.md": {
        "assemblyInputId": "auth.ancestories",
        "placement": "ch10-ancestories",
        "title": "Ancestories",
        "assemblyMode": "whole-document",
    },
    "docs/player-facing/world/communities.md": {
        "assemblyInputId": "auth.communities",
        "placement": "ch11-communities",
        "title": "Communities",
        "assemblyMode": "whole-document",
    },
    "docs/gm-facing/index.md": {
        "assemblyInputId": "auth.gm-guide-index",
        "placement": "gm-front-matter",
        "title": "Cybermancy — GM Guide",
        "assemblyMode": "whole-document",
        "assemblyNote": (
            "Consume as the GM-section opener/front-matter source after the "
            "spoiler divider. Editorial cleanup of navigation/development "
            "phrasing is deferred to Step 4 normalization."
        ),
    },
    "docs/gm-facing/world/project-helios-remnants.md": {
        "assemblyInputId": "auth.project-helios",
        "placement": "ch24-project-helios",
        "title": "Project Helios and the Hidden History",
        "assemblyMode": "whole-document",
    },
    "docs/gm-facing/world/the-council.md": {
        "assemblyInputId": "auth.council",
        "placement": "ch25-council",
        "title": "The Council",
        "assemblyMode": "whole-document",
    },
    "docs/gm-facing/world/the-cabal.md": {
        "assemblyInputId": "auth.cabal",
        "placement": "ch26-cabal",
        "title": "The Cabal",
        "assemblyMode": "whole-document",
    },
    "docs/gm-facing/world/the-cabal-projects.md": {
        "assemblyInputId": "auth.cabal-projects",
        "placement": "ch27-cabal-projects",
        "title": "Cabal Projects",
        "assemblyMode": "whole-document",
    },
    "docs/gm-facing/world/the-chessboard.md": {
        "assemblyInputId": "auth.chessboard",
        "placement": "ch28-chessboard",
        "title": "The Chessboard",
        "assemblyMode": "whole-document",
    },
    "docs/gm-facing/world/timeline.md": {
        "assemblyInputId": "auth.gm-resonance",
        "placement": "ch29-gm-resonance",
        "title": "The Resonance: GM Interpretation",
        "assemblyMode": "segment",
        "selector": {
            "include": [
                "heading 'Philosophical Interpretation'",
                "heading 'Tone and Themes'",
            ],
            "exclude": (
                "the include-markdown transclusion of "
                "docs/_shared/world/the-resonance.md, which is assembled once "
                "in ch02-resonance"
            ),
        },
    },
}


# Structured families are mapped by generatorFamily.
# Source paths, entity counts, digests, etc. are read from Step 2.
STRUCTURED_ARCHITECTURE: dict[str, dict[str, Any]] = {
    "adversaries": {
        "placement": "ch30-adversaries",
        "title": "Adversaries",
        "sort": ["tier", "classification", "name"],
    },
    "adversaries-features": {
        "placement": "ch32-adversary-features",
        "title": "Adversary Feature Reference",
        "sort": ["source-folder", "name"],
    },
    "ammo": {
        "placement": "ch17-ammunition",
        "title": "Ammunition",
        "sort": ["tier", "name"],
    },
    "armors": {
        "placement": "ch18-armor",
        "title": "Armor",
        "sort": ["tier", "name"],
    },
    "classes": {
        "placement": "ch12-classes",
        "title": "Classes",
        "sort": ["name"],
    },
    "consumables": {
        "placement": "ch21-consumables",
        "title": "Consumables",
        "sort": ["tier", "name"],
    },
    "cybernetics": {
        "placement": "ch19-cybernetics",
        "title": "Cybernetics",
        "sort": ["tier", "name"],
    },
    "domains": {
        "placement": "ch14-domains",
        "title": "Domains and Domain Cards",
        "sort": ["source-folder", "level-or-tier", "name"],
    },
    "drones-devices": {
        "placement": "ch20-drones-devices",
        "title": "Drones and Devices",
        "sort": ["tier", "name"],
    },
    "environments": {
        "placement": "ch31-environments",
        "title": "Environments",
        "sort": ["tier", "classification", "name"],
    },
    "features": {
        "placement": "ch15-feature-reference",
        "title": "Feature Reference",
        "sort": ["source-folder", "name"],
    },
    "loot": {
        "placement": "ch23-loot",
        "title": "Loot",
        "sort": ["tier", "name"],
    },
    "mods": {
        "placement": "ch22-mods",
        "title": "Mods",
        "sort": ["tier", "name"],
    },
    "subclasses": {
        "placement": "ch13-subclasses",
        "title": "Subclasses",
        "sort": ["parent-class-or-source-folder", "name"],
    },
    "weapons": {
        "placement": "ch16-weapons",
        "title": "Weapons",
        "sort": ["tier", "trait", "name"],
    },
}


BOOK_STRUCTURE: list[dict[str, Any]] = [
    {
        "id": "part-i-world",
        "order": 100,
        "title": "The World of Cybermancy",
        "audience": "player",
        "chapters": [
            {
                "id": "ch01-welcome",
                "number": 1,
                "title": "Welcome to Cybermancy",
                "contentRefs": ["auth.welcome"],
            },
            {
                "id": "ch02-resonance",
                "number": 2,
                "title": "The Resonance Cascade",
                "contentRefs": ["auth.resonance"],
            },
            {
                "id": "ch03-megacorporations",
                "number": 3,
                "title": "Megacorporations",
                "contentRefs": ["auth.corps"],
            },
        ],
    },
    {
        "id": "part-ii-rules",
        "order": 200,
        "title": "Cybermancy Rules",
        "audience": "player",
        "chapters": [
            {
                "id": "ch04-frame-rules",
                "number": 4,
                "title": "Cybermancy Frame Rules",
                "contentRefs": ["auth.frame-rules"],
            },
            {
                "id": "ch05-item-loadouts",
                "number": 5,
                "title": "Item Loadouts",
                "contentRefs": ["auth.loadouts"],
            },
            {
                "id": "ch06-flashbacks",
                "number": 6,
                "title": "Flashbacks",
                "contentRefs": ["auth.flashbacks"],
            },
            {
                "id": "ch07-bennies",
                "number": 7,
                "title": "Bennies",
                "contentRefs": ["auth.bennies"],
            },
            {
                "id": "ch08-driving-chases",
                "number": 8,
                "title": "Driving and Chases",
                "contentRefs": ["auth.driving"],
            },
            {
                "id": "ch09-netrunning",
                "number": 9,
                "title": "Netrunning and Device Intrusion",
                "contentRefs": ["auth.netrunning"],
            },
        ],
    },
    {
        "id": "part-iii-characters",
        "order": 300,
        "title": "Characters and Character Options",
        "audience": "player",
        "chapters": [
            {
                "id": "ch10-ancestories",
                "number": 10,
                "title": "Ancestories",
                "contentRefs": ["auth.ancestories"],
            },
            {
                "id": "ch11-communities",
                "number": 11,
                "title": "Communities",
                "contentRefs": ["auth.communities"],
            },
            {
                "id": "ch12-classes",
                "number": 12,
                "title": "Classes",
                "contentRefs": ["family:classes"],
            },
            {
                "id": "ch13-subclasses",
                "number": 13,
                "title": "Subclasses",
                "contentRefs": ["family:subclasses"],
            },
            {
                "id": "ch14-domains",
                "number": 14,
                "title": "Domains and Domain Cards",
                "contentRefs": ["family:domains"],
            },
            {
                "id": "ch15-feature-reference",
                "number": 15,
                "title": "Feature Reference",
                "contentRefs": ["family:features"],
            },
        ],
    },
    {
        "id": "part-iv-equipment",
        "order": 400,
        "title": "Equipment and Technology",
        "audience": "player",
        "chapters": [
            {
                "id": "ch16-weapons",
                "number": 16,
                "title": "Weapons",
                "contentRefs": ["family:weapons"],
            },
            {
                "id": "ch17-ammunition",
                "number": 17,
                "title": "Ammunition",
                "contentRefs": ["family:ammo"],
            },
            {
                "id": "ch18-armor",
                "number": 18,
                "title": "Armor",
                "contentRefs": ["family:armors"],
            },
            {
                "id": "ch19-cybernetics",
                "number": 19,
                "title": "Cybernetics",
                "contentRefs": ["family:cybernetics"],
            },
            {
                "id": "ch20-drones-devices",
                "number": 20,
                "title": "Drones and Devices",
                "contentRefs": ["family:drones-devices"],
            },
            {
                "id": "ch21-consumables",
                "number": 21,
                "title": "Consumables",
                "contentRefs": ["family:consumables"],
            },
            {
                "id": "ch22-mods",
                "number": 22,
                "title": "Mods",
                "contentRefs": ["family:mods"],
            },
            {
                "id": "ch23-loot",
                "number": 23,
                "title": "Loot",
                "contentRefs": ["family:loot"],
            },
        ],
    },
    {
        "id": "part-v-gm-world",
        "order": 500,
        "title": "GM World Guide",
        "audience": "gm",
        "requiresGmDivider": True,
        "openerRefs": ["auth.gm-guide-index"],
        "openerPlacement": "after GM spoiler divider; before Chapter 24",
        "chapters": [
            {
                "id": "ch24-project-helios",
                "number": 24,
                "title": "Project Helios and the Hidden History",
                "contentRefs": ["auth.project-helios"],
            },
            {
                "id": "ch25-council",
                "number": 25,
                "title": "The Council",
                "contentRefs": ["auth.council"],
            },
            {
                "id": "ch26-cabal",
                "number": 26,
                "title": "The Cabal",
                "contentRefs": ["auth.cabal"],
            },
            {
                "id": "ch27-cabal-projects",
                "number": 27,
                "title": "Cabal Projects",
                "contentRefs": ["auth.cabal-projects"],
            },
            {
                "id": "ch28-chessboard",
                "number": 28,
                "title": "The Chessboard",
                "contentRefs": ["auth.chessboard"],
            },
            {
                "id": "ch29-gm-resonance",
                "number": 29,
                "title": "The Resonance: GM Interpretation",
                "contentRefs": ["auth.gm-resonance"],
            },
        ],
    },
    {
        "id": "part-vi-gm-toolkit",
        "order": 600,
        "title": "GM Encounter Toolkit",
        "audience": "gm",
        "chapters": [
            {
                "id": "ch30-adversaries",
                "number": 30,
                "title": "Adversaries",
                "contentRefs": ["family:adversaries"],
            },
            {
                "id": "ch31-environments",
                "number": 31,
                "title": "Environments",
                "contentRefs": ["family:environments"],
            },
            {
                "id": "ch32-adversary-features",
                "number": 32,
                "title": "Adversary Feature Reference",
                "contentRefs": ["family:adversaries-features"],
            },
        ],
    },
]


PLACEMENT_ORDER = {
    "ch01-welcome": 10,
    "ch02-resonance": 20,
    "ch03-megacorporations": 30,
    "ch04-frame-rules": 40,
    "ch05-item-loadouts": 50,
    "ch06-flashbacks": 60,
    "ch07-bennies": 70,
    "ch08-driving-chases": 80,
    "ch09-netrunning": 90,
    "ch10-ancestories": 100,
    "ch11-communities": 110,
    "gm-front-matter": 235,
    "ch24-project-helios": 240,
    "ch25-council": 250,
    "ch26-cabal": 260,
    "ch27-cabal-projects": 270,
    "ch28-chessboard": 280,
    "ch29-gm-resonance": 290,
}


DEFERRED_EXCLUSIONS = {
    "A024": (
        "Intentionally outside this rulebook snapshot."
    ),
    "A020": (
        "Excluded by the corrected Step 2 authority decision; no assembly placement."
    ),
    "A007": (
        "Campaign/adventure-specific actor aggregation is outside reusable "
        "System rulebook authority."
    ),
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

class ManifestError(RuntimeError):
    """Raised when the Step 2 manifest cannot be safely mapped to Step 3."""


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int

    @classmethod
    def parse(cls, text: str) -> "Version":
        match = re.fullmatch(r"(\d+)\.(\d+)", text.strip())
        if not match:
            raise ManifestError(f"Unsupported manifest version format: {text!r}")
        return cls(int(match.group(1)), int(match.group(2)))

    def short(self) -> str:
        return f"{self.major}.{self.minor}"

    def semver(self) -> str:
        return f"{self.major}.{self.minor}.0"


def repo_root_from_script() -> Path:
    """
    With the script at build/rulebook/scripts/<script>.py:
      parents[0] = scripts
      parents[1] = rulebook
      parents[2] = build
      parents[3] = repository root
    """
    path = Path(__file__).resolve()
    try:
        return path.parents[3]
    except IndexError as exc:
        raise ManifestError(
            f"Cannot derive repository root from script location: {path}"
        ) from exc


def resolve_path(value: str | None, repo_root: Path) -> Path | None:
    if value is None:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = repo_root / p
    return p.resolve()


def latest_publication_manifest(manifests_dir: Path) -> Path:
    candidates: list[tuple[Version, Path]] = []
    pattern = re.compile(
        r"^cybermancy-rulebook-publication-manifest-v(\d+\.\d+)\.json$"
    )
    for path in manifests_dir.glob("cybermancy-rulebook-publication-manifest-v*.json"):
        match = pattern.match(path.name)
        if not match:
            continue
        candidates.append((Version.parse(match.group(1)), path))

    if not candidates:
        raise ManifestError(
            "No publication manifest found in "
            f"{manifests_dir}. Expected a filename like "
            "cybermancy-rulebook-publication-manifest-v1.1.json"
        )

    candidates.sort()
    return candidates[-1][1]


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
    except FileNotFoundError as exc:
        raise ManifestError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ManifestError(f"Expected a JSON object at top level: {path}")
    return value


def require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ManifestError(f"Missing required field {key!r} in {context}")
    return mapping[key]


def format_set_delta(expected: set[str], actual: set[str], label: str) -> str:
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    chunks = [f"{label} no longer matches the approved Step 3 architecture."]
    if missing:
        chunks.append("Missing from Step 2 INCLUDE set:\n  - " + "\n  - ".join(missing))
    if extra:
        chunks.append("New/unmapped Step 2 INCLUDE sources:\n  - " + "\n  - ".join(extra))
    chunks.append(
        "Review the information architecture and update the Step 3 mapping "
        "rather than allowing automatic placement."
    )
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Validation and transformation
# ---------------------------------------------------------------------------

def validate_parent_manifest(pub: dict[str, Any]) -> Version:
    schema = require(pub, "schema", "publication manifest")
    if not str(schema).startswith(PUBLICATION_SCHEMA_PREFIX):
        raise ManifestError(
            "Input is not a Cybermancy Rulebook publication manifest: "
            f"{schema!r}"
        )

    if require(pub, "status", "publication manifest") != "FROZEN":
        raise ManifestError(
            "Step 3 requires a FROZEN Step 2 publication manifest."
        )

    version = Version.parse(str(require(pub, "manifestVersion", "publication manifest")))

    summary = require(pub, "summary", "publication manifest")
    inputs = require(pub, "publicationInputs", "publication manifest")
    authored = require(inputs, "authoredDocuments", "publicationInputs")
    families = require(inputs, "structuredFamilies", "publicationInputs")

    if len(authored) != int(require(summary, "authoredPublicationInputs", "summary")):
        raise ManifestError(
            "authoredDocuments count does not match summary.authoredPublicationInputs"
        )
    if len(families) != int(require(summary, "structuredPublicationFamilies", "summary")):
        raise ManifestError(
            "structuredFamilies count does not match summary.structuredPublicationFamilies"
        )

    total_entities = sum(int(require(x, "entityCount", "structured family")) for x in families)
    if total_entities != int(require(summary, "structuredPublicationEntities", "summary")):
        raise ManifestError(
            "Structured entity total does not match summary.structuredPublicationEntities"
        )

    if len(authored) + len(families) != int(require(summary, "includeRows", "summary")):
        raise ManifestError(
            "Authored + structured publication inputs do not match summary.includeRows"
        )

    for record in authored:
        if record.get("authority") != "CANONICAL-CANDIDATE":
            raise ManifestError(
                f"Included authored source is not CANONICAL-CANDIDATE: {record.get('path')}"
            )
        if record.get("disposition") != "INCLUDE":
            raise ManifestError(
                f"publicationInputs authored source is not INCLUDE: {record.get('path')}"
            )
        if record.get("decisionStatus") != "DECIDED":
            raise ManifestError(
                f"publicationInputs authored source is not DECIDED: {record.get('path')}"
            )

    for record in families:
        if record.get("authority") != "CANONICAL-CANDIDATE":
            raise ManifestError(
                f"Included structured family is not CANONICAL-CANDIDATE: "
                f"{record.get('generatorFamily')}"
            )
        if record.get("disposition") != "INCLUDE":
            raise ManifestError(
                f"publicationInputs structured family is not INCLUDE: "
                f"{record.get('generatorFamily')}"
            )
        if record.get("decisionStatus") != "DECIDED":
            raise ManifestError(
                f"publicationInputs structured family is not DECIDED: "
                f"{record.get('generatorFamily')}"
            )

    actual_authored = {str(x["path"]) for x in authored}
    expected_authored = set(AUTHORED_ARCHITECTURE)
    if actual_authored != expected_authored:
        raise ManifestError(
            format_set_delta(expected_authored, actual_authored, "Authored INCLUDE set")
        )

    actual_families = {str(x["generatorFamily"]) for x in families}
    expected_families = set(STRUCTURED_ARCHITECTURE)
    if actual_families != expected_families:
        raise ManifestError(
            format_set_delta(expected_families, actual_families, "Structured-family INCLUDE set")
        )

    return version


def build_authored_inputs(pub: dict[str, Any]) -> list[dict[str, Any]]:
    parent_records = {
        x["path"]: x
        for x in pub["publicationInputs"]["authoredDocuments"]
    }

    results: list[dict[str, Any]] = []
    for path, architecture in AUTHORED_ARCHITECTURE.items():
        parent = parent_records[path]
        record = copy.deepcopy(architecture)
        record.update(
            {
                "parentDecisionId": parent["id"],
                "path": path,
                "audience": parent["audience"],
                "parentAuthority": parent["authority"],
                "parentDisposition": parent["disposition"],
                "sourceSha256": parent["sha256"],
                "parentBookSection": parent["bookSection"],
            }
        )
        results.append(record)

    results.sort(key=lambda x: PLACEMENT_ORDER.get(x["placement"], 999))
    return results


def build_structured_families(pub: dict[str, Any]) -> list[dict[str, Any]]:
    parent_records = {
        x["generatorFamily"]: x
        for x in pub["publicationInputs"]["structuredFamilies"]
    }

    results: list[dict[str, Any]] = []
    for family, architecture in STRUCTURED_ARCHITECTURE.items():
        parent = parent_records[family]
        record: dict[str, Any] = {
            "familyId": family,
            "sourcePath": parent["sourcePath"],
            "entityCount": parent["entityCount"],
            "audience": parent["audience"],
            "placement": architecture["placement"],
            "title": architecture["title"],
            "materialization": "generate-directly-from-canonical-structured-source",
            "sort": architecture["sort"],
            "recordFilter": (
                "logical entity records only; exclude Foundry "
                "folder/manifest/organizational records"
            ),
            "generatedIntermediate": f"build/rulebook/source/generated/{family}/",
            "generatedIntermediateAuthority": "DERIVATIVE",
            "parentDecisionId": parent["id"],
            "parentAuthority": parent["authority"],
            "parentDisposition": parent["disposition"],
            "sourceGlob": parent["sourceGlob"],
            "contentDigestSha256": parent["contentDigestSha256"],
            "generatedOutputDir": parent["generatedOutputDir"],
            "generatedOutputAuthority": parent["generatedOutputAuthority"],
            "generatedOutputDisposition": parent["generatedOutputDisposition"],
        }

        if family in {"adversaries", "environments"}:
            record["fastPlayRule"] = (
                "Consume flags.cybermancy.fastPlay structurally and render it "
                "as a dedicated Fast Play section; do not flatten it into Description."
            )

        results.append(record)

    return results


def decision_by_id(pub: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        x["id"]: x
        for x in pub.get("decisions", [])
        if isinstance(x, dict) and "id" in x
    }


def build_deferred_exclusions(pub: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = decision_by_id(pub)
    results: list[dict[str, Any]] = []

    for decision_id, reason in DEFERRED_EXCLUSIONS.items():
        decision = decisions.get(decision_id)
        if not decision:
            continue

        # These entries are meaningful only while they remain excluded.
        if decision.get("disposition") != "EXCLUDE":
            raise ManifestError(
                f"Step 3 exclusion rule {decision_id} is no longer EXCLUDE; "
                "review the information architecture."
            )

        results.append(
            {
                "parentDecisionId": decision_id,
                "path": decision["sourceLocator"],
                "parentDecision": (
                    f"{decision['authority']} / "
                    f"{decision['disposition']} / "
                    f"{decision['decisionStatus']}"
                ),
                "reason": reason,
            }
        )

    return results


def build_supersedes(
    version: Version,
    manifests_dir: Path,
) -> dict[str, Any]:
    candidates: list[tuple[Version, Path]] = []
    pattern = re.compile(
        r"^cybermancy-rulebook-assembly-manifest-v(\d+\.\d+)\.json$"
    )
    for path in manifests_dir.glob("cybermancy-rulebook-assembly-manifest-v*.json"):
        match = pattern.match(path.name)
        if not match:
            continue
        candidate_version = Version.parse(match.group(1))
        if candidate_version < version:
            candidates.append((candidate_version, path))

    if candidates:
        candidates.sort()
        previous_version, previous_path = candidates[-1]
        previous_name = previous_path.name
    else:
        previous_version = None
        previous_name = None

    result: dict[str, Any] = {
        "manifest": previous_name,
        "reason": (
            f"Rebuilt against frozen Rulebook Step 2 publication manifest "
            f"v{version.short()} using the approved Step 3 information architecture."
        ),
    }

    if previous_version is not None:
        result["previousVersion"] = previous_version.short()

    return result


def build_manifest(
    pub: dict[str, Any],
    version: Version,
    manifests_dir: Path,
) -> dict[str, Any]:
    summary = pub["summary"]
    repository = pub["repository"]

    authored_inputs = build_authored_inputs(pub)
    structured_families = build_structured_families(pub)
    book_structure = copy.deepcopy(BOOK_STRUCTURE)

    manifest: dict[str, Any] = {
        "schema": f"{ASSEMBLY_SCHEMA_PREFIX}{version.short()}",
        "version": version.semver(),
        "status": "NORMATIVE",
        "phase": "Rulebook Step 3 — Book Information Architecture",
        "generatedDate": date.today().isoformat(),
        "authority": {
            "parentPublicationManifest": (
                f"cybermancy-rulebook-publication-manifest-v{version.short()}.json"
            ),
            "parentPublicationManifestStatus": pub["status"],
            "repository": repository["name"],
            "sourceCommit": repository["gitCommit"],
            "expectedIncludeCount": summary["includeRows"],
            "expectedAuthoredIncludeCount": summary["authoredPublicationInputs"],
            "expectedStructuredFamilyCount": summary["structuredPublicationFamilies"],
            "expectedStructuredEntityCount": summary["structuredPublicationEntities"],
            "joinRule": (
                "Resolve every assembly input against the frozen Rulebook Step 2 "
                "publication manifest by exact authored path or exact structured-family "
                "source path. Assembly MUST fail if an input is absent from, or not "
                "CANONICAL-CANDIDATE + INCLUDE + DECIDED in, the frozen parent manifest."
            ),
            "sourcePrecedence": [
                "Explicit current user instruction",
                f"Frozen Rulebook Step 2 publication manifest v{version.short()}",
                (
                    "Canonical authored Markdown and canonical src/packs structured "
                    "sources named by that manifest"
                ),
                "Generated assembly intermediates (derivative only)",
            ],
        },
        "scope": {
            "purpose": (
                "Define book topology, ordering, audience boundaries, placement of "
                "canonical authored inputs and structured families, cross-reference "
                "conventions, and appendices."
            ),
            "normalizationStatus": "DEFERRED",
            "normalizationRule": (
                "Do not rewrite Markdown, HTML, Jinja, include-markdown, links, or "
                "source prose in Step 3. Source selectors in this manifest only define "
                "logical assembly ownership and deduplication boundaries."
            ),
            "baseSystemDependency": (
                "Cybermancy is assembled as a Daggerheart supplement/extension. "
                "Foundational Daggerheart rules are external prerequisites unless "
                "explicitly present in an INCLUDE source."
            ),
            "generatedMkdocsAuthority": "DERIVATIVE / EXCLUDE AS INPUT",
            "frontMatterPolicy": (
                "The hand-authored player and GM landing pages are explicit canonical "
                "publication inputs. The player landing page supplies the Welcome "
                "material; the GM landing page supplies a GM-only section opener after "
                "the spoiler divider. Full prose/HTML normalization remains deferred."
            ),
        },
        "audiencePolicy": {
            "audiences": {
                "shared": "Safe for all readers; included wherever needed.",
                "player": "Player-safe; included in player and complete builds.",
                "gm": (
                    "GM-only/spoiler-bearing; excluded from player builds and placed "
                    "only after the GM divider in complete builds."
                ),
                "developer": "Never reader-facing; excluded from book assembly.",
            },
            "boundaryRules": [
                "Player/shared content MUST NOT cross-reference GM-only content.",
                "GM content MAY cross-reference player/shared content.",
                (
                    "GM-only authored setting material is publication content only; "
                    "it does not become mechanical authority for reusable System design."
                ),
                (
                    "A complete-book build places all player-safe material before any "
                    "GM-only material."
                ),
            ],
        },
        "buildProfiles": [
            {
                "id": "complete-rulebook",
                "title": "Cybermancy Complete Rulebook",
                "includeAudiences": ["shared", "player", "gm"],
                "primary": True,
            },
            {
                "id": "player-guide",
                "title": "Cybermancy Player Guide",
                "includeAudiences": ["shared", "player"],
                "primary": False,
            },
        ],
        "hierarchy": {
            "levels": [
                "book",
                "part",
                "chapter",
                "section",
                "collection",
                "entry",
                "subentry",
            ],
            "rules": [
                "Authored prose attaches at chapter or section level.",
                (
                    "Structured families materialize as collections; each logical "
                    "source entity becomes one canonical entry."
                ),
                (
                    "Folder/organizational records may create grouping headings but "
                    "never count as entries."
                ),
                (
                    "A canonical definition renders in one primary location. Other "
                    "appearances use cross-references unless a later layout standard "
                    "explicitly permits controlled duplication."
                ),
            ],
        },
        "authoredInputs": authored_inputs,
        "structuredFamilies": structured_families,
        "bookStructure": book_structure,
        "gmDivider": {
            "beforePart": "part-v-gm-world",
            "title": "GM MATERIAL — SPOILERS BEYOND THIS POINT",
            "audience": "gm",
            "requiredInCompleteBuild": True,
            "omittedInPlayerBuild": True,
            "afterDividerFrontMatterRefs": ["auth.gm-guide-index"],
        },
        "crossReferencePolicy": {
            "semanticTargetForms": [
                "section:<section-or-chapter-id>",
                "family:<family-id>",
                "entity:<family-id>:<stable-source-id>",
            ],
            "identityRule": (
                "Structured entity references resolve by family plus stable "
                "source/Foundry ID when available; display name alone is never "
                "a unique key."
            ),
            "collisionRule": (
                "Same-name entities in different families are intentionally "
                "disambiguated by family-qualified semantic IDs."
            ),
            "pageNumberRule": (
                "Page numbers are render-time products and MUST NOT be stored as "
                "source-of-truth cross-references."
            ),
            "legacyLinkRule": (
                "Existing relative Markdown/MkDocs links remain untouched in Step 3. "
                "Step 4 normalization converts eligible internal links to semantic "
                "cross-references."
            ),
            "profileRule": (
                "A cross-reference target must exist in the selected build profile; "
                "player/shared nodes cannot target GM-only nodes."
            ),
            "externalRule": (
                "References to Daggerheart use external semantic references; the "
                "assembly process does not copy missing Daggerheart rules text."
            ),
        },
        "generatedCollectionPolicy": {
            "canonicalInput": "src/packs sources listed in structuredFamilies",
            "forbiddenInput": (
                "docs/... generated collection/detail pages and MkDocs CSV/Jinja "
                "aggregation pages"
            ),
            "intermediateRoot": "build/rulebook/source/generated/",
            "intermediateStatus": "DERIVATIVE",
            "materializationStatus": "DEFERRED UNTIL ASSEMBLY IMPLEMENTATION",
            "entryCountInvariant": summary["structuredPublicationEntities"],
            "fastPlayPolicy": (
                "For adversaries and environments, render "
                "flags.cybermancy.fastPlay structurally as Fast Play."
            ),
            "validation": [
                (
                    "Per-family logical entity counts must match this manifest and "
                    "the frozen publication manifest."
                ),
                "No generated page may become a canonical source.",
                (
                    "Generated collection output must preserve source identity for "
                    "semantic cross-references."
                ),
                (
                    "Sorting/grouping changes presentation only and never source "
                    "authority."
                ),
            ],
        },
        "appendices": [
            {
                "id": "appendix-a-quick-reference",
                "label": "Appendix A",
                "title": "Cybermancy Rules Quick Reference",
                "audience": "player",
                "status": "RESERVED / GENERATED LATER",
                "sourceRule": (
                    "May only summarize already-included rules; may not introduce "
                    "new mechanics."
                ),
            },
            {
                "id": "appendix-b-entity-index",
                "label": "Appendix B",
                "title": "Entity Index",
                "audience": "profile-filtered",
                "status": "RESERVED / GENERATED LATER",
                "sourceRule": (
                    "Generated from semantic IDs/titles of structured entries and "
                    "authored section targets; filtered by build profile."
                ),
            },
            {
                "id": "appendix-c-attribution",
                "label": "Appendix C",
                "title": "Attribution and Publication Notice",
                "audience": "shared",
                "status": "RESERVED / EDITORIAL-LATER",
                "sourceRule": (
                    "Populate only from verified licensing/attribution inputs; "
                    "no legal language is invented by this manifest."
                ),
            },
        ],
        "deferredOrExcluded": build_deferred_exclusions(pub),
        "step3Acceptance": {
            "mustHold": [
                (
                    f"{summary['authoredPublicationInputs']} authored inputs mapped "
                    "exactly once to a primary book or front-matter location."
                ),
                (
                    f"{summary['structuredPublicationFamilies']} structured families "
                    "mapped exactly once to a primary book location."
                ),
                (
                    f"Structured family counts sum to "
                    f"{summary['structuredPublicationEntities']}."
                ),
                (
                    f"All {summary['includeRows']} INCLUDE rows in the frozen parent "
                    "manifest are represented by authored inputs plus structured families."
                ),
                (
                    "GM-only content begins only after the GM divider in the complete build."
                ),
                "Player build contains no GM-only nodes.",
                (
                    "docs/gm-facing/world/the-alternate-chessboard.md is not assembled."
                ),
                "No generated MkDocs derivative is an input.",
                (
                    "Adversary/environment Fast Play is consumed from "
                    "flags.cybermancy.fastPlay."
                ),
                "No full Markdown/HTML normalization is performed by Step 3.",
            ]
        },
        "supersedes": build_supersedes(version, manifests_dir),
    }

    validate_assembly_manifest(manifest, pub)
    return manifest


def validate_assembly_manifest(
    manifest: dict[str, Any],
    pub: dict[str, Any],
) -> None:
    summary = pub["summary"]

    authored = manifest["authoredInputs"]
    families = manifest["structuredFamilies"]

    if len(authored) != summary["authoredPublicationInputs"]:
        raise ManifestError("Generated authored input count is incorrect.")
    if len(families) != summary["structuredPublicationFamilies"]:
        raise ManifestError("Generated structured-family count is incorrect.")
    if sum(int(x["entityCount"]) for x in families) != summary["structuredPublicationEntities"]:
        raise ManifestError("Generated structured entity total is incorrect.")

    parent_authored_paths = {
        x["path"] for x in pub["publicationInputs"]["authoredDocuments"]
    }
    generated_authored_paths = {x["path"] for x in authored}
    if generated_authored_paths != parent_authored_paths:
        raise ManifestError("Generated authored path set does not match Step 2.")

    parent_family_paths = {
        x["sourcePath"] for x in pub["publicationInputs"]["structuredFamilies"]
    }
    generated_family_paths = {x["sourcePath"] for x in families}
    if generated_family_paths != parent_family_paths:
        raise ManifestError("Generated structured-family path set does not match Step 2.")

    content_refs: list[str] = []
    for part in manifest["bookStructure"]:
        content_refs.extend(part.get("openerRefs", []))
        for chapter in part.get("chapters", []):
            content_refs.extend(chapter.get("contentRefs", []))

    authored_refs = [x for x in content_refs if x.startswith("auth.")]
    family_refs = [x for x in content_refs if x.startswith("family:")]

    expected_authored_refs = {x["assemblyInputId"] for x in authored}
    if len(authored_refs) != len(set(authored_refs)):
        raise ManifestError("An authored input has more than one primary placement.")
    if set(authored_refs) != expected_authored_refs:
        raise ManifestError("Not every authored input has exactly one primary placement.")

    expected_family_refs = {f"family:{x['familyId']}" for x in families}
    if len(family_refs) != len(set(family_refs)):
        raise ManifestError("A structured family has more than one primary placement.")
    if set(family_refs) != expected_family_refs:
        raise ManifestError("Not every structured family has exactly one primary placement.")

    if len(authored) + len(families) != summary["includeRows"]:
        raise ManifestError("Generated inputs do not account for all Step 2 INCLUDE rows.")

    excluded_paths = {x["path"] for x in manifest["deferredOrExcluded"]}
    if "docs/gm-facing/world/the-alternate-chessboard.md" not in excluded_paths:
        raise ManifestError("Corrected alternate-chessboard exclusion is missing.")


# ---------------------------------------------------------------------------
# Markdown companion
# ---------------------------------------------------------------------------

def markdown_structure(parts: Iterable[dict[str, Any]]) -> str:
    lines: list[str] = []
    for part in parts:
        suffix = " **[GM ONLY]**" if part["audience"] == "gm" else ""
        lines.append(f"### {part['title']}{suffix}")
        if part.get("openerRefs"):
            refs = ", ".join(f"`{x}`" for x in part["openerRefs"])
            lines.append(f"- **Section opener:** {refs}")
        for chapter in part["chapters"]:
            refs = ", ".join(f"`{x}`" for x in chapter["contentRefs"])
            lines.append(
                f"- **{chapter['number']}. {chapter['title']}** — {refs}"
            )
        lines.append("")
    return "\n".join(lines)


def markdown_authored_rows(records: Iterable[dict[str, Any]]) -> str:
    rows: list[str] = []
    for x in records:
        rows.append(
            f"| {x['parentDecisionId']} | `{x['path']}` | {x['audience']} | "
            f"{x['placement']} | {x['title']} | {x['assemblyMode']} |"
        )
    return "\n".join(rows)


def markdown_family_rows(records: Iterable[dict[str, Any]]) -> str:
    rows: list[str] = []
    for x in records:
        rows.append(
            f"| {x['parentDecisionId']} | `{x['familyId']}` | "
            f"`{x['sourcePath']}` | {x['entityCount']} | "
            f"{x['audience']} | {x['placement']} |"
        )
    return "\n".join(rows)


def build_markdown(manifest: dict[str, Any], pub: dict[str, Any]) -> str:
    summary = pub["summary"]
    version = Version.parse(pub["manifestVersion"])
    supersedes = manifest.get("supersedes", {}).get("manifest") or "none"

    return f"""# Cybermancy Rulebook Assembly Manifest v{version.short()}

**Status:** NORMATIVE  
**Step:** Rulebook Step 3 — Book Information Architecture  
**Parent authority:** `cybermancy-rulebook-publication-manifest-v{version.short()}.json`  
**Frozen repository commit:** `{pub['repository']['gitCommit']}`  
**Supersedes:** `{supersedes}`

## 1. Rebuild result

This manifest consumes the frozen Step 2 publication manifest and applies the
approved Step 3 information architecture.

Hard invariants:

- **{summary['includeRows']} INCLUDE rows**
- **{summary['authoredPublicationInputs']} authored publication inputs**
- **{summary['structuredPublicationFamilies']} structured publication families**
- **{summary['structuredPublicationEntities']} logical structured entities**
- generated MkDocs collection/detail output remains **DERIVATIVE / EXCLUDE**
- canonical structured publication content comes directly from `src/packs/...`
- full Markdown/HTML/Jinja normalization remains deferred to Step 4

The hand-authored player and GM landing pages are canonical publication inputs.
The player landing page supplies the Welcome material. The GM landing page is
placed as GM-only front matter after the spoiler divider and before Chapter 24.

`docs/gm-facing/world/the-alternate-chessboard.md` is explicitly excluded from
assembly. Campaign/adventure actor aggregation such as
`docs/gm-facing/adventures/npc-actors.md` remains outside reusable rulebook
authority.

## 2. Book architecture

{markdown_structure(manifest['bookStructure'])}

The complete book inserts **GM MATERIAL — SPOILERS BEYOND THIS POINT** before
Part V. A player-guide build omits the divider, GM opener, Parts V–VI, and all
GM-only structured collections.

## 3. Authored input mapping

| Step 2 ID | Source | Audience | Placement | Book role/title | Assembly mode |
|---|---|---|---|---|---|
{markdown_authored_rows(manifest['authoredInputs'])}

### Structural deduplication

Three sources use assembly-level segmentation without rewriting their source:

1. `docs/player-facing/index.md` supplies **Welcome to Cybermancy** but does not
   duplicate the Resonance section owned by `docs/_shared/world/the-resonance.md`.
2. `docs/player-facing/rules/index.md` supplies the Frame Rules lead plus unique
   Critical Fail / Armor Slot material, while dedicated rule files own their
   complete rule sections.
3. `docs/gm-facing/world/timeline.md` supplies its unique GM interpretation and
   tone sections but does not duplicate the shared Resonance text it transcludes.

The GM landing page is mapped whole as the GM section opener. Any editorial
cleanup of navigation/development phrasing is deferred to Step 4.

## 4. Structured-family mapping

| Step 2 ID | Family | Canonical source | Entities | Audience | Placement |
|---|---|---|---:|---|---|
{markdown_family_rows(manifest['structuredFamilies'])}

**Total logical structured entities: {summary['structuredPublicationEntities']}.**

Generated book collections consume canonical structured sources directly.
Existing generated MkDocs detail pages and aggregation pages remain excluded as
authority.

For **Adversaries** and **Environments**, `flags.cybermancy.fastPlay` is consumed
structurally and rendered as a dedicated **Fast Play** section rather than
flattened into Description.

## 5. Audience and front-matter routing

- `shared`: safe for all builds.
- `player`: player-safe; included in player and complete builds.
- `gm`: complete build only, after the spoiler divider.
- `developer`: never reader-facing.

Player/shared content must not target GM-only semantic references.

## 6. Cross-reference convention

Semantic targets are:

- `section:<chapter-or-section-id>`
- `family:<family-id>`
- `entity:<family-id>:<stable-source-id>`

Structured entities resolve by family plus stable source/Foundry ID where
available. Page numbers remain render-time products. Existing Markdown/MkDocs
links remain untouched until Step 4 normalization.

## 7. Appendices

- **Appendix A — Cybermancy Rules Quick Reference**
- **Appendix B — Entity Index**
- **Appendix C — Attribution and Publication Notice**

These remain generated/editorial-later and cannot introduce authority outside
the frozen publication inputs.

## 8. Validation

The generated manifest passes the Step 3 structural gate when:

- all {summary['authoredPublicationInputs']} authored inputs have exactly one
  primary book/front-matter placement;
- all {summary['structuredPublicationFamilies']} structured families have
  exactly one primary placement;
- structured-family counts sum to {summary['structuredPublicationEntities']};
- all {summary['includeRows']} Step 2 INCLUDE rows are represented;
- the GM boundary is preserved;
- generated MkDocs outputs remain derivative;
- Fast Play structured-source handling is preserved; and
- no full Markdown/HTML normalization is performed.

The JSON file is the normative machine-readable assembly manifest. This
Markdown file is its human-readable companion.
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the normative Cybermancy Rulebook Step 3 "
            "assembly/book manifest from the frozen Step 2 publication manifest."
        )
    )
    parser.add_argument(
        "--publication-manifest",
        help=(
            "Path to the Step 2 publication manifest JSON. Relative paths are "
            "resolved from the repository root. If omitted, the highest-version "
            "publication manifest in build/rulebook/manifests is used."
        ),
    )
    parser.add_argument(
        "--manifests-dir",
        help=(
            "Manifest directory. Defaults to build/rulebook/manifests under "
            "the repository root."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Validate and build in memory, but do not write output files. "
            "Useful for CI/pre-commit checks."
        ),
    )
    parser.add_argument(
        "--print-paths",
        action="store_true",
        help="Print resolved input/output paths.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        repo_root = repo_root_from_script()
        manifests_dir = resolve_path(args.manifests_dir, repo_root)
        if manifests_dir is None:
            manifests_dir = repo_root / "build" / "rulebook" / "manifests"
        manifests_dir = manifests_dir.resolve()
        manifests_dir.mkdir(parents=True, exist_ok=True)

        publication_path = resolve_path(args.publication_manifest, repo_root)
        if publication_path is None:
            publication_path = latest_publication_manifest(manifests_dir)

        pub = load_json(publication_path)
        version = validate_parent_manifest(pub)

        expected_publication_name = (
            f"cybermancy-rulebook-publication-manifest-v{version.short()}.json"
        )
        if publication_path.name != expected_publication_name:
            print(
                "WARNING: publication manifest filename is non-standard:\n"
                f"  actual:   {publication_path.name}\n"
                f"  expected: {expected_publication_name}",
                file=sys.stderr,
            )

        output_json = (
            manifests_dir
            / f"cybermancy-rulebook-assembly-manifest-v{version.short()}.json"
        )
        output_md = (
            manifests_dir
            / f"cybermancy-rulebook-assembly-manifest-v{version.short()}.md"
        )

        manifest = build_manifest(pub, version, manifests_dir)
        markdown = build_markdown(manifest, pub)

        if args.print_paths:
            print(f"Repository root:      {repo_root}")
            print(f"Publication manifest: {publication_path}")
            print(f"Assembly JSON:        {output_json}")
            print(f"Assembly Markdown:    {output_md}")

        if args.check:
            print(
                "PASS — Step 3 assembly architecture validated against "
                f"publication manifest v{version.short()}."
            )
            print(
                f"       {len(manifest['authoredInputs'])} authored inputs; "
                f"{len(manifest['structuredFamilies'])} structured families; "
                f"{sum(x['entityCount'] for x in manifest['structuredFamilies'])} entities."
            )
            return 0

        output_json.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        output_md.write_text(markdown, encoding="utf-8")

        print(
            "PASS — generated normative Rulebook Step 3 assembly manifest.\n"
            f"  JSON: {output_json}\n"
            f"  MD:   {output_md}\n"
            f"  Inputs: {len(manifest['authoredInputs'])} authored + "
            f"{len(manifest['structuredFamilies'])} structured families = "
            f"{len(manifest['authoredInputs']) + len(manifest['structuredFamilies'])}\n"
            f"  Structured entities: "
            f"{sum(x['entityCount'] for x in manifest['structuredFamilies'])}"
        )
        return 0

    except ManifestError as exc:
        print(f"ERROR — {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
