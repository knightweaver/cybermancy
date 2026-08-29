from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

FEATURE_FAMILY = "adversaries-features"
DECISIONS_SCHEMA = "cybermancy-step4-adversary-feature-equivalence-decisions-v1.0"
PUBLICATION_EQUIVALENCE_SCHEMA = "cybermancy-step4-adversary-feature-publication-equivalence-v1.0"
PUBLICATION_SELECTION_SCHEMA = "cybermancy-step4-adversary-feature-publication-selection-v1.0"
DECISIONS_REPO_PATH = Path("build/rulebook/scripts/data/adversary-feature-equivalence-decisions-v1.json")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _feature_entities(sidecar: dict) -> list[dict]:
    return [
        entity
        for entity in sidecar.get("entities") or []
        if isinstance(entity, dict) and str(entity.get("family") or "") == FEATURE_FAMILY
    ]


def _source_id(entity: dict) -> str:
    source_id = str(entity.get("sourceId") or "").strip()
    if source_id:
        return source_id
    semantic_id = str(entity.get("semanticId") or "")
    prefix = f"entity:{FEATURE_FAMILY}:"
    return semantic_id[len(prefix) :] if semantic_id.startswith(prefix) else ""


def _display_name(entity: dict) -> str:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    reference = pdata.get("referenceEntry") if isinstance(pdata.get("referenceEntry"), dict) else {}
    return str(reference.get("name") or entity.get("name") or "")


def apply_feature_publication_equivalence(
    sidecar: dict,
    decisions: dict,
) -> tuple[dict, list[dict]]:
    """Apply reviewed Chapter 32 publication grouping without deleting source entities.

    All canonical Step 4 entities remain in ``structured-entities.json``. Grouped
    members receive publication metadata; only one member is marked as the
    Chapter 32 representative. Feature-Library-backed groups may also provide a
    reader-neutral ``referenceEntry`` used only by the reference chapter.
    """
    errors: list[dict] = []
    if decisions.get("schema") != DECISIONS_SCHEMA:
        return {}, [{
            "code": "ADVERSARY_FEATURE_EQUIVALENCE_DECISIONS_SCHEMA",
            "message": f"Expected decisions schema {DECISIONS_SCHEMA}.",
            "actual": decisions.get("schema"),
        }]
    if str(decisions.get("status") or "") != "approved":
        return {}, [{
            "code": "ADVERSARY_FEATURE_EQUIVALENCE_DECISIONS_NOT_APPROVED",
            "message": "Publication-equivalence decisions must have status='approved'.",
        }]

    features = _feature_entities(sidecar)
    by_source: dict[str, dict] = {}
    for entity in features:
        source_id = _source_id(entity)
        if not source_id:
            errors.append({
                "code": "ADVERSARY_FEATURE_SOURCE_ID_MISSING",
                "semanticId": entity.get("semanticId"),
                "name": entity.get("name"),
            })
            continue
        if source_id in by_source:
            errors.append({
                "code": "ADVERSARY_FEATURE_SOURCE_ID_DUPLICATE",
                "sourceId": source_id,
            })
            continue
        by_source[source_id] = entity

    expected_source = decisions.get("sourceFeatureCount")
    try:
        expected_source_count = int(expected_source)
    except (TypeError, ValueError):
        expected_source_count = -1
        errors.append({
            "code": "ADVERSARY_FEATURE_EQUIVALENCE_SOURCE_COUNT_INVALID",
            "value": expected_source,
        })
    if expected_source_count >= 0 and len(features) != expected_source_count:
        errors.append({
            "code": "ADVERSARY_FEATURE_EQUIVALENCE_SOURCE_COUNT_DRIFT",
            "expected": expected_source_count,
            "actual": len(features),
            "message": "Canonical standalone Feature count changed; equivalence decisions require review.",
        })

    groups = decisions.get("groups") if isinstance(decisions.get("groups"), list) else []
    seen_members: set[str] = set()
    plan: list[dict] = []
    for raw_group in groups:
        if not isinstance(raw_group, dict):
            errors.append({"code": "ADVERSARY_FEATURE_EQUIVALENCE_GROUP_INVALID"})
            continue
        group_id = str(raw_group.get("groupId") or "").strip()
        member_source_ids = [
            str(value).strip()
            for value in raw_group.get("memberSourceIds") or []
            if str(value or "").strip()
        ]
        representative_source_id = str(raw_group.get("representativeSourceId") or "").strip()
        if not group_id or len(member_source_ids) < 2:
            errors.append({
                "code": "ADVERSARY_FEATURE_EQUIVALENCE_GROUP_INVALID",
                "groupId": group_id,
                "memberCount": len(member_source_ids),
            })
            continue
        if len(set(member_source_ids)) != len(member_source_ids):
            errors.append({
                "code": "ADVERSARY_FEATURE_EQUIVALENCE_GROUP_MEMBER_DUPLICATE",
                "groupId": group_id,
            })
        if representative_source_id not in member_source_ids:
            errors.append({
                "code": "ADVERSARY_FEATURE_EQUIVALENCE_REPRESENTATIVE_INVALID",
                "groupId": group_id,
                "representativeSourceId": representative_source_id,
            })
        overlap = sorted(set(member_source_ids) & seen_members)
        if overlap:
            errors.append({
                "code": "ADVERSARY_FEATURE_EQUIVALENCE_GROUP_OVERLAP",
                "groupId": group_id,
                "sourceIds": overlap,
            })
        seen_members.update(member_source_ids)
        missing = [source_id for source_id in member_source_ids if source_id not in by_source]
        if missing:
            errors.append({
                "code": "ADVERSARY_FEATURE_EQUIVALENCE_MEMBER_MISSING",
                "groupId": group_id,
                "sourceIds": missing,
            })
            continue
        if representative_source_id not in by_source:
            continue

        reference_entry = raw_group.get("publicationEntry")
        if reference_entry is not None and not isinstance(reference_entry, dict):
            errors.append({
                "code": "ADVERSARY_FEATURE_REFERENCE_ENTRY_INVALID",
                "groupId": group_id,
            })
            continue
        if isinstance(reference_entry, dict):
            if not str(reference_entry.get("name") or "").strip() or not str(reference_entry.get("rulesMarkdown") or "").strip():
                errors.append({
                    "code": "ADVERSARY_FEATURE_REFERENCE_ENTRY_INVALID",
                    "groupId": group_id,
                    "message": "referenceEntry requires name and rulesMarkdown.",
                })
                continue
            if "actions" in reference_entry and not isinstance(reference_entry.get("actions"), list):
                errors.append({
                    "code": "ADVERSARY_FEATURE_REFERENCE_ENTRY_INVALID",
                    "groupId": group_id,
                    "message": "referenceEntry.actions must be a list when supplied.",
                })
                continue

        plan.append({
            "raw": raw_group,
            "groupId": group_id,
            "memberSourceIds": member_source_ids,
            "representativeSourceId": representative_source_id,
            "referenceEntry": reference_entry,
        })

    if errors:
        return {}, errors

    # Clear only metadata owned by this pass so repeat builds are deterministic.
    for entity in features:
        pdata = entity.setdefault("publicationData", {})
        pdata.pop("publicationEquivalence", None)
        pdata.pop("referenceEntry", None)

    group_records: list[dict] = []
    excluded_semantic_ids: list[str] = []
    for item in plan:
        raw_group = item["raw"]
        member_entities = [by_source[source_id] for source_id in item["memberSourceIds"]]
        representative = by_source[item["representativeSourceId"]]
        member_semantic_ids = [str(entity.get("semanticId") or "") for entity in member_entities]
        representative_semantic_id = str(representative.get("semanticId") or "")
        common = {
            "schema": PUBLICATION_EQUIVALENCE_SCHEMA,
            "groupId": item["groupId"],
            "basis": raw_group.get("basis"),
            "familyId": raw_group.get("familyId"),
            "representativeSemanticId": representative_semantic_id,
            "memberSemanticIds": member_semantic_ids,
        }
        if isinstance(raw_group.get("mechanicalParameters"), dict):
            common["mechanicalParameters"] = copy.deepcopy(raw_group["mechanicalParameters"])
        if isinstance(raw_group.get("featureLibraryEvidence"), dict):
            common["featureLibraryEvidence"] = copy.deepcopy(raw_group["featureLibraryEvidence"])

        for entity in member_entities:
            pdata = entity.setdefault("publicationData", {})
            metadata = dict(common)
            metadata["isRepresentative"] = entity is representative
            pdata["publicationEquivalence"] = metadata
            if entity is not representative:
                excluded_semantic_ids.append(str(entity.get("semanticId") or ""))

        if isinstance(item["referenceEntry"], dict):
            representative.setdefault("publicationData", {})["referenceEntry"] = copy.deepcopy(item["referenceEntry"])

        group_records.append({
            "groupId": item["groupId"],
            "basis": raw_group.get("basis"),
            "familyId": raw_group.get("familyId"),
            "representativeSemanticId": representative_semantic_id,
            "memberSemanticIds": member_semantic_ids,
            "memberCount": len(member_semantic_ids),
            "publicationName": _display_name(representative),
            **(
                {"mechanicalParameters": copy.deepcopy(raw_group["mechanicalParameters"])}
                if isinstance(raw_group.get("mechanicalParameters"), dict)
                else {}
            ),
        })

    representatives = []
    for entity in features:
        pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
        metadata = pdata.get("publicationEquivalence") if isinstance(pdata.get("publicationEquivalence"), dict) else {}
        if metadata.get("isRepresentative") is False:
            continue
        representatives.append(entity)
    representatives.sort(
        key=lambda entity: (
            _display_name(entity).casefold(),
            str(entity.get("semanticId") or ""),
        )
    )

    expected_representatives = decisions.get("expectedPublicationRepresentativeCount")
    try:
        expected_representative_count = int(expected_representatives)
    except (TypeError, ValueError):
        expected_representative_count = -1
        errors.append({
            "code": "ADVERSARY_FEATURE_EQUIVALENCE_REPRESENTATIVE_COUNT_INVALID",
            "value": expected_representatives,
        })
    if expected_representative_count >= 0 and len(representatives) != expected_representative_count:
        errors.append({
            "code": "ADVERSARY_FEATURE_EQUIVALENCE_REPRESENTATIVE_COUNT_DRIFT",
            "expected": expected_representative_count,
            "actual": len(representatives),
        })
    if errors:
        return {}, errors

    representative_ids = [str(entity.get("semanticId") or "") for entity in representatives]
    selection = {
        "schema": PUBLICATION_SELECTION_SCHEMA,
        "status": "APPLIED",
        "canonicalSourceFeatureCount": len(features),
        "publicationRepresentativeCount": len(representatives),
        "excludedRedundantCount": len(excluded_semantic_ids),
        "approvedGroupCount": len(group_records),
        "representativeSemanticIds": representative_ids,
        "excludedSemanticIds": sorted(excluded_semantic_ids),
        "groups": sorted(group_records, key=lambda group: str(group.get("groupId") or "")),
    }
    return selection, []


def _postprocess_feature_publication_equivalence(
    repo_root: Path,
    outroot: Path,
    config: dict,
    report: dict,
    *,
    add_check,
) -> None:
    del config
    metadata_root = outroot / "source" / "metadata"
    sidecar_path = metadata_root / "structured-entities.json"
    validation_path = metadata_root / "validation.json"
    selection_path = metadata_root / "adversary-feature-publication-selection.json"
    decisions_path = repo_root / DECISIONS_REPO_PATH

    if not sidecar_path.is_file() or not decisions_path.is_file():
        details = {
            "sidecar": str(sidecar_path),
            "decisions": str(decisions_path),
        }
        add_check(
            report,
            "ADVERSARY_FEATURE_PUBLICATION_EQUIVALENCE",
            "ERROR",
            "Approved Adversary Feature publication equivalence could not run because required input is missing.",
            details,
        )
        _write_json(validation_path, report)
        return

    try:
        sidecar = _load_json(sidecar_path)
        decisions = _load_json(decisions_path)
    except Exception as exc:
        add_check(
            report,
            "ADVERSARY_FEATURE_PUBLICATION_EQUIVALENCE",
            "ERROR",
            f"Could not load Feature publication-equivalence inputs: {exc}",
        )
        _write_json(validation_path, report)
        return

    selection, errors = apply_feature_publication_equivalence(sidecar, decisions)
    encounter = sidecar.get("encounterSemantics") if isinstance(sidecar.get("encounterSemantics"), dict) else {}
    audit_summary = encounter.get("adversaryFeatureEquivalence") if isinstance(encounter.get("adversaryFeatureEquivalence"), dict) else {}

    if errors:
        audit_summary.update({
            "publicationStatus": "FAIL",
            "decisions": str(DECISIONS_REPO_PATH).replace("\\", "/"),
            "selection": "metadata/adversary-feature-publication-selection.json",
            "decisionErrorCount": len(errors),
        })
        encounter["adversaryFeatureEquivalence"] = audit_summary
        encounter["status"] = "FAIL"
        sidecar["encounterSemantics"] = encounter
        _write_json(sidecar_path, sidecar)
        add_check(
            report,
            "ADVERSARY_FEATURE_PUBLICATION_EQUIVALENCE",
            "ERROR",
            f"Approved Adversary Feature publication equivalence failed with {len(errors)} decision error(s).",
            errors,
        )
        _write_json(validation_path, report)
        return

    _write_json(selection_path, selection)
    audit_summary.update({
        "publicationSchema": PUBLICATION_EQUIVALENCE_SCHEMA,
        "publicationStatus": "APPLIED",
        "decisions": str(DECISIONS_REPO_PATH).replace("\\", "/"),
        "selection": "metadata/adversary-feature-publication-selection.json",
        "canonicalSourceFeatureCount": selection["canonicalSourceFeatureCount"],
        "publicationRepresentativeCount": selection["publicationRepresentativeCount"],
        "excludedRedundantCount": selection["excludedRedundantCount"],
        "approvedGroupCount": selection["approvedGroupCount"],
    })
    encounter["adversaryFeatureEquivalence"] = audit_summary
    sidecar["encounterSemantics"] = encounter
    _write_json(sidecar_path, sidecar)

    add_check(
        report,
        "ADVERSARY_FEATURE_PUBLICATION_EQUIVALENCE",
        "PASS",
        (
            "Approved Adversary Feature publication equivalence was applied without deleting canonical entities: "
            f"{selection['canonicalSourceFeatureCount']} canonical Features -> "
            f"{selection['publicationRepresentativeCount']} Chapter 32 representatives."
        ),
        {
            "selection": "metadata/adversary-feature-publication-selection.json",
            "canonicalSourceFeatureCount": selection["canonicalSourceFeatureCount"],
            "publicationRepresentativeCount": selection["publicationRepresentativeCount"],
            "excludedRedundantCount": selection["excludedRedundantCount"],
            "approvedGroupCount": selection["approvedGroupCount"],
        },
    )
    _write_json(validation_path, report)


def configure_step4_feature_publication_equivalence(namespace: dict[str, Any]) -> None:
    del namespace
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_feature_publication_equivalence_patch", False):
        return

    original_materialize = pipeline.materialize

    def materialize(
        repo_root: Path,
        outroot: Path,
        pub: dict,
        asm: dict,
        config: dict,
        base_report: dict | None = None,
    ) -> dict:
        report = original_materialize(repo_root, outroot, pub, asm, config, base_report)
        _postprocess_feature_publication_equivalence(
            repo_root,
            outroot,
            config,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._feature_publication_equivalence_patch = True
