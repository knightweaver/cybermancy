from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rulebook_normalize.markdown import html_to_markdown


ICE_SEMANTICS_SCHEMA = "cybermancy-step4-ice-semantics-v1.0"
FEATURE_FAMILY = "features"
ICE_FOLDER_NAMES = {
    "Sentry ICE": "sentry",
    "Wall ICE": "wall",
}
EXPECTED_ICE_COUNTS = {
    "sentry": 6,
    "wall": 7,
}
EXPECTED_ICE_TOTAL = 13


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _markdown(value: Any) -> str:
    if value in (None, ""):
        return ""
    return html_to_markdown(str(value)).strip()


def _iter_action_values(node: Any):
    if isinstance(node, dict):
        for value in node.values():
            if isinstance(value, dict):
                yield value
    elif isinstance(node, list):
        for value in node:
            if isinstance(value, dict):
                yield value


def _semantic_action_score(action: dict) -> tuple[int, int, str]:
    """Prefer the richer canonical duplicate without depending on Foundry keys."""
    description = _markdown(action.get("description"))
    semantic_fields = 0
    for key in ("cost", "uses", "damage", "effects", "target", "range"):
        if _nonempty(action.get(key)):
            semantic_fields += 1
    return (
        len(description),
        semantic_fields,
        json.dumps(action, sort_keys=True, ensure_ascii=False),
    )


def _action_identity(action: dict) -> str:
    source_id = action.get("_id")
    if isinstance(source_id, str) and source_id:
        return f"id:{source_id}"
    return "semantic:" + json.dumps(
        {
            "name": action.get("name"),
            "type": action.get("type"),
            "actionType": action.get("actionType"),
            "description": _markdown(action.get("description")),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _normalize_costs(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record = {
            "key": item.get("key"),
            "value": item.get("value"),
            "scalable": bool(item.get("scalable", False)),
            "step": item.get("step"),
            "consumeOnSuccess": bool(item.get("consumeOnSuccess", False)),
        }
        record = {
            key: val
            for key, val in record.items()
            if _nonempty(val) or val is False
        }
        if record:
            out.append(record)
    return out


def _normalize_uses(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "value": value.get("value"),
        "max": value.get("max"),
        "recovery": value.get("recovery"),
        "consumeOnSuccess": bool(value.get("consumeOnSuccess", False)),
    }
    out = {
        key: val
        for key, val in out.items()
        if _nonempty(val) or val is False
    }
    return out or None


def _normalize_damage(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    parts = value.get("parts")
    if not isinstance(parts, list):
        return None
    normalized_parts: list[dict] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        raw_value = part.get("value") if isinstance(part.get("value"), dict) else {}
        custom = raw_value.get("custom") if isinstance(raw_value.get("custom"), dict) else {}
        damage_value = {
            "dice": raw_value.get("dice"),
            "bonus": raw_value.get("bonus"),
            "multiplier": raw_value.get("multiplier"),
            "flatMultiplier": raw_value.get("flatMultiplier"),
        }
        if custom.get("enabled") and _nonempty(custom.get("formula")):
            damage_value["customFormula"] = custom.get("formula")
        damage_value = {
            key: val for key, val in damage_value.items() if _nonempty(val)
        }

        record = {
            "applyTo": part.get("applyTo"),
            "types": (
                list(part.get("type") or [])
                if isinstance(part.get("type"), list)
                else part.get("type")
            ),
            "base": bool(part.get("base", False)),
            "resultBased": bool(part.get("resultBased", False)),
            "value": damage_value,
        }
        record = {
            key: val
            for key, val in record.items()
            if _nonempty(val)
            or (key in {"base", "resultBased"} and val is False)
        }
        if record:
            normalized_parts.append(record)
    if not normalized_parts:
        return None
    return {
        "includeBase": bool(value.get("includeBase", False)),
        "parts": normalized_parts,
    }


def normalize_actions(system: dict) -> list[dict]:
    """Project Foundry actions into reader/mechanical semantics and deduplicate aliases."""
    candidates: dict[str, dict] = {}
    for action in _iter_action_values(system.get("actions")):
        identity = _action_identity(action)
        incumbent = candidates.get(identity)
        if incumbent is None or _semantic_action_score(action) > _semantic_action_score(incumbent):
            candidates[identity] = action

    out: list[dict] = []
    for identity, action in sorted(
        candidates.items(),
        key=lambda pair: (
            str(pair[1].get("name") or "").casefold(),
            str(pair[1].get("type") or "").casefold(),
            pair[0],
        ),
    ):
        record: dict[str, Any] = {}
        if identity.startswith("id:"):
            record["sourceId"] = identity[3:]
        if _nonempty(action.get("name")):
            record["name"] = str(action.get("name"))
        if _nonempty(action.get("type")):
            record["type"] = str(action.get("type"))
        if _nonempty(action.get("actionType")):
            record["actionType"] = str(action.get("actionType"))
        rules_markdown = _markdown(action.get("description"))
        if rules_markdown:
            record["rulesMarkdown"] = rules_markdown
        costs = _normalize_costs(action.get("cost"))
        if costs:
            record["cost"] = costs
        uses = _normalize_uses(action.get("uses"))
        if uses:
            record["uses"] = uses
        if _nonempty(action.get("range")):
            record["range"] = action.get("range")
        target = action.get("target") if isinstance(action.get("target"), dict) else {}
        target_out = {
            key: target.get(key)
            for key in ("type", "amount")
            if _nonempty(target.get(key))
        }
        if target_out:
            record["target"] = target_out
        damage = _normalize_damage(action.get("damage"))
        if damage:
            record["damage"] = damage
        if record:
            out.append(record)
    return out


def normalize_resource(system: dict) -> dict | None:
    resource = system.get("resource")
    if not isinstance(resource, dict):
        return None
    out = {
        key: resource.get(key)
        for key in ("type", "value", "max")
        if _nonempty(resource.get(key))
    }
    return out or None


def _has_meaningful_action(action: dict) -> bool:
    return bool(
        action.get("rulesMarkdown")
        or action.get("damage")
        or action.get("cost")
        or action.get("range")
        or action.get("target")
    )


def has_reader_rules(publication_data: dict) -> bool:
    if str(publication_data.get("rulesMarkdown") or "").strip():
        return True
    return any(
        _has_meaningful_action(action)
        for action in publication_data.get("actions", [])
        if isinstance(action, dict)
    )


def resolve_ice_folders(feature_root: Path) -> tuple[dict[str, str], list[dict]]:
    """Resolve ICE types through canonical Foundry folder records.

    Entity names never determine membership. The two accepted ICE folders must
    exist exactly once and share the canonical Device Features parent.
    """
    folder_records: dict[str, list[dict]] = {}
    for path in sorted(feature_root.glob("*.json")):
        try:
            doc = _load_json(path)
        except Exception:
            continue
        key = doc.get("_key") if isinstance(doc, dict) else None
        if not isinstance(key, str) or "!folders!" not in key:
            continue
        name = doc.get("name")
        if isinstance(name, str):
            folder_records.setdefault(name, []).append(doc)

    errors: list[dict] = []
    device_matches = folder_records.get("Device Features", [])
    device_folder_id: str | None = None
    if len(device_matches) != 1:
        errors.append(
            {
                "code": "ICE_PARENT_FOLDER_RESOLUTION",
                "folderName": "Device Features",
                "matchCount": len(device_matches),
                "message": "Expected exactly one canonical Device Features folder record.",
            }
        )
    else:
        raw_id = device_matches[0].get("_id")
        if isinstance(raw_id, str) and raw_id:
            device_folder_id = raw_id
        else:
            errors.append(
                {
                    "code": "ICE_PARENT_FOLDER_ID_MISSING",
                    "folderName": "Device Features",
                }
            )

    resolved: dict[str, str] = {}
    for folder_name, ice_type in ICE_FOLDER_NAMES.items():
        matches = folder_records.get(folder_name, [])
        if len(matches) != 1:
            errors.append(
                {
                    "code": "ICE_FOLDER_RESOLUTION",
                    "folderName": folder_name,
                    "matchCount": len(matches),
                    "message": "Expected exactly one canonical ICE folder record.",
                }
            )
            continue
        doc = matches[0]
        folder_id = doc.get("_id")
        if not isinstance(folder_id, str) or not folder_id:
            errors.append(
                {
                    "code": "ICE_FOLDER_ID_MISSING",
                    "folderName": folder_name,
                    "message": "Canonical ICE folder record has no stable _id.",
                }
            )
            continue
        if device_folder_id is not None and doc.get("folder") != device_folder_id:
            errors.append(
                {
                    "code": "ICE_FOLDER_PARENT_MISMATCH",
                    "folderName": folder_name,
                    "expectedParent": device_folder_id,
                    "actualParent": doc.get("folder"),
                    "message": "ICE folder is not a direct child of Device Features.",
                }
            )
            continue
        resolved[folder_id] = ice_type
    return resolved, errors


def classify_ice_document(doc: dict, folder_types: dict[str, str]) -> str | None:
    folder_id = doc.get("folder")
    return folder_types.get(folder_id) if isinstance(folder_id, str) else None


def ice_publication_data(doc: dict, ice_type: str) -> dict:
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    rules_markdown = _markdown(system.get("description"))
    out: dict[str, Any] = {
        "featureCategory": "ice",
        "iceType": ice_type,
        "standalonePublication": True,
    }
    if rules_markdown:
        out["rulesMarkdown"] = rules_markdown
    actions = normalize_actions(system)
    if actions:
        out["actions"] = actions
    resource = normalize_resource(system)
    if resource:
        out["resource"] = resource
    return out


def _feature_source_document(
    repo_root: Path,
    entity: dict,
) -> tuple[dict | None, dict | None]:
    source_path = entity.get("sourcePath")
    if not isinstance(source_path, str) or not source_path:
        return None, {
            "code": "ICE_SOURCE_PATH_MISSING",
            "semanticId": entity.get("semanticId"),
        }
    path = repo_root / source_path
    if not path.is_file():
        return None, {
            "code": "ICE_SOURCE_MISSING",
            "semanticId": entity.get("semanticId"),
            "sourcePath": source_path,
        }
    try:
        doc = _load_json(path)
    except Exception as exc:
        return None, {
            "code": "ICE_SOURCE_INVALID",
            "semanticId": entity.get("semanticId"),
            "sourcePath": source_path,
            "message": str(exc),
        }
    if not isinstance(doc, dict):
        return None, {
            "code": "ICE_SOURCE_INVALID",
            "semanticId": entity.get("semanticId"),
            "sourcePath": source_path,
            "message": "Canonical Feature source is not a JSON object.",
        }
    return doc, None


def _postprocess_materialization(
    repo_root: Path,
    outroot: Path,
    report: dict,
    *,
    add_check,
) -> None:
    sidecar_path = outroot / "source" / "metadata" / "structured-entities.json"
    validation_path = outroot / "source" / "metadata" / "validation.json"
    feature_root = repo_root / "src" / "packs" / "system" / "features"

    folder_types, errors = resolve_ice_folders(feature_root)
    if not sidecar_path.is_file():
        errors.append(
            {
                "code": "ICE_SIDECAR_MISSING",
                "message": "Step 4 structured-entities sidecar is missing.",
            }
        )
        add_check(
            report,
            "ICE_SEMANTICS",
            "ERROR",
            "ICE semantic enrichment could not run.",
            errors,
        )
        _write_json(validation_path, report)
        return

    sidecar = _load_json(sidecar_path)
    entities = sidecar.get("entities") if isinstance(sidecar, dict) else None
    if not isinstance(entities, list):
        errors.append(
            {
                "code": "ICE_SIDECAR_INVALID",
                "message": "structured-entities.json has no entities array.",
            }
        )
        add_check(
            report,
            "ICE_SEMANTICS",
            "ERROR",
            "ICE sidecar is invalid.",
            errors,
        )
        _write_json(validation_path, report)
        return

    counts = {"sentry": 0, "wall": 0}
    ice_ids: list[str] = []
    for entity in entities:
        if entity.get("family") != FEATURE_FAMILY:
            continue
        doc, source_error = _feature_source_document(repo_root, entity)
        if source_error:
            errors.append(source_error)
            continue
        assert doc is not None
        ice_type = classify_ice_document(doc, folder_types)
        if ice_type is None:
            # The family collection is GM-only, but ClassPackage still consumes
            # non-ICE Feature semantics. Preserve those entity semantics as
            # player-safe rather than reclassifying them as GM material.
            entity["audience"] = "player"
            continue

        counts[ice_type] = counts.get(ice_type, 0) + 1
        ice_ids.append(str(entity.get("semanticId") or ""))
        publication_data = entity.setdefault("publicationData", {})
        publication_data.update(ice_publication_data(doc, ice_type))
        entity["audience"] = "gm"
        if not has_reader_rules(publication_data):
            errors.append(
                {
                    "code": "ICE_RULES_EMPTY",
                    "semanticId": entity.get("semanticId"),
                    "name": entity.get("name"),
                    "iceType": ice_type,
                    "sourcePath": entity.get("sourcePath"),
                    "message": (
                        "ICE has neither reader-facing rules text nor a meaningful "
                        "normalized action."
                    ),
                }
            )

    for ice_type, expected in EXPECTED_ICE_COUNTS.items():
        actual = counts.get(ice_type, 0)
        if actual != expected:
            errors.append(
                {
                    "code": "ICE_COUNT_MISMATCH",
                    "iceType": ice_type,
                    "expected": expected,
                    "actual": actual,
                }
            )
    total = sum(counts.values())
    if total != EXPECTED_ICE_TOTAL:
        errors.append(
            {
                "code": "ICE_TOTAL_MISMATCH",
                "expected": EXPECTED_ICE_TOTAL,
                "actual": total,
            }
        )

    summary = {
        "schema": ICE_SEMANTICS_SCHEMA,
        "featureCategory": "ice",
        "iceCount": total,
        "sentryCount": counts.get("sentry", 0),
        "wallCount": counts.get("wall", 0),
        "semanticIds": sorted(ice_ids),
        "status": "FAIL" if errors else "PASS",
    }
    sidecar["iceSemantics"] = summary
    _write_json(sidecar_path, sidecar)

    if errors:
        add_check(
            report,
            "ICE_SEMANTICS",
            "ERROR",
            f"Targeted ICE semantic validation found {len(errors)} blocking issue(s).",
            errors[:200],
        )
    else:
        add_check(
            report,
            "ICE_SEMANTICS",
            "PASS",
            "Normalized the 13-entity GM ICE publication subset (6 Sentry, 7 Wall).",
            summary,
        )
    _write_json(validation_path, report)


def configure_step4_ice_semantics(namespace: dict[str, Any]) -> None:
    """Install targeted ICE publication selection and semantic enrichment."""
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_ice_semantics_patch", False):
        return

    original_render_entity = pipeline.render_entity
    original_materialize = pipeline.materialize

    repo_root = Path(__file__).resolve().parents[3]
    feature_root = repo_root / "src" / "packs" / "system" / "features"
    folder_types, folder_errors = resolve_ice_folders(feature_root)

    def render_entity(family: str, doc: dict, *args: Any, **kwargs: Any):
        markdown, metadata = original_render_entity(family, doc, *args, **kwargs)
        if family != FEATURE_FAMILY:
            return markdown, metadata
        if folder_errors:
            # Fail closed in the validator while preserving diagnostic output.
            return markdown, metadata
        if classify_ice_document(doc, folder_types) is None:
            # All Feature entities remain normalized into the sidecar for owning
            # systems such as ClassPackage. Only ICE receives an independent
            # standalone family collection for Chapter 29.
            return "", metadata
        return markdown, metadata

    def materialize(
        repo_root: Path,
        outroot: Path,
        pub: dict,
        asm: dict,
        config: dict,
        base_report: dict | None = None,
    ) -> dict:
        report = original_materialize(
            repo_root,
            outroot,
            pub,
            asm,
            config,
            base_report,
        )
        _postprocess_materialization(
            repo_root,
            outroot,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.render_entity = render_entity
    pipeline.materialize = materialize
    pipeline._ice_semantics_patch = True
