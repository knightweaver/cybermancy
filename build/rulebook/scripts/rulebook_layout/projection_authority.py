from __future__ import annotations

from typing import Any

from .structured_count_authority import (
    count_authority_descriptor,
    reconcile_structured_count_authority,
    sidecar_family_state,
)


PROJECTION_FAMILIES = ("ice", "adversaryFeatures")
ICE_SEMANTICS_SCHEMA = "cybermancy-step4-ice-semantics-v1.0"
ADVERSARY_FEATURE_SELECTION_SCHEMA = (
    "cybermancy-step4-adversary-feature-publication-selection-v1.0"
)


def projection_authority_descriptor(projection: str) -> dict[str, str]:
    if projection == "ice":
        return {
            "canonicalSource": (
                "selected-publication-manifest:publicationInputs.structuredFamilies"
                "[generatorFamily=features].entityCount"
            ),
            "normalizedSelection": "step4-structured-sidecar:iceSemantics.semanticIds",
            "reconciliation": "source-exact-selected-subset-before-render",
        }
    if projection == "adversaryFeatures":
        return {
            "canonicalSource": (
                "selected-publication-manifest:publicationInputs.structuredFamilies"
                "[generatorFamily=adversaries-features].entityCount"
            ),
            "normalizedSelection": (
                "step4-adversary-feature-publication-selection:representativeSemanticIds"
            ),
            "reconciliation": "applied-source-exact-selected-subset-before-render",
        }
    raise ValueError(f"Unsupported structured projection: {projection}")


def validate_projection_authority_descriptor(
    projection: str, descriptor: Any
) -> list[str]:
    expected = projection_authority_descriptor(projection)
    if not isinstance(descriptor, dict):
        return [
            f"Malformed projection-authority descriptor for {projection}: expected an object"
        ]
    if descriptor != expected:
        return [
            f"Malformed projection-authority descriptor for {projection}: "
            f"expected {expected!r}, got {descriptor!r}"
        ]
    return []


def _strict_count(value: Any, *, owner: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{owner} must be a non-negative integer")
    return value


def _semantic_ids(value: Any, *, owner: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{owner} must be an array")
    result: list[str] = []
    missing: list[int] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        semantic_id = str(raw or "").strip()
        if not semantic_id:
            missing.append(index)
            continue
        if semantic_id in seen:
            duplicates.append(semantic_id)
            continue
        seen.add(semantic_id)
        result.append(semantic_id)
    if missing:
        raise ValueError(f"{owner} contains blank semantic IDs at indices {missing}")
    if duplicates:
        raise ValueError(
            f"{owner} contains duplicate semantic IDs: {sorted(set(duplicates))}"
        )
    return result


def _family_entity_map(sidecar: dict[str, Any], family: str) -> dict[str, dict[str, Any]]:
    entities = sidecar.get("entities")
    if not isinstance(entities, list):
        raise ValueError("Step 4 structured sidecar has no entities list")
    rows = [
        entity
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("family") or "") == family
    ]
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        semantic_id = str(row.get("semanticId") or "").strip()
        if semantic_id:
            result[semantic_id] = row
    return result


def sidecar_ice_projection_state(sidecar: dict[str, Any]) -> dict[str, Any]:
    """Validate and return the dynamic ICE subset projected from Features."""
    source = sidecar_family_state(sidecar, "features")
    source_ids = set(str(value) for value in source["semanticIds"])
    by_id = _family_entity_map(sidecar, "features")

    semantics = sidecar.get("iceSemantics")
    if not isinstance(semantics, dict):
        raise ValueError("Step 4 structured sidecar has no iceSemantics object")
    if semantics.get("schema") != ICE_SEMANTICS_SCHEMA:
        raise ValueError(f"Step 4 iceSemantics.schema must be {ICE_SEMANTICS_SCHEMA}")
    if semantics.get("status") != "PASS":
        raise ValueError("Step 4 iceSemantics status must be PASS")

    selected = _semantic_ids(
        semantics.get("semanticIds"), owner="Step 4 iceSemantics.semanticIds"
    )
    if not selected:
        raise ValueError("Step 4 ICE projection must contain at least one semantic ID")
    selected_set = set(selected)
    unknown = sorted(selected_set - source_ids)
    if unknown:
        raise ValueError(
            f"Step 4 ICE projection contains IDs outside the Features source family: {unknown}"
        )

    declared_total = _strict_count(
        semantics.get("iceCount"), owner="Step 4 iceSemantics.iceCount"
    )
    declared_sentry = _strict_count(
        semantics.get("sentryCount"), owner="Step 4 iceSemantics.sentryCount"
    )
    declared_wall = _strict_count(
        semantics.get("wallCount"), owner="Step 4 iceSemantics.wallCount"
    )
    if declared_total != len(selected):
        raise ValueError(
            f"Step 4 iceSemantics.iceCount declares {declared_total}, "
            f"but semanticIds contains {len(selected)} entries"
        )
    if declared_sentry + declared_wall != declared_total:
        raise ValueError(
            "Step 4 ICE sentryCount + wallCount does not equal iceCount"
        )

    discovered: set[str] = set()
    type_counts = {"sentry": 0, "wall": 0}
    errors: list[str] = []
    for semantic_id, entity in by_id.items():
        publication = (
            entity.get("publicationData")
            if isinstance(entity.get("publicationData"), dict)
            else {}
        )
        if publication.get("featureCategory") != "ice":
            continue
        discovered.add(semantic_id)
        ice_type = str(publication.get("iceType") or "")
        if ice_type not in type_counts:
            errors.append(
                f"{semantic_id} has unsupported ICE type {ice_type!r}"
            )
            continue
        type_counts[ice_type] += 1
        if str(entity.get("audience") or "") != "gm":
            errors.append(f"{semantic_id} is ICE but is not GM audience")
        if publication.get("standalonePublication") is not True:
            errors.append(
                f"{semantic_id} is ICE but standalonePublication is not true"
            )

    if discovered != selected_set:
        missing = sorted(discovered - selected_set)
        extra = sorted(selected_set - discovered)
        errors.append(
            "Step 4 ICE semanticIds do not exactly match Features marked as ICE; "
            f"missing={missing}, extra={extra}"
        )
    if type_counts["sentry"] != declared_sentry or type_counts["wall"] != declared_wall:
        errors.append(
            "Step 4 ICE type counts do not match selected entity semantics; "
            f"declared={{'sentry': {declared_sentry}, 'wall': {declared_wall}}}, "
            f"actual={type_counts}"
        )
    if errors:
        raise ValueError("; ".join(errors))

    return {
        "sourceFamily": "features",
        "sourceCount": int(source["actualCount"]),
        "projectedCount": len(selected),
        "projectedSemanticIds": selected,
        "groupCounts": type_counts,
    }


def sidecar_adversary_feature_projection_state(
    sidecar: dict[str, Any]
) -> dict[str, Any]:
    """Validate the APPLIED Chapter 32 projection stored in the Step 4 sidecar."""
    source = sidecar_family_state(sidecar, "adversaries-features")
    source_ids = set(str(value) for value in source["semanticIds"])
    by_id = _family_entity_map(sidecar, "adversaries-features")
    semantics = sidecar.get("encounterSemantics")
    if not isinstance(semantics, dict):
        raise ValueError("Step 4 structured sidecar has no encounterSemantics object")
    equivalence = semantics.get("adversaryFeatureEquivalence")
    if not isinstance(equivalence, dict):
        raise ValueError(
            "Step 4 encounterSemantics has no adversaryFeatureEquivalence object"
        )
    if equivalence.get("publicationStatus") != "APPLIED":
        raise ValueError(
            "Step 4 Adversary Feature publication equivalence must be APPLIED"
        )

    representatives: list[str] = []
    excluded: list[str] = []
    for semantic_id in source["semanticIds"]:
        entity = by_id[str(semantic_id)]
        publication = (
            entity.get("publicationData")
            if isinstance(entity.get("publicationData"), dict)
            else {}
        )
        metadata = (
            publication.get("publicationEquivalence")
            if isinstance(publication.get("publicationEquivalence"), dict)
            else {}
        )
        if metadata.get("isRepresentative") is False:
            excluded.append(str(semantic_id))
        else:
            representatives.append(str(semantic_id))

    canonical_count = _strict_count(
        equivalence.get("canonicalSourceFeatureCount"),
        owner="Step 4 adversaryFeatureEquivalence.canonicalSourceFeatureCount",
    )
    published_count = _strict_count(
        equivalence.get("publicationRepresentativeCount"),
        owner="Step 4 adversaryFeatureEquivalence.publicationRepresentativeCount",
    )
    excluded_count = _strict_count(
        equivalence.get("excludedRedundantCount"),
        owner="Step 4 adversaryFeatureEquivalence.excludedRedundantCount",
    )
    if canonical_count != int(source["actualCount"]):
        raise ValueError(
            "Step 4 Adversary Feature canonical source count does not match the "
            "normalized source family"
        )
    if published_count != len(representatives):
        raise ValueError(
            "Step 4 Adversary Feature publication representative count does not "
            "match sidecar representative metadata"
        )
    if excluded_count != len(excluded):
        raise ValueError(
            "Step 4 Adversary Feature excluded redundant count does not match "
            "sidecar representative metadata"
        )
    if set(representatives) | set(excluded) != source_ids:
        raise ValueError(
            "Step 4 Adversary Feature representative/excluded partition does not "
            "cover the canonical source family exactly"
        )

    return {
        "sourceFamily": "adversaries-features",
        "sourceCount": int(source["actualCount"]),
        "projectedCount": len(representatives),
        "projectedSemanticIds": representatives,
        "excludedCount": len(excluded),
        "excludedSemanticIds": excluded,
        "approvedGroupCount": _strict_count(
            equivalence.get("approvedGroupCount"),
            owner="Step 4 adversaryFeatureEquivalence.approvedGroupCount",
        ),
    }


def _source_authority(
    publication_manifest: dict[str, Any], sidecar: dict[str, Any], family: str
) -> dict[str, Any]:
    return reconcile_structured_count_authority(
        publication_manifest,
        sidecar,
        families=(family,),
        descriptors={family: count_authority_descriptor(family)},
    )


def reconcile_ice_projection_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
    *,
    descriptor: Any | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "projection": "ice",
        "projectionAuthority": projection_authority_descriptor("ice"),
        "status": "PASS",
        "errors": [],
    }
    if descriptor is not None:
        errors = validate_projection_authority_descriptor("ice", descriptor)
        if errors:
            report["status"] = "FAIL"
            report["errors"].extend(errors)
            return report
    source = _source_authority(publication_manifest, sidecar, "features")
    report["sourceAuthority"] = source
    if source.get("status") != "PASS":
        report["status"] = "FAIL"
        report["errors"].extend(source.get("errors") or [])
        return report
    try:
        report.update(sidecar_ice_projection_state(sidecar))
    except Exception as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))
    return report


def reconcile_adversary_feature_projection_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
    selection: Any,
    *,
    descriptor: Any | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "projection": "adversaryFeatures",
        "projectionAuthority": projection_authority_descriptor("adversaryFeatures"),
        "status": "PASS",
        "errors": [],
    }
    if descriptor is not None:
        errors = validate_projection_authority_descriptor(
            "adversaryFeatures", descriptor
        )
        if errors:
            report["status"] = "FAIL"
            report["errors"].extend(errors)
            return report
    source = _source_authority(
        publication_manifest, sidecar, "adversaries-features"
    )
    report["sourceAuthority"] = source
    if source.get("status") != "PASS":
        report["status"] = "FAIL"
        report["errors"].extend(source.get("errors") or [])
        return report
    try:
        state = sidecar_adversary_feature_projection_state(sidecar)
        report.update(state)
        if not isinstance(selection, dict):
            raise ValueError(
                "Step 4 Adversary Feature publication-selection artifact is not an object"
            )
        if selection.get("schema") != ADVERSARY_FEATURE_SELECTION_SCHEMA:
            raise ValueError(
                "Step 4 Adversary Feature publication-selection artifact has an unsupported schema"
            )
        if selection.get("status") != "APPLIED":
            raise ValueError(
                "Step 4 Adversary Feature publication-selection status must be APPLIED"
            )
        representative_ids = _semantic_ids(
            selection.get("representativeSemanticIds"),
            owner="Step 4 Adversary Feature representativeSemanticIds",
        )
        excluded_ids = _semantic_ids(
            selection.get("excludedSemanticIds"),
            owner="Step 4 Adversary Feature excludedSemanticIds",
        )
        if set(representative_ids) != set(state["projectedSemanticIds"]):
            raise ValueError(
                "Step 4 Adversary Feature publication-selection representatives do not "
                "match sidecar APPLIED metadata"
            )
        if set(excluded_ids) != set(state["excludedSemanticIds"]):
            raise ValueError(
                "Step 4 Adversary Feature publication-selection exclusions do not "
                "match sidecar APPLIED metadata"
            )
        if _strict_count(
            selection.get("canonicalSourceFeatureCount"),
            owner="Step 4 publication selection canonicalSourceFeatureCount",
        ) != state["sourceCount"]:
            raise ValueError(
                "Step 4 Adversary Feature publication-selection canonical count does not "
                "match source authority"
            )
        if _strict_count(
            selection.get("publicationRepresentativeCount"),
            owner="Step 4 publication selection publicationRepresentativeCount",
        ) != state["projectedCount"]:
            raise ValueError(
                "Step 4 Adversary Feature publication-selection representative count does "
                "not match selected semantic IDs"
            )
        if _strict_count(
            selection.get("excludedRedundantCount"),
            owner="Step 4 publication selection excludedRedundantCount",
        ) != state["excludedCount"]:
            raise ValueError(
                "Step 4 Adversary Feature publication-selection excluded count does not "
                "match excluded semantic IDs"
            )
        groups = selection.get("groups")
        if not isinstance(groups, list):
            raise ValueError("Step 4 Adversary Feature publication-selection groups must be an array")
        if _strict_count(
            selection.get("approvedGroupCount"),
            owner="Step 4 publication selection approvedGroupCount",
        ) != len(groups):
            raise ValueError(
                "Step 4 Adversary Feature publication-selection approvedGroupCount does "
                "not match groups[]"
            )
        if int(selection["approvedGroupCount"]) != state["approvedGroupCount"]:
            raise ValueError(
                "Step 4 Adversary Feature publication-selection group count does not "
                "match sidecar APPLIED metadata"
            )
    except Exception as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))
    return report


def reconcile_structured_projection_authority(
    publication_manifest: dict[str, Any],
    sidecar: dict[str, Any],
    selection: Any,
    *,
    descriptors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    configured = descriptors if isinstance(descriptors, dict) else {}
    ice = reconcile_ice_projection_authority(
        publication_manifest,
        sidecar,
        descriptor=configured.get("ice") if descriptors is not None else None,
    )
    adversary_features = reconcile_adversary_feature_projection_authority(
        publication_manifest,
        sidecar,
        selection,
        descriptor=(
            configured.get("adversaryFeatures") if descriptors is not None else None
        ),
    )
    status = (
        "PASS"
        if ice.get("status") == "PASS" and adversary_features.get("status") == "PASS"
        else "FAIL"
    )
    return {
        "schema": "cybermancy-structured-projection-authority-v1",
        "status": status,
        "projections": {
            "ice": ice,
            "adversaryFeatures": adversary_features,
        },
        "errors": [
            *list(ice.get("errors") or []),
            *list(adversary_features.get("errors") or []),
        ],
    }
