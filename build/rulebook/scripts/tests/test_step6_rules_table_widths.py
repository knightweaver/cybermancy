from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
RULEBOOK_DIR = HERE.parents[2]
FILTER = RULEBOOK_DIR / "layout" / "rules" / "pandoc" / "rules.lua"
PANDOC = shutil.which("pandoc")


def _table_widths(table: dict) -> list[float | None]:
    widths: list[float | None] = []
    for colspec in table["c"][2]:
        width = colspec[1]
        widths.append(float(width["c"]) if width.get("t") == "ColWidth" else None)
    return widths


def _document_text(value: Any) -> str:
    if isinstance(value, list):
        return "".join(_document_text(item) for item in value)
    if not isinstance(value, dict):
        return ""
    kind = value.get("t")
    if kind == "Str":
        return str(value.get("c") or "")
    if kind in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if kind:
        return _document_text(value.get("c"))
    return " ".join(_document_text(item) for item in value.values())


@unittest.skipUnless(PANDOC, "Pandoc is required for rules-table Lua-filter tests.")
class Step6RulesTableWidthTests(unittest.TestCase):
    def _tables(self, markdown: str) -> tuple[list[dict], str]:
        proc = subprocess.run(
            [
                str(PANDOC),
                "--from=markdown",
                "--to=json",
                "--wrap=none",
                f"--lua-filter={FILTER}",
            ],
            input=markdown,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=True,
        )
        document = json.loads(proc.stdout)
        tables = [block for block in document.get("blocks", []) if block.get("t") == "Table"]
        return tables, " ".join(_document_text(document).split())

    def test_progression_table_receives_accepted_widths(self) -> None:
        tables, output = self._tables(
            """
| Level | Scope | Progress Required | Typical Effect |
|---|---|---|---|
| P2 | Limited | 2 | Alter a bounded subsystem without changing the whole network. |
"""
        )
        self.assertEqual(len(tables), 1)
        self.assertEqual(_table_widths(tables[0]), [0.10, 0.15, 0.18, 0.57])
        self.assertIn("Limited", output)
        self.assertIn("bounded subsystem", output)

    def test_progression_signature_normalizes_case_and_whitespace(self) -> None:
        tables, _ = self._tables(
            """
| LEVEL |  Scope  | Progress  Required | TYPICAL EFFECT |
|---|---|---|---|
| P1 | Discrete | 1 | One tightly bounded effect. |
"""
        )
        self.assertEqual(_table_widths(tables[0]), [0.10, 0.15, 0.18, 0.57])

    def test_similar_four_column_table_keeps_default_widths(self) -> None:
        tables, _ = self._tables(
            """
| Level | Scope | Progress | Typical Effect |
|---|---|---|---|
| P1 | Discrete | 1 | One tightly bounded effect. |
"""
        )
        self.assertEqual(_table_widths(tables[0]), [None, None, None, None])

    def test_result_table_receives_accepted_widths(self) -> None:
        tables, output = self._tables(
            """
| Roll Result | Progress | Hacking Consequence |
|---|---|---|
| Success with Hope | +1 | The intrusion advances without an immediate consequence. |
"""
        )
        self.assertEqual(len(tables), 1)
        self.assertEqual(_table_widths(tables[0]), [0.24, 0.10, 0.66])
        self.assertIn("Success with Hope", output)
        self.assertIn("immediate consequence", output)

    def test_result_signature_normalizes_case_and_whitespace(self) -> None:
        tables, _ = self._tables(
            """
| ROLL RESULT | Progress | Hacking  Consequence |
|---|---|---|
| Failure with Fear | 0 | Apply the appropriate consequence. |
"""
        )
        self.assertEqual(_table_widths(tables[0]), [0.24, 0.10, 0.66])

    def test_similar_three_column_table_keeps_default_widths(self) -> None:
        tables, _ = self._tables(
            """
| Roll Result | Progress | Consequence |
|---|---|---|
| Success | +1 | None. |
"""
        )
        self.assertEqual(_table_widths(tables[0]), [None, None, None])

    def test_both_policies_coexist_without_touching_unrelated_table(self) -> None:
        tables, _ = self._tables(
            """
| Level | Scope | Progress Required | Typical Effect |
|---|---|---|---|
| P3 | Broad | 3 | Affect several related subsystems. |

| Roll Result | Progress | Hacking Consequence |
|---|---|---|
| Success with Fear | +1 | The intrusion advances and creates a consequence. |

| Access | Modifier | Notes |
|---|---|---|
| User | +0 | Ordinary access. |
"""
        )
        self.assertEqual(len(tables), 3)
        self.assertEqual(_table_widths(tables[0]), [0.10, 0.15, 0.18, 0.57])
        self.assertEqual(_table_widths(tables[1]), [0.24, 0.10, 0.66])
        self.assertEqual(_table_widths(tables[2]), [None, None, None])


if __name__ == "__main__":
    unittest.main()
