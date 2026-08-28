from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any


SUPPORTED_IMAGE_SCHEMA = "cybermancy-step4-ice-publication-images-v1.0"


def _add_check(
    report: dict[str, Any],
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report.setdefault("checks", []).append(item)
    if status == "ERROR":
        report["status"] = "FAIL"
        report.setdefault("errors", []).append(item)
    elif status == "WARNING":
        report.setdefault("warnings", []).append(item)


def attach_ice_reference_images(
    view: dict[str, Any] | None,
    sidecar: dict[str, Any],
    config: dict[str, Any],
    report: dict[str, Any],
) -> None:
    """Attach staged Step 4 ICE publication images to an already composed H2 view.

    The semantic composer remains responsible for ICE selection/rules. This pass
    only reconciles each selected semantic ID to publicationData.image and copies
    the normalized staged path into the Step 6 view. No Foundry/runtime paths are
    consulted here.
    """
    if view is None:
        return

    policy = config.get("prototypePolicy") if isinstance(config.get("prototypePolicy"), dict) else {}
    # Canonical H2.2 explicitly enables both requirements. Defaults remain false
    # so older unit fixtures and alternate experimental configs do not silently
    # acquire a new publication-image dependency.
    require_images = bool(policy.get("requireStagedImages", False))
    require_summary = bool(policy.get("requirePublicationImageSemanticsPass", False))

    summary = sidecar.get("icePublicationImageSemantics")
    if not isinstance(summary, dict):
        summary = {}
    actual_schema = str(summary.get("schema") or "")
    actual_status = str(summary.get("status") or "")
    summary_ok = actual_schema == SUPPORTED_IMAGE_SCHEMA and actual_status == "PASS"
    if require_summary:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGE_SEMANTICS",
            "PASS" if summary_ok else "ERROR",
            (
                "Step 4 ICE publication image semantics are available."
                if summary_ok
                else "Step 4 ICE publication image semantics are missing, stale, or failed."
            ),
            {
                "actualSchema": actual_schema,
                "requiredSchema": SUPPORTED_IMAGE_SCHEMA,
                "actualStatus": actual_status,
                "requiredStatus": "PASS",
            },
        )

    entities = sidecar.get("entities")
    index: dict[str, dict[str, Any]] = {}
    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            semantic_id = str(entity.get("semanticId") or "").strip()
            if semantic_id:
                index[semantic_id] = entity

    missing: list[dict[str, str]] = []
    attached = 0
    for group in view.get("groups", []):
        if not isinstance(group, dict):
            continue
        for entry in group.get("entries", []):
            if not isinstance(entry, dict):
                continue
            semantic_id = str(entry.get("semanticId") or "").strip()
            entity = index.get(semantic_id)
            publication = entity.get("publicationData") if isinstance(entity, dict) else None
            image = str(publication.get("image") or "").strip() if isinstance(publication, dict) else ""
            image = image.replace("\\", "/")
            if image:
                pure = PurePosixPath(image)
                if pure.is_absolute() or ".." in pure.parts or image.startswith(("modules/", "worlds/", "docs/", "src/")):
                    missing.append({"semanticId": semantic_id, "reason": "non-publication-path", "image": image})
                    continue
                entry["image"] = image
                attached += 1
            elif require_images:
                missing.append({"semanticId": semantic_id, "reason": "missing"})

    _add_check(
        report,
        "ICE_REFERENCE_IMAGES",
        "ERROR" if missing else "PASS",
        (
            f"{len(missing)} selected ICE image(s) are missing or invalid."
            if missing
            else f"Attached staged publication images to {attached} selected ICE entries."
        ),
        missing or {"attached": attached},
    )


def ice_reference_publication_images(view: dict[str, Any] | None) -> list[str]:
    if view is None:
        return []
    images: list[str] = []
    for group in view.get("groups", []):
        if not isinstance(group, dict):
            continue
        for entry in group.get("entries", []):
            if not isinstance(entry, dict):
                continue
            image = str(entry.get("image") or "").strip().replace("\\", "/")
            if image:
                images.append(image)
    return images
