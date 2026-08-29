from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

FEATURE_EQUIVALENCE_SCHEMA = "cybermancy-step4-adversary-feature-equivalence-audit-v1.0"
FEATURE_FAMILY = "adversaries-features"
FUZZY_SEQUENCE_THRESHOLD = 0.90
FUZZY_TOKEN_JACCARD_THRESHOLD = 0.75

_WS_RE = re.compile(r"\s+")
_MARKDOWN_PUNCT_RE = re.compile(r"[*`_]+")
_TRIVIAL_PUNCT_RE = re.compile(r"[^\w\s+\-/%=]+", re.UNICODE)
_LETTER_HYPHEN_RE = re.compile(r"(?<=[^\W\d_])-(?=[^\W\d_])", re.UNICODE)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _surface_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return _WS_RE.sub(" ", text).strip()


def _trivial_text(value: Any) -> str:
    text = _surface_text(value).casefold()
    text = _MARKDOWN_PUNCT_RE.sub("", text)
    text = text.replace("'", "")
    text = _LETTER_HYPHEN_RE.sub(" ", text)
    text = _TRIVIAL_PUNCT_RE.sub(" ", text)
    text = re.sub(r"\s*([+\-/%=])\s*", r"\1", text)
    return _WS_RE.sub(" ", text).strip()


def _name_key(value: Any) -> str:
    return _trivial_text(value)


def _canonical_structure(value: Any, *, trivial: bool) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _canonical_structure(val, trivial=trivial)
            for key, val in sorted(value.items(), key=lambda pair: str(pair[0]))
            if key not in {"sourceId", "semanticId", "_id"} and val not in (None, "", [], {})
        }
    if isinstance(value, list):
        return [_canonical_structure(item, trivial=trivial) for item in value]
    if isinstance(value, str):
        return _trivial_text(value) if trivial else _surface_text(value)
    return value


def _rules_text(entity: dict) -> str:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    return str(pdata.get("rulesMarkdown") or pdata.get("descriptionMarkdown") or pdata.get("description") or "")


def _actions(entity: dict) -> list[dict]:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    actions = pdata.get("actions")
    return [action for action in actions if isinstance(action, dict)] if isinstance(actions, list) else []


def _exact_action_payload(action: dict) -> dict:
    return _canonical_structure(action, trivial=False)


def _trivial_action_payload(action: dict, feature_rules: str) -> dict | None:
    rules = _trivial_text(action.get("rulesMarkdown") or action.get("description") or "")
    mechanics = {
        key: _canonical_structure(action.get(key), trivial=True)
        for key in ("cost", "uses", "range", "target", "damage")
        if action.get(key) not in (None, "", [], {})
    }
    # Foundry frequently stores a display/action mirror whose only meaningful
    # text repeats the Feature body. Treat that as serialization, not a second rule.
    if not mechanics and rules and rules == feature_rules:
        return None

    payload: dict[str, Any] = {}
    action_type = action.get("actionType") or action.get("type")
    if action_type not in (None, ""):
        payload["actionType"] = _trivial_text(action_type)
    if rules:
        payload["rules"] = rules
    payload.update(mechanics)
    return payload or None


def _exact_payload(entity: dict) -> dict:
    actions = [_exact_action_payload(action) for action in _actions(entity)]
    actions.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return {
        "name": _surface_text(entity.get("name")),
        "rules": _surface_text(_rules_text(entity)),
        "actions": actions,
    }


def _trivial_payload(entity: dict) -> dict:
    rules = _trivial_text(_rules_text(entity))
    actions = []
    for action in _actions(entity):
        payload = _trivial_action_payload(action, rules)
        if payload is not None:
            actions.append(payload)
    actions.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return {
        "nameKey": _name_key(entity.get("name")),
        "rules": rules,
        "actions": actions,
    }


def _signature(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _information_score(entity: dict) -> tuple[int, int, str]:
    rules = _surface_text(_rules_text(entity))
    actions = _actions(entity)
    semantic_fields = sum(
        1
        for action in actions
        for key in ("cost", "uses", "range", "target", "damage")
        if action.get(key) not in (None, "", [], {})
    )
    return (len(rules), semantic_fields + len(actions), str(entity.get("semanticId") or ""))


def _recommended_representative(members: list[dict]) -> dict:
    ordered = sorted(
        members,
        key=lambda entity: (
            -_information_score(entity)[0],
            -_information_score(entity)[1],
            str(entity.get("semanticId") or ""),
        ),
    )
    return ordered[0]


def _comparison_text(entity: dict) -> str:
    payload = _trivial_payload(entity)
    action_text = " ".join(json.dumps(action, sort_keys=True, ensure_ascii=False) for action in payload["actions"])
    return _WS_RE.sub(" ", f"{payload['rules']} {action_text}").strip()


def _token_jaccard(left: str, right: str) -> float:
    a = set(left.split())
    b = set(right.split())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _member_record(entity: dict) -> dict:
    pdata = entity.get("publicationData") if isinstance(entity.get("publicationData"), dict) else {}
    actions = pdata.get("actions") if isinstance(pdata.get("actions"), list) else []
    return {
        "semanticId": entity.get("semanticId"),
        "name": entity.get("name"),
        "sourcePath": entity.get("sourcePath"),
        "rulesPreview": _surface_text(_rules_text(entity))[:320],
        "actionNames": [
            str(action.get("name") or action.get("actionType") or action.get("type") or "Action")
            for action in actions
            if isinstance(action, dict)
        ],
    }


def build_feature_equivalence_audit(entities: list[dict]) -> dict:
    features = sorted(
        [
            entity
            for entity in entities
            if isinstance(entity, dict) and str(entity.get("family") or "") == FEATURE_FAMILY
        ],
        key=lambda entity: str(entity.get("semanticId") or ""),
    )

    by_trivial: dict[str, list[dict]] = {}
    exact_signatures: dict[str, str] = {}
    for entity in features:
        semantic_id = str(entity.get("semanticId") or "")
        exact_signatures[semantic_id] = _signature(_exact_payload(entity))
        trivial_signature = _signature(_trivial_payload(entity))
        by_trivial.setdefault(trivial_signature, []).append(entity)

    groups: list[dict] = []
    unit_records: list[dict] = []
    auto_member_ids: set[str] = set()
    exact_group_count = 0
    trivial_group_count = 0
    auto_redundant = 0

    for trivial_signature, members in sorted(by_trivial.items()):
        if len(members) > 1:
            exact_count = len({exact_signatures[str(member.get("semanticId") or "")] for member in members})
            level = "exact" if exact_count == 1 else "trivial"
            if level == "exact":
                exact_group_count += 1
            else:
                trivial_group_count += 1
            representative = _recommended_representative(members)
            group_id = f"afeq-{trivial_signature[:12]}"
            member_ids = [str(member.get("semanticId") or "") for member in members]
            auto_member_ids.update(member_ids)
            auto_redundant += len(members) - 1
            groups.append(
                {
                    "groupId": group_id,
                    "equivalenceLevel": level,
                    "normalizedName": _name_key(representative.get("name")),
                    "memberCount": len(members),
                    "memberSemanticIds": member_ids,
                    "recommendedRepresentativeSemanticId": representative.get("semanticId"),
                    "recommendedRepresentativeName": representative.get("name"),
                    "representativePolicy": "highest publication information score; semanticId tie-breaker",
                    "exactSignatureCount": exact_count,
                    "members": [_member_record(member) for member in members],
                }
            )
            unit_records.append(
                {
                    "unitId": group_id,
                    "representative": representative,
                    "memberSemanticIds": member_ids,
                    "trivialSignature": trivial_signature,
                }
            )
        else:
            entity = members[0]
            unit_records.append(
                {
                    "unitId": str(entity.get("semanticId") or ""),
                    "representative": entity,
                    "memberSemanticIds": [str(entity.get("semanticId") or "")],
                    "trivialSignature": trivial_signature,
                }
            )

    candidate_pairs: list[dict] = []
    units_by_name: dict[str, list[dict]] = {}
    for unit in unit_records:
        representative = unit["representative"]
        units_by_name.setdefault(_name_key(representative.get("name")), []).append(unit)

    for name_key, units in sorted(units_by_name.items()):
        ordered_units = sorted(units, key=lambda unit: str(unit["unitId"]))
        for i, left in enumerate(ordered_units):
            for right in ordered_units[i + 1 :]:
                if left["trivialSignature"] == right["trivialSignature"]:
                    continue
                left_entity = left["representative"]
                right_entity = right["representative"]
                left_text = _comparison_text(left_entity)
                right_text = _comparison_text(right_entity)
                sequence = SequenceMatcher(None, left_text, right_text).ratio()
                jaccard = _token_jaccard(left_text, right_text)
                if sequence < FUZZY_SEQUENCE_THRESHOLD or jaccard < FUZZY_TOKEN_JACCARD_THRESHOLD:
                    continue
                pair_seed = "|".join(sorted([str(left["unitId"]), str(right["unitId"])]))
                pair_id = "afcand-" + hashlib.sha256(pair_seed.encode("utf-8")).hexdigest()[:12]
                candidate_pairs.append(
                    {
                        "pairId": pair_id,
                        "normalizedName": name_key,
                        "left": {
                            "unitId": left["unitId"],
                            "representativeSemanticId": left_entity.get("semanticId"),
                            "representativeName": left_entity.get("name"),
                            "memberSemanticIds": left["memberSemanticIds"],
                            "rulesPreview": _surface_text(_rules_text(left_entity))[:320],
                        },
                        "right": {
                            "unitId": right["unitId"],
                            "representativeSemanticId": right_entity.get("semanticId"),
                            "representativeName": right_entity.get("name"),
                            "memberSemanticIds": right["memberSemanticIds"],
                            "rulesPreview": _surface_text(_rules_text(right_entity))[:320],
                        },
                        "sequenceSimilarity": round(sequence, 4),
                        "tokenJaccard": round(jaccard, 4),
                        "decision": "review",
                        "reason": "same normalized Feature name with highly similar but non-equivalent publication semantics",
                    }
                )

    source_count = len(features)
    summary = {
        "sourceFeatureCount": source_count,
        "autoEquivalentGroupCount": len(groups),
        "exactEquivalentGroupCount": exact_group_count,
        "trivialEquivalentGroupCount": trivial_group_count,
        "autoEquivalentEntityCount": len(auto_member_ids),
        "autoRedundantEntityCount": auto_redundant,
        "provisionalRepresentativeCount": source_count - auto_redundant,
        "reviewCandidatePairCount": len(candidate_pairs),
        "ungroupedFeatureCount": source_count - len(auto_member_ids),
        "reviewStatus": "REVIEW_REQUIRED" if groups or candidate_pairs else "CLEAR",
    }
    return {
        "schema": FEATURE_EQUIVALENCE_SCHEMA,
        "policy": {
            "scope": FEATURE_FAMILY,
            "canonicalSourceMutation": False,
            "publicationMutation": False,
            "exactAndTrivialGroupsAreRecommendationsOnly": True,
            "fuzzyCandidatesNeverAutoCollapse": True,
            "fuzzySequenceThreshold": FUZZY_SEQUENCE_THRESHOLD,
            "fuzzyTokenJaccardThreshold": FUZZY_TOKEN_JACCARD_THRESHOLD,
        },
        "summary": summary,
        "autoEquivalentGroups": groups,
        "reviewCandidatePairs": candidate_pairs,
    }


def render_feature_equivalence_review_markdown(audit: dict) -> str:
    summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    lines = [
        "# Adversary Feature Publication Equivalence Audit",
        "",
        "This is a Step 4 publication audit. It does **not** delete or alter canonical Foundry Feature entities.",
        "No Chapter 32 deduplication is applied until equivalence decisions are reviewed and approved.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, label in (
        ("sourceFeatureCount", "Canonical standalone Features"),
        ("autoEquivalentGroupCount", "Exact/trivial equivalence groups"),
        ("exactEquivalentGroupCount", "Exact groups"),
        ("trivialEquivalentGroupCount", "Trivial-normalization groups"),
        ("autoRedundantEntityCount", "Potential redundant publication entries"),
        ("provisionalRepresentativeCount", "Provisional representatives after safe groups"),
        ("reviewCandidatePairCount", "Fuzzy review candidate pairs"),
    ):
        lines.append(f"| {label} | {summary.get(key, 0)} |")

    lines.extend(["", "## Exact / trivial equivalence groups", ""])
    groups = audit.get("autoEquivalentGroups") if isinstance(audit.get("autoEquivalentGroups"), list) else []
    if not groups:
        lines.append("_No exact or trivial equivalence groups detected._")
    for group in groups:
        lines.extend(
            [
                f"### {group.get('groupId')} — {group.get('recommendedRepresentativeName')} ({group.get('equivalenceLevel')})",
                "",
                f"Recommended representative: `{group.get('recommendedRepresentativeSemanticId')}`",
                "",
            ]
        )
        for member in group.get("members") or []:
            lines.append(
                f"- `{member.get('semanticId')}` — **{member.get('name')}** — `{member.get('sourcePath')}`"
            )
            preview = str(member.get("rulesPreview") or "").strip()
            if preview:
                lines.append(f"  - Rules: {preview}")
            actions = member.get("actionNames") if isinstance(member.get("actionNames"), list) else []
            if actions:
                lines.append(f"  - Actions: {', '.join(str(value) for value in actions)}")
        lines.append("")

    lines.extend(["## Fuzzy review candidates", ""])
    candidates = audit.get("reviewCandidatePairs") if isinstance(audit.get("reviewCandidatePairs"), list) else []
    if not candidates:
        lines.append("_No fuzzy review candidates detected._")
    for pair in candidates:
        left = pair.get("left") if isinstance(pair.get("left"), dict) else {}
        right = pair.get("right") if isinstance(pair.get("right"), dict) else {}
        lines.extend(
            [
                f"### {pair.get('pairId')} — {pair.get('normalizedName')}",
                "",
                f"Similarity: sequence `{pair.get('sequenceSimilarity')}`; token Jaccard `{pair.get('tokenJaccard')}`",
                "",
                f"- Left: `{left.get('representativeSemanticId')}` — **{left.get('representativeName')}**",
                f"  - {left.get('rulesPreview') or ''}",
                f"- Right: `{right.get('representativeSemanticId')}` — **{right.get('representativeName')}**",
                f"  - {right.get('rulesPreview') or ''}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_feature_equivalence_artifacts(
    sidecar: dict,
    audit_path: Path,
    review_path: Path,
) -> dict:
    entities = sidecar.get("entities") if isinstance(sidecar.get("entities"), list) else []
    audit = build_feature_equivalence_audit(entities)
    _write_json(audit_path, audit)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(render_feature_equivalence_review_markdown(audit), encoding="utf-8")
    return audit


def _postprocess_feature_equivalence(
    repo_root: Path,
    outroot: Path,
    config: dict,
    report: dict,
    *,
    add_check,
) -> None:
    del repo_root, config
    metadata_root = outroot / "source" / "metadata"
    sidecar_path = metadata_root / "structured-entities.json"
    validation_path = metadata_root / "validation.json"
    audit_path = metadata_root / "adversary-feature-equivalence-audit.json"
    review_path = metadata_root / "adversary-feature-equivalence-review.md"

    if not sidecar_path.is_file():
        add_check(
            report,
            "ADVERSARY_FEATURE_EQUIVALENCE_AUDIT",
            "ERROR",
            "Step 4 structured-entities sidecar is missing; Feature equivalence audit could not run.",
            {"path": str(sidecar_path)},
        )
        _write_json(validation_path, report)
        return

    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(
            report,
            "ADVERSARY_FEATURE_EQUIVALENCE_AUDIT",
            "ERROR",
            f"Could not load Step 4 structured-entities sidecar: {exc}",
        )
        _write_json(validation_path, report)
        return

    audit = write_feature_equivalence_artifacts(sidecar, audit_path, review_path)
    summary = audit["summary"]
    encounter = sidecar.get("encounterSemantics") if isinstance(sidecar.get("encounterSemantics"), dict) else {}
    encounter["adversaryFeatureEquivalence"] = {
        "schema": FEATURE_EQUIVALENCE_SCHEMA,
        "status": summary["reviewStatus"],
        "audit": "metadata/adversary-feature-equivalence-audit.json",
        "review": "metadata/adversary-feature-equivalence-review.md",
        **{key: value for key, value in summary.items() if key != "reviewStatus"},
    }
    sidecar["encounterSemantics"] = encounter
    _write_json(sidecar_path, sidecar)

    add_check(
        report,
        "ADVERSARY_FEATURE_EQUIVALENCE_AUDIT",
        "PASS",
        (
            "Adversary Feature publication-equivalence audit completed without mutating canonical entities "
            "or Chapter 32 selection."
        ),
        encounter["adversaryFeatureEquivalence"],
    )
    _write_json(validation_path, report)


def configure_step4_feature_equivalence(namespace: dict[str, Any]) -> None:
    del namespace
    import rulebook_normalize.pipeline as pipeline

    if getattr(pipeline, "_feature_equivalence_patch", False):
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
        _postprocess_feature_equivalence(
            repo_root,
            outroot,
            config,
            report,
            add_check=pipeline.add_check,
        )
        return report

    pipeline.materialize = materialize
    pipeline._feature_equivalence_patch = True
