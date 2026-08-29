from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.equipment_adapters import integrate_equipment_stage
from rulebook_layout.equipment_integration import (
    CONFIG_SCHEMA,
    EQUIPMENT_FAMILIES,
    REGISTRY_SCHEMA,
    SUPPORTED_SIDECAR_SCHEMA,
    EquipmentPayload,
    compose_equipment_stage,
)
from rulebook_layout.integration_ast import canonical_ast_sha256, family_body_is_exact_raw_latex


def _builder_module():
    path = SCRIPT_DIR / "build-rulebook-step6-integrated.py"
    spec = importlib.util.spec_from_file_location("step6_integrated_equipment_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _ast() -> dict:
    blocks = []
    for _chapter, family, _config in EQUIPMENT_FAMILIES:
        blocks.append(
            {
                "t": "Div",
                "c": [
                    [f"family:{family}", [], []],
                    [{"t": "Para", "c": [{"t": "Str", "c": f"placeholder-{family}"}]}],
                ],
            }
        )
    return {"pandoc-api-version": [1, 23, 1], "meta": {}, "blocks": blocks}


def _payloads() -> list[EquipmentPayload]:
    return [
        EquipmentPayload(
            chapter=chapter,
            family=family,
            title=family,
            config_path=f"{family}.json",
            entity_count=1,
            latex=f"LATEX-{family}",
        )
        for chapter, family, _config in EQUIPMENT_FAMILIES
    ]


def _contract(count: int = 1) -> dict:
    return {
        "structuredTargets": [
            {"chapter": chapter, "families": [family], "adapter": "equipment"}
            for chapter, family, _config in EQUIPMENT_FAMILIES
        ],
        "regressionExpectations": {
            "equipment": {family: count for _chapter, family, _config in EQUIPMENT_FAMILIES}
        },
    }


def _registry() -> dict:
    return {
        "schema": REGISTRY_SCHEMA,
        "families": [
            {
                "chapter": chapter,
                "family": family,
                "title": family.title(),
                "config": config,
            }
            for chapter, family, config in EQUIPMENT_FAMILIES
        ],
    }


def _config(chapter: int, family: str) -> dict:
    value = {
        "schema": CONFIG_SCHEMA,
        "layoutMode": "single-catalog",
        "family": family,
        "chapter": chapter,
        "title": family.title(),
        "expectedEntityCount": 1,
        "columns": [{"key": "name", "label": "Name", "widthIn": 1.0}],
    }
    if family == "weapons":
        value["expectedTierCounts"] = {"1": 1}
    return value


def _sidecar(schema: str = SUPPORTED_SIDECAR_SCHEMA) -> dict:
    entities = []
    for index, (_chapter, family, _config_name) in enumerate(EQUIPMENT_FAMILIES, start=1):
        publication = {"tier": 1} if family == "weapons" else {}
        entities.append(
            {
                "semanticId": f"{family}:fixture",
                "sourceId": f"source-{index}",
                "family": family,
                "name": f"Fixture {family}",
                "publicationData": publication,
            }
        )
    return {"schema": schema, "entities": entities}


class Step6EquipmentAdapterTests(unittest.TestCase):
    def test_equipment_stage_replaces_all_eight_families_atomically_and_is_idempotent(self) -> None:
        ast = _ast()
        payloads = _payloads()
        first = integrate_equipment_stage(ast, "player-guide", payloads)
        self.assertEqual(first["status"], "PASS", first)
        self.assertFalse(first["idempotent"])
        self.assertEqual(len(first["adapters"]), 8)
        for payload in payloads:
            self.assertTrue(family_body_is_exact_raw_latex(ast, payload.family, payload.latex))

        digest = canonical_ast_sha256(ast)
        second = integrate_equipment_stage(ast, "player-guide", payloads)
        self.assertEqual(second["status"], "PASS", second)
        self.assertTrue(second["idempotent"])
        self.assertEqual(canonical_ast_sha256(ast), digest)

    def test_equipment_stage_is_allowed_in_complete_rulebook(self) -> None:
        ast = _ast()
        result = integrate_equipment_stage(ast, "complete-rulebook", _payloads())
        self.assertEqual(result["status"], "PASS", result)

    def test_later_duplicate_family_discards_prior_staged_mutations(self) -> None:
        ast = _ast()
        # Duplicate Ammunition, the second adapter target. Weapons therefore
        # succeeds on the stage copy before Ammo fails; the original AST must
        # still remain completely untouched.
        duplicate = copy.deepcopy(ast["blocks"][1])
        ast["blocks"].append(duplicate)
        before = canonical_ast_sha256(ast)
        result = integrate_equipment_stage(ast, "player-guide", _payloads())
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(canonical_ast_sha256(ast), before)
        self.assertFalse(family_body_is_exact_raw_latex(ast, "weapons", "LATEX-weapons"))
        self.assertFalse(family_body_is_exact_raw_latex(ast, "ammo", "LATEX-ammo"))

    def test_incomplete_payload_order_fails_without_mutation(self) -> None:
        ast = _ast()
        before = canonical_ast_sha256(ast)
        result = integrate_equipment_stage(ast, "player-guide", _payloads()[:-1])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(canonical_ast_sha256(ast), before)


class Step6EquipmentCompositionTests(unittest.TestCase):
    def test_composer_builds_all_eight_body_payloads_from_v13_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            for chapter, family, config_name in EQUIPMENT_FAMILIES:
                (config_dir / config_name).write_text(
                    json.dumps(_config(chapter, family)),
                    encoding="utf-8",
                )
            payloads, report = compose_equipment_stage(
                _sidecar(),
                _registry(),
                config_dir,
                _contract(),
            )
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual([payload.family for payload in payloads], [row[1] for row in EQUIPMENT_FAMILIES])
        self.assertTrue(all(payload.latex for payload in payloads))
        self.assertTrue(all(len(payload.latex_sha256) == 64 for payload in payloads))

    def test_composer_rejects_old_step4_sidecar_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            for chapter, family, config_name in EQUIPMENT_FAMILIES:
                (config_dir / config_name).write_text(
                    json.dumps(_config(chapter, family)),
                    encoding="utf-8",
                )
            payloads, report = compose_equipment_stage(
                _sidecar("cybermancy-step4-structured-entities-v1.2"),
                _registry(),
                config_dir,
                _contract(),
            )
        self.assertEqual(payloads, [])
        self.assertEqual(report["status"], "FAIL")

    def test_composer_fails_on_corpus_count_drift(self) -> None:
        sidecar = _sidecar()
        sidecar["entities"] = [row for row in sidecar["entities"] if row["family"] != "loot"]
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            for chapter, family, config_name in EQUIPMENT_FAMILIES:
                (config_dir / config_name).write_text(
                    json.dumps(_config(chapter, family)),
                    encoding="utf-8",
                )
            payloads, report = compose_equipment_stage(
                sidecar,
                _registry(),
                config_dir,
                _contract(),
            )
        self.assertEqual(payloads, [])
        self.assertEqual(report["status"], "FAIL")


class Step6IntegratedParserEquipmentTests(unittest.TestCase):
    def test_integrate_equipment_command_is_exposed(self) -> None:
        builder = _builder_module()
        args = builder.parser().parse_args(["integrate-equipment", "--profile", "player-guide"])
        self.assertEqual(args.command, "integrate-equipment")
        self.assertEqual(args.profile, "player-guide")


if __name__ == "__main__":
    unittest.main()
