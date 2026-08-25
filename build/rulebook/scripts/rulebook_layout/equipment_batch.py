from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


AGGREGATE_SCHEMA = "cybermancy-rulebook-step6-equipment-all-v1.0"
CONFIG_GLOB = "*-v1.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _add_check(
    report: dict,
    code: str,
    status: str,
    message: str,
    details: Any = None,
) -> None:
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
    """Discover configured Equipment families and return them in chapter order.

    Every ``*-v1.json`` file in the Equipment layout directory is treated as an
    approved family configuration. Discovery fails closed when a config cannot
    be parsed, lacks a family/chapter, or duplicates another family/chapter.
    """
    discovered: list[dict] = []
    errors: list[dict] = []

    if not config_dir.is_dir():
        return [], [{"issue": "config-directory-missing", "path": str(config_dir)}]

    for path in sorted(config_dir.glob(CONFIG_GLOB), key=lambda value: value.name.casefold()):
        try:
            config = _load_json(path)
        except Exception as exc:
            errors.append({
                "issue": "config-json-invalid",
                "path": str(path),
                "error": str(exc),
            })
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
            errors.append({
                "issue": "config-chapter-invalid",
                "path": str(path),
                "family": family,
                "chapter": config.get("chapter"),
            })
            continue

        discovered.append({
            "family": family,
            "chapter": chapter,
            "title": title,
            "config": str(path.resolve()),
        })

    by_family: dict[str, list[dict]] = {}
    by_chapter: dict[int, list[dict]] = {}
    for item in discovered:
        by_family.setdefault(item["family"].casefold(), []).append(item)
        by_chapter.setdefault(item["chapter"], []).append(item)

    for matches in by_family.values():
        if len(matches) > 1:
            errors.append({
                "issue": "duplicate-family-config",
                "family": matches[0]["family"],
                "configs": [item["config"] for item in matches],
            })
    for chapter, matches in by_chapter.items():
        if len(matches) > 1:
            errors.append({
                "issue": "duplicate-chapter-config",
                "chapter": chapter,
                "families": [item["family"] for item in matches],
                "configs": [item["config"] for item in matches],
            })

    discovered.sort(key=lambda item: (item["chapter"], item["family"].casefold()))
    return discovered, errors


def _aggregate_shell(
    operation: str,
    config_dir: Path,
    sidecar: Path,
    manuscript: Path,
) -> dict:
    return {
        "schema": AGGREGATE_SCHEMA,
        "operation": operation,
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        "inputs": {
            "configDirectory": str(config_dir),
            "structuredEntities": str(sidecar),
            "assembledManuscript": str(manuscript),
        },
        "families": [],
    }


def _resolve_optional(value: str | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value else default.resolve()


def _family_report_path(report_dir: Path, family: str) -> Path:
    return (
        report_dir / "chapter16-weapons.json"
        if family == "weapons"
        else report_dir / f"equipment-{family}.json"
    )


def _child_command(
    operation: str,
    item: dict,
    args: argparse.Namespace,
    *,
    script_path: Path,
    output_base: Path | None,
) -> list[str]:
    command = [
        sys.executable,
        str(script_path),
        f"{operation}-equipment",
        "--family",
        str(item["family"]),
        "--config",
        str(item["config"]),
    ]
    if getattr(args, "sidecar", None):
        command.extend(["--sidecar", str(args.sidecar)])
    if getattr(args, "manuscript", None):
        command.extend(["--manuscript", str(args.manuscript)])
    if getattr(args, "report_dir", None):
        command.extend(["--report-dir", str(args.report_dir)])
    if operation == "build":
        if output_base is not None:
            command.extend([
                "--output-dir",
                str(output_base / f"chapter{int(item['chapter'])}"),
            ])
        if getattr(args, "tex_only", False):
            command.append("--tex-only")
    return command


def _invoke_child(command: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
                "details": {
                    "stdout": stdout[-12000:],
                    "stderr": (proc.stderr or "")[-12000:],
                },
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


def _family_summary(
    item: dict,
    payload: dict,
    returncode: int,
    report_dir: Path,
    *,
    stage: str,
) -> dict:
    status = "PASS" if returncode == 0 and payload.get("status") == "PASS" else "FAIL"
    return {
        "chapter": item["chapter"],
        "family": item["family"],
        "title": item["title"],
        "config": item["config"],
        "stage": stage,
        "status": status,
        "returnCode": returncode,
        "reportPath": str(_family_report_path(report_dir, item["family"])),
        "report": payload,
    }


def _discovery_check(report: dict, discovered: list[dict], errors: list[dict]) -> None:
    if errors:
        _add_check(
            report,
            "EQUIPMENT_CONFIG_DISCOVERY",
            "ERROR",
            f"Equipment config discovery found {len(errors)} blocking problem(s).",
            errors,
        )
        return
    if not discovered:
        _add_check(
            report,
            "EQUIPMENT_CONFIG_DISCOVERY",
            "ERROR",
            "No approved Equipment family configs were discovered.",
        )
        return
    _add_check(
        report,
        "EQUIPMENT_CONFIG_DISCOVERY",
        "PASS",
        f"Discovered {len(discovered)} Equipment family config(s).",
        [
            {
                "chapter": item["chapter"],
                "family": item["family"],
                "config": item["config"],
            }
            for item in discovered
        ],
    )
    _add_check(
        report,
        "EQUIPMENT_CHAPTER_ORDER",
        "PASS",
        "Equipment families will execute in configured chapter order.",
        [item["chapter"] for item in discovered],
    )


def _run_phase(
    operation: str,
    discovered: list[dict],
    args: argparse.Namespace,
    *,
    script_path: Path,
    report_dir: Path,
    output_base: Path | None,
    stop_on_failure: bool,
) -> tuple[list[dict], bool]:
    summaries: list[dict] = []
    failed = False
    for index, item in enumerate(discovered):
        if failed and stop_on_failure:
            summaries.append({
                "chapter": item["chapter"],
                "family": item["family"],
                "title": item["title"],
                "config": item["config"],
                "stage": operation,
                "status": "BLOCKED",
                "returnCode": None,
                "reportPath": str(_family_report_path(report_dir, item["family"])),
                "report": None,
                "reason": "A prior Equipment family failed during this batch phase.",
            })
            continue
        command = _child_command(
            operation,
            item,
            args,
            script_path=script_path,
            output_base=output_base,
        )
        returncode, payload = _invoke_child(command)
        summary = _family_summary(
            item,
            payload,
            returncode,
            report_dir,
            stage=operation,
        )
        summaries.append(summary)
        if summary["status"] != "PASS":
            failed = True
    return summaries, failed


def run_all_equipment_command(
    operation: str,
    args: argparse.Namespace,
    *,
    script_path: Path,
    config_dir: Path,
    default_sidecar: Path,
    default_manuscript: Path,
    default_report_dir: Path,
) -> int:
    """Execute every configured Equipment family in chapter order.

    ``build`` performs a complete validation preflight before rendering any
    chapter. If preflight fails, no family build commands are invoked. During
    the build phase, a failure stops later families and the aggregate report
    records those families as BLOCKED.
    """
    if operation not in {"inspect", "validate", "build"}:
        raise ValueError(f"Unsupported Equipment batch operation: {operation}")

    sidecar = _resolve_optional(getattr(args, "sidecar", None), default_sidecar)
    manuscript = _resolve_optional(getattr(args, "manuscript", None), default_manuscript)
    report_dir = _resolve_optional(getattr(args, "report_dir", None), default_report_dir)
    output_base = (
        Path(args.output_dir).expanduser().resolve()
        if operation == "build" and getattr(args, "output_dir", None)
        else None
    )

    aggregate = _aggregate_shell(operation, config_dir.resolve(), sidecar, manuscript)
    discovered, discovery_errors = discover_equipment_configs(config_dir.resolve())
    _discovery_check(aggregate, discovered, discovery_errors)
    if aggregate["status"] != "PASS":
        if operation != "inspect":
            _write_json(report_dir / "equipment-all.json", aggregate)
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 2

    if operation == "inspect":
        summaries, failed = _run_phase(
            "inspect",
            discovered,
            args,
            script_path=script_path,
            report_dir=report_dir,
            output_base=None,
            stop_on_failure=False,
        )
        aggregate["families"] = summaries
        _add_check(
            aggregate,
            "EQUIPMENT_FAMILY_RESULTS",
            "ERROR" if failed else "PASS",
            "One or more Equipment family inspections failed."
            if failed else
            "All configured Equipment families inspected successfully.",
        )
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 0 if aggregate["status"] == "PASS" else 2

    if operation == "validate":
        summaries, failed = _run_phase(
            "validate",
            discovered,
            args,
            script_path=script_path,
            report_dir=report_dir,
            output_base=None,
            stop_on_failure=False,
        )
        aggregate["families"] = summaries
        _add_check(
            aggregate,
            "EQUIPMENT_FAMILY_RESULTS",
            "ERROR" if failed else "PASS",
            "One or more Equipment family validations failed."
            if failed else
            "All configured Equipment families validated successfully.",
        )
        _write_json(report_dir / "equipment-all.json", aggregate)
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 0 if aggregate["status"] == "PASS" else 2

    preflight, preflight_failed = _run_phase(
        "validate",
        discovered,
        args,
        script_path=script_path,
        report_dir=report_dir,
        output_base=None,
        stop_on_failure=False,
    )
    if preflight_failed:
        aggregate["families"] = [
            {**summary, "stage": "preflight"}
            for summary in preflight
        ]
        _add_check(
            aggregate,
            "EQUIPMENT_BUILD_PREFLIGHT",
            "ERROR",
            "Equipment --all build is blocked because one or more family validations failed. No chapter builds were started.",
        )
        _write_json(report_dir / "equipment-all.json", aggregate)
        print(json.dumps(aggregate, indent=2, ensure_ascii=False))
        return 2

    _add_check(
        aggregate,
        "EQUIPMENT_BUILD_PREFLIGHT",
        "PASS",
        "All configured Equipment families passed validation preflight.",
    )
    builds, build_failed = _run_phase(
        "build",
        discovered,
        args,
        script_path=script_path,
        report_dir=report_dir,
        output_base=output_base,
        stop_on_failure=True,
    )
    aggregate["families"] = builds
    _add_check(
        aggregate,
        "EQUIPMENT_FAMILY_RESULTS",
        "ERROR" if build_failed else "PASS",
        "An Equipment family build failed; later family builds were blocked."
        if build_failed else
        "All configured Equipment families built successfully.",
    )
    _write_json(report_dir / "equipment-all.json", aggregate)
    print(json.dumps(aggregate, indent=2, ensure_ascii=False))
    return 0 if aggregate["status"] == "PASS" else 2
