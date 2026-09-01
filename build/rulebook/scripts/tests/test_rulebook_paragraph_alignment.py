from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
RULEBOOK_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulebook_layout.class_package_compact as class_compact
import rulebook_layout.domain_package_refined as domain_refined
import rulebook_layout.encounters as encounters
import rulebook_layout.ice_reference_refined as ice_refined
import rulebook_layout.latex as equipment_latex


def _load_hyphenated_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PROSE = _load_hyphenated_module(
    "tx8_rulebook_prose_builder",
    SCRIPT_DIR / "build-rulebook-prose.py",
)
PROSE_CONFIG = RULEBOOK_DIR / "layout" / "prose" / "prose-layout-v1.json"


class ParagraphAlignmentTests(unittest.TestCase):
    def test_prose_config_and_preamble_use_ragged_right(self) -> None:
        config = json.loads(PROSE_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["typography"]["bodyAlignment"], "ragged-right")

        tex = PROSE.document_preamble(config)
        self.assertIn(r"\usepackage{ragged2e}", tex)
        self.assertIn("\\frenchspacing\n\\RaggedRight\n", tex)
        self.assertLess(tex.index(r"\frenchspacing"), tex.index(r"\RaggedRight"))
        self.assertIn(r"\color{\CMRunningAccent}", tex)
        self.assertNotIn(r"\color{CMRunningAccent}", tex)
        self.assertIn(r"\centering", tex)

    def test_class_package_body_is_ragged_right_and_stats_remain_centered(self) -> None:
        view = {
            "chapter": 12,
            "class": {
                "name": "Alignment Class",
                "description": "A deliberately ordinary paragraph used to verify body alignment.",
                "domains": ["arcana", "circuit"],
                "hitPoints": 5,
                "evasion": 11,
                "image": "assets/icons/classes/alignment.png",
                "features": {"hope": [], "class": []},
                "classItems": [],
                "startingInventory": {},
                "characterGuide": {},
            },
            "subclasses": [],
        }
        config = {
            "chapter": 12,
            "partLabel": "CHARACTER OPTIONS",
            "composition": {"subclassPageColumns": 2},
            "style": {},
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = class_compact.render_class_package_tex(
                view,
                config,
                root / "source",
                root / "out",
            )

        self.assertIn("\\frenchspacing\n\\RaggedRight\n", tex)
        self.assertIn(r">{\centering\arraybackslash}X >{\centering\arraybackslash}X", tex)
        self.assertIn(r"\centering", tex)

    def test_domain_body_and_descriptions_are_ragged_right_with_display_alignment_preserved(self) -> None:
        description = domain_refined._description_block_tex("Description", 10.5, 12.1)
        self.assertIn(r"\RaggedRight", description)

        view = {
            "chapter": 14,
            "domain": {
                "name": "Circuit",
                "artwork": {"image": "assets/icons/domains/circuit.png"},
                "cardCount": 1,
            },
            "levels": [
                {
                    "level": 1,
                    "cards": [
                        {
                            "name": "Centered Card",
                            "description": "Ordinary card description text.",
                            "image": "assets/icons/domains/centered-card.png",
                            "level": 1,
                            "recallCost": 0,
                        }
                    ],
                }
            ],
        }
        config = {"partLabel": "CHARACTER OPTIONS", "style": {}, "composition": {}}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = domain_refined.render_domain_package_tex(
                view,
                config,
                root / "source",
                root / "out",
            )

        self.assertIn("\\sffamily\n\\RaggedRight\n", tex)
        self.assertIn(r"\raggedleft", tex)
        self.assertIn(r"\vspace{0pt}\centering", tex)

    def test_equipment_chapter_document_is_ragged_right(self) -> None:
        tex = equipment_latex.render_equipment_chapter_document(
            "BODY",
            {"chapter": 16, "partLabel": "EQUIPMENT & TECHNOLOGY", "title": "Weapons", "style": {}},
        )
        self.assertIn("\\sffamily\n\\RaggedRight\n", tex)

    def test_ice_body_scopes_are_ragged_right_and_identity_art_stays_centered(self) -> None:
        view = {
            "chapter": 29,
            "partLabel": "GM ENCOUNTER TOOLKIT",
            "title": "ICE Reference",
            "chapterIntro": "Introductory paragraph text.",
            "groups": [
                {
                    "title": "Wall ICE",
                    "entries": [
                        {
                            "name": "Alignment Wall",
                            "iceType": "wall",
                            "image": "assets/ice/alignment.png",
                            "rulesMarkdown": "Rules paragraph text.",
                            "actions": [
                                {
                                    "name": "Pulse",
                                    "rulesMarkdown": "Action rules paragraph text.",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        config = {"chapter": 29, "title": "ICE Reference", "style": {}, "composition": {"pageColumns": 2}}
        tex = ice_refined.render_ice_reference_tex(
            view,
            config,
            {"assets/ice/alignment.png": "assets/render/alignment.png"},
        )

        self.assertIn(r"\usepackage{ragged2e}", tex)
        self.assertIn("\\begin{document}\n\\RaggedRight\n", tex)
        self.assertGreaterEqual(tex.count(r"\RaggedRight"), 4)
        self.assertIn(r"\centering", tex)

    def test_encounter_preamble_is_ragged_right(self) -> None:
        tex = encounters._preamble("Adversaries", "Proof", columns=2)
        self.assertIn(r"\usepackage{ragged2e}", tex)
        self.assertIn("\\begin{document}\n\\RaggedRight\n", tex)
        self.assertIn(r"\begin{tcolorbox}", tex)


if __name__ == "__main__":
    unittest.main()
