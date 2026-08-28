from __future__ import annotations

import json
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


ICE_PUBLICATION_IMAGE_SCHEMA = "cybermancy-step4-ice-publication-images-v1.0"
_ASSET_KIND = "ice-publication-image"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def _source_document(repo_root: Path, entity: dict) -> tuple[dict | None, dict | None]:
    source_path = str(entity.get("sourcePath") or "")
    source = repo_root / source_path
    if not source_path or not source.is_file():
        return None, {
            "code": "ICE_PUBLICATION_IMAGE_SOURCE_MISSING",
            "semanticId": entity.get("semanticId"),
            "sourcePath": source_path,
        }
    try:
        document = _load_json(source)
    except Exception as exc:
        return None, {
            "code": "ICE_PUBLICATION_IMAGE_SOURCE_INVALID",
            "semanticId": entity.get("semanticId"),
            "sourcePath": source_path,
            "message": str(exc),
        }
    if not isinstance(document, dict):
        return None, {
            "code": "ICE_PUBLICATION_IMAGE_SOURCE_INVALID",
            "semanticId": entity.get("semanticId"),
            "sourcePath": source_path,
        }
    return document, None


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


def _postprocess_ice_images(
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
        add_check(report, "ICE_PUBLICATION_IMAGES", "ERROR", "Step 4 sidecar is missing; ICE publication images could not be staged.")
        _write_json(validation_path, report)
        return

    sidecar = _load_json(sidecar_path)
    entities = sidecar.get("entities") if isinstance(sidecar, dict) else None
    if not isinstance(entities, list):
        add_check(report, "ICE_PUBLICATION_IMAGES", "ERROR", "Step 4 sidecar has no entities array.")
        _write_json(validation_path, report)
        return

    ice_entities = sorted(
        [
            entity
            for entity in entities
            if isinstance(entity, dict)
            and entity.get("family") == "features"
            and isinstance(entity.get("publicationData"), dict)
            and entity["publicationData"].get("featureCategory") == "ice"
        ],
        key=lambda entity: str(entity.get("semanticId") or ""),
    )

    mappings = config.get("assets", {}).get("foundryRuntimeMappings", [])
    if not isinstance(mappings, list):
        mappings = []

    loaded_assets = _load_json(assets_path) if assets_path.is_file() else []
    asset_rows = loaded_assets if isinstance(loaded_assets, list) else []
    asset_rows = [
        row
        for row in asset_rows
        if not (isinstance(row, dict) and row.get("kind") == _ASSET_KIND)
    ]
    existing_sources = _existing_publication_sources(asset_rows)

    errors: list[dict[str, Any]] = []
    staged_rows: list[dict[str, Any]] = []
    staged_count = 0

    for entity in ice_entities:
        publication = entity["publicationData"]
        publication.pop("image", None)
        document, source_error = _source_document(repo_root, entity)
        if source_error:
            errors.append(source_error)
            continue
        assert document is not None

        raw_image = document.get("img")
        logical_rel, mapping_error = _mapped_logical_image(raw_image, mappings)
        if mapping_error or logical_rel is None:
            errors.append(
                {
                    "code": "ICE_PUBLICATION_IMAGE_REFERENCE_INVALID",
                    "semanticId": entity.get("semanticId"),
                    "name": entity.get("name"),
                    "sourceReference": raw_image,
                    "mappingStatus": mapping_error,
                }
            )
            continue

        # ICE artwork currently lives in the legacy player-facing publication
        # asset tree. Treat the art itself as shared visual source material while
        # the ICE entity remains GM-only. This stages a neutral Step 4 copy and
        # does not cause the Player Guide to publish ICE content.
        resolution = resolve_publication_source_asset(repo_root, logical_rel, "shared")
        if resolution.get("status") != "resolved":
            errors.append(
                {
                    "code": "ICE_PUBLICATION_IMAGE_MISSING",
                    "semanticId": entity.get("semanticId"),
                    "name": entity.get("name"),
                    "sourceReference": raw_image,
                    "logicalReference": logical_rel,
                    "resolution": resolution,
                }
            )
            continue

        source_repo_rel = str(resolution.get("sourceRepoPath") or "")
        publication_rel = publication_asset_path(logical_rel)
        conflicts = [
            source
            for source in existing_sources.get(publication_rel, [])
            if not _same_source_asset(repo_root, source, source_repo_rel)
        ]
        if conflicts:
            errors.append(
                {
                    "code": "ICE_PUBLICATION_IMAGE_COLLISION",
                    "semanticId": entity.get("semanticId"),
                    "publicationPath": publication_rel,
                    "sourceRepoPath": source_repo_rel,
                    "conflictingSources": sorted(set(conflicts)),
                }
            )
            continue

        try:
            staged = stage_publication_asset(
                repo_root,
                source_repo_rel,
                source_root,
                publication_rel,
            )
        except Exception as exc:
            errors.append(
                {
                    "code": "ICE_PUBLICATION_IMAGE_STAGING_FAILED",
                    "semanticId": entity.get("semanticId"),
                    "publicationPath": publication_rel,
                    "message": str(exc),
                }
            )
            continue

        staged_file = source_root / publication_rel
        if (
            staged.get("status") != "staged"
            or not staged_file.is_file()
            or staged.get("sha256") != sha256_file(staged_file)
        ):
            errors.append(
                {
                    "code": "ICE_PUBLICATION_IMAGE_STAGING_FAILED",
                    "semanticId": entity.get("semanticId"),
                    "publicationPath": publication_rel,
                }
            )
            continue

        publication["image"] = publication_rel
        staged_count += 1
        existing_sources.setdefault(publication_rel, []).append(source_repo_rel)
        staged_rows.append(
            {
                "kind": _ASSET_KIND,
                "sourceEntity": entity.get("semanticId"),
                "sourcePath": entity.get("sourcePath"),
                "sourceReference": raw_image,
                "reference": logical_rel,
                "sourceRepoPath": source_repo_rel,
                "audience": "gm",
                "publicationPath": publication_rel,
                "status": "staged",
                "sha256": staged.get("sha256"),
            }
        )

    asset_rows.extend(staged_rows)
    _write_json(assets_path, asset_rows)

    summary = {
        "schema": ICE_PUBLICATION_IMAGE_SCHEMA,
        "iceCount": len(ice_entities),
        "publicationImageCount": staged_count,
        "status": "FAIL" if errors else "PASS",
    }
    sidecar["icePublicationImageSemantics"] = summary
    _write_json(sidecar_path, sidecar)

    if errors:
        add_check(
            report,
            "ICE_PUBLICATION_IMAGES",
            "ERROR",
            f"ICE publication image validation found {len(errors)} blocking issue(s).",
            errors[:200],
        )
    else:
        add_check(
            report,
            "ICE_PUBLICATION_IMAGES",
            "PASS",
            f"Resolved and staged publication images for all {staged_count} ICE entities.",
            summary,
        )
    _write_json(validation_path, report)


def configure_step4_ice_publication_images(namespace: dict[str, Any]) -> None:
    """Promote canonical ICE icon references into staged Step 4 publication images."""
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_ice_publication_images_patch", False):
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
        _postprocess_ice_images(
            repo_root,
            outroot,
            config,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._ice_publication_images_patch = True
