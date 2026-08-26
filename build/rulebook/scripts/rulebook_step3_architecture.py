from __future__ import annotations

from typing import Any


CLASS_PACKAGE_CHAPTER_ID = "ch12-classes"
CLASS_PACKAGE_TITLE = "Classes and Subclasses"
RESERVED_CHAPTER_NUMBER = 13


def configure_class_package_architecture(namespace: dict[str, Any]) -> None:
    """Apply the approved Step 3 Class/Subclass publication composition.

    Classes and Subclasses remain separate canonical structured families, but
    their primary publication placement is one Chapter 12 Class Package. Step 4
    is responsible for resolving the Class/Subclass relationship; Step 6 will
    render each Subclass beneath exactly one linked Class.

    Chapter 13 is intentionally left unassigned. Chapters 14-23 retain their
    accepted numbering so the frozen Equipment regression baseline is not
    renumbered merely because two character-option families share one chapter.
    """
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
        "renderRule": (
            "Resolve each Subclass to exactly one linked Class and render the full "
            "Subclass structure beneath that Class; do not create an independent "
            "Subclass reference chapter."
        ),
    }
    class_chapter["assemblyNote"] = (
        "Classes and Subclasses form one publication unit. Chapter 13 is reserved "
        "and intentionally has no independent chapter node so Chapters 14-23 retain "
        "their accepted numbering."
    )

    part_three["chapters"] = [
        chapter for chapter in chapters if chapter.get("id") != "ch13-subclasses"
    ]
