from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ENCOUNTER_SPECS: tuple[dict[str, Any], ...] = (
    {
        "kind": "adversary",
        "chapter": 30,
        "chapterId": "ch30-adversaries",
        "family": "adversaries",
        "adapter": "adversary-package",
        "order": 100,
        "stem": "Cybermancy_Chapter30_Adversaries_Step6",
        "expected": 106,
        "version": "v1.1",
    },
    {
        "kind": "environment",
        "chapter": 31,
        "chapterId": "ch31-environments",
        "family": "environments",
        "adapter": "environment-package",
        "order": 110,
        "stem": "Cybermancy_Chapter31_Environments_Step6",
        "expected": 8,
        "version": "v1.0",
    },
    {
        "kind": "feature-reference",
        "chapter": 32,
        "chapterId": "ch32-adversary-features",
        "family": "adversaries-features",
        "adapter": "adversary-feature-reference",
        "order": 120,
        "stem": "Cybermancy_Chapter32_Adversary_Feature_Reference_Step6",
        "expected": 344,
        "version": "v1.0",
    },
)


@dataclass(frozen=True)
class EncounterPayload:
    kind: str
    chapter: int
    chapter_id: str
    family: str
    adapter: str
    order: int
    entry_count: int
    package_version: str
    header_latex: str
    body_latex: str
    source_tex_sha256: str

    def summary(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "chapter": self.chapter,
            "chapterId": self.chapter_id,
            "family": self.family,
            "adapter": self.adapter,
            "order": self.order,
            "entryCount": self.entry_count,
            "packageVersion": self.package_version,
            "sourceTexSha256": self.source_tex_sha256,
        }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_encounter_fragments(tex_text: str) -> tuple[str, str]:
    """Extract the frozen chapter opener and package body from standalone TeX.

    The standalone renderer remains authoritative for visual grammar. Integration
    discards only its local document shell/preamble and closing document marker.
    """
    begin = r"\begin{document}"
    end = r"\end{document}"
    opener_end = r"\vspace{-1mm}"
    begin_at = tex_text.find(begin)
    end_at = tex_text.rfind(end)
    if begin_at < 0 or end_at < 0 or end_at <= begin_at:
        raise ValueError("Encounter package TeX does not contain one standalone document body.")
    interior = tex_text[begin_at + len(begin) : end_at]
    opener_at = interior.find(opener_end)
    if opener_at < 0:
        raise ValueError("Encounter package TeX does not contain the frozen chapter-opener terminator.")
    split_at = opener_at + len(opener_end)
    header = interior[:split_at].strip() + "\n"
    body = interior[split_at:].strip() + "\n"
    if not header.strip() or not body.strip():
        raise ValueError("Encounter package fragment extraction produced an empty header or body.")

    forbidden = (
        r"\documentclass",
        r"\usepackage",
        r"\begin{document}",
        r"\end{document}",
    )
    leaked = [token for token in forbidden if token in header or token in body]
    if leaked:
        raise ValueError(f"Standalone Encounter Toolkit shell leaked into integration fragments: {leaked}")
    return header, body


def _contract_expected(contract: dict[str, Any], spec: dict[str, Any]) -> int:
    regression = contract.get("regressionExpectations") if isinstance(contract.get("regressionExpectations"), dict) else {}
    if spec["kind"] == "adversary":
        return int((regression.get("adversaries") or {}).get("entries") or 0)
    if spec["kind"] == "environment":
        return int((regression.get("environments") or {}).get("entries") or 0)
    return int((regression.get("adversaryFeatures") or {}).get("publishedRepresentatives") or 0)


def compose_encounter_stage(
    builder_script: Path,
    sidecar_path: Path,
    source_root: Path,
    config_root: Path,
    work_dir: Path,
    contract: dict[str, Any],
) -> tuple[list[EncounterPayload], dict[str, Any]]:
    """Compose frozen Chapters 30-32 through the accepted standalone producer."""
    report: dict[str, Any] = {
        "schema": "cybermancy-step6-encounter-integration-composition-v1",
        "status": "PASS",
        "checks": [],
        "errors": [],
        "packages": [],
    }

    for label, path, want_dir in (
        ("builder", builder_script, False),
        ("sidecar", sidecar_path, False),
        ("sourceRoot", source_root, True),
        ("configRoot", config_root, True),
    ):
        exists = path.is_dir() if want_dir else path.is_file()
        if not exists:
            report["status"] = "FAIL"
            report["errors"].append(f"Required Encounter Toolkit integration input is missing: {label}={path}")
    if report["status"] != "PASS":
        return [], report

    work_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(builder_script),
        "build",
        "--family",
        "all",
        "--sidecar",
        str(sidecar_path),
        "--source-root",
        str(source_root),
        "--config-root",
        str(config_root),
        "--output-dir",
        str(work_dir),
        "--tex-only",
    ]
    proc = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    report["builderReturnCode"] = proc.returncode
    report["builderOutputTail"] = (proc.stdout or "")[-12000:]
    if proc.returncode != 0:
        report["status"] = "FAIL"
        report["errors"].append("Frozen Encounter Toolkit production builder failed in --tex-only mode.")
        return [], report

    payloads: list[EncounterPayload] = []
    for spec in ENCOUNTER_SPECS:
        stem = str(spec["stem"])
        report_path = work_dir / f"{stem}.report.json"
        tex_path = work_dir / f"{stem}.tex"
        package_row: dict[str, Any] = {
            "kind": spec["kind"],
            "chapter": spec["chapter"],
            "family": spec["family"],
            "report": str(report_path),
            "tex": str(tex_path),
            "status": "PASS",
        }
        errors: list[str] = []
        if not report_path.is_file() or not tex_path.is_file():
            errors.append("Frozen production builder did not emit both report and TeX artifacts.")
        else:
            package_report = _load_json(report_path)
            package_contract = package_report.get("contract") if isinstance(package_report.get("contract"), dict) else {}
            expected = int(spec["expected"])
            integration_expected = _contract_expected(contract, spec)
            actual = int(package_report.get("entryCount") or -1)
            if package_report.get("status") != "PASS":
                errors.append("Standalone frozen package report is not PASS.")
            if integration_expected != expected:
                errors.append(
                    f"Integration regression contract expects {integration_expected}, but frozen package contract expects {expected}."
                )
            if actual != expected:
                errors.append(f"Rendered package contains {actual} entries; expected {expected}.")
            if int(package_contract.get("expectedEntryCount") or -1) != expected:
                errors.append("Standalone production report expected-entry count differs from the frozen integration anchor.")
            if str(package_contract.get("version") or "") != str(spec["version"]):
                errors.append("Standalone production report package version differs from the frozen integration anchor.")

        if errors:
            package_row["status"] = "FAIL"
            package_row["errors"] = errors
            report["status"] = "FAIL"
            report["errors"].extend(f"Chapter {spec['chapter']}: {message}" for message in errors)
            report["packages"].append(package_row)
            continue

        tex_text = tex_path.read_text(encoding="utf-8")
        try:
            header_latex, body_latex = extract_encounter_fragments(tex_text)
        except Exception as exc:
            package_row["status"] = "FAIL"
            package_row["errors"] = [f"Fragment extraction failed: {exc}"]
            report["status"] = "FAIL"
            report["errors"].append(f"Chapter {spec['chapter']}: fragment extraction failed: {exc}")
            report["packages"].append(package_row)
            continue

        if spec["kind"] == "adversary":
            if r"\begin{multicols}{2}" not in body_latex or r"\Needspace{" in body_latex:
                package_row["status"] = "FAIL"
                package_row["errors"] = ["Chapter 30 body lost its frozen two-column/multicol-safe flow grammar."]
        elif spec["kind"] == "environment":
            if body_latex.lstrip().startswith(r"\clearpage"):
                package_row["status"] = "FAIL"
                package_row["errors"] = ["Chapter 31 first Environment no longer shares the chapter-opener page."]
        else:
            if r"\begin{multicols}{2}" not in body_latex:
                package_row["status"] = "FAIL"
                package_row["errors"] = ["Chapter 32 body lost its frozen two-column reference grammar."]

        if package_row["status"] != "PASS":
            report["status"] = "FAIL"
            report["errors"].extend(
                f"Chapter {spec['chapter']}: {message}" for message in package_row.get("errors", [])
            )
            report["packages"].append(package_row)
            continue

        payload = EncounterPayload(
            kind=str(spec["kind"]),
            chapter=int(spec["chapter"]),
            chapter_id=str(spec["chapterId"]),
            family=str(spec["family"]),
            adapter=str(spec["adapter"]),
            order=int(spec["order"]),
            entry_count=int(spec["expected"]),
            package_version=str(spec["version"]),
            header_latex=header_latex,
            body_latex=body_latex,
            source_tex_sha256=_sha256_text(tex_text),
        )
        payloads.append(payload)
        package_row.update(payload.summary())
        report["packages"].append(package_row)

    expected_order = [int(spec["chapter"]) for spec in ENCOUNTER_SPECS]
    actual_order = [payload.chapter for payload in payloads]
    if report["status"] == "PASS" and actual_order != expected_order:
        report["status"] = "FAIL"
        report["errors"].append(
            f"Encounter Toolkit payload order is incomplete or unstable: expected {expected_order}, got {actual_order}."
        )
        return [], report

    report["checks"].append(
        {
            "code": "ENCOUNTER_STAGE_COMPOSITION",
            "status": "PASS" if report["status"] == "PASS" else "ERROR",
            "message": "Composed frozen Chapters 30-32 without importing their standalone document shells."
            if report["status"] == "PASS"
            else "Encounter Toolkit integration composition failed closed.",
        }
    )
    return payloads if report["status"] == "PASS" else [], report
