from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .structured import (
    classify_action,
    clean_description,
    get_in,
    weapon_feature_name,
)


SCHEMA_VERSION = "cybermancy-step4-structured-entities-v1.1"
_DAGGERHEART_FEATURE_SOURCE = Path(__file__).resolve().parents[4] / "daggerheart-mods" / "en.json"


def _description_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value") or ""
    return value


def _system_description(doc: dict) -> Any:
    value = get_in(doc, "system.description")
    if value not in (None, ""):
        return _description_value(value)
    return _description_value(get_in(doc, "system.description.value", ""))


def _format_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _damage_part_formula(part: dict) -> str:
    value = part.get("value") if isinstance(part.get("value"), dict) else {}
    dice = value.get("dice")
    bonus = value.get("bonus")
    formula = str(dice or "")
    if bonus not in (None, "", 0, 0.0):
        try:
            numeric = float(bonus)
            formula += ("+" if numeric >= 0 else "-") + _format_number(abs(numeric))
        except (TypeError, ValueError):
            raw = str(bonus).strip()
            if raw:
                formula += raw if raw.startswith(("+", "-")) else "+" + raw
    return formula


def damage_formula(attack: Any) -> str:
    """Return publication damage formulas only; Foundry damage types are excluded."""
    if not isinstance(attack, dict):
        return ""
    parts = get_in(attack, "damage.parts", [])
    if not isinstance(parts, list):
        return ""
    formulas = [
        _damage_part_formula(part)
        for part in parts
        if isinstance(part, dict)
    ]
    return "; ".join(formula for formula in formulas if formula)


def _iter_records(node: Any):
    if isinstance(node, dict):
        for value in node.values():
            if isinstance(value, dict):
                yield value
    elif isinstance(node, list):
        for value in node:
            if isinstance(value, dict):
                yield value


def _human_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1].upper() + text[1:] if text else ""


def _strip_mechanic_label(description: Any, display_name: str, kind: str) -> str:
    """Remove duplicated Foundry presentation labels without rewriting the rule text."""
    text = clean_description(description or "")
    if not text:
        return ""
    escaped = re.escape(str(display_name).strip())
    patterns = []
    if kind == "critical-effect":
        patterns.append(rf"^\s*Critical\s+Effect\s*[-–—:]\s*{escaped}\s*:\s*")
    patterns.append(rf"^\s*{escaped}\s*:\s*")
    for pattern in patterns:
        updated = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE)
        if updated != text:
            return updated.strip()
    return text.strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@lru_cache(maxsize=1)
def _standard_feature_catalog() -> tuple[dict[str, list[dict]], str]:
    """Index current Daggerheart localization feature definitions by identifier.

    Cybermancy weapon records store standard feature identifiers (for example,
    ``retractable``) without duplicating the Daggerheart rules text. The
    repository's Daggerheart localization is therefore the fallback publication
    definition when the canonical Cybermancy record has no local description.
    Ambiguous identifiers are preserved as multiple candidates and are never
    silently resolved.
    """
    if not _DAGGERHEART_FEATURE_SOURCE.is_file():
        return {}, ""
    data = json.loads(_DAGGERHEART_FEATURE_SOURCE.read_text(encoding="utf-8"))
    catalog: dict[str, list[dict]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, dict):
                    name = value.get("name")
                    description = value.get("description")
                    if isinstance(name, str) and name.strip() and isinstance(description, str) and description.strip():
                        candidate = {
                            "name": clean_description(name),
                            "description": clean_description(description),
                        }
                        bucket = catalog.setdefault(str(key).casefold(), [])
                        if candidate not in bucket:
                            bucket.append(candidate)
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return catalog, _sha256_file(_DAGGERHEART_FEATURE_SOURCE)


def _standard_weapon_feature_definition(identifier: str) -> dict:
    catalog, source_sha = _standard_feature_catalog()
    candidates = catalog.get(str(identifier).casefold(), [])
    base = {
        "name": _human_identifier(identifier),
        "kind": "weapon-feature",
        "description": "",
        "definitionSource": "daggerheart-standard",
        "definitionSourcePath": "daggerheart-mods/en.json",
        "definitionSourceSha256": source_sha,
    }
    if len(candidates) == 1:
        base.update(candidates[0])
        base["definitionStatus"] = "resolved"
    elif len(candidates) > 1:
        base["definitionStatus"] = "ambiguous"
        base["definitionCandidates"] = candidates
    else:
        base["definitionStatus"] = "missing"
    return base


def _weapon_feature_definitions(system: dict) -> list[dict]:
    features = system.get("weaponFeatures")
    values = list(_iter_records(features)) if isinstance(features, dict) else (
        features if isinstance(features, list) else []
    )
    definitions = []
    for feature in values:
        if not isinstance(feature, dict):
            continue
        raw_identifier = feature.get("value") or feature.get("name") or feature.get("label") or ""
        display_name = weapon_feature_name(feature)
        local_rules = (
            feature.get("rules")
            or feature.get("description")
            or get_in(feature, "system.description")
            or get_in(feature, "system.description.value")
            or ""
        )
        local_description = _strip_mechanic_label(local_rules, display_name, "weapon-feature")
        if local_description:
            definitions.append({
                "name": _human_identifier(display_name),
                "kind": "weapon-feature",
                "description": local_description,
                "definitionSource": "weapon-record",
                "definitionStatus": "resolved",
            })
            continue
        definitions.append(_standard_weapon_feature_definition(str(raw_identifier or display_name)))
    return definitions


def _weapon_action_definitions(system: dict) -> tuple[list[dict], list[dict]]:
    ordinary: list[dict] = []
    critical: list[dict] = []
    for action in _iter_records(system.get("actions")):
        semantic_type, display_name = classify_action("weapons", action)
        definition = {
            "name": display_name,
            "kind": semantic_type,
            "description": _strip_mechanic_label(action.get("description", ""), display_name, semantic_type),
            "definitionSource": "weapon-record",
            "definitionStatus": "resolved",
        }
        if semantic_type == "critical-effect":
            critical.append(definition)
        else:
            ordinary.append(definition)
    return ordinary, critical


def structured_publication_data(family: str, doc: dict, metadata: dict) -> dict:
    """Project a structured source record into stable publication semantics.

    The result is derived Step 4 data. It deliberately omits Foundry wiring and
    keeps only reader-facing values needed by later publication/layout stages.
    """
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    identity_description = _description_value(get_in(doc, "identity.description"))
    description = clean_description(identity_description or _system_description(doc) or "")

    result = {
        "tier": get_in(doc, "identity.tier") or system.get("tier"),
        "description": description,
        "burden": system.get("burden"),
        "range": system.get("range"),
    }

    if family == "weapons":
        attack = system.get("attack") if isinstance(system.get("attack"), dict) else {}
        semantics = metadata.get("weaponSemantics") if isinstance(metadata.get("weaponSemantics"), dict) else {}
        action_definitions, critical_definitions = _weapon_action_definitions(system)
        result["attack"] = {
            "trait": semantics.get("trait"),
            "range": attack.get("range"),
            "damageFormula": damage_formula(attack),
        }
        # Preserve the accepted C fields exactly; D adds explicit reference
        # definitions beside them rather than changing their meaning.
        result["weaponFeatures"] = list(semantics.get("weaponFeatures") or [])
        result["actions"] = list(semantics.get("actions") or [])
        result["criticalEffects"] = list(semantics.get("criticalEffects") or [])
        result["weaponFeatureDefinitions"] = _weapon_feature_definitions(system)
        result["actionDefinitions"] = action_definitions
        result["criticalEffectDefinitions"] = critical_definitions

    return result


def sidecar_entity(metadata: dict, publication_data: dict) -> dict:
    return {
        "semanticId": metadata["semanticId"],
        "family": metadata["family"],
        "sourceId": metadata["sourceId"],
        "name": metadata["name"],
        "audience": metadata.get("audience"),
        "sourcePath": metadata.get("sourcePath"),
        "publicationData": publication_data,
    }
