from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from rulebook_normalize.assets import (
    is_remote_asset_reference,
    map_asset_reference,
    publication_asset_path,
    resolve_publication_source_asset,
    sha256_file,
    stage_publication_asset,
)


DOMAIN_SEMANTICS_SCHEMA = "cybermancy-step4-domain-semantics-v1.0"
DOMAIN_FAMILY = "domains"
DOMAIN_DEFINITIONS = {
    "bullet": {
        "name": "Bullet",
        "image": "assets/icons/domains/bullet.png",
        "mask": "assets/icons/domains/bullet.svg",
    },
    "circuit": {
        "name": "Circuit",
        "image": "assets/icons/domains/circuit.png",
        "mask": "assets/icons/domains/circuit.svg",
    },
    "maker": {
        "name": "Maker",
        "image": "assets/icons/domains/maker.png",
        "mask": "assets/icons/domains/maker.svg",
    },
}
_CARD_IMAGE_KIND = "structured-domain-card-image"
_DOMAIN_ART_KIND = "structured-domain-artwork"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _issue(entity: dict | None, code: str, message: str, **details: Any) -> dict:
    item = {
        "code": code,
        "message": message,
    }
    if isinstance(entity, dict):
        item.update(
            {
                "ownerSemanticId": entity.get("semanticId"),
                "ownerFamily": entity.get("family"),
                "ownerName": entity.get("name"),
            }
        )
    if details:
        item.update(details)
    return item


def _source_document(repo_root: Path, entity: dict) -> tuple[dict | None, dict | None]:
    source_path = str(entity.get("sourcePath") or "")
    path = repo_root / source_path
    if not source_path or not path.is_file():
        return None, _issue(
            entity,
            "DOMAIN_SOURCE_MISSING",
            "Domain Card canonical source document is missing during Step 4 Domain normalization.",
            sourcePath=source_path,
        )
    try:
        document = _load_json(path)
    except Exception as exc:
        return None, _issue(
            entity,
            "DOMAIN_SOURCE_INVALID",
            f"Could not load Domain Card canonical source document: {exc}",
            sourcePath=source_path,
        )
    if not isinstance(document, dict):
        return None, _issue(
            entity,
            "DOMAIN_SOURCE_INVALID",
            "Domain Card canonical source document is not a JSON object.",
            sourcePath=source_path,
        )
    return document, None


def _domain_key(value: Any) -> str:
    return str(value or "").strip().casefold()


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


def _mapped_logical_image(raw_image: Any, mappings: list[dict]) -> tuple[str | None, str | None]:
    if not isinstance(raw_image, str) or not raw_image.strip():
        return None, "missing"
    target = raw_image.strip().replace("\\", "/").lstrip("/")
    if is_remote_asset_reference(target):
        return None, "remote"
    mapped = map_asset_reference(target, mappings)
    if not isinstance(mapped, str) or not mapped.strip():
        return None, "unmapped"
    mapped = mapped.replace("\\", "/").lstrip("/")
    if mapped.startswith(("modules/", "worlds/")):
        return None, "unmapped-runtime-prefix"
    return mapped, None


def _same_source_asset(repo_root: Path, first: str, second: str) -> bool:
    if first == second:
        return True
    first_path = repo_root / first
    second_path = repo_root / second
    return (
        first_path.is_file()
        and second_path.is_file()
        and sha256_file(first_path) == sha256_file(second_path)
    )


def _existing_publication_sources(asset_rows: list[dict]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in asset_rows:
        if not isinstance(row, dict):
            continue
        publication_path = str(row.get("publicationPath") or "")
        source = str(row.get("sourceRepoPath") or row.get("reference") or "")
        if publication_path and source:
            result.setdefault(publication_path, []).append(source)
    return result


def _stage_asset(
    *,
    repo_root: Path,
    source_root: Path,
    source_repo_rel: str,
    logical_rel: str,
    publication_rel: str,
    kind: str,
    existing_sources: dict[str, list[str]],
    staged_rows: list[dict],
    errors: list[dict],
    entity: dict | None = None,
    source_reference: Any = None,
    extra_row: dict | None = None,
) -> bool:
    conflicts = [
        source
        for source in existing_sources.get(publication_rel, [])
        if not _same_source_asset(repo_root, source, source_repo_rel)
    ]
    if conflicts:
        errors.append(
            _issue(
                entity,
                "DOMAIN_PUBLICATION_ASSET_COLLISION",
                "Domain publication asset collides with a different source asset at the same staged path.",
                sourceReference=source_reference,
                logicalReference=logical_rel,
                sourceRepoPath=source_repo_rel,
                publicationPath=publication_rel,
                conflictingSources=sorted(set(conflicts)),
            )
        )
        return False

    try:
        staged = stage_publication_asset(
            repo_root,
            source_repo_rel,
            source_root,
            publication_rel,
        )
    except Exception as exc:
        errors.append(
            _issue(
                entity,
                "DOMAIN_PUBLICATION_ASSET_STAGING_FAILED",
                f"Could not stage Domain publication asset: {exc}",
                sourceReference=source_reference,
                logicalReference=logical_rel,
                sourceRepoPath=source_repo_rel,
                publicationPath=publication_rel,
            )
        )
        return False

    staged_file = source_root / publication_rel
    if (
        staged.get("status") != "staged"
        or not staged_file.is_file()
        or staged.get("sha256") != sha256_file(staged_file)
    ):
        errors.append(
            _issue(
                entity,
                "DOMAIN_PUBLICATION_ASSET_STAGING_FAILED",
                "Domain publication asset failed staging existence/hash validation.",
                sourceReference=source_reference,
                logicalReference=logical_rel,
                sourceRepoPath=source_repo_rel,
                publicationPath=publication_rel,
            )
        )
        return False

    existing_sources.setdefault(publication_rel, []).append(source_repo_rel)
    row = {
        "kind": kind,
        "reference": logical_rel,
        "sourceRepoPath": source_repo_rel,
        "publicationPath": publication_rel,
        "status": "staged",
        "sha256": staged.get("sha256"),
    }
    if source_reference not in (None, ""):
        row["sourceReference"] = source_reference
    if isinstance(entity, dict):
        row["sourceEntity"] = entity.get("semanticId")
        row["sourcePath"] = entity.get("sourcePath")
        row["audience"] = entity.get("audience")
    if extra_row:
        row.update(extra_row)
    staged_rows.append(row)
    return True


def _load_domain_folders(repo_root: Path, entities: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    source_dirs = {
        (repo_root / str(entity.get("sourcePath"))).parent
        for entity in entities
        if str(entity.get("sourcePath") or "")
    }
    if len(source_dirs) != 1:
        return {}, [
            {
                "code": "DOMAIN_FOLDER_CROSSCHECK_UNAVAILABLE",
                "message": "Domain Card sources do not resolve to one canonical source directory; Foundry folder cross-check was skipped.",
                "sourceDirectories": sorted(str(path) for path in source_dirs),
            }
        ]

    source_dir = next(iter(source_dirs))
    if not source_dir.is_dir():
        return {}, [
            {
                "code": "DOMAIN_FOLDER_CROSSCHECK_UNAVAILABLE",
                "message": "Canonical Domain source directory is missing; Foundry folder cross-check was skipped.",
                "sourceDirectory": str(source_dir),
            }
        ]

    folders: dict[str, dict] = {}
    warnings: list[dict] = []
    for path in sorted(source_dir.rglob("*.json")):
        try:
            document = _load_json(path)
        except Exception:
            continue
        if not isinstance(document, dict):
            continue
        if not str(document.get("_key") or "").startswith("!folders!"):
            continue
        folder_id = str(document.get("_id") or "").strip()
        if not folder_id:
            continue
        if folder_id in folders:
            warnings.append(
                {
                    "code": "DOMAIN_FOLDER_ID_DUPLICATE",
                    "message": "Duplicate Foundry Domain folder ID encountered during non-authoritative cross-check.",
                    "folderId": folder_id,
                }
            )
            continue
        folders[folder_id] = document
    return folders, warnings


def _folder_crosscheck(
    entity: dict,
    document: dict,
    domain_key: str,
    level: int,
    folders: dict[str, dict],
) -> list[dict]:
    warnings: list[dict] = []
    folder_id = str(document.get("folder") or "").strip()
    if not folder_id:
        return [
            _issue(
                entity,
                "DOMAIN_FOLDER_UNASSIGNED",
                "Domain Card has no Foundry display folder; intrinsic Domain/level remain authoritative.",
            )
        ]

    level_folder = folders.get(folder_id)
    if level_folder is None:
        return [
            _issue(
                entity,
                "DOMAIN_FOLDER_REFERENCE_UNRESOLVED",
                "Domain Card Foundry folder reference could not be resolved; intrinsic Domain/level remain authoritative.",
                folderId=folder_id,
            )
        ]

    folder_level = _integer(level_folder.get("name"))
    if folder_level != level:
        warnings.append(
            _issue(
                entity,
                "DOMAIN_FOLDER_LEVEL_MISMATCH",
                "Foundry display-folder level disagrees with intrinsic system.level; intrinsic level remains authoritative.",
                intrinsicLevel=level,
                folderLevel=level_folder.get("name"),
                folderId=folder_id,
            )
        )

    parent_id = str(level_folder.get("folder") or "").strip()
    domain_folder = folders.get(parent_id)
    if domain_folder is None:
        warnings.append(
            _issue(
                entity,
                "DOMAIN_FOLDER_PARENT_UNRESOLVED",
                "Foundry level folder has no resolvable Domain parent; intrinsic system.domain remains authoritative.",
                levelFolderId=folder_id,
                parentFolderId=parent_id,
            )
        )
        return warnings

    folder_domain = _domain_key(domain_folder.get("name"))
    if folder_domain != domain_key:
        warnings.append(
            _issue(
                entity,
                "DOMAIN_FOLDER_DOMAIN_MISMATCH",
                "Foundry display-folder Domain disagrees with intrinsic system.domain; intrinsic Domain remains authoritative.",
                intrinsicDomain=domain_key,
                folderDomain=domain_folder.get("name"),
                domainFolderId=parent_id,
            )
        )
    return warnings


def _postprocess_domain_semantics(
    repo_root: Path,
    outroot: Path,
    config: dict,
    report: dict,
    *,
    add_check,
) -> None:
    source_root = outroot / "source"
    metadata_root = source_root / "metadata"
    sidecar_path = metadata_root / "structured-entities.json"
    assets_path = metadata_root / "assets.json"
    validation_path = metadata_root / "validation.json"

    if not sidecar_path.is_file():
        add_check(
            report,
            "DOMAIN_PUBLICATION_SEMANTICS",
            "ERROR",
            "Step 4 structured-entities sidecar is missing; Domain publication semantics could not be resolved.",
            {"path": str(sidecar_path)},
        )
        _write_json(validation_path, report)
        return

    try:
        sidecar = _load_json(sidecar_path)
    except Exception as exc:
        add_check(
            report,
            "DOMAIN_PUBLICATION_SEMANTICS",
            "ERROR",
            f"Could not load Step 4 structured-entities sidecar: {exc}",
        )
        _write_json(validation_path, report)
        return

    entities = sidecar.get("entities") if isinstance(sidecar, dict) else None
    if not isinstance(entities, list):
        add_check(
            report,
            "DOMAIN_PUBLICATION_SEMANTICS",
            "ERROR",
            "Step 4 structured-entities sidecar has no entities array.",
        )
        _write_json(validation_path, report)
        return

    try:
        loaded_assets = _load_json(assets_path) if assets_path.is_file() else []
    except Exception as exc:
        add_check(
            report,
            "DOMAIN_PUBLICATION_SEMANTICS",
            "ERROR",
            f"Could not load Step 4 publication asset metadata: {exc}",
        )
        _write_json(validation_path, report)
        return

    asset_rows = loaded_assets if isinstance(loaded_assets, list) else []
    asset_rows = [
        row
        for row in asset_rows
        if not (
            isinstance(row, dict)
            and row.get("kind") in {_CARD_IMAGE_KIND, _DOMAIN_ART_KIND}
        )
    ]
    existing_sources = _existing_publication_sources(asset_rows)
    staged_rows: list[dict] = []
    errors: list[dict] = []
    folder_warnings: list[dict] = []

    mappings = config.get("assets", {}).get("foundryRuntimeMappings", [])
    if not isinstance(mappings, list):
        mappings = []

    domain_entities = sorted(
        [
            entity
            for entity in entities
            if isinstance(entity, dict) and entity.get("family") == DOMAIN_FAMILY
        ],
        key=lambda entity: str(entity.get("semanticId") or ""),
    )

    folders, folder_load_warnings = _load_domain_folders(repo_root, domain_entities)
    folder_warnings.extend(folder_load_warnings)

    grouped: dict[str, list[dict]] = defaultdict(list)
    documents: dict[str, dict] = {}

    for entity in domain_entities:
        publication_data = entity.get("publicationData")
        if not isinstance(publication_data, dict):
            publication_data = {}
            entity["publicationData"] = publication_data
        for key in ("domainKey", "level", "recallCost", "cardType", "inVault", "image"):
            publication_data.pop(key, None)

        document, source_error = _source_document(repo_root, entity)
        if source_error is not None:
            errors.append(source_error)
            continue
        documents[str(entity.get("semanticId") or "")] = document

        if str(document.get("type") or "") != "domainCard":
            errors.append(
                _issue(
                    entity,
                    "DOMAIN_CARD_TYPE_INVALID",
                    "Domain structured entity is not a canonical domainCard Item.",
                    sourceType=document.get("type"),
                )
            )
            continue

        system = document.get("system") if isinstance(document.get("system"), dict) else {}
        domain_key = _domain_key(system.get("domain"))
        if domain_key not in DOMAIN_DEFINITIONS:
            errors.append(
                _issue(
                    entity,
                    "DOMAIN_KEY_INVALID",
                    "Domain Card system.domain is missing or is not a registered Cybermancy Domain.",
                    domainKey=domain_key,
                    registeredDomains=sorted(DOMAIN_DEFINITIONS),
                )
            )
            continue

        level = _integer(system.get("level"))
        if level is None or not 1 <= level <= 10:
            errors.append(
                _issue(
                    entity,
                    "DOMAIN_LEVEL_INVALID",
                    "Domain Card system.level must be an integer from 1 through 10.",
                    level=system.get("level"),
                )
            )
            continue

        recall_cost = _integer(system.get("recallCost"))
        if recall_cost is None or recall_cost < 0:
            errors.append(
                _issue(
                    entity,
                    "DOMAIN_RECALL_COST_INVALID",
                    "Domain Card system.recallCost must be a non-negative integer.",
                    recallCost=system.get("recallCost"),
                )
            )
            continue

        card_type = str(system.get("type") or "").strip()
        if not card_type:
            errors.append(
                _issue(
                    entity,
                    "DOMAIN_CARD_CLASSIFICATION_MISSING",
                    "Domain Card system.type is required for normalized publication semantics.",
                )
            )
            continue

        publication_data["domainKey"] = domain_key
        publication_data["level"] = level
        publication_data["recallCost"] = recall_cost
        publication_data["cardType"] = card_type
        publication_data["inVault"] = bool(system.get("inVault", False))

        raw_image = document.get("img")
        logical_rel, mapping_error = _mapped_logical_image(raw_image, mappings)
        if mapping_error is not None or logical_rel is None:
            errors.append(
                _issue(
                    entity,
                    "DOMAIN_CARD_IMAGE_REFERENCE_INVALID",
                    "Domain Card image reference did not resolve to a local logical publication asset.",
                    sourceReference=raw_image,
                    mappingStatus=mapping_error,
                )
            )
        else:
            resolution = resolve_publication_source_asset(
                repo_root,
                logical_rel,
                str(entity.get("audience") or ""),
            )
            if resolution.get("status") != "resolved":
                errors.append(
                    _issue(
                        entity,
                        "DOMAIN_CARD_IMAGE_MISSING",
                        "Domain Card publication image could not be resolved deterministically.",
                        sourceReference=raw_image,
                        logicalReference=logical_rel,
                        resolution=resolution,
                    )
                )
            else:
                source_repo_rel = str(resolution.get("sourceRepoPath") or "")
                publication_rel = publication_asset_path(logical_rel)
                if _stage_asset(
                    repo_root=repo_root,
                    source_root=source_root,
                    source_repo_rel=source_repo_rel,
                    logical_rel=logical_rel,
                    publication_rel=publication_rel,
                    kind=_CARD_IMAGE_KIND,
                    existing_sources=existing_sources,
                    staged_rows=staged_rows,
                    errors=errors,
                    entity=entity,
                    source_reference=raw_image,
                ):
                    publication_data["image"] = publication_rel

        folder_warnings.extend(
            _folder_crosscheck(entity, document, domain_key, level, folders)
        )
        grouped[domain_key].append(entity)

    packages: list[dict] = []
    for domain_key in sorted(grouped, key=lambda key: DOMAIN_DEFINITIONS[key]["name"].casefold()):
        definition = DOMAIN_DEFINITIONS[domain_key]
        artwork: dict[str, str] = {}
        for role in ("image", "mask"):
            logical_rel = str(definition[role])
            source_repo_rel = logical_rel
            source_path = repo_root / source_repo_rel
            if not source_path.is_file():
                errors.append(
                    {
                        "code": "DOMAIN_IDENTITY_ARTWORK_MISSING",
                        "message": "Canonical Domain identity artwork is missing.",
                        "domainKey": domain_key,
                        "domainName": definition["name"],
                        "artworkRole": role,
                        "sourceRepoPath": source_repo_rel,
                    }
                )
                continue
            publication_rel = publication_asset_path(logical_rel)
            if _stage_asset(
                repo_root=repo_root,
                source_root=source_root,
                source_repo_rel=source_repo_rel,
                logical_rel=logical_rel,
                publication_rel=publication_rel,
                kind=_DOMAIN_ART_KIND,
                existing_sources=existing_sources,
                staged_rows=staged_rows,
                errors=errors,
                extra_row={
                    "domainKey": domain_key,
                    "domainName": definition["name"],
                    "artworkRole": role,
                },
            ):
                artwork[role] = publication_rel

        ordered_entities = sorted(
            grouped[domain_key],
            key=lambda entity: (
                int(entity.get("publicationData", {}).get("level", 999)),
                str(entity.get("name") or "").casefold(),
                str(entity.get("sourceId") or ""),
            ),
        )
        card_ids = [str(entity.get("semanticId") or "") for entity in ordered_entities]
        cards_by_level: dict[int, list[str]] = defaultdict(list)
        for entity in ordered_entities:
            pdata = entity.get("publicationData", {})
            cards_by_level[int(pdata["level"])].append(str(entity.get("semanticId") or ""))

        packages.append(
            {
                "domainKey": domain_key,
                "name": definition["name"],
                "artwork": artwork,
                "cardCount": len(card_ids),
                "cards": card_ids,
                "levels": [
                    {"level": level, "cards": cards_by_level[level]}
                    for level in sorted(cards_by_level)
                ],
            }
        )

    asset_rows.extend(staged_rows)
    _write_json(assets_path, asset_rows)

    summary = {
        "schema": DOMAIN_SEMANTICS_SCHEMA,
        "domainCount": len(packages),
        "cardCount": sum(package["cardCount"] for package in packages),
        "folderCrosscheckIssueCount": len(folder_warnings),
        "status": "FAIL" if errors else "PASS",
    }
    sidecar["domainSemantics"] = summary
    sidecar["domainPackages"] = packages
    _write_json(sidecar_path, sidecar)

    if errors:
        add_check(
            report,
            "DOMAIN_PUBLICATION_SEMANTICS",
            "ERROR",
            f"Domain publication normalization found {len(errors)} blocking issue(s).",
            errors[:200],
        )
    else:
        add_check(
            report,
            "DOMAIN_PUBLICATION_SEMANTICS",
            "PASS",
            (
                f"Normalized {summary['cardCount']} Domain Cards into {summary['domainCount']} "
                "derived DomainPackages with deterministic level/name ordering and staged publication art."
            ),
            summary,
        )

    if folder_warnings:
        add_check(
            report,
            "DOMAIN_FOLDER_CROSSCHECK",
            "WARNING",
            (
                f"Foundry display-folder cross-check found {len(folder_warnings)} issue(s); "
                "intrinsic system.domain and system.level remain authoritative."
            ),
            folder_warnings[:200],
        )
    else:
        add_check(
            report,
            "DOMAIN_FOLDER_CROSSCHECK",
            "PASS",
            "Foundry display folders agree with intrinsic Domain Card domain/level semantics.",
            {"checkedCardCount": summary["cardCount"]},
        )

    _write_json(validation_path, report)


def configure_step4_domain_semantics(namespace: dict[str, Any]) -> None:
    """Install explicit Domain/Domain Card publication semantics in Step 4.

    Canonical Domain Card mechanics come from intrinsic ``system.domain``,
    ``system.level``, ``system.recallCost`` and related Item fields. Foundry
    folders are display convenience only and are consulted solely as a
    non-authoritative validation cross-check. The three Domain identity artworks
    are staged from ``assets/icons/domains``; PNG is the normal publication image
    and SVG is retained as an optional clipping mask. Step 6 can therefore consume
    ``domainPackages`` and normalized card publicationData without reading Foundry
    JSON, folder structure, runtime asset paths, or repository source assets.
    """
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_domain_semantics_patch", False):
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
        _postprocess_domain_semantics(
            repo_root,
            outroot,
            config,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._domain_semantics_patch = True
