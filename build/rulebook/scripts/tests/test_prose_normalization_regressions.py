import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_normalize.markdown import (
    ensure_image_heading_block_boundaries,
    select_named_sections,
)


class TestProseNormalizationRegressions(unittest.TestCase):
    def test_image_heading_block_boundary_is_explicit_and_idempotent(self):
        src = "![Corp](corp.webp)\n### Corp Name\nBody.\n"
        out = ensure_image_heading_block_boundaries(src)
        self.assertIn("![Corp](corp.webp)\n\n### Corp Name", out)
        self.assertEqual(ensure_image_heading_block_boundaries(out), out)

    def test_selected_parent_and_descendant_are_not_duplicated(self):
        src = (
            "# Philosophical Interpretation\n"
            "Lead.\n\n"
            "## Tone and Themes\n"
            "Keep once.\n"
        )
        out = select_named_sections(
            src,
            ["Philosophical Interpretation", "Tone and Themes"],
            include_preamble=False,
        )
        self.assertEqual(out.count("## Tone and Themes"), 1)
        self.assertEqual(out.count("Keep once."), 1)


if __name__ == "__main__":
    unittest.main()
