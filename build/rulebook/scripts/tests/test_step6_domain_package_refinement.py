import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.domain_package_refined import render_domain_package_tex


class TestStep6DomainPackageRefinement(unittest.TestCase):
    def _render(self) -> str:
        cards = [
            {
                "name": name,
                "description": (
                    f"{name} first sentence.\n\n{name} second sentence continues the same published card text."
                ),
                "image": f"assets/cards/{name.lower()}.png",
                "level": 3,
                "recallCost": 1,
                "cardType": "ability",
                "inVault": False,
            }
            for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")
        ]
        view = {
            "chapter": 14,
            "domain": {
                "name": "Maker",
                "cardCount": 6,
                "artwork": {"image": "assets/icons/domains/maker.png"},
            },
            "levels": [{"level": 3, "cards": cards}],
        }
        # Intentionally request values below the accepted minimum so this fixture
        # proves the renderer enforces the 10.5 pt card-text floor.
        config = {
            "chapter": 14,
            "partLabel": "CHARACTER OPTIONS",
            "composition": {
                "pageColumns": 3,
                "defaultCardType": "ability",
            },
            "style": {
                "columnSepIn": 0.18,
                "minimumCardTextFontPt": 10.5,
                "cardBodyFontPt": 9.0,
                "cardBodyLeadingPt": 11.3,
                "cardMetaFontPt": 8.0,
                "cardMetaLeadingPt": 9.0,
            },
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            return render_domain_package_tex(
                view,
                config,
                root / "source",
                root / "output",
            )

    def test_three_column_paracol_flow_is_used(self):
        tex = self._render()
        level = tex[tex.index("LEVEL 3") : tex.index("\\end{paracol}")]
        self.assertIn(r"\begin{paracol}{3}", level)
        self.assertEqual(level.count(r"\switchcolumn"), 2)
        self.assertNotIn(r"\begin{multicols}{3}", level)

    def test_each_column_starts_at_same_zero_glue_origin(self):
        tex = self._render()
        level = tex[tex.index(r"\begin{paracol}{3}") : tex.index(r"\end{paracol}")]
        columns = level.split(r"\switchcolumn")
        self.assertEqual(len(columns), 3)
        for segment, first_name in zip(columns, ("Alpha", "Gamma", "Epsilon")):
            self.assertIn(r"\vspace{0pt}", segment)
            prefix = segment[: segment.index(first_name)]
            self.assertNotIn(r"\Needspace", prefix)

    def test_card_header_rule_is_removed(self):
        tex = self._render()
        self.assertNotIn(r"\rule{\linewidth}{0.75pt}", tex)
        self.assertIn(r"\rule{\linewidth}{0.35pt}", tex)

    def test_card_description_uses_classpackage_zero_parskip_fix(self):
        tex = self._render()
        alpha = tex[tex.index("Alpha") : tex.index("Beta")]
        self.assertIn(r"\setlength{\parskip}{0pt}", alpha)
        self.assertIn(r"\setlength{\parindent}{0pt}", alpha)
        self.assertIn(r"\setlength{\emergencystretch}{1.5em}", alpha)
        self.assertIn(r"\fontsize{10.50}{12.10}\selectfont\color{CMInk}", alpha)
        self.assertIn(
            r"\noindent Alpha first sentence. Alpha second sentence continues the same published card text.\par",
            alpha,
        )

    def test_all_text_inside_card_respects_10_5pt_floor(self):
        tex = self._render()
        alpha = tex[tex.index("Alpha") : tex.index("Beta")]
        self.assertIn(r"\fontsize{12.00}{13.00}\selectfont", alpha)
        self.assertGreaterEqual(alpha.count(r"\fontsize{10.50}{11.50}\selectfont"), 2)
        self.assertNotIn(r"\fontsize{9.00}", alpha)
        self.assertNotIn(r"\fontsize{8.00}", alpha)
        self.assertNotIn(r"\fontsize{6.9}", alpha)

    def test_card_metadata_is_stacked_to_avoid_narrow_column_overflow(self):
        tex = self._render()
        alpha = tex[tex.index("Alpha") : tex.index("Beta")]
        self.assertIn("LEVEL 3\\par", alpha)
        self.assertIn("RECALL COST 1\\par", alpha)
        self.assertNotIn(r"\textbullet", alpha)


if __name__ == "__main__":
    unittest.main()
