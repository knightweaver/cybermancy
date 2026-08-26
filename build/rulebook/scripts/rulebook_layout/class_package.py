from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


SUPPORTED_SIDECAR_SCHEMA = "cybermancy-step4-structured-entities-v1.3"
VIEW_SCHEMA = "cybermancy-step6-class-package-view-v1.0"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def new_report() -> dict[str, Any]:
    return {"status": "PASS", "errors": [], "warnings": [], "checks": []}


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
    report["checks"].append(item)
    if status == "ERROR":
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status == "WARNING":
        report["warnings"].append(item)


def _index_entities(sidecar: dict[str, Any], report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = sidecar.get("entities")
    if not isinstance(rows, list):
        _add_check(report, "CLASS_PACKAGE_ENTITIES", "ERROR", "Step 4 sidecar has no entities array.")
        return {}
    index: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        semantic_id = str(row.get("semanticId") or "").strip()
        if not semantic_id:
            continue
        if semantic_id in index:
            duplicates.append(semantic_id)
        else:
            index[semantic_id] = row
    if duplicates:
        _add_check(
            report,
            "CLASS_PACKAGE_ENTITY_IDENTITY",
            "ERROR",
            "Step 4 sidecar contains duplicate semantic IDs.",
            sorted(set(duplicates)),
        )
    else:
        _add_check(
            report,
            "CLASS_PACKAGE_ENTITY_IDENTITY",
            "PASS",
            f"Indexed {len(index)} unique Step 4 semantic entities.",
        )
    return index


def _publication(entity: dict[str, Any]) -> dict[str, Any]:
    value = entity.get("publicationData")
    return value if isinstance(value, dict) else {}


def _entity_view(entity: dict[str, Any], *, include_description: bool = True) -> dict[str, Any]:
    publication = _publication(entity)
    result: dict[str, Any] = {
        "semanticId": entity.get("semanticId"),
        "family": entity.get("family"),
        "name": entity.get("name"),
    }
    if include_description:
        result["description"] = str(publication.get("description") or "").strip()
    image = str(publication.get("image") or "").strip()
    if image:
        result["image"] = image
    return result


def _resolve_entity(
    index: dict[str, dict[str, Any]],
    semantic_id: Any,
    report: dict[str, Any],
    *,
    owner: str,
    field: str,
    expected_family: str | None = None,
) -> dict[str, Any] | None:
    value = str(semantic_id or "").strip()
    if not value:
        _add_check(report, "CLASS_PACKAGE_REFERENCE", "ERROR", f"{owner}.{field} contains an empty semantic reference.")
        return None
    entity = index.get(value)
    if entity is None:
        _add_check(
            report,
            "CLASS_PACKAGE_REFERENCE",
            "ERROR",
            f"{owner}.{field} does not resolve in the Step 4 semantic corpus.",
            {"semanticId": value},
        )
        return None
    family = str(entity.get("family") or "")
    if expected_family and family != expected_family:
        _add_check(
            report,
            "CLASS_PACKAGE_REFERENCE_FAMILY",
            "ERROR",
            f"{owner}.{field} resolves to family {family!r}; expected {expected_family!r}.",
            {"semanticId": value},
        )
        return None
    return entity


def _safe_staged_image(
    entity: dict[str, Any],
    source_root: Path,
    report: dict[str, Any],
    *,
    owner: str,
) -> str:
    image = str(_publication(entity).get("image") or "").strip().replace("\\", "/")
    if not image:
        _add_check(report, "CLASS_PACKAGE_IMAGE", "ERROR", f"{owner} has no Step 4 publicationData.image.")
        return ""
    path = PurePosixPath(image)
    if path.is_absolute() or ".." in path.parts or not image.startswith("assets/"):
        _add_check(
            report,
            "CLASS_PACKAGE_IMAGE",
            "ERROR",
            f"{owner} image is not a normalized Step 4 assets/... path.",
            {"image": image},
        )
        return ""
    staged = source_root / Path(*path.parts)
    if not staged.is_file():
        _add_check(
            report,
            "CLASS_PACKAGE_IMAGE",
            "ERROR",
            f"{owner} Step 4 publication image is not staged.",
            {"image": image, "expectedPath": str(staged)},
        )
        return ""
    return image


def _feature_view(
    index: dict[str, dict[str, Any]],
    semantic_id: Any,
    report: dict[str, Any],
    *,
    owner: str,
    field: str,
    relationship: str,
) -> dict[str, Any] | None:
    entity = _resolve_entity(
        index,
        semantic_id,
        report,
        owner=owner,
        field=field,
        expected_family="features",
    )
    if entity is None:
        return None
    result = _entity_view(entity)
    result["relationship"] = relationship
    return result


def _simple_reference_view(
    index: dict[str, dict[str, Any]],
    semantic_id: Any,
    report: dict[str, Any],
    *,
    owner: str,
    field: str,
    expected_family: str | None = None,
) -> dict[str, Any] | None:
    entity = _resolve_entity(
        index,
        semantic_id,
        report,
        owner=owner,
        field=field,
        expected_family=expected_family,
    )
    return _entity_view(entity, include_description=False) if entity else None


def compose_class_package(
    sidecar: dict[str, Any],
    source_root: Path,
    class_semantic_id: str,
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Compose one reader-facing ClassPackage entirely from Step 4 semantics."""
    report = new_report()
    config = config or {}
    policy = config.get("prototypePolicy") if isinstance(config.get("prototypePolicy"), dict) else {}
    required_schema = str(policy.get("requireStructuredSidecarSchema") or SUPPORTED_SIDECAR_SCHEMA)

    actual_schema = str(sidecar.get("schema") or "")
    _add_check(
        report,
        "CLASS_PACKAGE_SIDECAR_SCHEMA",
        "PASS" if actual_schema == required_schema else "ERROR",
        f"Step 4 sidecar schema is {actual_schema or '<missing>'}.",
        {"required": required_schema},
    )

    image_semantics = sidecar.get("publicationImageSemantics")
    image_status = image_semantics.get("status") if isinstance(image_semantics, dict) else None
    require_image_pass = bool(policy.get("requirePublicationImageSemanticsPass", True))
    _add_check(
        report,
        "CLASS_PACKAGE_IMAGE_SEMANTICS",
        "PASS" if (not require_image_pass or image_status == "PASS") else "ERROR",
        "Step 4 publication-image semantics are available for ClassPackage composition."
        if image_status == "PASS"
        else "Step 4 publication-image semantics are not PASS.",
        image_semantics,
    )

    index = _index_entities(sidecar, report)
    class_entity = _resolve_entity(
        index,
        class_semantic_id,
        report,
        owner="prototype",
        field="classSemanticId",
        expected_family="classes",
    )
    if class_entity is None:
        return None, report

    class_pub = _publication(class_entity)
    class_owner = str(class_entity.get("name") or class_semantic_id)
    class_view = _entity_view(class_entity)
    class_view["image"] = _safe_staged_image(class_entity, source_root, report, owner=class_owner)
    class_view["domains"] = [str(v) for v in class_pub.get("domains", []) if str(v or "").strip()]
    class_view["hitPoints"] = class_pub.get("hitPoints")
    class_view["evasion"] = class_pub.get("evasion")

    class_features: dict[str, list[dict[str, Any]]] = {"hope": [], "class": []}
    raw_features = class_pub.get("features")
    if not isinstance(raw_features, list):
        _add_check(report, "CLASS_PACKAGE_CLASS_FEATURES", "ERROR", f"{class_owner} publicationData.features is not an array.")
        raw_features = []
    for idx, ref in enumerate(raw_features):
        if not isinstance(ref, dict):
            _add_check(report, "CLASS_PACKAGE_CLASS_FEATURES", "ERROR", f"{class_owner}.features[{idx}] is not an object.")
            continue
        relationship = str(ref.get("type") or "").strip().casefold()
        if relationship not in class_features:
            _add_check(
                report,
                "CLASS_PACKAGE_CLASS_FEATURE_TYPE",
                "ERROR",
                f"{class_owner}.features[{idx}] has unsupported relationship {relationship!r}.",
            )
            continue
        feature = _feature_view(
            index,
            ref.get("semanticId"),
            report,
            owner=class_owner,
            field=f"features[{idx}].semanticId",
            relationship=relationship,
        )
        if feature:
            class_features[relationship].append(feature)
    class_view["features"] = class_features

    class_items: list[dict[str, Any]] = []
    raw_class_items = class_pub.get("classItems", [])
    if isinstance(raw_class_items, list):
        for idx, semantic_id in enumerate(raw_class_items):
            resolved = _simple_reference_view(index, semantic_id, report, owner=class_owner, field=f"classItems[{idx}]")
            if resolved:
                class_items.append(resolved)
    class_view["classItems"] = class_items

    inventory_view: dict[str, list[dict[str, Any]]] = {}
    raw_inventory = class_pub.get("startingInventory")
    if isinstance(raw_inventory, dict):
        for key in ("take", "choiceA", "choiceB"):
            values = raw_inventory.get(key)
            if not isinstance(values, list):
                continue
            resolved_values: list[dict[str, Any]] = []
            for idx, semantic_id in enumerate(values):
                resolved = _simple_reference_view(
                    index,
                    semantic_id,
                    report,
                    owner=class_owner,
                    field=f"startingInventory.{key}[{idx}]",
                )
                if resolved:
                    resolved_values.append(resolved)
            if resolved_values:
                inventory_view[key] = resolved_values
    class_view["startingInventory"] = inventory_view

    guide_view: dict[str, Any] = {}
    raw_guide = class_pub.get("characterGuide")
    if isinstance(raw_guide, dict):
        traits = raw_guide.get("suggestedTraits")
        if isinstance(traits, dict):
            guide_view["suggestedTraits"] = dict(traits)
        for key, family in (
            ("suggestedPrimaryWeapon", "weapons"),
            ("suggestedSecondaryWeapon", "weapons"),
            ("suggestedArmor", "armors"),
        ):
            semantic_id = raw_guide.get(key)
            if semantic_id in (None, ""):
                guide_view[key] = None
                continue
            guide_view[key] = _simple_reference_view(
                index,
                semantic_id,
                report,
                owner=class_owner,
                field=f"characterGuide.{key}",
                expected_family=family,
            )
    class_view["characterGuide"] = guide_view

    for optional in ("backgroundQuestions", "connections"):
        values = class_pub.get(optional)
        if isinstance(values, list):
            clean = [str(v).strip() for v in values if str(v or "").strip()]
            if clean:
                class_view[optional] = clean

    subclasses: list[dict[str, Any]] = []
    raw_subclasses = class_pub.get("subclasses")
    if not isinstance(raw_subclasses, list):
        _add_check(report, "CLASS_PACKAGE_SUBCLASSES", "ERROR", f"{class_owner} publicationData.subclasses is not an array.")
        raw_subclasses = []
    seen_subclasses: set[str] = set()
    progression_order = (config.get("composition") or {}).get(
        "subclassProgressionOrder", ["foundation", "specialization", "mastery"]
    )
    if not isinstance(progression_order, list):
        progression_order = ["foundation", "specialization", "mastery"]

    for subclass_index, subclass_semantic_id in enumerate(raw_subclasses):
        subclass_entity = _resolve_entity(
            index,
            subclass_semantic_id,
            report,
            owner=class_owner,
            field=f"subclasses[{subclass_index}]",
            expected_family="subclasses",
        )
        if subclass_entity is None:
            continue
        sid = str(subclass_entity.get("semanticId") or "")
        if sid in seen_subclasses:
            _add_check(report, "CLASS_PACKAGE_SUBCLASS_DUPLICATE", "ERROR", f"{class_owner} contains duplicate subclass reference {sid}.")
            continue
        seen_subclasses.add(sid)
        subclass_pub = _publication(subclass_entity)
        subclass_name = str(subclass_entity.get("name") or sid)
        if subclass_pub.get("linkedClass") != class_semantic_id:
            _add_check(
                report,
                "CLASS_PACKAGE_SUBCLASS_PARENT",
                "ERROR",
                f"{subclass_name} linkedClass does not match {class_owner}.",
                {"linkedClass": subclass_pub.get("linkedClass"), "expected": class_semantic_id},
            )

        subclass_view = _entity_view(subclass_entity)
        subclass_view["image"] = _safe_staged_image(subclass_entity, source_root, report, owner=subclass_name)
        spellcasting_trait = str(subclass_pub.get("spellcastingTrait") or "").strip()
        if spellcasting_trait:
            subclass_view["spellcastingTrait"] = spellcasting_trait
        if not str(subclass_view.get("description") or "").strip():
            _add_check(
                report,
                "CLASS_PACKAGE_SUBCLASS_DESCRIPTION",
                "WARNING",
                f"{subclass_name} has no publication description; the prototype will omit the lead text.",
            )

        raw_progression = subclass_pub.get("progression")
        if not isinstance(raw_progression, dict):
            _add_check(report, "CLASS_PACKAGE_PROGRESSION", "ERROR", f"{subclass_name} publicationData.progression is not an object.")
            raw_progression = {}
        progression_view: dict[str, list[dict[str, Any]]] = {}
        for stage in progression_order:
            stage_name = str(stage)
            values = raw_progression.get(stage_name)
            if not isinstance(values, list):
                _add_check(
                    report,
                    "CLASS_PACKAGE_PROGRESSION",
                    "ERROR",
                    f"{subclass_name}.progression.{stage_name} is not an array.",
                )
                values = []
            stage_features: list[dict[str, Any]] = []
            for idx, semantic_id in enumerate(values):
                feature = _feature_view(
                    index,
                    semantic_id,
                    report,
                    owner=subclass_name,
                    field=f"progression.{stage_name}[{idx}]",
                    relationship=stage_name,
                )
                if feature:
                    stage_features.append(feature)
            progression_view[stage_name] = stage_features
        subclass_view["progression"] = progression_view
        subclasses.append(subclass_view)

    view: dict[str, Any] = {
        "schema": VIEW_SCHEMA,
        "chapter": int(config.get("chapter") or 12),
        "title": str(config.get("title") or "Classes and Subclasses"),
        "class": class_view,
        "subclasses": subclasses,
    }

    raw_view = json.dumps(view, ensure_ascii=False)
    leaked_tokens = [token for token in ("Compendium.", "modules/cybermancy/", "worlds/cybermancer/") if token in raw_view]
    _add_check(
        report,
        "CLASS_PACKAGE_NO_RAW_FOUNDRY_REFERENCES",
        "ERROR" if leaked_tokens else "PASS",
        "No raw Foundry UUID/runtime paths leaked into the Step 6 ClassPackage view."
        if not leaked_tokens
        else "Raw Foundry references leaked into the Step 6 ClassPackage view.",
        leaked_tokens or None,
    )

    _add_check(
        report,
        "CLASS_PACKAGE_COMPOSITION",
        "PASS" if report["status"] == "PASS" else "ERROR",
        f"Composed {class_owner} with {len(subclasses)} linked subclass(es) from Step 4 semantics."
        if report["status"] == "PASS"
        else f"{class_owner} ClassPackage composition contains blocking semantic errors.",
        {
            "classFeatures": sum(len(v) for v in class_features.values()),
            "subclasses": len(subclasses),
            "subclassFeatures": sum(
                len(features)
                for subclass in subclasses
                for features in subclass.get("progression", {}).values()
            ),
        },
    )
    return view, report


def latex_escape(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def _style(config: dict[str, Any]) -> dict[str, Any]:
    source = config.get("style") if isinstance(config.get("style"), dict) else {}
    return {
        "accent": source.get("accentColor", "0B6573"),
        "bright": source.get("accentBrightColor", "18A7B5"),
        "ink": source.get("inkColor", "183238"),
        "muted": source.get("mutedColor", "58747A"),
        "soft": source.get("softColor", "EAF4F5"),
        "subclass": source.get("subclassBandColor", "DDEEF0"),
        "margin": float(source.get("pageMarginIn", 0.55) or 0.55),
        "class_art": float(source.get("classArtWidthFraction", 0.43) or 0.43),
        "subclass_art": float(source.get("subclassArtWidthFraction", 0.34) or 0.34),
    }


def _tex_image_path(source_root: Path, output_dir: Path, publication_path: str) -> str:
    absolute = source_root / Path(*PurePosixPath(publication_path).parts)
    relative = os.path.relpath(absolute, output_dir).replace("\\", "/")
    return r"\detokenize{" + relative + "}"


def _feature_tex(feature: dict[str, Any]) -> str:
    name = latex_escape(feature.get("name"))
    description = latex_escape(feature.get("description"))
    lines = [
        r"\Needspace{0.8in}",
        rf"{{\fontsize{{10.5}}{{12}}\selectfont\bfseries\color{{CMInk}} {name}\par}}",
        r"{\color{CMBright}\rule{\linewidth}{0.45pt}}",
    ]
    if description:
        lines.append(rf"{{\fontsize{{8.8}}{{11}}\selectfont {description}\par}}")
    else:
        lines.append(r"{\fontsize{8.3}{10}\selectfont\itshape\color{CMMuted} No publication description supplied.\par}")
    lines.append(r"\vspace{2.2mm}")
    return "\n".join(lines)


def _reference_names(items: list[dict[str, Any]]) -> str:
    return ", ".join(latex_escape(item.get("name")) for item in items) or "—"


def _class_opening_tex(view: dict[str, Any], config: dict[str, Any], source_root: Path, output_dir: Path) -> str:
    style = _style(config)
    cls = view["class"]
    title = latex_escape(cls.get("name"))
    description = latex_escape(cls.get("description"))
    domains = " • ".join(latex_escape(str(v).upper()) for v in cls.get("domains", []))
    image = _tex_image_path(source_root, output_dir, str(cls.get("image") or ""))
    art_width = max(0.25, min(0.55, style["class_art"]))
    text_width = 0.96 - art_width

    pieces = [
        rf"{{\fontsize{{7.4}}{{8.4}}\selectfont\bfseries\color{{CMBright}} CHAPTER {int(view.get('chapter') or 12)} / {latex_escape(config.get('partLabel', 'CHARACTER OPTIONS'))}\par}}",
        r"\vspace{1.5mm}",
        rf"{{\fontsize{{31}}{{32}}\selectfont\bfseries\color{{CMInk}} {title.upper()}\par}}",
        r"\vspace{0.8mm}",
        rf"{{\fontsize{{9}}{{10}}\selectfont\bfseries\color{{CMAccent}} {domains}\par}}",
        r"\vspace{1.2mm}",
        r"{\color{CMBright}\rule{\linewidth}{0.8pt}}",
        r"\vspace{3mm}",
        rf"\begin{{minipage}}[t]{{{art_width:.3f}\linewidth}}",
        r"\centering",
        rf"\includegraphics[width=\linewidth,height=3.9in,keepaspectratio]{{{image}}}",
        r"\end{minipage}\hfill",
        rf"\begin{{minipage}}[t]{{{text_width:.3f}\linewidth}}",
        r"\vspace{0pt}",
        r"\begin{tabularx}{\linewidth}{>{\centering\arraybackslash}X >{\centering\arraybackslash}X}",
        r"\rowcolor{CMSoft}",
        rf"{{\fontsize{{8}}{{9}}\selectfont\bfseries\color{{CMMuted}} HIT POINTS}} & {{\fontsize{{8}}{{9}}\selectfont\bfseries\color{{CMMuted}} EVASION}} \\",
        rf"{{\fontsize{{21}}{{22}}\selectfont\bfseries\color{{CMInk}} {latex_escape(cls.get('hitPoints'))}}} & {{\fontsize{{21}}{{22}}\selectfont\bfseries\color{{CMInk}} {latex_escape(cls.get('evasion'))}}} \\",
        r"\end{tabularx}",
        r"\vspace{3mm}",
        rf"{{\fontsize{{9.2}}{{12}}\selectfont {description}\par}}",
        r"\end{minipage}",
        r"\vspace{4mm}",
    ]
    return "\n".join(pieces)


def _class_support_tex(cls: dict[str, Any]) -> str:
    pieces: list[str] = []
    features = cls.get("features") if isinstance(cls.get("features"), dict) else {}
    for key, label in (("hope", "Hope Feature"), ("class", "Class Features")):
        rows = features.get(key) if isinstance(features.get(key), list) else []
        if not rows:
            continue
        pieces.extend([
            r"\Needspace{1.0in}",
            rf"{{\fontsize{{15}}{{16}}\selectfont\bfseries\color{{CMAccent}} {label.upper()}\par}}",
            r"\vspace{1mm}",
        ])
        pieces.extend(_feature_tex(row) for row in rows)

    inventory = cls.get("startingInventory") if isinstance(cls.get("startingInventory"), dict) else {}
    guide = cls.get("characterGuide") if isinstance(cls.get("characterGuide"), dict) else {}
    class_items = cls.get("classItems") if isinstance(cls.get("classItems"), list) else []
    if inventory or guide or class_items:
        pieces.extend([
            r"\Needspace{1.35in}",
            r"{\fontsize{15}{16}\selectfont\bfseries\color{CMAccent} STARTING PACKAGE\par}",
            r"\vspace{1mm}",
            r"\begin{tabularx}{\linewidth}{>{\bfseries\color{CMMuted}}p{1.35in} X}",
        ])
        if class_items:
            pieces.append(rf"Class Items & {_reference_names(class_items)} \\")
        for key, label in (("take", "Take"), ("choiceA", "Choice A"), ("choiceB", "Choice B")):
            rows = inventory.get(key) if isinstance(inventory.get(key), list) else []
            if rows:
                pieces.append(rf"{label} & {_reference_names(rows)} \\")
        primary = guide.get("suggestedPrimaryWeapon")
        secondary = guide.get("suggestedSecondaryWeapon")
        armor = guide.get("suggestedArmor")
        if isinstance(primary, dict):
            pieces.append(rf"Suggested Weapon & {latex_escape(primary.get('name'))} \\")
        if isinstance(secondary, dict):
            pieces.append(rf"Secondary Weapon & {latex_escape(secondary.get('name'))} \\")
        if isinstance(armor, dict):
            pieces.append(rf"Suggested Armor & {latex_escape(armor.get('name'))} \\")
        traits = guide.get("suggestedTraits")
        if isinstance(traits, dict) and traits:
            trait_text = ", ".join(
                f"{latex_escape(str(name).title())} {latex_escape(value)}"
                for name, value in traits.items()
            )
            pieces.append(rf"Suggested Traits & {trait_text} \\")
        pieces.extend([r"\end{tabularx}", r"\vspace{2mm}"])

    for field, label in (("backgroundQuestions", "Background Questions"), ("connections", "Connections")):
        values = cls.get(field)
        if not isinstance(values, list) or not values:
            continue
        pieces.extend([
            rf"{{\fontsize{{13}}{{14}}\selectfont\bfseries\color{{CMAccent}} {label.upper()}\par}}",
            r"\begin{itemize}",
            *[rf"\item {latex_escape(value)}" for value in values],
            r"\end{itemize}",
        ])
    return "\n".join(pieces)


def _subclass_tex(
    subclass: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    style = _style(config)
    name = latex_escape(subclass.get("name"))
    description = latex_escape(subclass.get("description"))
    image = _tex_image_path(source_root, output_dir, str(subclass.get("image") or ""))
    art_width = max(0.22, min(0.48, style["subclass_art"]))
    text_width = 0.96 - art_width
    trait = str(subclass.get("spellcastingTrait") or "").strip()

    pieces = [
        r"\clearpage",
        r"{\fontsize{7.4}{8.4}\selectfont\bfseries\color{CMBright} SUBCLASS\par}",
        rf"{{\fontsize{{27}}{{28}}\selectfont\bfseries\color{{CMInk}} {name.upper()}\par}}",
        r"\vspace{0.7mm}",
        r"{\color{CMBright}\rule{\linewidth}{0.7pt}}",
        r"\vspace{3mm}",
        rf"\begin{{minipage}}[t]{{{art_width:.3f}\linewidth}}",
        r"\centering",
        rf"\includegraphics[width=\linewidth,height=3.1in,keepaspectratio]{{{image}}}",
        r"\end{minipage}\hfill",
        rf"\begin{{minipage}}[t]{{{text_width:.3f}\linewidth}}",
        r"\vspace{0pt}",
    ]
    if trait:
        pieces.extend([
            r"\colorbox{CMSubclass}{\parbox{0.92\linewidth}{\centering",
            rf"\bfseries\color{{CMInk}} SPELLCAST TRAIT: {latex_escape(trait.upper())}",
            r"}}",
            r"\vspace{2mm}",
        ])
    if description:
        pieces.append(rf"{{\fontsize{{9.2}}{{12}}\selectfont {description}\par}}")
    else:
        pieces.append(r"{\fontsize{8.5}{10}\selectfont\itshape\color{CMMuted} No subclass lead text is currently supplied by Step 4.\par}")
    pieces.extend([r"\end{minipage}", r"\vspace{4mm}"])

    progression = subclass.get("progression") if isinstance(subclass.get("progression"), dict) else {}
    for stage in (config.get("composition") or {}).get(
        "subclassProgressionOrder", ["foundation", "specialization", "mastery"]
    ):
        stage_name = str(stage)
        rows = progression.get(stage_name) if isinstance(progression.get(stage_name), list) else []
        pieces.extend([
            r"\Needspace{1.0in}",
            rf"{{\fontsize{{15}}{{16}}\selectfont\bfseries\color{{CMAccent}} {latex_escape(stage_name.upper())}\par}}",
            r"\vspace{1mm}",
        ])
        if rows:
            pieces.extend(_feature_tex(row) for row in rows)
        else:
            pieces.append(r"{\fontsize{8.5}{10}\selectfont\itshape\color{CMMuted} No features at this progression stage.\par}")
    return "\n".join(pieces)


def render_class_package_tex(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    output_dir: Path,
) -> str:
    """Render the D standalone ClassPackage design proof as LuaLaTeX."""
    style = _style(config)
    preamble = rf"""\documentclass[10pt]{{article}}
\usepackage[letterpaper,margin={style['margin']:g}in]{{geometry}}
\usepackage{{fontspec}}
\usepackage[table]{{xcolor}}
\usepackage{{graphicx}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{ragged2e}}
\usepackage{{microtype}}
\usepackage{{needspace}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{2.4mm}}
\IfFontExistsTF{{Roboto Condensed}}{{\setsansfont{{Roboto Condensed}}}}{{\setsansfont{{TeX Gyre Heros}}}}
\IfFontExistsTF{{Roboto}}{{\setmainfont{{Roboto}}}}{{\setmainfont{{TeX Gyre Heros}}}}
\definecolor{{CMAccent}}{{HTML}}{{{style['accent']}}}
\definecolor{{CMBright}}{{HTML}}{{{style['bright']}}}
\definecolor{{CMInk}}{{HTML}}{{{style['ink']}}}
\definecolor{{CMMuted}}{{HTML}}{{{style['muted']}}}
\definecolor{{CMSoft}}{{HTML}}{{{style['soft']}}}
\definecolor{{CMSubclass}}{{HTML}}{{{style['subclass']}}}
"""
    pieces = [preamble, r"\begin{document}", r"\sffamily", _class_opening_tex(view, config, source_root, output_dir)]
    pieces.append(_class_support_tex(view["class"]))
    for subclass in view.get("subclasses", []):
        pieces.append(_subclass_tex(subclass, config, source_root, output_dir))
    pieces.extend([r"\end{document}", ""])
    return "\n".join(pieces)
