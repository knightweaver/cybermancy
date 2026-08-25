from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .equipment_catalog import latex_escape


@dataclass(frozen=True)
class MechanicReference:
    name: str
    description: str
    kinds: tuple[str, ...]
    source_entities: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "kinds": list(self.kinds),
            "sourceEntities": list(self.source_entities),
        }


def display_mechanic_name(value: Any) -> str:
    """Match the Equipment Catalog's reader-facing mechanic-name convention."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text == text.casefold():
        return text.title()
    return text


def _definition_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _definition_key(value: Any) -> str:
    return _definition_text(value).casefold()


def _expected_names(entities: Iterable[dict], keys: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for entity in entities:
        data = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
        for key in keys:
            values = data.get(key)
            if not isinstance(values, list):
                continue
            for value in values:
                name = display_mechanic_name(value)
                if name:
                    out.setdefault(name.casefold(), name)
    return out


def _definition_records(entities: Iterable[dict], keys: tuple[str, ...]) -> list[dict]:
    out = []
    for entity in entities:
        semantic_id = str(entity.get("semanticId") or "")
        entity_name = str(entity.get("name") or "")
        data = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
        for key in keys:
            values = data.get(key)
            if not isinstance(values, list):
                continue
            for definition in values:
                if not isinstance(definition, dict):
                    continue
                out.append({
                    "name": display_mechanic_name(definition.get("name")),
                    "description": _definition_text(definition.get("description")),
                    "kind": str(definition.get("kind") or ""),
                    "sourceEntity": semantic_id,
                    "sourceEntityName": entity_name,
                    "definitionStatus": str(definition.get("definitionStatus") or ""),
                    "definitionSource": definition.get("definitionSource"),
                    "definitionSourcePath": definition.get("definitionSourcePath"),
                })
    return out


def _source_entity_details(entries: Iterable[dict]) -> list[dict]:
    """Return stable entity ID/name pairs for human-actionable validation reports."""
    details = {
        (str(entry.get("sourceEntity") or ""), str(entry.get("sourceEntityName") or ""))
        for entry in entries
        if entry.get("sourceEntity") or entry.get("sourceEntityName")
    }
    return [
        {"semanticId": semantic_id, "name": name}
        for semantic_id, name in sorted(details, key=lambda pair: (pair[1].casefold(), pair[0]))
    ]


def _collect_section(
    entities: list[dict],
    *,
    displayed_keys: tuple[str, ...],
    definition_keys: tuple[str, ...],
) -> tuple[list[MechanicReference], list[dict], list[dict], list[dict]]:
    expected = _expected_names(entities, displayed_keys)
    records = _definition_records(entities, definition_keys)
    grouped: dict[str, list[dict]] = {}
    for record in records:
        if record["name"]:
            grouped.setdefault(record["name"].casefold(), []).append(record)

    references: list[MechanicReference] = []
    collisions: list[dict] = []
    missing: list[dict] = []
    orphans: list[dict] = []

    for key, display_name in expected.items():
        matches = grouped.get(key, [])
        if not matches:
            missing.append({"name": display_name, "issue": "no-definition-record"})
            continue
        empty = [m for m in matches if not m["description"] or m.get("definitionStatus") in {"missing", "ambiguous"}]
        if empty:
            missing.append({
                "name": display_name,
                "issue": "definition-text-unresolved",
                "sources": [
                    {
                        "sourceEntity": m["sourceEntity"],
                        "sourceEntityName": m["sourceEntityName"],
                        "kind": m["kind"],
                        "definitionStatus": m.get("definitionStatus"),
                        "definitionSource": m.get("definitionSource"),
                        "definitionSourcePath": m.get("definitionSourcePath"),
                    }
                    for m in empty
                ],
            })
            continue

        variants: dict[str, list[dict]] = {}
        for match in matches:
            variants.setdefault(_definition_key(match["description"]), []).append(match)
        if len(variants) > 1:
            collisions.append({
                "name": display_name,
                "variants": [
                    {
                        "description": entries[0]["description"],
                        "sourceEntities": sorted({entry["sourceEntity"] for entry in entries}),
                        "sourceEntityDetails": _source_entity_details(entries),
                        "kinds": sorted({entry["kind"] for entry in entries if entry["kind"]}),
                    }
                    for entries in variants.values()
                ],
            })
            continue

        chosen = matches[0]
        references.append(MechanicReference(
            name=display_name,
            description=chosen["description"],
            kinds=tuple(sorted({m["kind"] for m in matches if m["kind"]})),
            source_entities=tuple(sorted({m["sourceEntity"] for m in matches if m["sourceEntity"]})),
        ))

    for key, matches in grouped.items():
        if key not in expected:
            orphans.append({
                "name": matches[0]["name"],
                "sourceEntities": sorted({m["sourceEntity"] for m in matches}),
                "sourceEntityDetails": _source_entity_details(matches),
                "kinds": sorted({m["kind"] for m in matches if m["kind"]}),
            })

    references.sort(key=lambda ref: (ref.name.casefold(), ref.name))
    collisions.sort(key=lambda item: str(item["name"]).casefold())
    missing.sort(key=lambda item: str(item["name"]).casefold())
    orphans.sort(key=lambda item: str(item["name"]).casefold())
    return references, collisions, missing, orphans


def collect_weapon_references(entities: Iterable[dict]) -> dict:
    weapons = [entity for entity in entities if entity.get("family") == "weapons"]
    actions, action_collisions, action_missing, action_orphans = _collect_section(
        weapons,
        displayed_keys=("weaponFeatures", "actions"),
        definition_keys=("weaponFeatureDefinitions", "actionDefinitions"),
    )
    critical, critical_collisions, critical_missing, critical_orphans = _collect_section(
        weapons,
        displayed_keys=("criticalEffects",),
        definition_keys=("criticalEffectDefinitions",),
    )
    return {
        "actions": actions,
        "criticalEffects": critical,
        "collisions": action_collisions + critical_collisions,
        "missingDefinitions": action_missing + critical_missing,
        "orphanDefinitions": action_orphans + critical_orphans,
    }


def _reference_column_spec(width: float, align: str) -> str:
    prefix = r">{\Centering\arraybackslash}" if align.casefold() == "center" else r">{\RaggedRight\arraybackslash}"
    return f"{prefix}m{{{width:.3f}in}}"


def _padded(value: str, padding_pt: float = 2.0, *, bold: bool = False) -> str:
    rendered = latex_escape(value)
    if bold:
        rendered = rf"\textbf{{{rendered}}}"
    return rf"\vspace*{{{padding_pt:g}pt}}\strut {rendered}\strut\par\vspace*{{{padding_pt:g}pt}}"


def _reference_section_title(references: list[MechanicReference], config: dict) -> str:
    ref_config = config.get("references", {}) if isinstance(config.get("references"), dict) else {}
    critical_only = bool(references) and all(
        set(reference.kinds).issubset({"critical-effect"})
        for reference in references
    )
    if critical_only:
        return str(ref_config.get("criticalEffectsTitle", "Critical Effects"))
    return str(ref_config.get("actionsTitle", "Weapon Actions"))


def _continuation_label(base_label: str, config: dict) -> str:
    pagination = config.get("pagination", {}) if isinstance(config.get("pagination"), dict) else {}
    template = str(pagination.get("continuationTemplate", "{label} — CONTINUED"))
    return template.format(label=base_label)


def render_mechanics_reference_latex(references: list[MechanicReference], config: dict) -> str:
    ref_config = config.get("references", {}) if isinstance(config.get("references"), dict) else {}
    columns = ref_config.get("columns") if isinstance(ref_config.get("columns"), list) else []
    if len(columns) != 2:
        columns = [
            {"label": "Name", "widthIn": 1.55, "align": "left"},
            {"label": "Effect", "widthIn": 5.90, "align": "left"},
        ]
    padding = float(ref_config.get("verticalPaddingPt", 2) or 2)
    spec = "@{}" + "".join(
        _reference_column_spec(float(column["widthIn"]), str(column.get("align", "left")))
        for column in columns
    ) + "@{}"
    header = r"\rowcolor{CMTableHeader}" + " & ".join(
        rf"\textbf{{\color{{white}}\MakeUppercase{{{latex_escape(column['label'])}}}}}"
        for column in columns
    ) + r" \\"
    continuation = _continuation_label(_reference_section_title(references, config), config)
    continuation_band = (
        rf"\rowcolor{{CMGroupBand}}\multicolumn{{{len(columns)}}}{{@{{}}l@{{}}}}{{"
        rf"\textbf{{\color{{CMTextDark}} {latex_escape(continuation)}}}}} \\"
    )
    lines = [
        r"\begingroup",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\setlength{\LTpre}{0pt}",
        r"\setlength{\LTpost}{0pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\fontsize{7.3}{8.6}\selectfont",
        rf"\begin{{longtable}}{{{spec}}}",
        header,
        r"\endfirsthead",
        continuation_band,
        header,
        r"\endhead",
    ]
    for index, reference in enumerate(references):
        if index % 2 == 0:
            lines.append(r"\rowcolor{CMAltRow}")
        lines.append(
            _padded(reference.name, padding, bold=True)
            + " & "
            + _padded(reference.description, padding)
            + r" \\"
        )
    lines += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines) + "\n"
