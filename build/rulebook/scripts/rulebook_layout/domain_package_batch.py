from __future__ import annotations

import re
from typing import Any, Iterable

from .domain_package_refined import domain_package_output_stem


def slugify_domain_name(name: Any) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(name or "").casefold()).strip("-")
    return value or "domain"


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("+-").isdigit():
            return int(text)
    return None


def validate_domain_package_membership(
    sidecar: dict[str, Any], expected_semantic_ids: Iterable[str]
) -> dict[str, Any]:
    """Reconcile DomainPackage card membership to authoritative Step 4 identities."""
    packages = sidecar.get("domainPackages")
    report: dict[str, Any] = {
        "status": "PASS",
        "packageCount": 0,
        "membershipCount": 0,
        "duplicates": [],
        "missing": [],
        "extra": [],
        "errors": [],
    }
    if not isinstance(packages, list):
        report["status"] = "FAIL"
        report["errors"].append("Step 4 sidecar has no domainPackages array.")
        return report

    membership: list[str] = []
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            report["errors"].append(f"domainPackages[{index}] is not an object.")
            continue
        cards = package.get("cards")
        if not isinstance(cards, list):
            report["errors"].append(
                f"domainPackages[{index}] ({package.get('domainKey')!r}) has no cards array."
            )
            continue
        for card_index, value in enumerate(cards):
            semantic_id = str(value or "").strip()
            if not semantic_id:
                report["errors"].append(
                    f"domainPackages[{index}].cards[{card_index}] has no semantic identity."
                )
            else:
                membership.append(semantic_id)

    expected = [str(value or "").strip() for value in expected_semantic_ids]
    expected_set = set(expected)
    membership_set = set(membership)
    report["packageCount"] = len(packages)
    report["membershipCount"] = len(membership)
    report["duplicates"] = sorted(
        {semantic_id for semantic_id in membership if membership.count(semantic_id) > 1}
    )
    report["missing"] = sorted(expected_set - membership_set)
    report["extra"] = sorted(membership_set - expected_set)
    if (
        report["errors"]
        or report["duplicates"]
        or report["missing"]
        or report["extra"]
        or len(membership) != len(expected)
    ):
        report["status"] = "FAIL"
    return report


def discover_domain_package_targets(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    """Discover every Step 4 DomainPackage without hard-coding Domain keys.

    Discovery is intentionally based on the normalized ``domainPackages``
    publication structure rather than the flat Domain entity family or Foundry
    folder hierarchy. It also reconciles package/card totals with the Step 4
    Domain semantics summary when those counts are available.
    """
    packages = sidecar.get("domainPackages")
    if not isinstance(packages, list):
        raise ValueError("Step 4 sidecar has no domainPackages array.")

    targets: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    seen_slugs: set[str] = set()
    total_cards = 0

    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            raise ValueError(f"domainPackages[{index}] is not an object.")

        domain_key = str(package.get("domainKey") or "").strip().casefold()
        name = str(package.get("name") or "").strip()
        card_count = _integer(package.get("cardCount"))
        cards = package.get("cards")

        if not domain_key:
            raise ValueError(f"domainPackages[{index}] is missing domainKey.")
        if not name:
            raise ValueError(f"DomainPackage {domain_key!r} is missing name.")
        if domain_key in seen_keys:
            raise ValueError(f"Duplicate DomainPackage domainKey in Step 4 sidecar: {domain_key}")
        if card_count is None or card_count < 0:
            raise ValueError(f"DomainPackage {domain_key!r} has invalid cardCount.")
        if not isinstance(cards, list):
            raise ValueError(f"DomainPackage {domain_key!r} has no cards array.")
        if len(cards) != card_count:
            raise ValueError(
                f"DomainPackage {domain_key!r} declares {card_count} card(s) but contains {len(cards)} card reference(s)."
            )

        slug = slugify_domain_name(name)
        if slug in seen_slugs:
            raise ValueError(f"Duplicate DomainPackage output slug in Step 4 sidecar: {slug}")

        seen_keys.add(domain_key)
        seen_slugs.add(slug)
        total_cards += card_count
        targets.append(
            {
                "domainKey": domain_key,
                "name": name,
                "slug": slug,
                "cardCount": card_count,
                "outputStem": domain_package_output_stem(name),
            }
        )

    if not targets:
        raise ValueError("Step 4 sidecar contains no DomainPackages.")

    semantics = sidecar.get("domainSemantics")
    if isinstance(semantics, dict):
        expected_domains = _integer(semantics.get("domainCount"))
        expected_cards = _integer(semantics.get("cardCount"))
        if expected_domains is not None and expected_domains != len(targets):
            raise ValueError(
                f"Step 4 domainSemantics.domainCount is {expected_domains}, but domainPackages contains {len(targets)} package(s)."
            )
        if expected_cards is not None and expected_cards != total_cards:
            raise ValueError(
                f"Step 4 domainSemantics.cardCount is {expected_cards}, but domainPackages contains {total_cards} card(s)."
            )

    targets.sort(key=lambda row: (str(row["name"]).casefold(), str(row["domainKey"])))
    return targets
