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
                    "class": [
                        feature("Class Engine", "First class feature text."),
                        feature("Class Relay", "Second class feature text."),
                    ],
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
                        "foundation": [
                            feature("A Foundation", "Foundation A."),
                            feature("A Foundation Two", "Foundation A2."),
                        ],
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

    def _render(self, view=None, config=None) -> str:
        if view is None or config is None:
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

    def test_refined_renderer_loads_wrapfig(self):
        tex = self._render()
        self.assertIn(r"\usepackage{wrapfig}", tex)

    def test_subclass_lead_uses_left_wrapfigure_not_fixed_minipages(self):
        tex = self._render()
        path_a = tex[tex.index("PATH A") : tex.index("FOUNDATION", tex.index("PATH A"))]
        self.assertIn(r"\begin{wrapfigure}{l}{0.340\linewidth}", path_a)
        self.assertIn("assets/icons/subclasses/path-a.png", path_a)
        self.assertIn(r"\end{wrapfigure}", path_a)
        self.assertNotIn(r"\begin{minipage}", path_a)
        self.assertIn("SPELLCAST TRAIT: INSTINCT", path_a)
        self.assertIn(
            r"\colorbox{CMSubclass}{\parbox{\dimexpr\linewidth-2\fboxsep\relax}{\centering",
            path_a,
        )
        self.assertIn(r"\noindent First subclass sentence. Second subclass sentence.\par", path_a)

    def test_subclass_wrap_is_cleared_before_first_progression_heading(self):
        tex = self._render()
        path_a = tex[tex.index("PATH A") : tex.index(r"\switchcolumn")]
        self.assertEqual(1, path_a.count(r"\WFclear"))
        self.assertLess(path_a.index(r"\end{wrapfigure}"), path_a.index(r"\WFclear"))
        self.assertLess(path_a.index(r"\WFclear"), path_a.index(r"\Needspace{0.45in}"))
        self.assertLess(path_a.index(r"\WFclear"), path_a.index("FOUNDATION"))

    def test_wrap_clear_reserves_unfinished_wrap_depth_before_wfclear(self):
        tex = self._render()
        path_a = tex[tex.index("PATH A") : tex.index(r"\switchcolumn")]
        self.assertIn(r"\ifnum\c@WF@wrappedlines>\@ne", path_a)
        self.assertIn(r"\@tempcnta=\c@WF@wrappedlines", path_a)
        self.assertIn(r"\multiply\dimen@\@tempcnta", path_a)
        self.assertIn(r"\vskip\dimen@", path_a)
        self.assertLess(path_a.index(r"\vskip\dimen@"), path_a.index(r"\WFclear"))

    def test_blank_subclass_lead_preserves_wrap_and_placeholder_structure(self):
        tex = self._render()
        path_b = tex[tex.index("PATH B") : tex.index(r"\end{paracol}")]
        self.assertIn(r"\begin{wrapfigure}{l}{0.340\linewidth}", path_b)
        self.assertIn(r"\setlength{\parskip}{0pt}", path_b)
        self.assertIn(r"\fontsize{10.5}{12.1}\selectfont\itshape\color{CMMuted}", path_b)
        self.assertIn(r"\noindent No subclass lead text is currently supplied by Step 4.\par", path_b)
        self.assertIn(r"\vskip\dimen@", path_b)
        self.assertLess(path_b.index(r"\WFclear"), path_b.index("FOUNDATION"))

    def test_missing_subclass_art_omits_wrapfigure_and_keeps_progression_full_width(self):
        view, config = self._fixture()
        view["subclasses"][0]["image"] = ""
        tex = self._render(view, config)
        path_a = tex[tex.index("PATH A") : tex.index(r"\switchcolumn")]
        self.assertNotIn(r"\begin{wrapfigure}", path_a)
        self.assertIn("SPELLCAST TRAIT: INSTINCT", path_a)
        self.assertIn(r"\noindent First subclass sentence. Second subclass sentence.\par", path_a)
        self.assertLess(path_a.index(r"\WFclear"), path_a.index("FOUNDATION"))

    def test_short_subclass_lead_reserves_art_depth_before_progression(self):
        view, config = self._fixture()
        view["subclasses"][0]["description"] = "Short lead."
        tex = self._render(view, config)
        path_a = tex[tex.index("PATH A") : tex.index(r"\switchcolumn")]
        self.assertIn(r"\begin{wrapfigure}{l}{0.340\linewidth}", path_a)
        self.assertIn(r"\noindent Short lead.\par", path_a)
        self.assertIn(r"\ifnum\c@WF@wrappedlines>\@ne", path_a)
        self.assertIn(r"\vskip\dimen@", path_a)
        self.assertLess(path_a.index(r"\vskip\dimen@"), path_a.index(r"\WFclear"))
        self.assertLess(path_a.index(r"\WFclear"), path_a.index("FOUNDATION"))

    def test_starting_package_rows_are_top_aligned_minipage_pairs(self):
        tex = self._render()
        package = tex[tex.index("STARTING PACKAGE") : tex.index(r"\Needspace{2.6in}")]
        self.assertNotIn(r"\begin{tabularx}", package)
        self.assertIn(r"\begin{minipage}[t]{0.300\linewidth}", package)
        self.assertIn(r"\begin{minipage}[t]{0.660\linewidth}", package)
        self.assertIn(r"\begin{minipage}[t]{0.430\linewidth}", package)
        self.assertIn(r"\begin{minipage}[t]{0.530\linewidth}", package)
        self.assertIn(r"\strut Take\par", package)
        self.assertIn(r"\strut Pendant Lens\par", package)
        self.assertIn(r"\strut Suggested Weapon\par", package)
        self.assertIn(r"\strut Light Pistol\par", package)
        self.assertGreaterEqual(package.count(r"\vspace{0pt}"), 10)

    def test_starting_package_preserves_zero_valued_traits(self):
        tex = self._render()
        package = tex[tex.index("STARTING PACKAGE") : tex.index(r"\Needspace{2.6in}")]
        self.assertIn("Agility 0, Finesse 1, Instinct 2", package)

    def test_feature_separators_render_once_per_class_feature_type(self):
        tex = self._render()
        hope = tex[tex.index("HOPE FEATURE") : tex.index("CLASS FEATURES")]
        class_features = tex[tex.index("CLASS FEATURES") : tex.index("STARTING PACKAGE")]

        self.assertEqual(1, hope.count(r"\rule{\linewidth}{0.45pt}"))
        self.assertEqual(1, class_features.count(r"\rule{\linewidth}{0.45pt}"))
        between_features = class_features[
            class_features.index("Class Engine") : class_features.index("Class Relay")
        ]
        self.assertNotIn(r"\rule{\linewidth}{0.45pt}", between_features)
        self.assertLess(
            class_features.index("Class Relay"),
            class_features.index(r"\rule{\linewidth}{0.45pt}"),
        )

    def test_feature_separators_render_once_per_subclass_progression_type(self):
        tex = self._render()
        path_a = tex[tex.index("PATH A") : tex.index(r"\switchcolumn")]
        foundation = path_a[path_a.index("FOUNDATION") : path_a.index("SPECIALIZATION")]
        specialization = path_a[path_a.index("SPECIALIZATION") : path_a.index("MASTERY")]
        mastery = path_a[path_a.index("MASTERY") :]

        self.assertEqual(1, foundation.count(r"\rule{\linewidth}{0.35pt}"))
        self.assertEqual(1, specialization.count(r"\rule{\linewidth}{0.35pt}"))
        self.assertEqual(1, mastery.count(r"\rule{\linewidth}{0.35pt}"))
        between_foundation_features = foundation[
            foundation.index("A Foundation") : foundation.index("A Foundation Two")
        ]
        self.assertNotIn(r"\rule{\linewidth}{0.35pt}", between_foundation_features)
        self.assertLess(
            foundation.index("A Foundation Two"),
            foundation.index(r"\rule{\linewidth}{0.35pt}"),
        )

    def test_non_feature_identity_separator_is_preserved(self):
        tex = self._render()
        path_a = tex[tex.index("PATH A") : tex.index("FOUNDATION")]
        self.assertIn(r"\rule{\linewidth}{0.55pt}", path_a)

    def test_refined_renderer_uses_parallel_breakable_subclass_flow_without_forced_clearpage(self):
        tex = self._render()
        self.assertIn(r"\usepackage{paracol}", tex)
        self.assertIn(r"\begin{paracol}{2}", tex)
        self.assertIn(r"\switchcolumn", tex)
        self.assertIn(r"\end{paracol}", tex)
        self.assertNotIn(r"\clearpage", tex)
        self.assertLess(tex.index("STARTING PACKAGE"), tex.index(r"\Needspace{2.6in}"))
        self.assertLess(tex.index(r"\Needspace{2.6in}"), tex.index(r"\begin{paracol}{2}"))

    def test_refined_renderer_restores_base_helpers_after_use(self):
        import rulebook_layout.class_package_compact as base

        before = (
            base._class_opening_tex,
            base._class_support_tex,
            base._subclass_tex,
            base._package_column_tex,
            base.latex_escape,
        )
        first = self._render()
        after_first = (
            base._class_opening_tex,
            base._class_support_tex,
            base._subclass_tex,
            base._package_column_tex,
            base.latex_escape,
        )
        second = self._render()
        after_second = (
            base._class_opening_tex,
            base._class_support_tex,
            base._subclass_tex,
            base._package_column_tex,
            base.latex_escape,
        )
        self.assertEqual(before, after_first)
        self.assertEqual(before, after_second)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()