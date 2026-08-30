from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PUBLICATION_SCHEMA_PREFIX = "cybermancy-rulebook-publication-manifest-v"


def _records_by_key(records: Any, key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(records, list):
        return result
    for record in records:
        if not isinstance(record, dict):
            continue
        value = record.get(key)
        if isinstance(value, str) and value:
            result[value] = record
    return result


def build_snapshot_change_summary(
    base: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Describe the actual publication delta from the selected base freeze.

    The publication generator deep-copies the accepted authority manifest before
    refreshing snapshot-dependent fields. This helper deliberately rebuilds the
    change summary from the selected base and the refreshed current manifest so
    historical summary data cannot leak forward into a new freeze.
    """
    base_inputs = base.get("publicationInputs") or {}
    current_inputs = current.get("publicationInputs") or {}

    base_authored = _records_by_key(base_inputs.get("authoredDocuments"), "path")
    current_authored = _records_by_key(current_inputs.get("authoredDocuments"), "path")
    authored_changes: list[dict[str, Any]] = []
    for path in sorted(set(base_authored) | set(current_authored), key=str.casefold):
        before = base_authored.get(path)
        after = current_authored.get(path)
        before_sha = before.get("sha256") if before else None
        after_sha = after.get("sha256") if after else None
        if before_sha == after_sha:
            continue
        record = after or before or {}
        authored_changes.append(
            {
                "id": record.get("id"),
                "path": path,
                "fromSha256": before_sha,
                "toSha256": after_sha,
            }
        )

    base_families = _records_by_key(base_inputs.get("structuredFamilies"), "generatorFamily")
    current_families = _records_by_key(
        current_inputs.get("structuredFamilies"), "generatorFamily"
    )
    structured_changes: list[dict[str, Any]] = []
    for family in sorted(set(base_families) | set(current_families), key=str.casefold):
        before = base_families.get(family)
        after = current_families.get(family)
        before_digest = before.get("contentDigestSha256") if before else None
        after_digest = after.get("contentDigestSha256") if after else None
        if before_digest == after_digest:
            continue
        record = after or before or {}
        structured_changes.append(
            {
                "id": record.get("id"),
                "generatorFamily": family,
                "sourcePath": record.get("sourcePath"),
                "fromDigestSha256": before_digest,
                "toDigestSha256": after_digest,
            }
        )

    authority_changed = (
        base.get("authorityDecisionFingerprint")
        != current.get("authorityDecisionFingerprint")
    )

    return {
        "previousManifestVersion": base.get("manifestVersion"),
        "previousGitCommit": (base.get("repository") or {}).get("gitCommit"),
        "currentGitCommit": (current.get("repository") or {}).get("gitCommit"),
        "authorityDecisionsChanged": authority_changed,
        "authoredPublicationInputsChanged": authored_changes,
        "structuredPublicationFamiliesChanged": structured_changes,
        "publicationContentChanged": bool(
            authority_changed or authored_changes or structured_changes
        ),
    }


def refresh_publication_digest_provenance(
    manifest: dict[str, Any],
    digest_version: int,
) -> None:
    """Keep descriptive digest provenance synchronized with the active algorithm."""
    supersedes = manifest.get("supersedes")
    if isinstance(supersedes, dict):
        supersedes["reason"] = (
            "Repository snapshot refreshed with unchanged Step 2 authority decisions. "
            "Structured entity accounting and family digests were recomputed from the "
            "selected inventory/source snapshot using stable Foundry/source identity "
            f"and shared structured-family digest v{digest_version}."
        )

    inputs = manifest.get("publicationInputs") or {}
    families = inputs.get("structuredFamilies") if isinstance(inputs, dict) else None
    if not isinstance(families, list):
        return
    for row in families:
        if not isinstance(row, dict):
            continue
        row["contentDigestValidation"] = (
            "Recomputed with the shared Step 2/Step 4 structured-family digest "
            f"implementation at v{digest_version}; authoritative folder-participation "
            "behavior is declared by contentDigestAlgorithm."
        )


def configure_publication_snapshot_summary(namespace: dict[str, Any]) -> None:
    """Patch Step 2 freeze output so snapshot and digest provenance are always fresh."""
    original_load_json = namespace["load_json"]
    original_update_summary = namespace["update_summary_and_validation"]
    error_type = namespace.get("ManifestBuildError", RuntimeError)
    digest_version = int(namespace["STRUCTURED_DIGEST_VERSION"])
    state: dict[str, dict[str, Any]] = {}

    def load_json(path: Path) -> dict[str, Any]:
        data = original_load_json(path)
        schema = str(data.get("schema") or "")
        if schema.startswith(PUBLICATION_SCHEMA_PREFIX) and "base" not in state:
            state["base"] = data
        return data

    def update_summary_and_validation(
        manifest: dict[str, Any],
        inventory: dict[str, Any],
        authored_count: int,
        family_count: int,
        entity_total: int,
        families: list[dict[str, Any]],
    ) -> None:
        original_update_summary(
            manifest,
            inventory,
            authored_count,
            family_count,
            entity_total,
            families,
        )
        base = state.get("base")
        if base is None:
            raise error_type(
                "Could not capture the selected base publication manifest while "
                "refreshing snapshotChangeSummary."
            )
        refresh_publication_digest_provenance(manifest, digest_version)
        manifest["snapshotChangeSummary"] = build_snapshot_change_summary(base, manifest)

    namespace["load_json"] = load_json
    namespace["update_summary_and_validation"] = update_summary_and_validation


def _first_gm_chapter_number(manifest: dict[str, Any]) -> int:
    for part in manifest.get("bookStructure") or []:
        if not isinstance(part, dict) or part.get("id") != "part-v-gm-world":
            continue
        chapters = part.get("chapters") or []
        if chapters and isinstance(chapters[0], dict):
            number = chapters[0].get("number")
            if isinstance(number, int):
                return number
    raise ValueError("Assembly manifest has no first GM-world chapter number.")


def configure_assembly_markdown_consistency(namespace: dict[str, Any]) -> None:
    """Keep the Step 3 Markdown companion synchronized with configured chapter IDs."""
    original_build_markdown = namespace["build_markdown"]
    error_type = namespace.get("ManifestError", RuntimeError)

    def build_markdown(manifest: dict[str, Any], pub: dict[str, Any]) -> str:
        text = original_build_markdown(manifest, pub)
        try:
            chapter_number = _first_gm_chapter_number(manifest)
        except ValueError as exc:
            raise error_type(str(exc)) from exc

        pattern = re.compile(
            r"(The GM landing page is\s+placed as GM-only front matter after the "
            r"spoiler divider and before Chapter )\d+(\.)"
        )
        replacement = rf"\g<1>{chapter_number}\g<2>"
        updated, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise error_type(
                "Could not synchronize the GM opener chapter number in the Step 3 "
                "Markdown companion."
            )
        return updated

    namespace["build_markdown"] = build_markdown
