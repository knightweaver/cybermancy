import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.class_package_compact import render_class_package_tex


class TestStep6CompactClassPackage(unittest.TestCase):
    def _fixture(self):
        feature = lambda name, description: {"name": name, "description": description}
        view = {
            "chapter": 12,
            "class": {
                "name": "Test Class",
                "description": "Class description.",
                "domains": ["arcana", "circuit"],
                "hitPoints": 5,
                "evasion": 11,
                "image": "assets/icons/classes/test-class.png",
                "features": {
                    "hope": [feature("Hope Signal", "Hope feature text.")],
                    "class": [feature("Class Engine", "Class feature text.")],
                },
                "classItems": [],
                "startingInventory": {},
                "characterGuide": {},
            },
            "subclasses": [
                {
                    "name": "Path A",
                    "description": "First subclass description.",
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
                    "description": "Second subclass description.",
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

    def test_class_stats_align_with_art_and_features_follow_opening(self):
        view, config = self._fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = render_class_package_tex(view, config, root / "source", root / "out")

        self.assertIn(
            "\\begin{minipage}[t]{0.430\\linewidth}\n\\vspace{0pt}\n\\centering\n\\includegraphics[width=\\linewidth,height=3.9in",
            tex,
        )
        self.assertLess(tex.index("HIT POINTS"), tex.index("HOPE FEATURE"))
        self.assertLess(tex.index("HOPE FEATURE"), tex.index("CLASS FEATURES"))
        self.assertLess(tex.index("CLASS FEATURES"), tex.index("\\clearpage"))

    def test_two_subclasses_share_one_page_in_parallel_columns(self):
        view, config = self._fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = render_class_package_tex(view, config, root / "source", root / "out")

        self.assertEqual(tex.count("\\clearpage"), 1)
        self.assertEqual(tex.count("\\begin{minipage}[t]{0.485\\linewidth}"), 2)
        self.assertIn("PATH A", tex)
        self.assertIn("PATH B", tex)
        between = tex[tex.index("PATH A") : tex.index("PATH B")]
        self.assertNotIn("\\clearpage", between)
        self.assertIn("\\hfill", between)

    def test_subclass_art_is_half_height_and_trait_starts_at_art_top(self):
        view, config = self._fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = render_class_package_tex(view, config, root / "source", root / "out")

        self.assertEqual(tex.count("height=1.55in"), 2)
        self.assertGreaterEqual(tex.count("\\vspace{0pt}"), 7)
        path_a = tex[tex.index("PATH A") : tex.index("PATH B")]
        self.assertLess(path_a.index("height=1.55in"), path_a.index("SPELLCAST TRAIT: INSTINCT"))
        self.assertLess(path_a.index("SPELLCAST TRAIT: INSTINCT"), path_a.index("FOUNDATION"))
        self.assertLess(path_a.index("FOUNDATION"), path_a.index("SPECIALIZATION"))
        self.assertLess(path_a.index("SPECIALIZATION"), path_a.index("MASTERY"))


if __name__ == "__main__":
    unittest.main()
