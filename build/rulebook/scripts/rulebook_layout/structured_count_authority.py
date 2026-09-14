from __future__ import annotations

from typing import Any, Iterable


MUTABLE_STRUCTURED_FAMILIES = ("domains", "adversaries", "environments")

_FAMILY_POLICIES: dict[str, dict[str, str]] = {
    "domains": {
        "audience": "player",
        "declaredContainer": "domainSemantics",
        "declaredField": "cardCount",
        "normalizedActual": "step4-structured-sidecar:domainSemantics.cardCount",
    },
    "adversaries": {
        "audience": "gm",
        "declaredContainer": "encounterSemantics.entityCounts",
        "declaredField": "adversaries",
        "normalizedActual": "step4-structured-sidecar:encounterSemantics.entityCounts.adversaries",
    },
    "environments": {
        "audience": "gm",
        "declaredContainer": "encounterSemantics.entityCounts",
        "declaredField": "environments",
        "normalizedActual": "step4-structured-sidecar:encounterSemantics.entityCounts.environments",
    },
}


def _policy(family: str) -> dict[str, str]:
    try:
        return _FAMILY_POLICIES[family]
    except KeyError as exc:
        raise ValueError(f"Unsupported mutable structured family: {family}") from exc


def _strict_count(value: Any, *, owner: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{owner} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{owner} must be a non-negative integer")
    return value


def count_authority_descriptor(family: str) -> dict[str, str]:
    policy = _policy(family)
    return {
        "canonicalExpected": (
            "selected-publication-manifest:publicationInputs.structuredFamilies"
            f"[generatorFamily={family}].entityCount"
        ),
        "normalizedActual": policy["normalizedActual"],
        "reconciliation": "exact-before-render",
    }


def validate_count_authority_descriptor(family: str, descriptor: Any) -> list[str]:
    expected = count_authority_descriptor(family)
    if not isinstance(descriptor, dict):
        return [f"Malformed count-authority descriptor for {family}: expected an object"]
    if descriptor != expected:
        return [
            f"Malformed count-authority descriptor for {family}: expected {expected!r}, got {descriptor!r}"
        ]
    return []


def _manifest_family_row(
    publication_manifest: dict[str, Any], family: str
) -> dict[str, Any]:
    policy = _policy(family)
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
    if not matches:
        raise ValueError(
            f"Selected publication manifest is missing structured family {family!r}"
        )
    if len(matches) != 1:
        raise ValueError(
            f"Selected publication manifest contains duplicate {family!r} structured families; found {len(matches)}"
        )
    row = matches[0]
    if (
        row.get("authority") != "CANONICAL-CANDIDATE"
        or row.get("disposition") != "INCLUDE"
        or row.get("decisionStatus") != "DECIDED"
    ):
        raise ValueError(
            f"Selected publication manifest does not authorize {family} as CANONICAL-CANDIDATE + INCLUDE + DECIDED"
        )
    expected_audience = policy["audience"]
    actual_audience = str(row.get("audience") or "")
    if actual_audience != expected_audience:
        raise ValueError(
            f"Selected publication manifest routes {family} to audience {actual_audience!r}; expected {expected_audience!r}"
        )
    _strict_count(
        row.get("entityCount"),
        owner=f"Selected publication manifest entityCount for {family}",
    )
    return row


def manifest_structured_counts(
    publication_manifest: dict[str, Any],
    families: Iterable[str] = MUTABLE_STRUCTURED_FAMILIES,
) -> dict[str, int]:
    return {
        family: int(_manifest_family_row(publication_manifest, family)["entityCount"])
        for family in families
    }


def _declared_sidecar_count(sidecar: dict[str, Any], family: str) -> int:
    policy = _policy(family)
    if family == "domains":
        semantics = sidecar.get("domainSemantics")
        if not isinstance(semantics, dict):
            raise ValueError("Step 4 structured sidecar has no domainSemantics object")
        return _strict_count(
            semantics.get("cardCount"),
            owner="Step 4 domainSemantics.cardCount",
        )

    semantics = sidecar.get("encounterSemantics")
    if not isinstance(semantics, dict):
        raise ValueError("Step 4 structured sidecar has no encounterSemantics object")
    declared_counts = semantics.get("entityCounts")
    if not isinstance(declared_counts, dict):
        raise ValueError("Step 4 encounterSemantics has no entityCounts object")
    return _strict_count(
        declared_counts.get(family),
        owner=f"Step 4 encounterSemantics.entityCounts.{family}",
    )


def sidecar_family_state(sidecar: dict[str, Any], family: str) -> dict[str, Any]:
    policy = _policy(family)
    entities = sidecar.get("entities")
    if not isinstance(entities, list):
        raise ValueError("Step 4 structured sidecar has no entities list")
    declared = _declared_sidecar_count(sidecar, family)
    rows = [
        entity
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("family") or "") == family
    ]
    if not rows:
        raise ValueError(f"Step 4 structured sidecar is missing family {family!r}")

    semantic_ids: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    missing: list[str] = []
    audience_errors: list[dict[str, Any]] = []
    expected_audience = policy["audience"]
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
        if audience != expected_audience:
            audience_errors.append(
                {
                    "semanticId": semantic_id or None,
                    "name": entity.get("name"),
                    "expected": expected_audience,
                    "actual": audience or None,
                }
            )

    if missing:
        raise ValueError(
            f"Step 4 {family} sidecar entities are missing semanticId: {missing}"
        )
    if duplicates:
        raise ValueError(
            f"Step 4 {family} sidecar contains duplicate semantic IDs: {sorted(set(duplicates))}"
        )
    if audience_errors:
        label = "GM" if expected_audience == "gm" else expected_audience
        raise ValueError(
            f"Step 4 {family} sidecar contains non-{label} entities: {audience_errors}"
        )
    if declared != len(rows):
        declared_path = policy["normalizedActual"].split(":", 1)[-1]
        raise ValueError(
            f"{declared_path} declares {declared} {family}, but entities[] contains {len(rows)}"
        )
    return {
        "declaredCount": declared,
        "actualCount": len(rows),
        "semanticIds": semantic_ids,
    }


def sidecar_structured_state(
    sidecar: dict[str, Any],
    families: Iterable[str] = MUTABLE_STRUCTURED_FAMILIES,
) -> dict[str, dict[str, Any]]:
    return {family: sidecar_family_state(sidecar, family) for family in families}


def sidecar_structured_counts(
    sidecar: dict[str, Any],
    families: Iterable[str] = MUTABLE_STRUCTURED_FAMILIES,
) -> dict[str, int]:
    state = sidecar_structured_state(sidecar, families)
    return {family: int(row["actualCount"]) for family, row in state.items()}


def reconcile_structured_count_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
    *,
    families: Iterable[str] = MUTABLE_STRUCTURED_FAMILIES,
    descriptors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    family_list = tuple(families)
    report: dict[str, Any] = {
        "schema": "cybermancy-structured-count-authority-v1",
        "status": "PASS",
        "families": {},
        "errors": [],
    }

    for family in family_list:
        row: dict[str, Any] = {
            "countAuthority": count_authority_descriptor(family),
            "status": "PASS",
            "errors": [],
        }
        if descriptors is not None:
            descriptor_errors = validate_count_authority_descriptor(
                family, descriptors.get(family)
            )
            if descriptor_errors:
                row["status"] = "FAIL"
                row["errors"].extend(descriptor_errors)
                report["status"] = "FAIL"
                report["errors"].extend(descriptor_errors)
                report["families"][family] = row
                continue

        try:
            manifest_row = _manifest_family_row(publication_manifest, family)
            expected = int(manifest_row["entityCount"])
        except Exception as exc:
            row["status"] = "FAIL"
            row["errors"].append(str(exc))
            report["status"] = "FAIL"
            report["errors"].append(str(exc))
            report["families"][family] = row
            continue

        try:
            state = sidecar_family_state(sidecar, family)
        except Exception as exc:
            row["status"] = "FAIL"
            row["errors"].append(str(exc))
            report["status"] = "FAIL"
            report["errors"].append(str(exc))
            report["families"][family] = row
            continue

        row.update(
            {
                "expectedCount": expected,
                "declaredStep4Count": state["declaredCount"],
                "actualStep4Count": state["actualCount"],
                "semanticIds": list(state["semanticIds"]),
            }
        )
        if expected != state["actualCount"]:
            message = (
                f"{family}: selected publication manifest expects {expected}, "
                f"but reconciled Step 4 sidecar contains {state['actualCount']}"
            )
            row["status"] = "FAIL"
            row["errors"].append(message)
            report["status"] = "FAIL"
            report["errors"].append(message)
        report["families"][family] = row

    return report


def require_reconciled_structured_count_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
    *,
    families: Iterable[str] = MUTABLE_STRUCTURED_FAMILIES,
    descriptors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = reconcile_structured_count_authority(
        publication_manifest,
        sidecar,
        families=families,
        descriptors=descriptors,
    )
    if report["status"] != "PASS":
        raise ValueError(
            "; ".join(report["errors"])
            or "Structured corpus count-authority reconciliation failed"
        )
    return report
