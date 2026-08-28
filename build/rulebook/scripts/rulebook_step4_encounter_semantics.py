from __future__ import annotations

import json
import math
import re
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
from rulebook_normalize.publication_markdown import html_to_publication_markdown
from rulebook_normalize.structured import clean_description, get_in
from rulebook_step4_ice_semantics import normalize_actions


ENCOUNTER_SEMANTICS_SCHEMA = "cybermancy-step4-encounter-semantics-v1.0"
ENCOUNTER_CORPUS_SCHEMA = "cybermancy-step4-encounter-corpus-v1.0"
ENCOUNTER_FAMILIES = {"adversaries", "environments", "adversaries-features"}
ART_ROLES = {
    "adversaries": "portrait",
    "environments": "environment",
}
_ASSET_KIND = "structured-encounter-publication-image"

_FAST_PLAY_SECTION_RE = re.compile(
    r"<section\b(?=[^>]*\bclass\s*=\s*['\"][^'\"]*\bcybermancy-fast-play\b[^'\"]*['\"])[^>]*>.*?</section>",
    re.IGNORECASE | re.DOTALL,
)
_FOUNDRY_LABEL_RE = re.compile(r"@[A-Za-z][A-Za-z0-9]*\[[^\]]*\]\{([^{}]+)\}")
_TEMPLATE_RE = re.compile(r"@Template\[[^\]]*\]", re.IGNORECASE)
_ACTOR_REF_RE = re.compile(r"(?:^|\.)Actor\.([A-Za-z0-9]{8,})$")
_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)


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


def _strip_fast_play_mirror(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return _FAST_PLAY_SECTION_RE.sub("", text).strip()


def _clean_foundry_publication_text(value: Any) -> str:
    text = str(value or "")
    text = _FOUNDRY_LABEL_RE.sub(lambda match: match.group(1), text)
    text = _TEMPLATE_RE.sub("", text)
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def _publication_markdown(value: Any, *, strip_fast_play: bool = False) -> str:
    text = str(value or "")
    if strip_fast_play:
        text = _strip_fast_play_mirror(text)
    if not text:
        return ""
    return _clean_foundry_publication_text(html_to_publication_markdown(text).strip())


def _publication_actions(system: dict) -> list[dict]:
    actions = normalize_actions(system)
    for action in actions:
        if isinstance(action, dict) and _nonempty(action.get("rulesMarkdown")):
            action["rulesMarkdown"] = _clean_foundry_publication_text(action["rulesMarkdown"])
    return actions


def _description_fields(doc: dict) -> tuple[str, str]:
    identity_description = get_in(doc, "identity.description")
    raw = identity_description if _nonempty(identity_description) else get_in(doc, "system.description", "")
    if isinstance(raw, dict):
        raw = raw.get("value") or ""
    raw = _strip_fast_play_mirror(raw)
    return clean_description(raw or ""), _publication_markdown(raw)


def _ordered_embedded_features(owner_semantic_id: str, doc: dict) -> list[dict]:
    items = doc.get("items")
    if not isinstance(items, list):
        return []
    candidates = [
        item for item in items
        if isinstance(item, dict) and item.get("type") == "feature"
    ]
    candidates.sort(
        key=lambda item: (
            item.get("sort") if isinstance(item.get("sort"), (int, float)) else 0,
            str(item.get("name") or "").casefold(),
            str(item.get("_id") or ""),
        )
    )
    out: list[dict] = []
    for item in candidates:
        source_id = str(item.get("_id") or "").strip()
        system = item.get("system") if isinstance(item.get("system"), dict) else {}
        raw_rules = system.get("description") or item.get("description") or ""
        record: dict[str, Any] = {
            "name": str(item.get("name") or "Feature"),
            "rulesMarkdown": _publication_markdown(raw_rules),
            "actions": _publication_actions(system),
        }
        if source_id:
            record["sourceId"] = source_id
            record["semanticId"] = f"{owner_semantic_id}:feature:{source_id}"
        out.append(record)
    return out


def _normalize_fast_play(doc: dict) -> dict | None:
    fp = get_in(doc, "flags.cybermancy.fastPlay")
    if not isinstance(fp, dict) or not fp:
        return None
    prompts: list[dict] = []
    raw_prompts = fp.get("prompts")
    if isinstance(raw_prompts, list):
        for prompt in raw_prompts:
            if not isinstance(prompt, dict):
                continue
            refs = prompt.get("featureRefs")
            refs = refs if isinstance(refs, list) else []
            prompts.append(
                {
                    "label": str(prompt.get("label") or "").strip(),
                    "text": str(prompt.get("text") or "").strip(),
                    "featureRefs": [
                        str(ref).strip() for ref in refs if str(ref or "").strip()
                    ],
                }
            )
    return {
        "prompts": prompts,
        "goal": str(fp.get("goal") or "").strip(),
    }


def _issue(entity: dict, code: str, message: str, *, severity: str = "WARNING", **details: Any) -> dict:
    item = {
        "code": code,
        "severity": severity,
        "ownerSemanticId": entity.get("semanticId"),
        "ownerFamily": entity.get("family"),
        "ownerName": entity.get("name"),
        "message": message,
    }
    if details:
        item.update(details)
    return item


def _fast_play_issues(entity: dict, fast_play: dict | None, features: list[dict]) -> list[dict]:
    if fast_play is None:
        return []
    issues: list[dict] = []
    prompts = fast_play.get("prompts") if isinstance(fast_play.get("prompts"), list) else []
    goal = str(fast_play.get("goal") or "").strip()
    if not 2 <= len(prompts) <= 5:
        issues.append(
            _issue(
                entity,
                "ENCOUNTER_FAST_PLAY_PROMPT_COUNT_INVALID",
                f"Fast Play must contain 2-5 ordered prompts; found {len(prompts)}.",
                severity="ERROR",
            )
        )
    if not goal:
        issues.append(
            _issue(
                entity,
                "ENCOUNTER_FAST_PLAY_GOAL_MISSING",
                "Fast Play has no Goal.",
                severity="ERROR",
            )
        )
    feature_names = {str(feature.get("name") or "") for feature in features}
    for index, prompt in enumerate(prompts):
        label = str(prompt.get("label") or "").strip()
        text = str(prompt.get("text") or "").strip()
        if not label or not text:
            issues.append(
                _issue(
                    entity,
                    "ENCOUNTER_FAST_PLAY_PROMPT_INVALID",
                    f"Fast Play prompt {index + 1} must contain both label and text.",
                    severity="ERROR",
                    promptIndex=index,
                )
            )
        refs = prompt.get("featureRefs") if isinstance(prompt.get("featureRefs"), list) else []
        unresolved = [ref for ref in refs if ref not in feature_names]
        if unresolved:
            issues.append(
                _issue(
                    entity,
                    "ENCOUNTER_FAST_PLAY_FEATURE_REF_UNRESOLVED",
                    "Fast Play featureRefs must exactly match embedded canonical Feature names.",
                    severity="ERROR",
                    promptIndex=index,
                    promptLabel=label,
                    unresolved=unresolved,
                )
            )
    return issues


def _normalize_experiences(value: Any) -> list[dict]:
    if isinstance(value, dict):
        records = list(value.values())
    elif isinstance(value, list):
        records = value
    else:
        records = []
    out: list[dict] = []
    for record in records:
        if not isinstance(record, dict) or not _nonempty(record.get("name")):
            continue
        item = {"name": str(record.get("name"))}
        if _nonempty(record.get("value")):
            item["value"] = record.get("value")
        out.append(item)
    return out


def _attack_damage_types(attack: dict) -> list[str]:
    parts = get_in(attack, "damage.parts", [])
    if not isinstance(parts, list):
        return []
    out: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        types = part.get("type")
        values = types if isinstance(types, list) else ([types] if _nonempty(types) else [])
        for value in values:
            label = str(value).strip()
            if label and label not in out:
                out.append(label)
    return out


def _format_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _encounter_damage_formula(attack: dict) -> str:
    parts = get_in(attack, "damage.parts", [])
    if not isinstance(parts, list):
        return ""
    formulas: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        value = part.get("value") if isinstance(part.get("value"), dict) else {}
        custom = value.get("custom") if isinstance(value.get("custom"), dict) else {}
        if custom.get("enabled") and _nonempty(custom.get("formula")):
            formulas.append(str(custom.get("formula")).strip())
            continue
        dice = str(value.get("dice") or "").strip()
        if not dice:
            continue
        multiplier = value.get("flatMultiplier")
        try:
            count = int(multiplier) if multiplier not in (None, "") else 1
        except (TypeError, ValueError):
            count = 1
        formula = f"{count if count > 1 else ''}{dice}"
        bonus = value.get("bonus")
        if bonus not in (None, "", 0, 0.0):
            try:
                numeric = float(bonus)
                formula += ("+" if numeric >= 0 else "-") + _format_number(abs(numeric))
            except (TypeError, ValueError):
                raw = str(bonus).strip()
                if raw:
                    formula += raw if raw.startswith(("+", "-")) else "+" + raw
        formulas.append(formula)
    return "; ".join(formula for formula in formulas if formula)


def _normalize_attack(attack: Any) -> dict | None:
    if not isinstance(attack, dict) or not attack:
        return None
    roll = attack.get("roll") if isinstance(attack.get("roll"), dict) else {}
    damage = attack.get("damage") if isinstance(attack.get("damage"), dict) else {}
    out: dict[str, Any] = {
        "name": attack.get("name") or "Attack",
        "bonus": roll.get("bonus"),
        "trait": roll.get("trait"),
        "difficulty": roll.get("difficulty"),
        "range": attack.get("range"),
        "damageFormula": _encounter_damage_formula(attack),
        "damageTypes": _attack_damage_types(attack),
    }
    if damage.get("direct") is True:
        out["direct"] = True
    return {key: value for key, value in out.items() if _nonempty(value) or value is True}


def _normalize_resistances(system: dict) -> dict | None:
    value = system.get("resistance")
    if not isinstance(value, dict):
        return None
    out: dict[str, dict] = {}
    for kind in ("physical", "magical"):
        source = value.get(kind) if isinstance(value.get(kind), dict) else {}
        record = {
            "resistance": bool(source.get("resistance", False)),
            "immunity": bool(source.get("immunity", False)),
            "reduction": source.get("reduction"),
        }
        meaningful = record["resistance"] or record["immunity"] or _nonempty(record["reduction"])
        if meaningful:
            out[kind] = record
    return out or None


def _normalize_condition_immunities(system: dict) -> list[str]:
    value = get_in(system, "rules.conditionImmunities", {})
    if not isinstance(value, dict):
        return []
    return [str(name) for name, enabled in value.items() if enabled is True]


def _string_semantic(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item or "").strip())
    return str(value or "").strip()


def _potential_strings(node: Any):
    if isinstance(node, str):
        if node.strip():
            yield node.strip()
    elif isinstance(node, dict):
        if "adversaries" in node:
            yield from _potential_strings(node.get("adversaries"))
        else:
            for value in node.values():
                if isinstance(value, (dict, list, str)):
                    yield from _potential_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _potential_strings(value)


def _resolve_potential_adversaries(value: Any, adversary_names: dict[str, str]) -> tuple[list[str], list[str]]:
    names: list[str] = []
    unresolved: list[str] = []
    for raw in _potential_strings(value):
        labelled = _FOUNDRY_LABEL_RE.sub(lambda match: match.group(1), raw)
        if labelled != raw:
            candidate = labelled.strip()
        else:
            match = _ACTOR_REF_RE.search(raw)
            if match:
                source_id = match.group(1)
                candidate = adversary_names.get(source_id, "")
                if not candidate:
                    unresolved.append(raw)
                    continue
            elif raw.startswith(("Actor.", "Compendium.")):
                unresolved.append(raw)
                continue
            else:
                candidate = raw
        if candidate and candidate not in names:
            names.append(candidate)
    return names, unresolved


def _source_document(repo_root: Path, entity: dict) -> tuple[dict | None, dict | None]:
    source_path = str(entity.get("sourcePath") or "")
    path = repo_root / source_path
    if not source_path or not path.is_file():
        return None, _issue(
            entity,
            "ENCOUNTER_SOURCE_MISSING",
            "Canonical encounter source document is missing during Step 4 enrichment.",
            severity="ERROR",
            sourcePath=source_path,
        )
    try:
        document = _load_json(path)
    except Exception as exc:
        return None, _issue(
            entity,
            "ENCOUNTER_SOURCE_INVALID",
            f"Could not load canonical encounter source document: {exc}",
            severity="ERROR",
            sourcePath=source_path,
        )
    if not isinstance(document, dict):
        return None, _issue(
            entity,
            "ENCOUNTER_SOURCE_INVALID",
            "Canonical encounter source document is not a JSON object.",
            severity="ERROR",
            sourcePath=source_path,
        )
    return document, None


def _mapped_logical_image(raw_image: Any, mappings: list[dict]) -> str | None:
    if not isinstance(raw_image, str) or not raw_image.strip():
        return None
    target = raw_image.strip().replace("\\", "/").lstrip("/")
    if is_remote_asset_reference(target):
        return None
    mapped = map_asset_reference(target, mappings)
    if not isinstance(mapped, str) or not mapped.strip():
        return None
    mapped = mapped.replace("\\", "/").lstrip("/")
    if mapped.startswith(("modules/", "worlds/")):
        return None
    return mapped


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


def _stage_optional_art(
    repo_root: Path,
    source_root: Path,
    entity: dict,
    doc: dict,
    mappings: list[dict],
    existing_sources: dict[str, list[str]],
) -> tuple[dict | None, dict | None, dict | None]:
    role = ART_ROLES.get(str(entity.get("family") or ""))
    if role is None:
        return None, None, None
    raw_image = doc.get("img")
    logical_rel = _mapped_logical_image(raw_image, mappings)
    if logical_rel is None:
        return None, None, None
    resolution = resolve_publication_source_asset(
        repo_root,
        logical_rel,
        str(entity.get("audience") or ""),
    )
    status = resolution.get("status")
    if status == "missing":
        # Artwork is optional for legacy Part VI corpus entries. Missing Foundry
        # core/system icons are coverage information, not a Step 4 failure.
        return None, None, None
    if status != "resolved":
        return None, None, _issue(
            entity,
            "ENCOUNTER_PUBLICATION_IMAGE_AMBIGUOUS",
            "Encounter image resolves to multiple equal-authority repository assets with different contents.",
            severity="ERROR",
            sourceReference=raw_image,
            logicalReference=logical_rel,
            resolution=resolution,
        )
    source_repo_rel = str(resolution.get("sourceRepoPath") or "")
    publication_rel = publication_asset_path(logical_rel)
    conflicts = [
        source for source in existing_sources.get(publication_rel, [])
        if not _same_source_asset(repo_root, source, source_repo_rel)
    ]
    if conflicts:
        return None, None, _issue(
            entity,
            "ENCOUNTER_PUBLICATION_IMAGE_COLLISION",
            "Encounter publication image collides with a different source asset at the same staged path.",
            severity="ERROR",
            sourceReference=raw_image,
            logicalReference=logical_rel,
            sourceRepoPath=source_repo_rel,
            publicationPath=publication_rel,
            conflictingSources=sorted(set(conflicts)),
        )
    try:
        staged = stage_publication_asset(
            repo_root,
            source_repo_rel,
            source_root,
            publication_rel,
        )
    except Exception as exc:
        return None, None, _issue(
            entity,
            "ENCOUNTER_PUBLICATION_IMAGE_STAGING_FAILED",
            f"Could not stage encounter publication image: {exc}",
            severity="ERROR",
            sourceReference=raw_image,
            logicalReference=logical_rel,
            sourceRepoPath=source_repo_rel,
            publicationPath=publication_rel,
        )
    staged_file = source_root / publication_rel
    if (
        staged.get("status") != "staged"
        or not staged_file.is_file()
        or staged.get("sha256") != sha256_file(staged_file)
    ):
        return None, None, _issue(
            entity,
            "ENCOUNTER_PUBLICATION_IMAGE_STAGING_FAILED",
            "Encounter publication image failed existence/hash validation after staging.",
            severity="ERROR",
            sourceReference=raw_image,
            logicalReference=logical_rel,
            sourceRepoPath=source_repo_rel,
            publicationPath=publication_rel,
        )
    existing_sources.setdefault(publication_rel, []).append(source_repo_rel)
    art = {"role": role, "image": publication_rel}
    row = {
        "kind": _ASSET_KIND,
        "sourceEntity": entity.get("semanticId"),
        "sourcePath": entity.get("sourcePath"),
        "sourceReference": raw_image,
        "reference": logical_rel,
        "sourceRepoPath": source_repo_rel,
        "audience": entity.get("audience"),
        "publicationPath": publication_rel,
        "role": role,
        "status": "staged",
        "sha256": staged.get("sha256"),
    }
    return art, row, None


def _word_count(value: Any) -> int:
    return len(_WORD_RE.findall(str(value or "")))


def _feature_rules_words(features: list[dict]) -> int:
    total = 0
    for feature in features:
        rules = str(feature.get("rulesMarkdown") or "")
        total += _word_count(rules)
        # An action that simply mirrors the Feature text is implementation
        # duplication. Count only distinct action rules in corpus sizing.
        for action in feature.get("actions", []):
            if not isinstance(action, dict):
                continue
            action_rules = str(action.get("rulesMarkdown") or "")
            if action_rules and action_rules.strip() != rules.strip():
                total += _word_count(action_rules)
    return total


def _entity_metrics(entity: dict) -> dict:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    features = pdata.get("features") if isinstance(pdata.get("features"), list) else []
    actions = pdata.get("actions") if isinstance(pdata.get("actions"), list) else []
    fast_play = pdata.get("fastPlay") if isinstance(pdata.get("fastPlay"), dict) else None
    description = (
        pdata.get("rulesMarkdown")
        if str(entity.get("family") or "") == "adversaries-features"
        else pdata.get("descriptionMarkdown") or pdata.get("description")
    ) or ""
    behavioral = " ".join(
        str(pdata.get(key) or "")
        for key in ("motivesAndTactics", "impulses")
    )
    rules_words = _word_count(description) + _word_count(behavioral)
    rules_words += _feature_rules_words(features)
    if str(entity.get("family") or "") == "adversaries-features":
        rules = pdata.get("rulesMarkdown") or pdata.get("description") or ""
        rules_words = _word_count(rules)
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_rules = str(action.get("rulesMarkdown") or "")
            if action_rules and action_rules.strip() != str(rules).strip():
                rules_words += _word_count(action_rules)
    fp_words = 0
    if fast_play:
        for prompt in fast_play.get("prompts", []):
            if isinstance(prompt, dict):
                fp_words += _word_count(prompt.get("text"))
        fp_words += _word_count(fast_play.get("goal"))
    action_count = len(actions) + sum(
        len(feature.get("actions", []))
        for feature in features
        if isinstance(feature, dict) and isinstance(feature.get("actions"), list)
    )
    return {
        "semanticId": entity.get("semanticId"),
        "family": entity.get("family"),
        "name": entity.get("name"),
        "tier": pdata.get("tier"),
        "classification": pdata.get("classification"),
        "descriptionWordCount": _word_count(description),
        "rulesWordCount": rules_words,
        "featureCount": len(features),
        "actionCount": action_count,
        "fastPlayWordCount": fp_words,
        "hasFastPlay": fast_play is not None,
        "hasPublicationArt": isinstance(pdata.get("publicationArt"), dict),
    }


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _distribution(rows: list[dict], field: str) -> dict:
    values = [int(row.get(field) or 0) for row in rows]
    return {
        "p50": _percentile(values, 0.50),
        "p90": _percentile(values, 0.90),
        "max": max(values) if values else 0,
    }


def _top(rows: list[dict], field: str, limit: int = 10) -> list[dict]:
    positive = [row for row in rows if int(row.get(field) or 0) > 0]
    return [
        {
            "semanticId": row.get("semanticId"),
            "name": row.get("name"),
            field: row.get(field),
        }
        for row in sorted(
            positive,
            key=lambda row: (
                -int(row.get(field) or 0),
                str(row.get("name") or "").casefold(),
                str(row.get("semanticId") or ""),
            ),
        )[:limit]
    ]


def _corpus_report(entities: list[dict]) -> dict:
    rows = [
        _entity_metrics(entity)
        for entity in entities
        if isinstance(entity, dict) and entity.get("family") in ENCOUNTER_FAMILIES
    ]
    families: dict[str, dict] = {}
    for family in sorted(ENCOUNTER_FAMILIES):
        family_rows = [row for row in rows if row.get("family") == family]
        tier_distribution: dict[str, int] = {}
        classification_distribution: dict[str, int] = {}
        for row in family_rows:
            tier_key = str(row.get("tier")) if _nonempty(row.get("tier")) else "missing"
            classification_key = str(row.get("classification") or "missing")
            tier_distribution[tier_key] = tier_distribution.get(tier_key, 0) + 1
            classification_distribution[classification_key] = classification_distribution.get(classification_key, 0) + 1
        families[family] = {
            "entityCount": len(family_rows),
            "fastPlayCount": sum(1 for row in family_rows if row.get("hasFastPlay")),
            "publicationArtCount": sum(1 for row in family_rows if row.get("hasPublicationArt")),
            "tierDistribution": dict(sorted(tier_distribution.items())),
            "classificationDistribution": dict(sorted(classification_distribution.items())),
            "descriptionWordCount": _distribution(family_rows, "descriptionWordCount"),
            "rulesWordCount": _distribution(family_rows, "rulesWordCount"),
            "featureCount": _distribution(family_rows, "featureCount"),
            "fastPlayWordCount": _distribution(family_rows, "fastPlayWordCount"),
            "rulesWordCountOutliers": _top(family_rows, "rulesWordCount"),
            "featureCountOutliers": _top(family_rows, "featureCount"),
            "fastPlayWordCountOutliers": _top(family_rows, "fastPlayWordCount"),
        }
    return {
        "schema": ENCOUNTER_CORPUS_SCHEMA,
        "families": families,
        "entities": sorted(rows, key=lambda row: (str(row.get("family")), str(row.get("semanticId")))),
    }


def _enrich_adversary(entity: dict, doc: dict) -> list[dict]:
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    pdata = entity.setdefault("publicationData", {})
    description, description_markdown = _description_fields(doc)
    pdata["description"] = description
    pdata["descriptionMarkdown"] = description_markdown
    pdata["classification"] = system.get("type") or system.get("role") or system.get("classification")
    pdata["difficulty"] = system.get("difficulty")
    thresholds = system.get("damageThresholds") if isinstance(system.get("damageThresholds"), dict) else {}
    pdata["damageThresholds"] = {
        "major": thresholds.get("major"),
        "severe": thresholds.get("severe"),
    }
    resources = system.get("resources") if isinstance(system.get("resources"), dict) else {}
    hp = resources.get("hitPoints") if isinstance(resources.get("hitPoints"), dict) else {}
    stress = resources.get("stress") if isinstance(resources.get("stress"), dict) else {}
    pdata["hitPoints"] = hp.get("max")
    pdata["stress"] = stress.get("max")
    if _nonempty(system.get("hordeHp")):
        pdata["hordeHp"] = system.get("hordeHp")
    pdata["motivesAndTactics"] = _string_semantic(
        system.get("motivesAndTactics") or get_in(doc, "design.motivesAndTactics")
    )
    pdata["experiences"] = _normalize_experiences(system.get("experiences"))
    attack = _normalize_attack(system.get("attack"))
    if attack:
        pdata["attack"] = attack
    else:
        pdata.pop("attack", None)
    pdata["actions"] = _publication_actions(system)
    features = _ordered_embedded_features(str(entity.get("semanticId") or ""), doc)
    pdata["features"] = features
    fast_play = _normalize_fast_play(doc)
    if fast_play:
        pdata["fastPlay"] = fast_play
    else:
        pdata.pop("fastPlay", None)
    resistances = _normalize_resistances(system)
    if resistances:
        pdata["resistances"] = resistances
    else:
        pdata.pop("resistances", None)
    condition_immunities = _normalize_condition_immunities(system)
    if condition_immunities:
        pdata["conditionImmunities"] = condition_immunities
    else:
        pdata.pop("conditionImmunities", None)
    issues = _fast_play_issues(entity, fast_play, features)
    if not _nonempty(pdata.get("classification")):
        issues.append(_issue(entity, "ENCOUNTER_CLASSIFICATION_MISSING", "Adversary classification is missing."))
    if not description:
        issues.append(_issue(entity, "ENCOUNTER_DESCRIPTION_MISSING", "Adversary description is missing."))
    return issues


def _enrich_environment(entity: dict, doc: dict, adversary_names: dict[str, str]) -> list[dict]:
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    pdata = entity.setdefault("publicationData", {})
    description, description_markdown = _description_fields(doc)
    pdata["description"] = description
    pdata["descriptionMarkdown"] = description_markdown
    pdata["classification"] = system.get("type") or system.get("classification")
    pdata["difficulty"] = system.get("difficulty")
    pdata["impulses"] = _string_semantic(system.get("impulses") or get_in(doc, "mechanics.impulses"))
    potential, unresolved = _resolve_potential_adversaries(
        system.get("potentialAdversaries") or get_in(doc, "mechanics.potentialAdversaries"),
        adversary_names,
    )
    pdata["potentialAdversaries"] = potential
    pdata["actions"] = _publication_actions(system)
    features = _ordered_embedded_features(str(entity.get("semanticId") or ""), doc)
    pdata["features"] = features
    fast_play = _normalize_fast_play(doc)
    if fast_play:
        pdata["fastPlay"] = fast_play
    else:
        pdata.pop("fastPlay", None)
    issues = _fast_play_issues(entity, fast_play, features)
    if unresolved:
        issues.append(
            _issue(
                entity,
                "ENCOUNTER_POTENTIAL_ADVERSARY_REF_UNRESOLVED",
                "Environment contains Foundry Actor references that do not resolve to published Cybermancy adversaries.",
                unresolved=unresolved,
            )
        )
    if not _nonempty(pdata.get("classification")):
        issues.append(_issue(entity, "ENCOUNTER_CLASSIFICATION_MISSING", "Environment classification is missing."))
    if not description:
        issues.append(_issue(entity, "ENCOUNTER_DESCRIPTION_MISSING", "Environment description is missing."))
    if not _nonempty(pdata.get("impulses")):
        issues.append(_issue(entity, "ENCOUNTER_IMPULSES_MISSING", "Environment impulses are missing."))
    return issues


def _enrich_adversary_feature(entity: dict, doc: dict) -> list[dict]:
    system = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    pdata = entity.setdefault("publicationData", {})
    raw_rules = system.get("description") or doc.get("description") or ""
    pdata["description"] = _clean_foundry_publication_text(clean_description(raw_rules or ""))
    pdata["rulesMarkdown"] = _publication_markdown(raw_rules)
    pdata["actions"] = _publication_actions(system)
    issues: list[dict] = []
    if not pdata["rulesMarkdown"] and not pdata["actions"]:
        issues.append(
            _issue(
                entity,
                "ENCOUNTER_FEATURE_RULES_MISSING",
                "Standalone Adversary Feature has neither rules text nor structured Actions.",
            )
        )
    return issues


def _postprocess_encounter_semantics(
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
    corpus_path = metadata_root / "encounter-corpus.json"
    validation_path = metadata_root / "validation.json"

    if not sidecar_path.is_file():
        add_check(
            report,
            "ENCOUNTER_PUBLICATION_SEMANTICS",
            "ERROR",
            "Step 4 structured-entities sidecar is missing; Part VI semantics could not be enriched.",
            {"path": str(sidecar_path)},
        )
        _write_json(validation_path, report)
        return

    try:
        sidecar = _load_json(sidecar_path)
    except Exception as exc:
        add_check(
            report,
            "ENCOUNTER_PUBLICATION_SEMANTICS",
            "ERROR",
            f"Could not load Step 4 structured-entities sidecar: {exc}",
        )
        _write_json(validation_path, report)
        return

    entities = sidecar.get("entities") if isinstance(sidecar, dict) else None
    if not isinstance(entities, list):
        add_check(
            report,
            "ENCOUNTER_PUBLICATION_SEMANTICS",
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
            "ENCOUNTER_PUBLICATION_SEMANTICS",
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

    encounter_entities = sorted(
        [
            entity for entity in entities
            if isinstance(entity, dict) and entity.get("family") in ENCOUNTER_FAMILIES
        ],
        key=lambda entity: (str(entity.get("family") or ""), str(entity.get("semanticId") or "")),
    )
    adversary_names = {
        str(entity.get("sourceId")): str(entity.get("name") or "")
        for entity in encounter_entities
        if entity.get("family") == "adversaries" and _nonempty(entity.get("sourceId"))
    }

    issues: list[dict] = []
    staged_rows: list[dict] = []
    staged_count = 0

    for entity in encounter_entities:
        pdata = entity.get("publicationData")
        if not isinstance(pdata, dict):
            pdata = {}
            entity["publicationData"] = pdata
        pdata.pop("image", None)
        pdata.pop("publicationArt", None)

        doc, source_error = _source_document(repo_root, entity)
        if source_error is not None:
            issues.append(source_error)
            continue

        family = str(entity.get("family") or "")
        if family == "adversaries":
            issues.extend(_enrich_adversary(entity, doc))
        elif family == "environments":
            issues.extend(_enrich_environment(entity, doc, adversary_names))
        elif family == "adversaries-features":
            issues.extend(_enrich_adversary_feature(entity, doc))

        art, row, art_error = _stage_optional_art(
            repo_root,
            source_root,
            entity,
            doc,
            mappings,
            existing_sources,
        )
        if art_error is not None:
            issues.append(art_error)
        if art is not None and row is not None:
            pdata["publicationArt"] = art
            pdata["image"] = art["image"]
            staged_rows.append(row)
            staged_count += 1

    asset_rows.extend(staged_rows)
    _write_json(assets_path, asset_rows)

    corpus = _corpus_report(encounter_entities)
    _write_json(corpus_path, corpus)

    errors = [issue for issue in issues if issue.get("severity") == "ERROR"]
    warnings = [issue for issue in issues if issue.get("severity") != "ERROR"]
    family_counts = {
        family: sum(1 for entity in encounter_entities if entity.get("family") == family)
        for family in sorted(ENCOUNTER_FAMILIES)
    }
    fast_play_counts = {
        family: sum(
            1 for entity in encounter_entities
            if entity.get("family") == family
            and isinstance(entity.get("publicationData"), dict)
            and isinstance(entity["publicationData"].get("fastPlay"), dict)
        )
        for family in ("adversaries", "environments")
    }
    art_counts = {
        family: sum(
            1 for entity in encounter_entities
            if entity.get("family") == family
            and isinstance(entity.get("publicationData"), dict)
            and isinstance(entity["publicationData"].get("publicationArt"), dict)
        )
        for family in ("adversaries", "environments")
    }
    summary = {
        "schema": ENCOUNTER_SEMANTICS_SCHEMA,
        "families": sorted(ENCOUNTER_FAMILIES),
        "entityCounts": family_counts,
        "fastPlayCounts": fast_play_counts,
        "publicationArtCounts": art_counts,
        "publicationImageCount": staged_count,
        "warningCount": len(warnings),
        "errorCount": len(errors),
        "corpusMetrics": "metadata/encounter-corpus.json",
        "status": "FAIL" if errors else ("WARNING" if warnings else "PASS"),
    }
    sidecar["encounterSemantics"] = summary
    _write_json(sidecar_path, sidecar)

    if errors:
        add_check(
            report,
            "ENCOUNTER_PUBLICATION_SEMANTICS",
            "ERROR",
            f"Part VI semantic enrichment found {len(errors)} blocking issue(s) and {len(warnings)} warning(s).",
            issues[:300],
        )
    elif warnings:
        add_check(
            report,
            "ENCOUNTER_PUBLICATION_SEMANTICS",
            "WARNING",
            f"Part VI semantic enrichment completed with {len(warnings)} source-quality warning(s).",
            warnings[:300],
        )
    else:
        add_check(
            report,
            "ENCOUNTER_PUBLICATION_SEMANTICS",
            "PASS",
            "Part VI Adversary, Environment, and Adversary Feature publication semantics were enriched deterministically.",
            summary,
        )
    _write_json(validation_path, report)


def configure_step4_encounter_semantics(namespace: dict[str, Any]) -> None:
    """Install the Step 4 Part VI semantic/publication-art enrichment pass.

    The core normalizer continues to own canonical source selection and generic
    entity materialization. This additive pass projects Part VI data into a
    layout-safe structured view model, preserves Fast Play as ordered structured
    data, stages optional checked-in encounter artwork, and emits corpus metrics
    for deterministic Step 6 proof selection.
    """
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_encounter_semantics_patch", False):
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
        _postprocess_encounter_semantics(
            repo_root,
            outroot,
            config,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._encounter_semantics_patch = True
