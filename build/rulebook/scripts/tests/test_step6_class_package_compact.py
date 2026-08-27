import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulebook_layout.class_package_compact as compact
from rulebook_layout.class_package_compact import render_class_package_tex


class TestStep6CompactClassPackage(unittest.TestCase):
    def _fixture(self):
        feature = lambda name, description: {"name": name, "description": description}
        view = {
            "chapter": 12,
            "class": {
                "name": "Test Class",
                "description": "First class sentence.\n\nSecond class sentence.\n\nThird class sentence.",
                "domains": ["arcana", "circuit"],
                "hitPoints": 5,
                "evasion": 11,
                "image": "assets/icons/classes/test-class.png",
                "features": {
                    "hope": [feature("Hope Signal", "First hope sentence. Second hope sentence.")],
                    "class": [feature("Class Engine", "Class feature text.")],
                },
                "classItems": [],
                "startingInventory": {
                    "take": [{"name": "Take Item"}],
                    "choiceA": [{"name": "Choice A Item"}],
                    "choiceB": [{"name": "Choice B Item"}],
                },
                "characterGuide": {
                    "suggestedPrimaryWeapon": {"name": "Primary Weapon"},
                    "suggestedSecondaryWeapon": None,
                    "suggestedArmor": {"name": "Test Armor"},
                    "suggestedTraits": {"agility": 2, "finesse": 1},
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

    def _render(self) -> str:
        view, config = self._fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            return render_class_package_tex(view, config, root / "source", root / "out")

    def test_class_stats_align_with_art_and_features_follow_opening(self):
        tex = self._render()

        self.assertIn(
            "\\begin{minipage}[t]{0.430\\linewidth}\n\\vspace{0pt}\n\\centering\n\\includegraphics[width=\\linewidth,height=3.9in",
            tex,
        )
        self.assertLess(tex.index("HIT POINTS"), tex.index("HOPE FEATURE"))
        self.assertLess(tex.index("HOPE FEATURE"), tex.index("CLASS FEATURES"))
        self.assertLess(tex.index("CLASS FEATURES"), tex.index("\\begin{paracol}{2}"))

    def test_two_subclasses_use_page_breakable_parallel_columns(self):
        tex = self._render()
        subclass_flow = tex[tex.index("\\begin{paracol}{2}") : tex.index("\\end{paracol}")]

        self.assertIn("\\usepackage{paracol}", tex)
        self.assertEqual(tex.count("\\begin{paracol}{2}"), 1)
        self.assertEqual(tex.count("\\end{paracol}"), 1)
        self.assertEqual(subclass_flow.count("\\switchcolumn"), 1)
        self.assertIn("PATH A", subclass_flow)
        self.assertIn("PATH B", subclass_flow)
        self.assertLess(subclass_flow.index("PATH A"), subclass_flow.index("\\switchcolumn"))
        self.assertLess(subclass_flow.index("\\switchcolumn"), subclass_flow.index("PATH B"))
        self.assertNotIn("\\clearpage", tex)

    def test_long_subclass_content_remains_in_parallel_breakable_columns(self):
        view, config = self._fixture()
        view["subclasses"][1]["description"] = " ".join(["Long subclass publication text."] * 180)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tex = render_class_package_tex(view, config, root / "source", root / "out")

        subclass_flow = tex[tex.index("\\begin{paracol}{2}") : tex.index("\\end{paracol}")]
        self.assertEqual(tex.count("\\begin{paracol}{2}"), 1)
        self.assertEqual(subclass_flow.count("\\switchcolumn"), 1)
        self.assertIn("Long subclass publication text.", subclass_flow)
        self.assertNotIn("\\clearpage", tex)
        self.assertFalse(hasattr(compact, "MAX_TWO_COLUMN_SUBCLASS_LINES"))

    def test_subclass_flow_can_follow_starting_package_without_forced_page_break(self):
        tex = self._render()
        package_to_subclasses = tex[tex.index("STARTING PACKAGE") : tex.index("\\begin{paracol}{2}")]

        self.assertNotIn("\\clearpage", package_to_subclasses)
        self.assertIn("\\Needspace{2.6in}", package_to_subclasses)
        self.assertIn("\\setlength{\\columnsep}{0.030\\linewidth}", package_to_subclasses)

    def test_webp_assets_are_converted_to_render_only_pngs_for_lualatex(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "source"
            output_dir = root / "out"
            source = source_root / "assets" / "icons" / "classes" / "cybermancer.webp"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"webp fixture")

            def fake_convert(source_path, destination_path):
                self.assertEqual(source_path, source)
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                destination_path.write_bytes(b"png fixture")

            with patch.object(compact, "_convert_raster_to_png", side_effect=fake_convert) as convert:
                tex_path = compact._tex_image_path(
                    source_root,
                    output_dir,
                    "assets/icons/classes/cybermancer.webp",
                )

            convert.assert_called_once()
            self.assertEqual(
                tex_path,
                r"\detokenize{_render-assets/assets/icons/classes/cybermancer.png}",
            )
            self.assertTrue((output_dir / "_render-assets/assets/icons/classes/cybermancer.png").is_file())

    def test_subclass_art_is_half_height_and_trait_starts_at_art_top(self):
        tex = self._render()

        self.assertEqual(tex.count("height=1.55in"), 2)
        self.assertGreaterEqual(tex.count("\\vspace{0pt}"), 5)
        path_a = tex[tex.index("PATH A") : tex.index("\\switchcolumn")]
        self.assertLess(path_a.index("height=1.55in"), path_a.index("SPELLCAST TRAIT: INSTINCT"))
        self.assertLess(path_a.index("SPELLCAST TRAIT: INSTINCT"), path_a.index("FOUNDATION"))
        self.assertLess(path_a.index("FOUNDATION"), path_a.index("SPECIALIZATION"))
        self.assertLess(path_a.index("SPECIALIZATION"), path_a.index("MASTERY"))

    def test_class_and_subclass_leads_are_collapsed_to_single_paragraphs(self):
        tex = self._render()

        self.assertIn("\\frenchspacing", tex)
        self.assertIn("First class sentence. Second class sentence. Third class sentence.", tex)
        self.assertNotIn("First class sentence.\n\nSecond class sentence.", tex)
        self.assertIn("First subclass sentence. Second subclass sentence.", tex)
        self.assertNotIn("First subclass sentence.\n\nSecond subclass sentence.", tex)

    def test_class_and_subclass_description_blocks_have_explicit_top_spacing(self):
        tex = self._render()

        self.assertIn(
            "\\end{tabularx}\n\\vspace{3.0mm}\n{\\fontsize{10.5}{12.3}\\selectfont First class sentence.",
            tex,
        )
        path_a = tex[tex.index("PATH A") : tex.index("\\switchcolumn")]
        self.assertIn(
            "SPELLCAST TRAIT: INSTINCT\n}}\n\\vspace{2.0mm}\n{\\fontsize{10.5}{12.1}\\selectfont First subclass sentence.",
            path_a,
        )

    def test_starting_package_uses_two_aligned_columns(self):
        tex = self._render()
        package = tex[tex.index("STARTING PACKAGE") : tex.index("\\Needspace{2.6in}")]

        self.assertEqual(package.count("\\begin{minipage}[t]{0.485\\linewidth}"), 2)
        self.assertIn("\\end{minipage}\\hfill", package)
        self.assertIn("\\strut Take & \\strut Take Item", package)
        self.assertIn("\\strut Choice A & \\strut Choice A Item", package)
        self.assertIn("\\strut Choice B & \\strut Choice B Item", package)
        self.assertIn("\\strut Suggested Weapon & \\strut Primary Weapon", package)
        self.assertIn("\\strut Suggested Armor & \\strut Test Armor", package)
        self.assertIn("\\strut Suggested Traits & \\strut Agility 2, Finesse 1", package)
        self.assertLess(package.index("\\strut Take"), package.index("\\strut Suggested Weapon"))

    def test_typography_has_ten_point_five_minimum_domains_fourteen_and_features_twelve(self):
        tex = self._render()

        explicit_sizes = [float(value) for value in re.findall(r"\\fontsize\{([0-9.]+)\}", tex)]
        self.assertTrue(explicit_sizes)
        self.assertGreaterEqual(min(explicit_sizes), 10.5)
        self.assertIn("\\fontsize{14}{15}\\selectfont\\bfseries\\color{CMAccent} ARCANA • CIRCUIT", tex)
        self.assertIn("\\fontsize{12}{13.2}\\selectfont\\bfseries\\color{CMInk} Hope Signal", tex)
        self.assertIn("\\fontsize{10.5}{12.3}\\selectfont First class sentence.", tex)
        self.assertIn("\\fontsize{10.5}{12.1}\\selectfont First subclass sentence.", tex)

    def test_feature_separator_follows_description(self):
        tex = self._render()

        hope = tex[tex.index("Hope Signal") : tex.index("CLASS FEATURES")]
        self.assertLess(hope.index("First hope sentence. Second hope sentence."), hope.index("\\rule{\\linewidth}{0.45pt}"))
        self.assertLess(hope.index("Hope Signal"), hope.index("First hope sentence. Second hope sentence."))

        path_a = tex[tex.index("A Foundation") : tex.index("A Specialization")]
        self.assertLess(path_a.index("Foundation A."), path_a.index("\\rule{\\linewidth}{0.35pt}"))


if __name__ == "__main__":
    unittest.main()
