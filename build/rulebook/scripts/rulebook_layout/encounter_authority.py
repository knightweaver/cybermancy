from __future__ import annotations

from typing import Any

from .structured_count_authority import (
    count_authority_descriptor as structured_count_authority_descriptor,
    manifest_structured_counts,
    reconcile_structured_count_authority,
    require_reconciled_structured_count_authority,
    sidecar_family_state,
)


MUTABLE_ENCOUNTER_FAMILIES = ("adversaries", "environments")
EXPECTED_AUDIENCE = "gm"


def count_authority_descriptor(family: str) -> dict[str, str]:
    if family not in MUTABLE_ENCOUNTER_FAMILIES:
        raise ValueError(f"Unsupported mutable encounter family: {family}")
    return structured_count_authority_descriptor(family)


def manifest_encounter_counts(publication_manifest: dict[str, Any]) -> dict[str, int]:
    return manifest_structured_counts(
        publication_manifest,
        families=MUTABLE_ENCOUNTER_FAMILIES,
    )


def sidecar_encounter_state(sidecar: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        family: sidecar_family_state(sidecar, family)
        for family in MUTABLE_ENCOUNTER_FAMILIES
    }


def sidecar_encounter_counts(sidecar: dict[str, Any]) -> dict[str, int]:
    state = sidecar_encounter_state(sidecar)
    return {
        family: int(state[family]["actualCount"])
        for family in MUTABLE_ENCOUNTER_FAMILIES
    }


def reconcile_encounter_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    report = reconcile_structured_count_authority(
        publication_manifest,
        sidecar,
        families=MUTABLE_ENCOUNTER_FAMILIES,
    )
    return {
        **report,
        "schema": "cybermancy-encounter-count-authority-v1",
    }


def require_reconciled_encounter_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    report = require_reconciled_structured_count_authority(
        publication_manifest,
        sidecar,
        families=MUTABLE_ENCOUNTER_FAMILIES,
    )
    return {
        **report,
        "schema": "cybermancy-encounter-count-authority-v1",
    }
