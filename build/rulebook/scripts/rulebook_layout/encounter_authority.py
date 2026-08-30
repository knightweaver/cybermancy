from __future__ import annotations

from typing import Any


MUTABLE_ENCOUNTER_FAMILIES = ("adversaries", "environments")
EXPECTED_AUDIENCE = "gm"


def count_authority_descriptor(family: str) -> dict[str, str]:
    if family not in MUTABLE_ENCOUNTER_FAMILIES:
        raise ValueError(f"Unsupported mutable encounter family: {family}")
    return {
        "canonicalExpected": (
            "selected-publication-manifest:publicationInputs.structuredFamilies"
            f"[generatorFamily={family}].entityCount"
        ),
        "normalizedActual": (
            f"step4-structured-sidecar:encounterSemantics.entityCounts.{family}"
        ),
        "reconciliation": "exact-before-render",
    }


def _manifest_family_row(publication_manifest: dict[str, Any], family: str) -> dict[str, Any]:
    publication_inputs = publication_manifest.get("publicationInputs")
    if not isinstance(publication_inputs, dict):
        raise ValueError("Selected publication manifest has no publicationInputs object")
    rows = publication_inputs.get("structuredFamilies")
    if not isinstance(rows, list):
        raise ValueError("Selected publication manifest has no structuredFamilies list")
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("generatorFamily") or "") == family
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Selected publication manifest must contain exactly one {family} structured family; "
            f"found {len(matches)}"
        )
    row = matches[0]
    if (
        row.get("authority") != "CANONICAL-CANDIDATE"
        or row.get("disposition") != "INCLUDE"
        or row.get("decisionStatus") != "DECIDED"
    ):
        raise ValueError(f"Selected publication manifest does not authorize {family} as INCLUDE + DECIDED")
    if str(row.get("audience") or "") != EXPECTED_AUDIENCE:
        raise ValueError(f"Selected publication manifest routes {family} to a non-GM audience")
    try:
        count = int(row.get("entityCount"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Selected publication manifest has no integer entityCount for {family}") from exc
    if count < 0:
        raise ValueError(f"Selected publication manifest has a negative entityCount for {family}")
    return row


def manifest_encounter_counts(publication_manifest: dict[str, Any]) -> dict[str, int]:
    return {
        family: int(_manifest_family_row(publication_manifest, family)["entityCount"])
        for family in MUTABLE_ENCOUNTER_FAMILIES
    }


def _sidecar_family_state(sidecar: dict[str, Any], family: str) -> dict[str, Any]:
    entities = sidecar.get("entities")
    if not isinstance(entities, list):
        raise ValueError("Step 4 structured sidecar has no entities list")
    semantics = sidecar.get("encounterSemantics")
    if not isinstance(semantics, dict):
        raise ValueError("Step 4 structured sidecar has no encounterSemantics object")
    declared_counts = semantics.get("entityCounts")
    if not isinstance(declared_counts, dict):
        raise ValueError("Step 4 encounterSemantics has no entityCounts object")
    try:
        declared = int(declared_counts.get(family))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Step 4 encounterSemantics has no integer count for {family}") from exc

    rows = [
        entity
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("family") or "") == family
    ]
    semantic_ids: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    missing: list[str] = []
    audience_errors: list[dict[str, Any]] = []
    for index, entity in enumerate(rows):
        semantic_id = str(entity.get("semanticId") or "").strip()
        if not semantic_id:
            missing.append(str(entity.get("name") or f"index:{index}"))
        elif semantic_id in seen:
            duplicates.append(semantic_id)
        else:
            seen.add(semantic_id)
            semantic_ids.append(semantic_id)
        audience = str(entity.get("audience") or "").strip()
        if audience != EXPECTED_AUDIENCE:
            audience_errors.append(
                {
                    "semanticId": semantic_id or None,
                    "name": entity.get("name"),
                    "expected": EXPECTED_AUDIENCE,
                    "actual": audience or None,
                }
            )

    if missing:
        raise ValueError(f"Step 4 {family} sidecar entities are missing semanticId: {missing}")
    if duplicates:
        raise ValueError(f"Step 4 {family} sidecar contains duplicate semantic IDs: {sorted(set(duplicates))}")
    if audience_errors:
        raise ValueError(f"Step 4 {family} sidecar contains non-GM entities: {audience_errors}")
    if declared != len(rows):
        raise ValueError(
            f"Step 4 encounterSemantics declares {declared} {family}, but entities[] contains {len(rows)}"
        )
    return {
        "declaredCount": declared,
        "actualCount": len(rows),
        "semanticIds": semantic_ids,
    }


def sidecar_encounter_state(sidecar: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        family: _sidecar_family_state(sidecar, family)
        for family in MUTABLE_ENCOUNTER_FAMILIES
    }


def sidecar_encounter_counts(sidecar: dict[str, Any]) -> dict[str, int]:
    state = sidecar_encounter_state(sidecar)
    return {family: int(state[family]["actualCount"]) for family in MUTABLE_ENCOUNTER_FAMILIES}


def reconcile_encounter_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "cybermancy-encounter-count-authority-v1",
        "status": "PASS",
        "families": {},
        "errors": [],
    }
    try:
        expected = manifest_encounter_counts(publication_manifest)
    except Exception as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))
        return report
    try:
        sidecar_state = sidecar_encounter_state(sidecar)
    except Exception as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))
        return report

    for family in MUTABLE_ENCOUNTER_FAMILIES:
        state = sidecar_state[family]
        row = {
            "expectedCount": expected[family],
            "declaredStep4Count": state["declaredCount"],
            "actualStep4Count": state["actualCount"],
            "semanticIds": list(state["semanticIds"]),
            "status": "PASS",
        }
        if expected[family] != state["actualCount"]:
            row["status"] = "FAIL"
            report["status"] = "FAIL"
            report["errors"].append(
                f"{family}: selected publication manifest expects {expected[family]}, "
                f"but reconciled Step 4 sidecar contains {state['actualCount']}"
            )
        report["families"][family] = row
    return report


def require_reconciled_encounter_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    report = reconcile_encounter_authority(publication_manifest, sidecar)
    if report["status"] != "PASS":
        raise ValueError("; ".join(report["errors"]) or "Encounter corpus authority reconciliation failed")
    return report
