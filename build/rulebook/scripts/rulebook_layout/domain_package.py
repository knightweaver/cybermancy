from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


SUPPORTED_SIDECAR_SCHEMA = "cybermancy-step4-structured-entities-v1.3"
SUPPORTED_DOMAIN_SEMANTICS_SCHEMA = "cybermancy-step4-domain-semantics-v1.0"
VIEW_SCHEMA = "cybermancy-step6-domain-package-view-v1.0"


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


def _publication(entity: dict[str, Any]) -> dict[str, Any]:
    value = entity.get("publicationData")
    return value if isinstance(value, dict) else {}


def _index_entities(sidecar: dict[str, Any], report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = sidecar.get("entities")
    if not isinstance(rows, list):
        _add_check(report, "DOMAIN_PACKAGE_ENTITIES", "ERROR", "Step 4 sidecar has no entities array.")
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
            "DOMAIN_PACKAGE_ENTITY_IDENTITY",
            "ERROR",
            "Step 4 sidecar contains duplicate semantic IDs.",
            sorted(set(duplicates)),
        )
    else:
        _add_check(
            report,
            "DOMAIN_PACKAGE_ENTITY_IDENTITY",
            "PASS",
            f"Indexed {len(index)} unique Step 4 semantic entities.",
        )
    return index


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
        _add_check(
            report,
            "DOMAIN_PACKAGE_REFERENCE",
            "ERROR",
            f"{owner}.{field} contains an empty semantic reference.",
        )
        return None

    entity = index.get(value)
    if entity is None:
        _add_check(
            report,
            "DOMAIN_PACKAGE_REFERENCE",
            "ERROR",
            f"{owner}.{field} does not resolve in the Step 4 semantic corpus.",
            {"semanticId": value},
        )
        return None

    family = str(entity.get("family") or "")
    if expected_family and family != expected_family:
        _add_check(
            report,
            "DOMAIN_PACKAGE_REFERENCE_FAMILY",
            "ERROR",
            f"{owner}.{field} resolves to family {family!r}; expected {expected_family!r}.",
            {"semanticId": value},
        )
        return None
    return entity


def _normalized_asset_path(
    publication_path: Any,
    source_root: Path,
    report: dict[str, Any],
    *,
    owner: str,
    field: str,
    required_suffixes: tuple[str, ...] | None = None,
) -> str:
    value = str(publication_path or "").strip().replace("\\", "/")
    if not value:
        _add_check(
            report,
            "DOMAIN_PACKAGE_ASSET",
            "ERROR",
            f"{owner}.{field} is missing from Step 4 staged publication assets.",
        )
        return ""

    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not value.startswith("assets/"):
        _add_check(
            report,
            "DOMAIN_PACKAGE_ASSET",
            "ERROR",
            f"{owner}.{field} is not a normalized Step 4 assets/... path.",
            {"path": value},
        )
        return ""

    if required_suffixes and pure.suffix.casefold() not in {suffix.casefold() for suffix in required_suffixes}:
        _add_check(
            report,
            "DOMAIN_PACKAGE_ASSET_TYPE",
            "ERROR",
            f"{owner}.{field} has unsupported publication asset type.",
            {"path": value, "requiredSuffixes": list(required_suffixes)},
        )
        return ""

    staged = source_root / Path(*pure.parts)
    if not staged.is_file():
        _add_check(
            report,
            "DOMAIN_PACKAGE_ASSET",
            "ERROR",
            f"{owner}.{field} Step 4 publication asset is not staged.",
            {"path": value, "expectedPath": str(staged)},
        )
        return ""
    return value


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("+-").isdigit():
            return int(text)
    return None


def _package_index(sidecar: dict[str, Any], report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = sidecar.get("domainPackages")
    if not isinstance(rows, list):
        _add_check(
            report,
            "DOMAIN_PACKAGE_PACKAGES",
            "ERROR",
            "Step 4 sidecar has no domainPackages array.",
        )
        return {}

    index: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("domainKey") or "").strip().casefold()
        if not key:
            continue
        if key in index:
            duplicates.append(key)
        else:
            index[key] = row

    if duplicates:
        _add_check(
            report,
            "DOMAIN_PACKAGE_IDENTITY",
            "ERROR",
            "Step 4 sidecar contains duplicate DomainPackage keys.",
            sorted(set(duplicates)),
        )
    else:
        _add_check(
            report,
            "DOMAIN_PACKAGE_IDENTITY",
            "PASS",
            f"Indexed {len(index)} unique Step 4 DomainPackages.",
        )
    return index


def _validate_package_membership(
    package: dict[str, Any],
    index: dict[str, dict[str, Any]],
    domain_key: str,
    report: dict[str, Any],
) -> tuple[list[str], dict[int, list[str]]]:
    owner = f"domainPackages[{domain_key}]"
    raw_cards = package.get("cards")
    if not isinstance(raw_cards, list):
        _add_check(
            report,
            "DOMAIN_PACKAGE_CARD_LIST",
            "ERROR",
            f"{owner}.cards is not an array.",
        )
        raw_cards = []

    cards = [str(value or "").strip() for value in raw_cards if str(value or "").strip()]
    if len(cards) != len(raw_cards):
        _add_check(
            report,
            "DOMAIN_PACKAGE_CARD_LIST",
            "ERROR",
            f"{owner}.cards contains empty or invalid semantic references.",
        )

    duplicates = sorted({sid for sid in cards if cards.count(sid) > 1})
    if duplicates:
        _add_check(
            report,
            "DOMAIN_PACKAGE_CARD_DUPLICATE",
            "ERROR",
            f"{owner}.cards contains duplicate card membership.",
            duplicates,
        )

    declared_count = _integer(package.get("cardCount"))
    if declared_count != len(cards):
        _add_check(
            report,
            "DOMAIN_PACKAGE_CARD_COUNT",
            "ERROR",
            f"{owner}.cardCount does not match the cards array.",
            {"declared": package.get("cardCount"), "actual": len(cards)},
        )

    raw_levels = package.get("levels")
    if not isinstance(raw_levels, list):
        _add_check(
            report,
            "DOMAIN_PACKAGE_LEVELS",
            "ERROR",
            f"{owner}.levels is not an array.",
        )
        raw_levels = []

    levels: dict[int, list[str]] = {}
    level_order: list[int] = []
    level_membership: list[str] = []
    duplicate_level_rows: list[int] = []

    for idx, row in enumerate(raw_levels):
        if not isinstance(row, dict):
            _add_check(
                report,
                "DOMAIN_PACKAGE_LEVELS",
                "ERROR",
                f"{owner}.levels[{idx}] is not an object.",
            )
            continue

        level = _integer(row.get("level"))
        if level is None or not 1 <= level <= 10:
            _add_check(
                report,
                "DOMAIN_PACKAGE_LEVEL_RANGE",
                "ERROR",
                f"{owner}.levels[{idx}].level must be an integer from 1 through 10.",
                {"level": row.get("level")},
            )
            continue

        if level in levels:
            duplicate_level_rows.append(level)
            continue

        values = row.get("cards")
        if not isinstance(values, list):
            _add_check(
                report,
                "DOMAIN_PACKAGE_LEVELS",
                "ERROR",
                f"{owner}.levels[{idx}].cards is not an array.",
            )
            values = []

        clean_values = [str(value or "").strip() for value in values if str(value or "").strip()]
        levels[level] = clean_values
        level_order.append(level)
        level_membership.extend(clean_values)

    if duplicate_level_rows:
        _add_check(
            report,
            "DOMAIN_PACKAGE_LEVEL_DUPLICATE",
            "ERROR",
            f"{owner}.levels contains duplicate level buckets.",
            sorted(set(duplicate_level_rows)),
        )

    if level_order != sorted(level_order):
        _add_check(
            report,
            "DOMAIN_PACKAGE_LEVEL_ORDER",
            "ERROR",
            f"{owner}.levels is not in ascending level order.",
            {"actual": level_order, "expected": sorted(level_order)},
        )

    level_duplicates = sorted({sid for sid in level_membership if level_membership.count(sid) > 1})
    if level_duplicates:
        _add_check(
            report,
            "DOMAIN_PACKAGE_LEVEL_CARD_DUPLICATE",
            "ERROR",
            f"{owner}.levels contains cards in more than one level bucket.",
            level_duplicates,
        )

    if level_membership != cards:
        if sorted(level_membership) != sorted(cards):
            _add_check(
                report,
                "DOMAIN_PACKAGE_LEVEL_MEMBERSHIP",
                "ERROR",
                f"{owner}.levels does not contain exactly the package card membership.",
                {"packageCards": cards, "levelCards": level_membership},
            )
        else:
            _add_check(
                report,
                "DOMAIN_PACKAGE_LEVEL_CARD_ORDER",
                "ERROR",
                f"{owner}.levels does not preserve the package card ordering.",
                {"packageCards": cards, "levelCards": level_membership},
            )

    sortable: list[tuple[int, str, str, str]] = []
    for sid in cards:
        entity = index.get(sid)
        if not isinstance(entity, dict):
            continue
        pdata = _publication(entity)
        level = _integer(pdata.get("level"))
        sortable.append(
            (
                level if level is not None else 999,
                str(entity.get("name") or "").casefold(),
                str(entity.get("sourceId") or ""),
                sid,
            )
        )
    expected_order = [row[-1] for row in sorted(sortable)]

    if cards and len(expected_order) == len(cards) and cards != expected_order:
        _add_check(
            report,
            "DOMAIN_PACKAGE_CARD_ORDER",
            "ERROR",
            f"{owner}.cards does not follow Step 4 level/name/source-ID ordering.",
            {"actual": cards, "expected": expected_order},
        )

    for level, semantic_ids in levels.items():
        for idx, sid in enumerate(semantic_ids):
            entity = _resolve_entity(
                index,
                sid,
                report,
                owner=owner,
                field=f"levels[{level}].cards[{idx}]",
                expected_family="domains",
            )
            if entity is None:
                continue
            intrinsic_level = _integer(_publication(entity).get("level"))
            if intrinsic_level != level:
                _add_check(
                    report,
                    "DOMAIN_PACKAGE_LEVEL_MISMATCH",
                    "ERROR",
                    f"{entity.get('name') or sid} is listed under Domain level {level} but Step 4 publicationData.level is {intrinsic_level}.",
                    {"semanticId": sid, "bucketLevel": level, "publicationLevel": intrinsic_level},
                )

    if not report["errors"]:
        _add_check(
            report,
            "DOMAIN_PACKAGE_MEMBERSHIP",
            "PASS",
            f"{owner} contains {len(cards)} unique cards with deterministic level membership and ordering.",
        )
    return cards, levels


def compose_domain_package(
    sidecar: dict[str, Any],
    source_root: Path,
    domain_key: str,
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Compose one reader-facing DomainPackage entirely from Step 4 semantics."""
    report = new_report()
    config = config or {}
    policy = config.get("prototypePolicy") if isinstance(config.get("prototypePolicy"), dict) else {}

    required_sidecar_schema = str(
        policy.get("requireStructuredSidecarSchema") or SUPPORTED_SIDECAR_SCHEMA
    )
    actual_sidecar_schema = str(sidecar.get("schema") or "")
    _add_check(
        report,
        "DOMAIN_PACKAGE_SIDECAR_SCHEMA",
        "PASS" if actual_sidecar_schema == required_sidecar_schema else "ERROR",
        f"Step 4 sidecar schema is {actual_sidecar_schema or '<missing>'}.",
        {"required": required_sidecar_schema},
    )

    semantics = sidecar.get("domainSemantics")
    required_semantics_schema = str(
        policy.get("requireDomainSemanticsSchema") or SUPPORTED_DOMAIN_SEMANTICS_SCHEMA
    )
    semantics_schema = str(semantics.get("schema") or "") if isinstance(semantics, dict) else ""
    semantics_status = str(semantics.get("status") or "") if isinstance(semantics, dict) else ""
    _add_check(
        report,
        "DOMAIN_PACKAGE_DOMAIN_SEMANTICS",
        "PASS"
        if semantics_schema == required_semantics_schema and semantics_status == "PASS"
        else "ERROR",
        "Step 4 Domain publication semantics are available for DomainPackage composition."
        if semantics_schema == required_semantics_schema and semantics_status == "PASS"
        else "Step 4 Domain publication semantics are missing, unsupported, or not PASS.",
        {
            "schema": semantics_schema or None,
            "status": semantics_status or None,
            "requiredSchema": required_semantics_schema,
        },
    )

    normalized_key = str(domain_key or "").strip().casefold()
    if not normalized_key:
        _add_check(
            report,
            "DOMAIN_PACKAGE_REQUEST",
            "ERROR",
            "No Domain key was supplied for DomainPackage composition.",
        )
        return None, report

    index = _index_entities(sidecar, report)
    package_index = _package_index(sidecar, report)
    package = package_index.get(normalized_key)
    if package is None:
        _add_check(
            report,
            "DOMAIN_PACKAGE_REQUEST",
            "ERROR",
            f"DomainPackage {normalized_key!r} does not exist in Step 4 domainPackages.",
            {"available": sorted(package_index)},
        )
        return None, report

    package_name = str(package.get("name") or normalized_key.title()).strip()
    owner = package_name or normalized_key

    artwork = package.get("artwork")
    if not isinstance(artwork, dict):
        _add_check(
            report,
            "DOMAIN_PACKAGE_ARTWORK",
            "ERROR",
            f"{owner} DomainPackage has no artwork object.",
        )
        artwork = {}

    identity_image = _normalized_asset_path(
        artwork.get("image"),
        source_root,
        report,
        owner=owner,
        field="artwork.image",
        required_suffixes=(".png", ".jpg", ".jpeg", ".webp"),
    )
    identity_mask = _normalized_asset_path(
        artwork.get("mask"),
        source_root,
        report,
        owner=owner,
        field="artwork.mask",
        required_suffixes=(".svg",),
    )

    cards, levels = _validate_package_membership(package, index, normalized_key, report)

    card_views: dict[str, dict[str, Any]] = {}
    require_description = bool(policy.get("requireCardDescription", True))
    for idx, semantic_id in enumerate(cards):
        entity = _resolve_entity(
            index,
            semantic_id,
            report,
            owner=owner,
            field=f"cards[{idx}]",
            expected_family="domains",
        )
        if entity is None:
            continue

        publication = _publication(entity)
        card_name = str(entity.get("name") or semantic_id)
        card_domain = str(publication.get("domainKey") or "").strip().casefold()
        if card_domain != normalized_key:
            _add_check(
                report,
                "DOMAIN_PACKAGE_CARD_DOMAIN",
                "ERROR",
                f"{card_name} belongs to Domain {card_domain!r}, not {normalized_key!r}.",
                {"semanticId": semantic_id},
            )

        level = _integer(publication.get("level"))
        if level is None or not 1 <= level <= 10:
            _add_check(
                report,
                "DOMAIN_PACKAGE_CARD_LEVEL",
                "ERROR",
                f"{card_name} has invalid Step 4 publicationData.level.",
                {"semanticId": semantic_id, "level": publication.get("level")},
            )

        recall_cost = _integer(publication.get("recallCost"))
        if recall_cost is None or recall_cost < 0:
            _add_check(
                report,
                "DOMAIN_PACKAGE_RECALL_COST",
                "ERROR",
                f"{card_name} has invalid Step 4 publicationData.recallCost.",
                {"semanticId": semantic_id, "recallCost": publication.get("recallCost")},
            )

        card_type = str(publication.get("cardType") or "").strip()
        if not card_type:
            _add_check(
                report,
                "DOMAIN_PACKAGE_CARD_TYPE",
                "ERROR",
                f"{card_name} has no Step 4 publicationData.cardType.",
                {"semanticId": semantic_id},
            )

        in_vault = publication.get("inVault")
        if not isinstance(in_vault, bool):
            _add_check(
                report,
                "DOMAIN_PACKAGE_IN_VAULT",
                "ERROR",
                f"{card_name} publicationData.inVault is not boolean.",
                {"semanticId": semantic_id, "inVault": in_vault},
            )

        description = str(publication.get("description") or "").strip()
        if require_description and not description:
            _add_check(
                report,
                "DOMAIN_PACKAGE_CARD_DESCRIPTION",
                "ERROR",
                f"{card_name} has no normalized publication description.",
                {"semanticId": semantic_id},
            )
        elif not description:
            _add_check(
                report,
                "DOMAIN_PACKAGE_CARD_DESCRIPTION",
                "WARNING",
                f"{card_name} has no normalized publication description.",
                {"semanticId": semantic_id},
            )

        image = _normalized_asset_path(
            publication.get("image"),
            source_root,
            report,
            owner=card_name,
            field="publicationData.image",
            required_suffixes=(".png", ".jpg", ".jpeg", ".webp"),
        )

        card_views[semantic_id] = {
            "semanticId": semantic_id,
            "name": card_name,
            "domainKey": card_domain,
            "level": level,
            "recallCost": recall_cost,
            "cardType": card_type,
            "inVault": in_vault if isinstance(in_vault, bool) else False,
            "description": description,
            "image": image,
        }

    level_views: list[dict[str, Any]] = []
    for level in sorted(levels):
        level_cards = [
            card_views[sid]
            for sid in levels[level]
            if sid in card_views
        ]
        level_views.append({"level": level, "cards": level_cards})

    view: dict[str, Any] = {
        "schema": VIEW_SCHEMA,
        "chapter": int(config.get("chapter") or 14),
        "title": str(config.get("title") or "Domains and Domain Cards"),
        "domain": {
            "key": normalized_key,
            "name": package_name,
            "artwork": {
                "image": identity_image,
                "mask": identity_mask,
            },
            "cardCount": len(cards),
        },
        "levels": level_views,
    }

    raw_view = json.dumps(view, ensure_ascii=False)
    leakage_tokens = (
        "Compendium.",
        "modules/",
        "modules\\",
        "worlds/",
        "worlds\\",
        "docs/",
        "docs\\",
        "src/packs/",
        "src\\packs\\",
        "!folders!",
    )
    leaked_tokens = [token for token in leakage_tokens if token in raw_view]
    _add_check(
        report,
        "DOMAIN_PACKAGE_NO_SOURCE_LEAKAGE",
        "ERROR" if leaked_tokens else "PASS",
        "No raw Foundry/source-tree references leaked into the Step 6 DomainPackage view."
        if not leaked_tokens
        else "Raw Foundry/source-tree references leaked into the Step 6 DomainPackage view.",
        leaked_tokens or None,
    )

    composed_count = sum(len(row["cards"]) for row in level_views)
    if composed_count != len(cards):
        _add_check(
            report,
            "DOMAIN_PACKAGE_VIEW_COUNT",
            "ERROR",
            f"{owner} view contains {composed_count} composed cards but the package declares {len(cards)}.",
        )

    _add_check(
        report,
        "DOMAIN_PACKAGE_COMPOSITION",
        "PASS" if report["status"] == "PASS" else "ERROR",
        f"Composed {owner} with {composed_count} Domain Cards across {len(level_views)} level group(s) from Step 4 semantics."
        if report["status"] == "PASS"
        else f"{owner} DomainPackage composition contains blocking semantic errors.",
        {
            "domainKey": normalized_key,
            "cardCount": composed_count,
            "levelCount": len(level_views),
        },
    )
    return view, report
