from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rulebook_layout import class_package_compact as class_base
from rulebook_layout.class_package import compose_class_package
from rulebook_layout.class_package_batch import discover_class_package_targets
from rulebook_layout.class_package_refined import (
    _class_opening_tex as refined_class_opening_tex,
    _class_support_tex as refined_class_support_tex,
    _subclass_tex as refined_subclass_tex,
)
from rulebook_layout.domain_package import compose_domain_package
from rulebook_layout.domain_package_batch import discover_domain_package_targets
from rulebook_layout.domain_package_refined import (
    _identity_tex as domain_identity_tex,
    _level_tex as domain_level_tex,
    _style as domain_style,
)
from rulebook_layout.render_assets import prepare_lualatex_render_assets

SUPPORTED_SIDECAR_SCHEMA = "cybermancy-step4-structured-entities-v1.3"
CLASS_CONFIG_SCHEMA = "cybermancy-step6-class-package-config-v1.0"
DOMAIN_CONFIG_SCHEMA = "cybermancy-step6-domain-package-config-v1.0"
CLASS_AST_TARGET = "chapter12-family-classes-subclasses-replacement"
DOMAIN_AST_TARGET = "chapter14-family-domains-replacement"
CLASS_FAMILIES = ("classes", "subclasses")
DOMAIN_FAMILIES = ("domains",)
CLASS_SUBCLASS_MARKER = (
    "% family:subclasses rendered inside Chapter 12 ClassPackages in family:classes."
)


@dataclass(frozen=True)
class ClassStagePayload:
    classes_latex: str
    subclasses_latex: str
    class_count: int
    subclass_count: int

    def summary(self) -> dict[str, Any]:
        return {
            "chapter": 12,
            "families": list(CLASS_FAMILIES),
            "classCount": self.class_count,
            "subclassCount": self.subclass_count,
            "classesLatexSha256": hashlib.sha256(
                self.classes_latex.encode("utf-8")
            ).hexdigest(),
            "subclassesLatexSha256": hashlib.sha256(
                self.subclasses_latex.encode("utf-8")
            ).hexdigest(),
        }


@dataclass(frozen=True)
class DomainStagePayload:
    domains_latex: str
    domain_count: int
    card_count: int
    render_asset_count: int

    def summary(self) -> dict[str, Any]:
        return {
            "chapter": 14,
            "families": list(DOMAIN_FAMILIES),
            "domainCount": self.domain_count,
            "cardCount": self.card_count,
            "renderAssetCount": self.render_asset_count,
            "domainsLatexSha256": hashlib.sha256(
                self.domains_latex.encode("utf-8")
            ).hexdigest(),
        }


def _report(schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        "packages": [],
    }


def _check(
    report: dict[str, Any],
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
    item: dict[str, Any] = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def _target(contract: dict[str, Any], adapter: str) -> dict[str, Any] | None:
    rows = [
        row
        for row in contract.get("structuredTargets", [])
        if isinstance(row, dict) and row.get("adapter") == adapter
    ]
    return rows[0] if len(rows) == 1 else None


def _family_entities(sidecar: dict[str, Any], family: str) -> list[dict[str, Any]]:
    rows = sidecar.get("entities")
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict) and row.get("family") == family
    ]


def _render_class_body(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    work_dir: Path,
) -> str:
    """Render the accepted ClassPackage grammar without its standalone shell."""
    original = class_base._subclass_tex
    class_base._subclass_tex = refined_subclass_tex
    try:
        pieces = [
            r"\begingroup",
            r"\setlength{\parindent}{0pt}",
            r"\setlength{\parskip}{1.35mm}",
            r"\sffamily",
            r"\fontsize{10.5}{12.2}\selectfont",
            r"\frenchspacing",
            refined_class_opening_tex(view, config, source_root, work_dir),
            refined_class_support_tex(view["class"]),
        ]
        subclasses = (
            view.get("subclasses")
            if isinstance(view.get("subclasses"), list)
            else []
        )
        if subclasses:
            pieces.append(
                class_base._subclass_pages_tex(
                    subclasses, config, source_root, work_dir
                )
            )
        pieces.append(r"\endgroup")
        return "\n".join(pieces)
    finally:
        class_base._subclass_tex = original


def _domain_images(view: dict[str, Any]) -> list[str]:
    result: list[str] = []
    domain = view.get("domain") if isinstance(view.get("domain"), dict) else {}
    artwork = domain.get("artwork") if isinstance(domain.get("artwork"), dict) else {}
    image = str(artwork.get("image") or "").strip()
    if image:
        result.append(image)
    for level in view.get("levels", []):
        if not isinstance(level, dict):
            continue
        for card in level.get("cards", []):
            if not isinstance(card, dict):
                continue
            image = str(card.get("image") or "").strip()
            if image:
                result.append(image)
    return result


def _render_domain_body(
    view: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    work_dir: Path,
    render_assets: dict[str, str],
) -> str:
    """Render the accepted DomainPackage grammar without its standalone shell."""
    style = domain_style(config)
    pieces = [
        r"\begingroup",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0pt}",
        rf"\setlength{{\columnsep}}{{{style['column_sep']:.3f}in}}",
        r"\setlength{\multicolsep}{0pt}",
        r"\setlength{\columnseprule}{0pt}",
        rf"\addtolength{{\textheight}}{{-{style['page_bottom_safety_pt']:.2f}pt}}",
        r"\raggedbottom",
        r"\sffamily",
        domain_identity_tex(view, config, source_root, work_dir, render_assets),
    ]
    for row in view.get("levels", []):
        if isinstance(row, dict):
            pieces.append(
                domain_level_tex(row, config, source_root, work_dir, render_assets)
            )
    pieces.append(r"\endgroup")
    return "\n".join(pieces)


def compose_class_stage(
    sidecar: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    work_dir: Path,
    contract: dict[str, Any],
) -> tuple[ClassStagePayload | None, dict[str, Any]]:
    report = _report("cybermancy-step6-class-integration-compose-v1")
    target = _target(contract, "class-package")
    composition = (
        config.get("composition") if isinstance(config.get("composition"), dict) else {}
    )
    policy = (
        config.get("prototypePolicy")
        if isinstance(config.get("prototypePolicy"), dict)
        else {}
    )
    regression = contract.get("regressionExpectations", {}).get("classes", {})
    expected_classes = (
        int(regression.get("classes") or 0) if isinstance(regression, dict) else 0
    )
    expected_subclasses = (
        int(regression.get("subclasses") or 0)
        if isinstance(regression, dict)
        else 0
    )

    _check(
        report,
        "CLASS_STAGE_SIDECAR_SCHEMA",
        "PASS" if sidecar.get("schema") == SUPPORTED_SIDECAR_SCHEMA else "ERROR",
        "Current Step 4 sidecar schema loaded.",
        sidecar.get("schema"),
    )
    config_ok = (
        config.get("schema") == CLASS_CONFIG_SCHEMA
        and int(config.get("chapter") or 0) == 12
        and composition.get("primaryFamily") == "classes"
        and composition.get("nestedFamily") == "subclasses"
        and policy.get("astIntegration") == CLASS_AST_TARGET
    )
    _check(
        report,
        "CLASS_STAGE_CONFIG",
        "PASS" if config_ok else "ERROR",
        "Accepted Chapter 12 ClassPackage config loaded."
        if config_ok
        else "ClassPackage config differs from the accepted Chapter 12 contract.",
    )
    target_ok = (
        isinstance(target, dict)
        and int(target.get("chapter") or 0) == 12
        and target.get("families") == list(CLASS_FAMILIES)
    )
    _check(
        report,
        "CLASS_STAGE_TARGET",
        "PASS" if target_ok else "ERROR",
        "Chapter 12 targets family:classes plus family:subclasses exactly."
        if target_ok
        else "Chapter 12 structured target differs from the integration contract.",
        target,
    )
    regression_ok = expected_classes > 0 and expected_subclasses > 0
    _check(
        report,
        "CLASS_STAGE_REGRESSION_CONTRACT",
        "PASS" if regression_ok else "ERROR",
        f"Frozen Class corpus is {expected_classes} Classes / {expected_subclasses} Subclasses."
        if regression_ok
        else "Class regression counts are missing.",
    )

    classes = _family_entities(sidecar, "classes")
    subclasses = _family_entities(sidecar, "subclasses")
    counts_ok = (
        len(classes) == expected_classes and len(subclasses) == expected_subclasses
    )
    _check(
        report,
        "CLASS_STAGE_CORPUS_COUNTS",
        "PASS" if counts_ok else "ERROR",
        "Step 4 Class/Subclass counts match the frozen corpus."
        if counts_ok
        else "Step 4 Class/Subclass counts differ from the frozen corpus.",
        {"classes": len(classes), "subclasses": len(subclasses)},
    )
    if report["status"] != "PASS":
        return None, report

    try:
        targets = discover_class_package_targets(sidecar)
    except Exception as exc:
        _check(
            report,
            "CLASS_STAGE_DISCOVERY",
            "ERROR",
            f"ClassPackage target discovery failed: {exc}",
        )
        return None, report
    _check(
        report,
        "CLASS_STAGE_DISCOVERY",
        "PASS" if len(targets) == expected_classes else "ERROR",
        f"Discovered {len(targets)} ClassPackage targets.",
        targets,
    )
    if report["status"] != "PASS":
        return None, report

    rendered: list[str] = []
    seen_classes: list[str] = []
    seen_subclasses: list[str] = []
    for index, item in enumerate(targets):
        semantic_id = str(item["semanticId"])
        view, package_report = compose_class_package(
            sidecar, source_root, semantic_id, config
        )
        ok = package_report.get("status") == "PASS" and isinstance(view, dict)
        row: dict[str, Any] = {
            "semanticId": semantic_id,
            "name": item.get("name"),
            "status": "PASS" if ok else "FAIL",
            "report": package_report,
        }
        report["packages"].append(row)
        if not ok or not isinstance(view, dict):
            _check(
                report,
                "CLASS_STAGE_PACKAGE",
                "ERROR",
                f"ClassPackage composition failed for {item.get('name') or semantic_id}.",
                row,
            )
            continue

        cls = view.get("class") if isinstance(view.get("class"), dict) else {}
        seen_classes.append(str(cls.get("semanticId") or ""))
        package_subclasses = [
            sub for sub in view.get("subclasses", []) if isinstance(sub, dict)
        ]
        seen_subclasses.extend(
            str(sub.get("semanticId") or "") for sub in package_subclasses
        )
        body = _render_class_body(view, config, source_root, work_dir)
        if index:
            rendered.append(r"\clearpage")
        rendered.append(body)
        row["subclassCount"] = len(package_subclasses)
        row["latexSha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    expected_class_ids = sorted(str(row.get("semanticId") or "") for row in classes)
    expected_subclass_ids = sorted(
        str(row.get("semanticId") or "") for row in subclasses
    )
    coverage_ok = (
        len(seen_classes) == expected_classes
        and len(set(seen_classes)) == expected_classes
        and sorted(seen_classes) == expected_class_ids
        and len(seen_subclasses) == expected_subclasses
        and len(set(seen_subclasses)) == expected_subclasses
        and sorted(seen_subclasses) == expected_subclass_ids
    )
    _check(
        report,
        "CLASS_STAGE_COVERAGE",
        "PASS" if coverage_ok else "ERROR",
        "Every Class and Subclass is consumed exactly once by Chapter 12 ClassPackages."
        if coverage_ok
        else "ClassPackage coverage omitted, duplicated, or misassigned a Class/Subclass.",
    )
    complete = (
        report["status"] == "PASS"
        and len(rendered) == expected_classes * 2 - 1
    )
    _check(
        report,
        "CLASS_STAGE_COMPOSITION",
        "PASS" if complete else "ERROR",
        "Composed the complete Chapter 12 ClassPackage body without a standalone shell."
        if complete
        else "Chapter 12 ClassPackage composition is incomplete.",
    )
    if not complete:
        return None, report

    payload = ClassStagePayload(
        "\n".join(rendered),
        CLASS_SUBCLASS_MARKER,
        expected_classes,
        expected_subclasses,
    )
    report["payload"] = payload.summary()
    return payload, report


def compose_domain_stage(
    sidecar: dict[str, Any],
    config: dict[str, Any],
    source_root: Path,
    work_dir: Path,
    contract: dict[str, Any],
) -> tuple[DomainStagePayload | None, dict[str, Any]]:
    report = _report("cybermancy-step6-domain-integration-compose-v1")
    target = _target(contract, "domain-package")
    lifecycle = (
        config.get("lifecycle") if isinstance(config.get("lifecycle"), dict) else {}
    )
    acceptance = (
        lifecycle.get("acceptance")
        if isinstance(lifecycle.get("acceptance"), dict)
        else {}
    )
    policy = (
        config.get("prototypePolicy")
        if isinstance(config.get("prototypePolicy"), dict)
        else {}
    )
    regression = contract.get("regressionExpectations", {}).get("domains", {})
    expected_domains = (
        int(regression.get("domains") or 0) if isinstance(regression, dict) else 0
    )
    expected_cards = (
        int(regression.get("cards") or 0) if isinstance(regression, dict) else 0
    )

    _check(
        report,
        "DOMAIN_STAGE_SIDECAR_SCHEMA",
        "PASS" if sidecar.get("schema") == SUPPORTED_SIDECAR_SCHEMA else "ERROR",
        "Current Step 4 sidecar schema loaded.",
        sidecar.get("schema"),
    )
    config_ok = (
        config.get("schema") == DOMAIN_CONFIG_SCHEMA
        and int(config.get("chapter") or 0) == 14
        and lifecycle.get("status") == "frozen"
        and policy.get("astIntegration") == DOMAIN_AST_TARGET
    )
    _check(
        report,
        "DOMAIN_STAGE_CONFIG",
        "PASS" if config_ok else "ERROR",
        "Frozen Chapter 14 DomainPackage config loaded."
        if config_ok
        else "DomainPackage config differs from the frozen Chapter 14 contract.",
    )
    target_ok = (
        isinstance(target, dict)
        and int(target.get("chapter") or 0) == 14
        and target.get("families") == list(DOMAIN_FAMILIES)
    )
    _check(
        report,
        "DOMAIN_STAGE_TARGET",
        "PASS" if target_ok else "ERROR",
        "Chapter 14 targets family:domains exactly."
        if target_ok
        else "Chapter 14 structured target differs from the integration contract.",
        target,
    )
    regression_ok = (
        expected_domains > 0
        and expected_cards > 0
        and int(acceptance.get("domainCount") or 0) == expected_domains
        and int(acceptance.get("cardCount") or 0) == expected_cards
    )
    _check(
        report,
        "DOMAIN_STAGE_REGRESSION_CONTRACT",
        "PASS" if regression_ok else "ERROR",
        f"Frozen Domain corpus is {expected_domains} Domains / {expected_cards} Domain Cards."
        if regression_ok
        else "Domain acceptance counts differ from the integration contract.",
        acceptance,
    )
    if report["status"] != "PASS":
        return None, report

    try:
        targets = discover_domain_package_targets(sidecar)
    except Exception as exc:
        _check(
            report,
            "DOMAIN_STAGE_DISCOVERY",
            "ERROR",
            f"DomainPackage target discovery failed: {exc}",
        )
        return None, report
    actual_cards = sum(int(item.get("cardCount") or 0) for item in targets)
    discovery_ok = len(targets) == expected_domains and actual_cards == expected_cards
    _check(
        report,
        "DOMAIN_STAGE_DISCOVERY",
        "PASS" if discovery_ok else "ERROR",
        f"Discovered {len(targets)} DomainPackages / {actual_cards} Domain Cards.",
        targets,
    )
    if report["status"] != "PASS":
        return None, report

    views: list[tuple[dict[str, Any], dict[str, Any]]] = []
    images: list[str] = []
    for item in targets:
        key = str(item["domainKey"])
        view, package_report = compose_domain_package(sidecar, source_root, key, config)
        ok = package_report.get("status") == "PASS" and isinstance(view, dict)
        row: dict[str, Any] = {
            "domainKey": key,
            "name": item.get("name"),
            "status": "PASS" if ok else "FAIL",
            "report": package_report,
        }
        report["packages"].append(row)
        if not ok or not isinstance(view, dict):
            _check(
                report,
                "DOMAIN_STAGE_PACKAGE",
                "ERROR",
                f"DomainPackage composition failed for {item.get('name') or key}.",
                row,
            )
            continue
        views.append((view, row))
        images.extend(_domain_images(view))
    if report["status"] != "PASS":
        return None, report

    render_assets, asset_report = prepare_lualatex_render_assets(
        images,
        source_root,
        work_dir / "domain-render-assets",
    )
    _check(
        report,
        "DOMAIN_STAGE_RENDER_ASSETS",
        "PASS" if asset_report.get("status") == "PASS" else "ERROR",
        "Prepared integrated DomainPackage render assets."
        if asset_report.get("status") == "PASS"
        else "DomainPackage render-asset preparation failed.",
        asset_report,
    )
    if report["status"] != "PASS":
        return None, report

    rendered: list[str] = []
    rendered_cards = 0
    for index, (view, row) in enumerate(views):
        body = _render_domain_body(
            view, config, source_root, work_dir, render_assets
        )
        if index:
            rendered.append(r"\clearpage")
        rendered.append(body)
        cards = sum(
            len(level.get("cards", []))
            for level in view.get("levels", [])
            if isinstance(level, dict)
        )
        rendered_cards += cards
        row["renderedCardCount"] = cards
        row["latexSha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    coverage_ok = len(views) == expected_domains and rendered_cards == expected_cards
    _check(
        report,
        "DOMAIN_STAGE_COVERAGE",
        "PASS" if coverage_ok else "ERROR",
        "Every DomainPackage and Domain Card is rendered exactly once in Chapter 14."
        if coverage_ok
        else "DomainPackage coverage omitted or duplicated content.",
    )
    complete = (
        report["status"] == "PASS"
        and len(rendered) == expected_domains * 2 - 1
    )
    _check(
        report,
        "DOMAIN_STAGE_COMPOSITION",
        "PASS" if complete else "ERROR",
        "Composed the complete Chapter 14 DomainPackage body without a standalone shell."
        if complete
        else "Chapter 14 DomainPackage composition is incomplete.",
    )
    if not complete:
        return None, report

    payload = DomainStagePayload(
        "\n".join(rendered),
        expected_domains,
        expected_cards,
        len(render_assets),
    )
    report["payload"] = payload.summary()
    return payload, report
