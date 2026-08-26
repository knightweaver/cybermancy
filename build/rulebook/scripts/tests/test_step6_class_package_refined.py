import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.class_package_refined import render_class_package_tex


class TestStep6RefinedClassPackage(unittest.TestCase):
    def _fixture(self):
        feature = lambda name, description: {"name": name, "description": description}
        view = {
            "chapter": 12,
            "class": {
                "name": "Test Class",
                "description": "First class sentence.\n\nSecond class sentence that continues the lead.",
                "domains": ["arcana", "circuit"],
                "hitPoints": 5,
                "evasion": 11,
                "image": "assets/icons/classes/test-class.png",
                "features": {
                    "hope": [feature("Hope Signal", "Hope feature text.")],
                    "class": [feature("Class Engine", "Class feature text.")],
                },
                "classItems": [],
                "startingInventory": {
                    "take": [{"name": "Pendant Lens"}],
                    "choiceA": [{"name": "Minor Patch"}],
                    "choiceB": [{"name": "Bedroll Key"}],
                },
                "characterGuide": {
                    "suggestedPrimaryWeapon": {"name": "Light Pistol"},
                    "suggestedArmor": {"name": "Kevlar Shirt"},
                    "suggestedTraits": {"agility": 0, "finesse": 1, "instinct": 2},
                },
            },
            "subclasses": [
                {
                    "name": "Path A",
                    "description": "First subclass sentence.\n\nSecond subclass sentence.",
                    "image": "assets/icons/subclasses/path-a.png",
                    "spellcastingTrait": "instinct",
                    "progression": {
                        "foundation": [feature("A Foundation", "Foundation A.")],
                        "specialization": [feature("A Specialization", "Specialization A.")],
                        "mastery": [feature("A Mastery", "Mastery A.")],
                    },
                },
                {
                    "name": "Path B",
                    "description": "",
                    "image": "assets/icons/subclasses/path-b.png",
                    "spellcastingTrait": "finesse",
                    "progression": {
                        "foundation": [feature("B Foundation", "Foundation B.")],
                        "specialization": [feature("B Specialization", "Specialization B.")],
                        "mastery": [feature("B Mastery", "Mastery B.")],
                    },
                },
            ],
        }
        config = {
            "chapter": 12,
            "partLabel": "CHARACTER OPTIONS",
            "composition": {
                "subclassProgressionOrder": ["foundation", "specialization", "mastery"],
                "subclassPageColumns": 2,
            },
            "style": {
                "classArtWidthFraction": 0.43,
                "classArtMaxHeightIn": 3.9,
                "subclassColumnWidthFraction": 0.485,
                "subclassArtWidthFraction": 0.34,
                "subclassArtMaxHeightIn": 1.55,
            },
        }
        return view, config

    def _render(self) -> str:
        view, config = self._fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            return render_class_package_tex(view, config, root / "source", root / "out")

    def test_class_description_is_its_own_zero_parskip_block(self):
        tex = self._render()
        expected = (
            "\\end{tabularx}\n"
            "\\par\n"
            "\\vspace{3.0mm}\n"
            "\\begingroup\n"
            "\\setlength{\\parskip}{0pt}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\fontsize{10.5}{12.3}\\selectfont\n"
            "\\noindent First class sentence. Second class sentence that continues the lead.\\par"
        )
        self.assertIn(expected, tex)

    def test_subclass_trait_terminates_before_description_block(self):
        tex = self._render()
        path_a = tex[tex.index("PATH A") : tex.index("PATH B")]
        self.assertIn(
            "SPELLCAST TRAIT: INSTINCT\n}}\n\\par\n\\vspace{2.0mm}\n\\begingroup",
            path_a,
        )
        self.assertIn("\\fontsize{10.5}{12.1}\\selectfont", path_a)
        self.assertIn("\\noindent First subclass sentence. Second subclass sentence.\\par", path_a)

    def test_blank_subclass_lead_uses_same_paragraph_structure(self):
        tex = self._render()
        path_b = tex[tex.index("PATH B") :]
        self.assertIn("\\setlength{\\parskip}{0pt}", path_b)
        self.assertIn("\\fontsize{10.5}{12.1}\\selectfont\\itshape\\color{CMMuted}", path_b)
        self.assertIn("\\noindent No subclass lead text is currently supplied by Step 4.\\par", path_b)

    def test_starting_package_rows_are_top_aligned_minipage_pairs(self):
        tex = self._render()
        package = tex[tex.index("STARTING PACKAGE") : tex.index("\\clearpage")]
        self.assertNotIn("\\begin{tabularx}", package)
        self.assertIn("\\begin{minipage}[t]{0.300\\linewidth}", package)
        self.assertIn("\\begin{minipage}[t]{0.660\\linewidth}", package)
        self.assertIn("\\begin{minipage}[t]{0.430\\linewidth}", package)
        self.assertIn("\\begin{minipage}[t]{0.530\\linewidth}", package)
        self.assertIn("\\strut Take\\par", package)
        self.assertIn("\\strut Pendant Lens\\par", package)
        self.assertIn("\\strut Suggested Weapon\\par", package)
        self.assertIn("\\strut Light Pistol\\par", package)
        self.assertGreaterEqual(package.count("\\vspace{0pt}"), 10)

    def test_refined_renderer_restores_base_helpers_after_use(self):
        import rulebook_layout.class_package_compact as base

        before = (base._class_opening_tex, base._subclass_tex, base._package_column_tex)
        first = self._render()
        after_first = (base._class_opening_tex, base._subclass_tex, base._package_column_tex)
        second = self._render()
        after_second = (base._class_opening_tex, base._subclass_tex, base._package_column_tex)
        self.assertEqual(before, after_first)
        self.assertEqual(before, after_second)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
