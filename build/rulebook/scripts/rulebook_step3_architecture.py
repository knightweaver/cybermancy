from __future__ import annotations

from typing import Any


CLASS_PACKAGE_CHAPTER_ID = "ch12-classes"
CLASS_PACKAGE_TITLE = "Classes and Subclasses"
RESERVED_CHAPTER_NUMBER = 13
ICE_REFERENCE_CHAPTER_ID = "ch29-ice-reference"
ICE_REFERENCE_TITLE = "ICE Reference"

# The accepted Step H correction removes the standalone all-Feature reference
# from the player section. The source Feature family remains normalized because
# ClassPackage consumes Class/Subclass Feature semantics, but only the ICE
# subset receives an independent rulebook placement.
CHAPTER_RENUMBERING = {
    "ch16-weapons": ("ch15-weapons", 15),
    "ch17-ammunition": ("ch16-ammunition", 16),
    "ch18-armor": ("ch17-armor", 17),
    "ch19-cybernetics": ("ch18-cybernetics", 18),
    "ch20-drones-devices": ("ch19-drones-devices", 19),
    "ch21-consumables": ("ch20-consumables", 20),
    "ch22-mods": ("ch21-mods", 21),
    "ch23-loot": ("ch22-loot", 22),
    "ch24-project-helios": ("ch23-project-helios", 23),
    "ch25-council": ("ch24-council", 24),
    "ch26-cabal": ("ch25-cabal", 25),
    "ch27-cabal-projects": ("ch26-cabal-projects", 26),
    "ch28-chessboard": ("ch27-chessboard", 27),
    "ch29-gm-resonance": ("ch28-gm-resonance", 28),
}


def _rename_placement(value: str) -> str:
    replacement = CHAPTER_RENUMBERING.get(value)
    return replacement[0] if replacement else value


def _renumber_chapter(chapter: dict[str, Any]) -> None:
    replacement = CHAPTER_RENUMBERING.get(str(chapter.get("id") or ""))
    if not replacement:
        return
    chapter["id"], chapter["number"] = replacement


def _configure_class_package(namespace: dict[str, Any]) -> None:
    structured = namespace["STRUCTURED_ARCHITECTURE"]
    structured["classes"]["placement"] = CLASS_PACKAGE_CHAPTER_ID
    structured["subclasses"]["placement"] = CLASS_PACKAGE_CHAPTER_ID

    part_three = next(
        part
        for part in namespace["BOOK_STRUCTURE"]
        if part.get("id") == "part-iii-characters"
    )
    chapters = list(part_three["chapters"])
    class_chapter = next(
        chapter for chapter in chapters if chapter.get("id") == CLASS_PACKAGE_CHAPTER_ID
    )

    class_chapter["title"] = CLASS_PACKAGE_TITLE
    class_chapter["contentRefs"] = ["family:classes", "family:subclasses"]
    class_chapter["composition"] = {
        "kind": "class-package",
        "primaryFamily": "classes",
        "nestedFamily": "subclasses",
        "relationshipResolutionStage": "Step 4",
        "renderRule":": "Resolve each Subclass to exactly one linked Class and render the full Subclass structure beneath that Class; do not create an independent Subclass reference chapter.",
    }
    class_chapter["assemblyNote"] = (
        "Classes and Subclasses form one publication unit. Chapter 13 is reserved "
        "and intentionally has no independent chapter node."
    )

    part_three["chapters"] = [
        chapter for chapter in chapters if chapter.get("id") != "ch13-subclasses"
    ]


def _configure_ice_reference(namespace: dict[str, Any]) -> None:
    structured = namespace["STRUCTURED_ARCHITECTURE"]
    authored = namespace["AUTHORED_ARCHITECTURE"]

    # Remove the original player-facing all-Feature chapter. Domains remain 14;
    # Chapter 13 remains reserved by ClassPackage.
    part_three = next(
        part
        for part in namespace["BOOK_STRUCTURE"]
        if part.get("id") == "part-iii-characters"
    )
    part_three["chapters"] = [
        chapter
        for chapter in part_three["chapters"]
        if chapter.get("id") != "ch15-feature-reference"
    ]

    # Renumber the accepted equipment and GM-world chapters down one slot.
    for part in namespace["BOOK_STRUCTURE"]:
        for chapter in part.get("chapters", []):
            _renumber_chapter(chapter)

    for architecture in structured.values():
        placement = architecture.get("placement")
        if isinstance(placement, str):
            architecture["placement"] = _rename_placement(placement)
    for architecture in authored.values():
        placement = architecture.get("placement")
        if isinstance(placement, str):
            architecture["placement"] = _rename_placement(placement)

    # The Feature family remains one canonical Step 2/Step 4 family, but its
    # independent publication placement is now the GM-only ICE subset.
    feature_architecture = structured["features"]
    feature_architecture["placement"] = ICE_REFERENCE_CHAPTER_ID
    feature_architecture["title"] = ICE_REFERENCE_TITLE
    feature_architecture["sort"] = ["name"]
    feature_architecture["publicationSelection"] = {
        "kind": "ice-feature-subset",
        "featureCategory": "ice",
        "iceTypes": ["sentry", "wall"],
        "selectionStage": "Step 4",
        "normalizeNonSelectedEntities": True,
        "standaloneAudience": "gm",
    }

    part_five = next(
        part
        for part in namespace["BOOK_STRUCTURE"]
        if part.get("id") == "part-v-gm-world"
    )
    part_five["openerPlacement"] = "after GM spoiler divider; before Chapter 23"

    part_six = next(
        part
        for part in namespace["BOOK_STRUCTURE"]
        if part.get("id") == "part-vi-gm-toolkit"
    )
    ice_chapter = {
        "id": ICE_REFERENCE_CHAPTER_ID,
        "number": 29,
        "title": ICE_REFERENCE_TITLE,
        "contentRefs": ["family:features"],
        "composition": {
            "kind": "ice-reference",
            "sourceFamily": "features",
            "publicationSubset": {
                "featureCategory": "ice",
                "iceTypes": ["sentry", "wall"],
            },
            "relationshipResolutionStage": "Step 4",
            "renderRule": (
                "Normalize the complete Feature family for dependent mechanics, but "
                "publish only normalized Sentry ICE and Wall ICE Features as the "
                "standalone Chapter 29 reference."
            ),
        },
    }
    part_six["chapters"] = [ice_chapter] + [
        chapter
        for chapter in part_six["chapters"]
        if chapter.get("id") != ICE_REFERENCE_CHAPTER_ID
    ]

    # Keep authored ordering deterministic after the GM-world renumbering.
    placement_order = namespace["PLACEMENT_ORDER"]
    for old_id, (new_id, new_number) in CHAPTER_RENUMBERING.items():
        if old_id in placement_order:
            placement_order[new_id] = new_number * 10
            placement_order.pop(old_id, None)
    placement_order["gm-front-matter"] = 225

    # Step 3's base builder copies only its original structured-family fields.
    # Preserve the approved publication-subset contract in the generated
    # assembly manifest without changing the Step 2 source-family identity.
    original_build_structured_families = namespace["build_structured_families"]

    def build_structured_families(pub: dict[str, Any]) -> list[dict[str, Any]]:
        records = original_build_structured_families(pub)
        for record in records:
            if record.get("familyId") != "features":
                continue
            record["materialization"] = "normalize-all-publish-selected-subset"
            record["recordFilter"] = (
                "Normalize all logical Feature entities required by dependent mechanics; "
                "the independent rulebook collection publishes only entities whose Step 4 "
                "publicationData.featureCategory is 'ice' and iceType is 'sentry' or 'wall'."
            )
            record["publicationSelection"] = dict(
                feature_architecture["publicationSelection"]
            )
        return records

    namespace["build_structured_families"] = build_structured_families


def configure_class_package_architecture(namespace: dict[str, Any]) -> None:
    """Apply the accepted Step 3 publication architecture corrections.

    This compatibility entry point retains the historical function name used by
    the public Step 3 launcher. It now applies both frozen ClassPackage v1
    composition and the approved Step H correction that replaces the former
    player-facing all-Feature chapter with a GM-only Chapter 29 ICE Reference.
    """
    _configure_class_package(namespace)
    _configure_ice_reference(namespace)
