from __future__ import annotations

import copy
from typing import Any

from rulebook_layout.ice_reference import compose_ice_reference
from rulebook_layout.ice_reference_refined import _chapter_header, _group_tex
from rulebook_layout.projection_authority import (
    sidecar_ice_projection_state,
    validate_projection_authority_descriptor,
)


def runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    """Translate the frozen v1 publication contract to legacy internal keys.

    H2/H3 used ``prototype`` / ``prototypePolicy`` internally. The frozen v1
    contract removes that terminology, but the accepted semantic composer and
    image reconciler remain stable. Legacy synthetic test configs are passed
    through unchanged so the freeze does not invalidate historical unit fixtures.
    """
    if "selection" not in config and "publicationPolicy" not in config:
        return copy.deepcopy(config)

    result = copy.deepcopy(config)
    selection = result.get("selection") if isinstance(result.get("selection"), dict) else {}
    policy = result.get("publicationPolicy") if isinstance(result.get("publicationPolicy"), dict) else {}
    result["prototype"] = {
        "mode": str(selection.get("mode") or "full-corpus"),
    }
    if isinstance(selection.get("semanticIds"), list):
        result["prototype"]["semanticIds"] = list(selection["semanticIds"])
    result["prototypePolicy"] = copy.deepcopy(policy)
    return result


def _productionize_report(report: dict[str, Any]) -> None:
    replacements = {
        "ICE_REFERENCE_PROOF_COUNT": "ICE_REFERENCE_SELECTION_COUNT",
        "ICE_REFERENCE_PROTOTYPE_DUPLICATE": "ICE_REFERENCE_SELECTION_DUPLICATE",
        "ICE_REFERENCE_PROTOTYPE_SCOPE": "ICE_REFERENCE_SELECTION_SCOPE",
    }
    for collection in ("checks", "errors", "warnings"):
        rows = report.get(collection)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "")
            if code in replacements:
                row["code"] = replacements[code]
            message = str(row.get("message") or "")
            message = message.replace("H2 prototype", "ICEReferencePackage")
            message = message.replace("H2 proof", "ICEReferencePackage")
            message = message.replace("H2 contract", "ICEReferencePackage contract")
            row["message"] = message


def _projection_check(
    sidecar: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    policy = (
        config.get("publicationPolicy")
        if isinstance(config.get("publicationPolicy"), dict)
        else {}
    )
    errors = validate_projection_authority_descriptor(
        "ice", policy.get("projectionAuthority")
    )
    if errors:
        return None, errors
    try:
        return sidecar_ice_projection_state(sidecar), []
    except Exception as exc:
        return None, [str(exc)]


def compose_ice_reference_package(
    sidecar: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    """Compose ICEReferencePackage v1 from Step 4 normalized semantics."""
    projection, projection_errors = _projection_check(sidecar, config)
    compat = runtime_config(config)
    view, report = compose_ice_reference(sidecar, compat)
    _productionize_report(report)

    projection_check: dict[str, Any] = {
        "code": "ICE_REFERENCE_PROJECTION_AUTHORITY",
        "status": "ERROR" if projection_errors else "PASS",
        "message": (
            "ICEReferencePackage projection authority failed."
            if projection_errors
            else "ICEReferencePackage consumes the complete validated dynamic Step 4 ICE projection."
        ),
    }
    projection_check["details"] = projection_errors or projection
    report.setdefault("checks", []).append(projection_check)
    if projection_errors:
        report["status"] = "FAIL"
        report.setdefault("errors", []).append(projection_check)
        view = None

    if view is not None:
        package = view.pop("prototype", {})
        if not isinstance(package, dict):
            package = {}
        lifecycle = config.get("lifecycle") if isinstance(config.get("lifecycle"), dict) else {}
        selection = config.get("selection") if isinstance(config.get("selection"), dict) else {}
        package["version"] = str(lifecycle.get("version") or "v1.0")
        package["status"] = str(lifecycle.get("status") or "test-fixture")
        package["mode"] = str(selection.get("mode") or package.get("mode") or "full-corpus")
        if projection is not None:
            package["sourceFeatureCount"] = projection["sourceCount"]
            package["entryCount"] = projection["projectedCount"]
            package["groupCounts"] = dict(projection["groupCounts"])
        view["package"] = package
    return view, report, compat


def render_integration_fragments(
    view: dict[str, Any],
    config: dict[str, Any],
    render_assets: dict[str, str],
) -> tuple[str, str]:
    """Return the accepted Chapter 29 header and family body LaTeX fragments."""
    header = _chapter_header(view, config)
    groups = [row for row in view.get("groups", []) if isinstance(row, dict)]
    body = "\n".join(_group_tex(group, config, render_assets) for group in groups)
    return header, body


def _header_identifier(node: dict[str, Any]) -> str:
    if node.get("t") != "Header":
        return ""
    content = node.get("c")
    if not (isinstance(content, list) and len(content) >= 2):
        return ""
    attr = content[1]
    if not (isinstance(attr, list) and len(attr) == 3):
        return ""
    return str(attr[0] or "")


def _div_identifier(node: dict[str, Any]) -> str:
    if node.get("t") != "Div":
        return ""
    content = node.get("c")
    if not (isinstance(content, list) and len(content) == 2):
        return ""
    attr = content[0]
    if not (isinstance(attr, list) and len(attr) == 3):
        return ""
    return str(attr[0] or "")


def integrate_chapter29_ast(
    ast: dict[str, Any],
    header_latex: str,
    body_latex: str,
) -> dict[str, int]:
    """Replace Chapter 29's normalized heading and Feature-family body.

    Step 3 owns the Chapter 29 placement and Step 4 owns the ``family:features``
    publication container. Integration replaces exactly one Chapter 29 Header
    and exactly one Feature-family Div body. The Feature family outside this
    independent GM publication remains normalized upstream for dependent rules.
    """
    header_ids = {
        "ch29-ice-reference",
        "section:ch29-ice-reference",
        r"section\:ch29-ice-reference",
    }
    counts = {"chapterHeader": 0, "familyFeatures": 0}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            ident = _header_identifier(value)
            if ident in header_ids:
                value.clear()
                value.update({"t": "RawBlock", "c": ["latex", header_latex]})
                counts["chapterHeader"] += 1
                return
            if _div_identifier(value) == "family:features":
                value["c"][1] = [{"t": "RawBlock", "c": ["latex", body_latex]}]
                counts["familyFeatures"] += 1
                return
            for child in list(value.values()):
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(ast)
    return counts
