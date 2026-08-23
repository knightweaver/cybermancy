from __future__ import annotations

from typing import Any

from .structured import clean_description, get_in


SCHEMA_VERSION = "cybermancy-step4-structured-entities-v1.0"


def _system_description(doc: dict) -> Any:
    value = get_in(doc, "system.description")
    if isinstance(value, dict):
        return value.get("value") or ""
    if value not in (None, ""):
        return value
    return get_in(doc, "system.description.value", "")


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


def structured_publication_data(family: str, doc: dict, metadata: dict) -> dict:
    """Project a structured source record into stable publication semantics.

    The result is derived Step 4 data. It deliberately omits Foundry wiring and
    keeps only reader-facing values needed by later publication/layout stages.
    """
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    identity_description = get_in(doc, "identity.description")
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
        result["attack"] = {
            "trait": semantics.get("trait"),
            "range": attack.get("range"),
            "damageFormula": damage_formula(attack),
        }
        result["weaponFeatures"] = list(semantics.get("weaponFeatures") or [])
        result["actions"] = list(semantics.get("actions") or [])
        result["criticalEffects"] = list(semantics.get("criticalEffects") or [])

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
