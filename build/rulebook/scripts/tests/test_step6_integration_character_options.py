from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = HERE.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.character_options_adapters import (
    integrate_character_options_stage,
)
from rulebook_layout.character_options_integration import (
    ClassStagePayload,
    DomainStagePayload,
)
from rulebook_layout.integration_ast import (
    canonical_ast_sha256,
    family_body_is_exact_raw_latex,
)


def _builder_module():
    path = SCRIPT_DIR / "build-rulebook-step6-integrated.py"
    spec = importlib.util.spec_from_file_location(
        "step6_integrated_character_options_test", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _family_div(family: str) -> dict:
    return {
        "t": "Div",
        "c": [
            [f"family:{family}", [], []],
            [
                {
                    "t": "Para",
                    "c": [{"t": "Str", "c": f"placeholder-{family}"}],
                }
            ],
        ],
    }


def _ast() -> dict:
    return {
        "pandoc-api-version": [1, 23, 1],
        "meta": {},
        "blocks": [
            _family_div("classes"),
            _family_div("subclasses"),
            _family_div("domains"),
        ],
    }


def _class_payload() -> ClassStagePayload:
    return ClassStagePayload(
        classes_latex=(
            "LATEX-CLASSES-WITH-NESTED-SUBCLASSES\n"
            "\\begin{wrapfigure}{l}{0.340\\linewidth}\n"
            "SUBCLASS-LEAD-ART\n"
            "\\end{wrapfigure}\n"
            "SUBCLASS-LEAD-TEXT\n"
            "\\WFclear\n"
            "FOUNDATION"
        ),
        subclasses_latex="% SUBCLASSES-NESTED-IN-CLASSES",
        class_count=5,
        subclass_count=10,
    )


def _domain_payload() -> DomainStagePayload:
    return DomainStagePayload(
        domains_latex="LATEX-DOMAINS",
        domain_count=3,
        card_count=73,
        render_asset_count=76,
    )


class Step6CharacterOptionsAdapterTests(unittest.TestCase):
    def test_stage_replaces_chapters_12_and_14_and_is_idempotent(self) -> None:
        for profile in ("player-guide", "complete-rulebook"):
            with self.subTest(profile=profile):
                ast = _ast()
                first = integrate_character_options_stage(
                    ast, profile, _class_payload(), _domain_payload()
                )
                self.assertEqual(first["status"], "PASS", first)
                self.assertFalse(first["idempotent"])
                self.assertEqual(
                    [row["adapter"] for row in first["adapters"]],
                    ["class-package", "domain-package"],
                )
                self.assertEqual(
                    [row["order"] for row in first["adapters"]], [50, 60]
                )
                self.assertTrue(
                    family_body_is_exact_raw_latex(
                        ast, "classes", _class_payload().classes_latex
                    )
                )
                self.assertTrue(
                    family_body_is_exact_raw_latex(
                        ast, "subclasses", _class_payload().subclasses_latex
                    )
                )
                self.assertTrue(
                    family_body_is_exact_raw_latex(
                        ast, "domains", _domain_payload().domains_latex
                    )
                )

                digest = canonical_ast_sha256(ast)
                repeated = integrate_character_options_stage(
                    ast, profile, _class_payload(), _domain_payload()
                )
                self.assertEqual(repeated["status"], "PASS", repeated)
                self.assertTrue(repeated["idempotent"], repeated)
                self.assertTrue(
                    all(row["idempotent"] for row in repeated["adapters"]), repeated
                )
                self.assertEqual(canonical_ast_sha256(ast), digest)

    def test_integrated_class_payload_preserves_subclass_wrap_grammar(self) -> None:
        ast = _ast()
        payload = _class_payload()
        result = integrate_character_options_stage(
            ast, "complete-rulebook", payload, _domain_payload()
        )
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(family_body_is_exact_raw_latex(ast, "classes", payload.classes_latex))
        self.assertEqual(payload.class_count, 5)
        self.assertEqual(payload.subclass_count, 10)
        self.assertIn(r"\begin{wrapfigure}{l}{0.340\linewidth}", payload.classes_latex)
        self.assertIn(r"\WFclear", payload.classes_latex)
        self.assertLess(payload.classes_latex.index(r"\WFclear"), payload.classes_latex.index("FOUNDATION"))

    def test_domain_failure_rolls_back_successful_staged_class_replacement(self) -> None:
        ast = _ast()
        ast["blocks"].append(copy.deepcopy(ast["blocks"][2]))
        before = canonical_ast_sha256(ast)
        result = integrate_character_options_stage(
            ast, "player-guide", _class_payload(), _domain_payload()
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(
            [row["adapter"] for row in result["adapters"]],
            ["class-package", "domain-package"],
        )
        self.assertEqual(result["adapters"][0]["status"], "PASS")
        self.assertEqual(result["adapters"][1]["status"], "FAIL")
        self.assertEqual(canonical_ast_sha256(ast), before)
        self.assertFalse(
            family_body_is_exact_raw_latex(
                ast, "classes", _class_payload().classes_latex
            )
        )
        self.assertFalse(
            family_body_is_exact_raw_latex(
                ast, "subclasses", _class_payload().subclasses_latex
            )
        )

    def test_class_precondition_failure_does_not_mutate_ast(self) -> None:
        ast = _ast()
        ast["blocks"].append(copy.deepcopy(ast["blocks"][0]))
        before = canonical_ast_sha256(ast)
        result = integrate_character_options_stage(
            ast, "complete-rulebook", _class_payload(), _domain_payload()
        )
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(len(result["adapters"]), 1)
        self.assertEqual(result["adapters"][0]["adapter"], "class-package")
        self.assertEqual(canonical_ast_sha256(ast), before)


class Step6CharacterOptionsContractTests(unittest.TestCase):
    def test_contract_freezes_current_class_subclass_counts(self) -> None:
        contract_path = (
            RULEBOOK_DIR / "layout" / "integration" / "step6-integration-v1.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["regressionExpectations"]["classes"],
            {"classes": 5, "subclasses": 10},
        )
        targets = {
            row["adapter"]: row
            for row in contract["structuredTargets"]
            if row.get("adapter") in {"class-package", "domain-package"}
        }
        self.assertEqual(targets["class-package"]["chapter"], 12)
        self.assertEqual(
            targets["class-package"]["families"], ["classes", "subclasses"]
        )
        self.assertEqual(targets["domain-package"]["chapter"], 14)
        self.assertEqual(targets["domain-package"]["families"], ["domains"])


class Step6IntegratedParserCharacterOptionsTests(unittest.TestCase):
    def test_integrate_character_options_command_is_exposed(self) -> None:
        builder = _builder_module()
        args = builder.parser().parse_args(
            ["integrate-character-options", "--profile", "player-guide"]
        )
        self.assertEqual(args.command, "integrate-character-options")
        self.assertEqual(args.profile, "player-guide")


if __name__ == "__main__":
    unittest.main()
