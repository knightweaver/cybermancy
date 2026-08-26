from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rulebook_normalize.assets import (
    is_remote_asset_reference,
    map_asset_reference,
    publication_asset_path,
    sha256_file,
    stage_publication_asset,
)


PUBLICATION_IMAGE_SCHEMA = "cybermancy-step4-class-publication-images-v1.0"
CLASS_FAMILIES = {"classes", "subclasses"}
_ASSET_KIND = "structured-publication-image"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _issue(entity: dict, code: str, message: str, **details: Any) -> dict:
    item = {
        "code": code,
        "ownerSemanticId": entity.get("semanticId"),
        "ownerFamily": entity.get("family"),
        "ownerName": entity.get("name"),
        "message": message,
    }
    if details:
        item.update(details)
    return item


def _source_document(repo_root: Path, entity: dict) -> tuple[dict | None, dict | None]:
    source_path = str(entity.get("sourcePath") or "")
    path = repo_root / source_path
    if not source_path or not path.is_file():
        return None, _issue(
            entity,
            "CLASS_PUBLICATION_IMAGE_SOURCE_MISSING",
            "Class/Subclass canonical source document is missing while resolving publication art.",
            sourcePath=source_path,
        )
    try:
        document = _load_json(path)
    except Exception as exc:
        return None, _issue(
            entity,
            "CLASS_PUBLICATION_IMAGE_SOURCE_INVALID",
            f"Could not load Class/Subclass canonical source document: {exc}",
            sourcePath=source_path,
        )
    if not isinstance(document, dict):
        return None, _issue(
            entity,
            "CLASS_PUBLICATION_IMAGE_SOURCE_INVALID",
            "Class/Subclass canonical source document is not a JSON object.",
            sourcePath=source_path,
        )
    return document, None


def _mapped_repo_image(raw_image: Any, mappings: list[dict]) -> tuple[str | None, str | None]:
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
        source = str(row.get("reference") or row.get("sourceRepoPath") or "")
        if publication_path and source:
            result.setdefault(publication_path, []).append(source)
    return result


def _postprocess_publication_images(
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
            "CLASS_PUBLICATION_IMAGES",
            "ERROR",
            "Step 4 structured-entities sidecar is missing; Class/Subclass publication art could not be resolved.",
            {"path": str(sidecar_path)},
        )
        _write_json(validation_path, report)
        return

    try:
        sidecar = _load_json(sidecar_path)
    except Exception as exc:
        add_check(
            report,
            "CLASS_PUBLICATION_IMAGES",
            "ERROR",
            f"Could not load Step 4 structured-entities sidecar: {exc}",
        )
        _write_json(validation_path, report)
        return

    entities = sidecar.get("entities") if isinstance(sidecar, dict) else None
    if not isinstance(entities, list):
        add_check(
            report,
            "CLASS_PUBLICATION_IMAGES",
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
            "CLASS_PUBLICATION_IMAGES",
            "ERROR",
            f"Could not load Step 4 publication asset metadata: {exc}",
        )
        _write_json(validation_path, report)
        return
    asset_rows = loaded_assets if isinstance(loaded_assets, list) else []
    asset_rows = [
        row for row in asset_rows
        if not (isinstance(row, dict) and row.get("kind") == _ASSET_KIND)
    ]
    existing_sources = _existing_publication_sources(asset_rows)

    mappings = config.get("assets", {}).get("foundryRuntimeMappings", [])
    if not isinstance(mappings, list):
        mappings = []

    class_entities = sorted(
        [e for e in entities if isinstance(e, dict) and e.get("family") in CLASS_FAMILIES],
        key=lambda e: (str(e.get("family") or ""), str(e.get("semanticId") or "")),
    )

    errors: list[dict] = []
    staged_rows: list[dict] = []
    staged_count = 0

    for entity in class_entities:
        publication_data = entity.get("publicationData")
        if not isinstance(publication_data, dict):
            publication_data = {}
            entity["publicationData"] = publication_data
        publication_data.pop("image", None)

        document, source_error = _source_document(repo_root, entity)
        if source_error is not None:
            errors.append(source_error)
            continue

        raw_image = document.get("img") if isinstance(document, dict) else None
        repo_rel, mapping_error = _mapped_repo_image(raw_image, mappings)
        if mapping_error is not None or repo_rel is None:
            if mapping_error == "missing":
                message = "Class/Subclass canonical source has no publication image reference."
            elif mapping_error == "remote":
                message = "Class/Subclass publication art must be a local repository asset so Step 4 can stage it deterministically."
            else:
                message = "Class/Subclass Foundry image reference did not map to a repository asset."
            errors.append(
                _issue(
                    entity,
                    "CLASS_PUBLICATION_IMAGE_REFERENCE_INVALID",
                    message,
                    sourceReference=raw_image,
                    mappingStatus=mapping_error,
                )
            )
            continue

        publication_rel = publication_asset_path(repo_rel)
        conflicts = [
            source for source in existing_sources.get(publication_rel, [])
            if not _same_source_asset(repo_root, source, repo_rel)
        ]
        if conflicts:
            errors.append(
                _issue(
                    entity,
                    "CLASS_PUBLICATION_IMAGE_COLLISION",
                    "Class/Subclass publication image collides with a different source asset at the same staged path.",
                    sourceReference=raw_image,
                    reference=repo_rel,
                    publicationPath=publication_rel,
                    conflictingSources=sorted(set(conflicts)),
                )
            )
            continue

        try:
            staged = stage_publication_asset(
                repo_root,
                repo_rel,
                source_root,
                publication_rel,
            )
        except Exception as exc:
            errors.append(
                _issue(
                    entity,
                    "CLASS_PUBLICATION_IMAGE_STAGING_FAILED",
                    f"Could not stage Class/Subclass publication image: {exc}",
                    sourceReference=raw_image,
                    reference=repo_rel,
                    publicationPath=publication_rel,
                )
            )
            continue

        if staged.get("status") != "staged":
            errors.append(
                _issue(
                    entity,
                    "CLASS_PUBLICATION_IMAGE_MISSING",
                    "Class/Subclass publication image does not exist at the mapped repository path.",
                    sourceReference=raw_image,
                    reference=repo_rel,
                    publicationPath=publication_rel,
                )
            )
            continue

        staged_file = source_root / publication_rel
        if not staged_file.is_file() or staged.get("sha256") != sha256_file(staged_file):
            errors.append(
                _issue(
                    entity,
                    "CLASS_PUBLICATION_IMAGE_STAGING_FAILED",
                    "Staged Class/Subclass publication image failed existence/hash validation.",
                    sourceReference=raw_image,
                    reference=repo_rel,
                    publicationPath=publication_rel,
                )
            )
            continue

        publication_data["image"] = publication_rel
        staged_count += 1
        existing_sources.setdefault(publication_rel, []).append(repo_rel)
        staged_rows.append(
            {
                "kind": _ASSET_KIND,
                "sourceEntity": entity.get("semanticId"),
                "sourcePath": entity.get("sourcePath"),
                "sourceReference": raw_image,
                "reference": repo_rel,
                "publicationPath": publication_rel,
                "sourceRepoPath": repo_rel,
                "status": "staged",
                "sha256": staged.get("sha256"),
            }
        )

    asset_rows.extend(staged_rows)
    _write_json(assets_path, asset_rows)

    summary = {
        "schema": PUBLICATION_IMAGE_SCHEMA,
        "families": sorted(CLASS_FAMILIES),
        "entityCount": len(class_entities),
        "publicationImageCount": staged_count,
        "status": "FAIL" if errors else "PASS",
    }
    sidecar["publicationImageSemantics"] = summary
    _write_json(sidecar_path, sidecar)

    if errors:
        add_check(
            report,
            "CLASS_PUBLICATION_IMAGES",
            "ERROR",
            f"Class/Subclass publication image validation found {len(errors)} blocking issue(s).",
            errors[:200],
        )
    else:
        add_check(
            report,
            "CLASS_PUBLICATION_IMAGES",
            "PASS",
            (
                f"Resolved and staged publication images for all {staged_count} "
                "Class/Subclass entities; sidecar image paths are Step 4 source-relative."
            ),
            summary,
        )
    _write_json(validation_path, report)


def configure_step4_class_publication_images(namespace: dict[str, Any]) -> None:
    """Install deterministic Class/Subclass publication-image promotion.

    Foundry ``img`` remains runtime provenance in the generic normalizer. For
    ClassPackage publication, this pass deliberately promotes only Class and
    Subclass identity art into ``publicationData.image`` using a normalized path
    below ``build/rulebook/source/assets``. The raw Foundry path is retained only
    in asset provenance metadata and never exposed to Step 6 as the publication
    image value.
    """
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_class_publication_images_patch", False):
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
        _postprocess_publication_images(
            repo_root,
            outroot,
            config,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._class_publication_images_patch = True
