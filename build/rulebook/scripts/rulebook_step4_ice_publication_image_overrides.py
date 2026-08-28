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
    """
    import rulebook_step4_ice_publication_images as images

    if getattr(images, "_ice_publication_image_overrides_patch", False):
        return

    original_mapped_logical_image = images._mapped_logical_image

    def mapped_logical_image(raw_image: Any, mappings: list[dict]):
        # Preserve normal behavior here. Entity-specific override selection is
        # injected through a tiny helper consumed by the staging loop below.
        return original_mapped_logical_image(raw_image, mappings)

    original_source_document = images._source_document

    def source_document(repo_root, entity):
        document, error = original_source_document(repo_root, entity)
        if error is None and isinstance(document, dict):
            override = publication_image_override(entity.get("semanticId"))
            if override:
                # Add publication-only provenance without rewriting canonical img.
                document = dict(document)
                document["_publicationImageOverride"] = override
        return document, error

    original_mapper = images._mapped_logical_image

    def override_aware_mapper(raw_image: Any, mappings: list[dict]):
        # Kept as a normal mapping function; staging resolves the override marker
        # immediately before calling this function.
        return original_mapper(raw_image, mappings)

    images._source_document = source_document
    images._mapped_logical_image = override_aware_mapper
    images._ice_publication_image_overrides_patch = True
