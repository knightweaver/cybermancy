from __future__ import annotations

from typing import Any


# Wall of Static is the sole current ICE whose canonical Foundry image points to
# a third-party JB2A runtime asset rather than Cybermancy's own module path.
# A checked-in Cybermancy publication image already exists for this entity.
# Keep the exception explicit by stable semantic ID instead of guessing from the
# entity name or deriving a slug from generated documentation.
ICE_PUBLICATION_IMAGE_OVERRIDES = {
    "entity:features:DtCHCxPKWAwK89kq": "assets/icons/features/wall-of-static.webp",
}


def publication_image_override(semantic_id: Any) -> str | None:
    key = str(semantic_id or "").strip()
    return ICE_PUBLICATION_IMAGE_OVERRIDES.get(key)


def configure_step4_ice_publication_image_overrides(namespace: dict[str, Any]) -> None:
    """Install explicit publication-image exceptions before ICE image staging.

    The normal Step 4 path remains canonical Foundry ``img`` -> runtime mapping ->
    checked-in publication asset. This hook only handles individually approved
    exceptions where the Foundry runtime reference is third-party while a stable
    Cybermancy publication asset already exists in the repository.

    The canonical source document is never edited. The staging pass receives a
    shallow in-memory copy whose ``img`` value is replaced by the explicit logical
    publication path, after which the normal mapping/resolution/staging pipeline
    runs unchanged.
    """
    import rulebook_step4_ice_publication_images as images

    if getattr(images, "_ice_publication_image_overrides_patch", False):
        return

    original_source_document = images._source_document

    def source_document(repo_root, entity):
        document, error = original_source_document(repo_root, entity)
        if error is None and isinstance(document, dict):
            override = publication_image_override(entity.get("semanticId"))
            if override:
                document = dict(document)
                document["img"] = override
        return document, error

    images._source_document = source_document
    images._ice_publication_image_overrides_patch = True
