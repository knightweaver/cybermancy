from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rulebook_normalize.relationships import apply_class_relationship_semantics


RELATIONSHIP_SCHEMA = "cybermancy-step4-class-relationships-v1.0"
CLASS_FAMILIES = {"classes", "subclasses"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _foundry_uuid_leaks(value: Any, path: str = "publicationData") -> list[dict]:
    leaks: list[dict] = []
    if isinstance(value, dict):
        for key, child in value.items():
            leaks.extend(_foundry_uuid_leaks(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaks.extend(_foundry_uuid_leaks(child, f"{path}[{index}]"))
    elif isinstance(value, str) and value.startswith("Compendium."):
        leaks.append({"path": path, "value": value})
    return leaks


def _source_records(repo_root: Path, entities: list[dict]) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    errors: list[dict] = []
    for entity in entities:
        family = str(entity.get("family") or "")
        if family not in CLASS_FAMILIES:
            continue
        semantic_id = str(entity.get("semanticId") or "")
        source_path = str(entity.get("sourcePath") or "")
        path = repo_root / source_path
        if not source_path or not path.is_file():
            errors.append(
                {
                    "code": "RELATION_SOURCE_MISSING",
                    "ownerSemanticId": semantic_id,
                    "ownerFamily": family,
                    "ownerName": entity.get("name"),
                    "sourcePath": source_path,
                    "message": "Class/Subclass canonical source document is missing during Step 4 relationship resolution.",
                }
            )
            continue
        try:
            document = _load_json(path)
        except Exception as exc:
            errors.append(
                {
                    "code": "RELATION_SOURCE_INVALID",
                    "ownerSemanticId": semantic_id,
                    "ownerFamily": family,
                    "ownerName": entity.get("name"),
                    "sourcePath": source_path,
                    "message": f"Could not load Class/Subclass canonical source document: {exc}",
                }
            )
            continue
        if not isinstance(document, dict):
            errors.append(
                {
                    "code": "RELATION_SOURCE_INVALID",
                    "ownerSemanticId": semantic_id,
                    "ownerFamily": family,
                    "ownerName": entity.get("name"),
                    "sourcePath": source_path,
                    "message": "Class/Subclass canonical source document is not a JSON object.",
                }
            )
            continue
        records.append(
            {
                "semanticId": semantic_id,
                "family": family,
                "sourcePath": source_path,
                "document": document,
            }
        )
    return records, errors


def _postprocess_materialization(
    repo_root: Path,
    outroot: Path,
    report: dict,
    *,
    add_check,
) -> None:
    sidecar_path = outroot / "source" / "metadata" / "structured-entities.json"
    validation_path = outroot / "source" / "metadata" / "validation.json"
    if not sidecar_path.is_file():
        add_check(
            report,
            "CLASS_RELATIONSHIP_SEMANTICS",
            "ERROR",
            "Step 4 structured-entities sidecar is missing; Class relationship semantics could not be resolved.",
            {"path": str(sidecar_path)},
        )
        _write_json(validation_path, report)
        return

    try:
        sidecar = _load_json(sidecar_path)
    except Exception as exc:
        add_check(
            report,
            "CLASS_RELATIONSHIP_SEMANTICS",
            "ERROR",
            f"Could not load Step 4 structured-entities sidecar: {exc}",
        )
        _write_json(validation_path, report)
        return

    entities = sidecar.get("entities") if isinstance(sidecar, dict) else None
    if not isinstance(entities, list):
        add_check(
            report,
            "CLASS_RELATIONSHIP_SEMANTICS",
            "ERROR",
            "Step 4 structured-entities sidecar has no entities array.",
        )
        _write_json(validation_path, report)
        return

    records, source_errors = _source_records(repo_root, entities)
    result = apply_class_relationship_semantics(records, entities)
    errors = list(source_errors) + list(result.get("errors") or [])

    leaks: list[dict] = []
    for entity in entities:
        if entity.get("family") not in CLASS_FAMILIES:
            continue
        for leak in _foundry_uuid_leaks(entity.get("publicationData", {})):
            leaks.append(
                {
                    "ownerSemanticId": entity.get("semanticId"),
                    "ownerFamily": entity.get("family"),
                    "ownerName": entity.get("name"),
                    **leak,
                }
            )
    if leaks:
        errors.append(
            {
                "code": "RELATION_FOUNDRY_UUID_LEAK",
                "message": "Raw Foundry Compendium UUIDs remain in normalized Class/Subclass publication data.",
                "leaks": leaks,
            }
        )

    summary = {
        "schema": RELATIONSHIP_SCHEMA,
        "classCount": int(result.get("classCount") or 0),
        "subclassCount": int(result.get("subclassCount") or 0),
        "featureEdgeCount": int(result.get("featureEdgeCount") or 0),
        "featureTargetCount": int(result.get("featureTargetCount") or 0),
        "status": "FAIL" if errors else "PASS",
    }
    sidecar["relationshipSemantics"] = summary
    _write_json(sidecar_path, sidecar)

    if errors:
        add_check(
            report,
            "CLASS_RELATIONSHIP_SEMANTICS",
            "ERROR",
            f"Class → Subclass → Feature relationship validation found {len(errors)} blocking issue(s).",
            errors[:200],
        )
    else:
        add_check(
            report,
            "CLASS_RELATIONSHIP_SEMANTICS",
            "PASS",
            (
                f"Resolved {summary['classCount']} Classes, {summary['subclassCount']} Subclasses, "
                f"and {summary['featureEdgeCount']} Class/Subclass → Feature relationships to semantic IDs."
            ),
            summary,
        )
    _write_json(validation_path, report)


def configure_step4_class_relationships(namespace: dict[str, Any]) -> None:
    """Install the Step 4 relationship pass before deterministic materialization.

    The public Step 4 launcher imports the established normalization pipeline
    before its CLI wrapper can configure it. Patching the pipeline's materialize
    global here keeps both deterministic clean builds on the same code path,
    while leaving the mature materializer otherwise unchanged.
    """
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_class_relationship_semantics_patch", False):
        return

    original_materialize = pipeline.materialize
    original_source_sort_value = pipeline.source_sort_value

    def source_sort_value(
        family: str,
        doc: dict,
        source_rel: str,
        sort_spec: list[str],
    ):
        # Step 3's historical sorter looked for system.class/parentClass. The
        # canonical Cybermancy subclass relationship is system.linkedClass.
        if family == "subclasses" and "parent-class-or-source-folder" in sort_spec:
            system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
            linked_class = system.get("linkedClass")
            if linked_class and not system.get("class") and not system.get("parentClass"):
                shadow = dict(doc)
                shadow_system = dict(system)
                shadow_system["parentClass"] = linked_class
                shadow["system"] = shadow_system
                doc = shadow
        return original_source_sort_value(family, doc, source_rel, sort_spec)

    def materialize(
        repo_root: Path,
        outroot: Path,
        pub: dict,
        asm: dict,
        config: dict,
        base_report: dict | None = None,
    ) -> dict:
        report = original_materialize(repo_root, outroot, pub, asm, config, base_report)
        _postprocess_materialization(
            repo_root,
            outroot,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.source_sort_value = source_sort_value
    pipeline.materialize = materialize
    pipeline._class_relationship_semantics_patch = True
