from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


AGGREGATE_SCHEMA = "cybermancy-rulebook-step6-equipment-all-v1.1"
SECTION_SCHEMA = "cybermancy-step6-equipment-section-v1.0"
CONFIG_GLOB = "*-v1.json"
SECTION_FILENAME = "equipment-section-v1.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _add_check(report: dict, code: str, status: str, message: str, details: Any = None) -> None:
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["status"] = "FAIL"
        report["errors"].append(item)
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def discover_equipment_configs(config_dir: Path) -> tuple[list[dict], list[dict]]:
    """Discover family configs only; the section registry is not a family config."""
    discovered: list[dict] = []
    errors: list[dict] = []
    if not config_dir.is_dir():
        return [], [{"issue": "config-directory-missing", "path": str(config_dir)}]

    for path in sorted(config_dir.glob(CONFIG_GLOB), key=lambda value: value.name.casefold()):
        if path.name == SECTION_FILENAME:
            continue
        try:
            config = _load_json(path)
        except Exception as exc:
            errors.append({"issue": "config-json-invalid", "path": str(path), "error": str(exc)})
            continue
        family = str(config.get("family") or "").strip()
        title = str(config.get("title") or family).strip()
        try:
            chapter = int(config.get("chapter"))
        except (TypeError, ValueError):
            chapter = 0
        if not family:
            errors.append({"issue": "config-family-missing", "path": str(path)})
            continue
        if chapter <= 0:
            errors.append({"issue": "config-chapter-invalid", "path": str(path), "family": family, "chapter": config.get("chapter")})
            continue
        discovered.append({"family": family, "chapter": chapter, "title": title, "config": str(path.resolve())})

    by_family: dict[str, list[dict]] = {}
    by_chapter: dict[int, list[dict]] = {}
    for item in discovered:
        by_family.setdefault(item["family"].casefold(), []).append(item)
        by_chapter.setdefault(item["chapter"], []).append(item)
    for matches in by_family.values():
        if len(matches) > 1:
            errors.append({"issue": "duplicate-family-config", "family": matches[0]["family"], "configs": [item["config"] for item in matches]})
    for chapter, matches in by_chapter.items():
        if len(matches) > 1:
            errors.append({"issue": "duplicate-chapter-config", "chapter": chapter, "families": [item["family"] for item in matches], "configs": [item["config"] for item in matches]})
    discovered.sort(key=lambda item: (item["chapter"], item["family"].casefold()))
    return discovered, errors


def resolve_equipment_section(section_registry: Path, config_dir: Path) -> tuple[list[dict], list[dict]]:
    """Resolve the authoritative Equipment section contract against family configs."""
    errors: list[dict] = []
    if not section_registry.is_file():
        return [], [{"issue": "section-registry-missing", "path": str(section_registry)}]
    try:
        registry = _load_json(section_registry)
    except Exception as exc:
        return [], [{"issue": "section-registry-json-invalid", "path": str(section_registry), "error": str(exc)}]
    if registry.get("schema") != SECTION_SCHEMA:
        errors.append({"issue": "section-registry-schema", "expected": SECTION_SCHEMA, "actual": registry.get("schema")})
    entries = registry.get("families") if isinstance(registry.get("families"), list) else []
    if not entries:
        errors.append({"issue": "section-registry-empty", "path": str(section_registry)})
        return [], errors

    resolved: list[dict] = []
    seen_families: set[str] = set()
    seen_chapters: set[int] = set()
    expected_config_paths: set[Path] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append({"issue": "section-entry-invalid", "entry": entry})
            continue
        family = str(entry.get("family") or "").strip()
        title = str(entry.get("title") or family).strip()
        config_name = str(entry.get("config") or f"{family}-v1.json").strip()
        try:
            chapter = int(entry.get("chapter"))
        except (TypeError, ValueError):
            chapter = 0
        key = family.casefold()
        if not family or chapter <= 0 or not config_name:
            errors.append({"issue": "section-entry-required-field", "entry": entry})
            continue
        if key in seen_families:
            errors.append({"issue": "section-duplicate-family", "family": family})
            continue
        if chapter in seen_chapters:
            errors.append({"issue": "section-duplicate-chapter", "chapter": chapter})
            continue
        seen_families.add(key)
        seen_chapters.add(chapter)
        config_path = (config_dir / config_name).resolve()
        expected_config_paths.add(config_path)
        item = {
            "family": family,
            "chapter": chapter,
            "title": title,
            "config": str(config_path),
            "configPresent": config_path.is_file(),
        }
        if config_path.is_file():
            try:
                config = _load_json(config_path)
                if str(config.get("family") or "") != family or int(config.get("chapter") or 0) != chapter:
                    errors.append({
                        "issue": "section-config-mismatch",
                        "family": family,
                        "chapter": chapter,
                        "config": str(config_path),
                        "configFamily": config.get("family"),
                        "configChapter": config.get("chapter"),
                    })
            except Exception as exc:
                errors.append({"issue": "section-config-invalid", "config": str(config_path), "error": str(exc)})
        resolved.append(item)

    discovered, discovery_errors = discover_equipment_configs(config_dir)
    errors.extend(discovery_errors)
    for item in discovered:
        path = Path(item["config"]).resolve()
        if path not in expected_config_paths:
            errors.append({"issue": "unregistered-family-config", "family": item["family"], "chapter": item["chapter"], "config": str(path)})

    resolved.sort(key=lambda item: (item["chapter"], item["family"].casefold()))
    return resolved, errors


def _aggregate_shell(operation: str, config_dir: Path, section_registry: Path, sidecar: Path, manuscript: Path) -> dict:
    return {
        "schema": AGGREGATE_SCHEMA,
        "operation": operation,
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputs": {
            "configDirectory": str(config_dir),
            "sectionRegistry": str(section_registry),
            "structuredEntities": str(sidecar),
            "assembledManuscript": str(manuscript),
        },
        "families": [],
    }


def _resolve_optional(value: str | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value else default.resolve()


def _family_report_path(report_dir: Path, family: str) -> Path:
    return report_dir / "chapter16-weapons.json" if family == "weapons" else report_dir / f"equipment-{family}.json"


def _child_command(operation: str, item: dict, args: argparse.Namespace, *, script_path: Path, output_base: Path | None) -> list[str]:
    command = [sys.executable, str(script_path), f"{operation}-equipment", "--family", str(item["family"]), "--config", str(item["config"])]
    if getattr(args, "sidecar", None):
        command.extend(["--sidecar", str(args.sidecar)])
    if getattr(args, "manuscript", None):
        command.extend(["--manuscript", str(args.manuscript)])
    if getattr(args, "report_dir", None):
        command.extend(["--report-dir", str(args.report_dir)])
    if operation == "build":
        if output_base is not None:
            command.extend(["--output-dir", str(output_base / f"chapter{int(item['chapter'])}")])
        if getattr(args, "tex_only", False):
            command.append("--tex-only")
    return command


def _invoke_child(command: list[str]) -> tuple[int, dict]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout = (proc.stdout or "").strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        payload = {
            "status": "FAIL",
            "errors": [{
                "code": "CHILD_OUTPUT_JSON",
                "status": "ERROR",
                "message": "Equipment child command did not return valid JSON.",
                "details": {"stdout": stdout[-12000:], "stderr": (proc.stderr or "")[-12000:]},
            }],
        }
    if proc.returncode != 0 and payload.get("status") != "FAIL":
        payload["status"] = "FAIL"
        payload.setdefault("errors", []).append({
            "code": "CHILD_COMMAND_EXIT",
            "status": "ERROR",
            "message": f"Equipment child command exited with status {proc.returncode}.",
            "details": (proc.stderr or "")[-12000:],
        })
    return proc.returncode, payload


def _family_summary(item: dict, payload: dict, returncode: int, report_dir: Path, *, stage: str) -> dict:
    status = "PASS" if returncode == 0 and payload.get("status") == "PASS" else "FAIL"
    return {
        "chapter": item["chapter"], "family": item["family"], "title": item["title"],
        "config": item["config"], "stage": stage, "status": status,
        "returnCode": returncode, "reportPath": str(_family_report_path(report_dir, item["family"])),
        "report": payload,
    }


def _missing_summary(item: dict, *, stage: str) -> dict:
    return {
        "chapter": item["chapter"], "family": item["family"], "title": item["title"],
        "config": item["config"], "stage": stage, "status": "BLOCKED", "returnCode": None,
        "reportPath": None, "report": None,
        "reason": "Required Equipment family config has not yet been implemented.",
    }


def _section_checks(report: dict, section: list[dict], errors: list[dict]) -> bool:
    if errors:
        _add_check(report, "EQUIPMENT_SECTION_CONTRACT", "ERROR", f"Equipment section contract has {len(errors)} blocking problem(s).", errors)
        return False
    _add_check(
        report, "EQUIPMENT_SECTION_CONTRACT", "PASS",
        f"Resolved {len(section)} required Equipment & Technology chapter(s) from the section registry.",
        [{"chapter": x["chapter"], "family": x["family"], "config": x["config"]} for x in section],
    )
    missing = [x for x in section if not x["configPresent"]]
    _add_check(
        report, "EQUIPMENT_CONFIG_COVERAGE", "BLOCKED" if missing else "PASS",
        f"{len(missing)} required Equipment family config(s) are not yet implemented." if missing else "Every required Equipment family has an approved Step 6 config.",
        [{"chapter": x["chapter"], "family": x["family"], "config": x["config"]} for x in missing] or None,
    )
    _add_check(report, "EQUIPMENT_CHAPTER_ORDER", "PASS", "Equipment families execute in authoritative chapter order.", [x["chapter"] for x in section])
    return True


def _run_phase(operation: str, implemented: list[dict], args: argparse.Namespace, *, script_path: Path, report_dir: Path, output_base: Path | None, stop_on_failure: bool) -> tuple[list[dict], bool]:
    summaries: list[dict] = []
    failed = False
    for item in implemented:
        if failed and stop_on_failure:
            summaries.append({
                "chapter": item["chapter"], "family": item["family"], "title": item["title"],
                "config": item["config"], "stage": operation, "status": "BLOCKED", "returnCode": None,
                "reportPath": str(_family_report_path(report_dir, item["family"])), "report": None,
                "reason": "A prior implemented Equipment family failed during this batch phase.",
            })
            continue
        command = _child_command(operation, item, args, script_path=script_path, output_base=output_base)
        returncode, payload = _invoke_child(command)
        summary = _family_summary(item, payload, returncode, report_dir, stage=operation)
        summaries.append(summary)
        if summary["status"] != "PASS":
            failed = True
    return summaries, failed


def _merge_section(section: list[dict], summaries: list[dict], *, stage: str) -> list[dict]:
    by_family = {summary["family"]: summary for summary in summaries}
    return [by_family.get(item["family"], _missing_summary(item, stage=stage)) for item in section]


def run_all_equipment_command(
    operation: str,
    args: argparse.Namespace,
    *,
    script_path: Path,
    config_dir: Path,
    section_registry: Path,
    default_sidecar: Path,
    default_manuscript: Path,
    default_report_dir: Path,
) -> int:
    """Execute the authoritative Equipment section while exposing missing configs.

    Missing family configs are recorded as BLOCKED and make the aggregate result
    fail, but already implemented families are still inspected/validated/built.
    A semantic validation failure in an implemented family remains fail-closed:
    no implemented family builds start until all implemented configs validate.
    """
    if operation not in {"inspect", "validate", "build"}:
        raise ValueError(f"Unsupported Equipment batch operation: {operation}")

    sidecar = _resolve_optional(getattr(args, "sidecar", None), default_sidecar)
    manuscript = _resolve_optional(getattr(args, "manuscript", None), default_manuscript)
    report_dir = _resolve_optional(getattr(args, "report_dir", None), default_report_dir)
    output_base = Path(args.output_dir).expanduser().resolve() if operation == "build" and getattr(args, "output_dir", None) else None

    aggregate = _aggregate_shell(operation, config_dir.resolve(), section_registry.resolve(), sidecar, manuscript)
    section, section_errors = resolve_equipment_section(section_registry.resolve(), config_dir.resolve())
    if not _section_checks(aggregate, section, section_errors):
        if operation != "inspect":
            _write_json(report_dir / "equipment-all.json", aggregate)
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 2

    implemented = [item for item in section if item["configPresent"]]

    if operation == "inspect":
        summaries, failed = _run_phase("inspect", implemented, args, script_path=script_path, report_dir=report_dir, output_base=None, stop_on_failure=False)
        aggregate["families"] = _merge_section(section, summaries, stage="inspect")
        _add_check(aggregate, "EQUIPMENT_FAMILY_RESULTS", "ERROR" if failed else "PASS", "One or more implemented Equipment family inspections failed." if failed else "All implemented Equipment families inspected successfully.")
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 0 if aggregate["status"] == "PASS" else 2

    if operation == "validate":
        summaries, failed = _run_phase("validate", implemented, args, script_path=script_path, report_dir=report_dir, output_base=None, stop_on_failure=False)
        aggregate["families"] = _merge_section(section, summaries, stage="validate")
        _add_check(aggregate, "EQUIPMENT_FAMILY_RESULTS", "ERROR" if failed else "PASS", "One or more implemented Equipment family validations failed." if failed else "All implemented Equipment families validated successfully.")
        _write_json(report_dir / "equipment-all.json", aggregate)
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 0 if aggregate["status"] == "PASS" else 2

    preflight, preflight_failed = _run_phase("validate", implemented, args, script_path=script_path, report_dir=report_dir, output_base=None, stop_on_failure=False)
    if preflight_failed:
        aggregate["families"] = _merge_section(section, [{**summary, "stage": "preflight"} for summary in preflight], stage="preflight")
        _add_check(aggregate, "EQUIPMENT_BUILD_PREFLIGHT", "ERROR", "Equipment --all build is blocked because one or more implemented family validations failed. No implemented chapter builds were started.")
        _write_json(report_dir / "equipment-all.json", aggregate)
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 2

    _add_check(aggregate, "EQUIPMENT_BUILD_PREFLIGHT", "PASS", "All implemented Equipment families passed validation preflight.")
    builds, build_failed = _run_phase("build", implemented, args, script_path=script_path, report_dir=report_dir, output_base=output_base, stop_on_failure=True)
    aggregate["families"] = _merge_section(section, builds, stage="build")
    _add_check(
        aggregate, "EQUIPMENT_FAMILY_RESULTS", "ERROR" if build_failed else "PASS",
        "An implemented Equipment family build failed; later implemented builds were blocked." if build_failed else "All implemented Equipment families built successfully.",
    )
    _write_json(report_dir / "equipment-all.json", aggregate)
    print(json.dumps(aggregate, indent=2, ensure_ascii=False))
    return 0 if aggregate["status"] == "PASS" else 2
