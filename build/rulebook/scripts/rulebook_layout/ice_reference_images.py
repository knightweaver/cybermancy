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
    """Attach staged Step 4 ICE images, using a deterministic blank fallback.

    ICE artwork is decorative publication material rather than reader-facing rule
    semantics. Missing or invalid artwork may therefore fall back to a blank
    identity block when the package policy explicitly permits it. Runtime paths
    are still never passed through to Step 6.
    """
    if view is None:
        return

    policy = config.get("prototypePolicy") if isinstance(config.get("prototypePolicy"), dict) else {}
    composition = config.get("composition") if isinstance(config.get("composition"), dict) else {}
    require_images = bool(policy.get("requireStagedImages", False))
    require_summary = bool(policy.get("requirePublicationImageSemanticsPass", False))
    fallback_kind = str(composition.get("missingImageFallback") or "").strip()
    fallback_enabled = bool(policy.get("allowMissingImagesWithBlankFallback", False)) and fallback_kind == "blank-block"

    summary = sidecar.get("icePublicationImageSemantics")
    if not isinstance(summary, dict):
        summary = {}
    actual_schema = str(summary.get("schema") or "")
    actual_status = str(summary.get("status") or "")
    schema_ok = actual_schema == SUPPORTED_IMAGE_SCHEMA
    summary_ok = schema_ok and actual_status == "PASS"

    if not schema_ok:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGE_SEMANTICS",
            "ERROR",
            "Step 4 ICE publication image semantics are missing or use an unsupported schema.",
            {
                "actualSchema": actual_schema,
                "requiredSchema": SUPPORTED_IMAGE_SCHEMA,
                "actualStatus": actual_status,
            },
        )
    elif summary_ok:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGE_SEMANTICS",
            "PASS",
            "Step 4 ICE publication image semantics are available.",
            {
                "actualSchema": actual_schema,
                "actualStatus": actual_status,
            },
        )
    elif fallback_enabled and not require_summary:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGE_SEMANTICS",
            "WARNING",
            "Step 4 ICE publication image semantics are incomplete; missing artwork will use the approved blank-block fallback.",
            {
                "actualSchema": actual_schema,
                "actualStatus": actual_status,
                "fallback": fallback_kind,
            },
        )
    else:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGE_SEMANTICS",
            "ERROR",
            "Step 4 ICE publication image semantics are missing, stale, or failed.",
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
    fallback: list[dict[str, str]] = []
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
            reason = ""
            if image:
                pure = PurePosixPath(image)
                if pure.is_absolute() or ".." in pure.parts or image.startswith(("modules/", "worlds/", "docs/", "src/")):
                    reason = "non-publication-path"
                else:
                    entry["image"] = image
                    attached += 1
                    continue
            else:
                reason = "missing"

            detail = {"semanticId": semantic_id, "reason": reason}
            if image:
                detail["image"] = image
            if fallback_enabled:
                entry["imageFallback"] = fallback_kind
                fallback.append(detail)
            elif require_images:
                missing.append(detail)

    if missing:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGES",
            "ERROR",
            f"{len(missing)} selected ICE image(s) are missing or invalid.",
            missing,
        )
    elif fallback:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGES",
            "WARNING",
            f"Attached {attached} staged ICE image(s); {len(fallback)} selected ICE entry/entries will use a blank image block.",
            {"attached": attached, "fallback": fallback},
        )
    else:
        _add_check(
            report,
            "ICE_REFERENCE_IMAGES",
            "PASS",
            f"Attached staged publication images to {attached} selected ICE entries.",
            {"attached": attached},
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
