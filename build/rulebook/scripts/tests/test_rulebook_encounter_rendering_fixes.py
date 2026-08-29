import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _load_builder():
    path = SCRIPT_DIR / "build-rulebook-encounters.py"
    spec = importlib.util.spec_from_file_location("build_rulebook_encounters_rendering_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestEncounterRenderingFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = _load_builder()

    def test_environment_opener_removes_only_first_clearpage(self):
        source = r"TITLE\clearpage FIRST ENVIRONMENT\clearpage SECOND ENVIRONMENT"
        rendered, merged = self.builder._merge_environment_chapter_opener(source)
        self.assertTrue(merged)
        self.assertEqual(rendered, r"TITLE FIRST ENVIRONMENT\clearpage SECOND ENVIRONMENT")

    def test_adversary_needspace_is_rewritten_for_multicol_flow(self):
        source = (
            r"\Needspace{10\baselineskip} HEADER "
            r"\Needspace{5\baselineskip} FEATURES"
        )
        rendered, rewrites = self.builder._make_adversary_needspace_multicol_safe(source)
        self.assertEqual(rewrites, 2)
        self.assertNotIn(r"\Needspace{", rendered)
        self.assertEqual(rendered.count(r"\needspace{"), 2)
        self.assertIn(r"\needspace{10\baselineskip}", rendered)
        self.assertIn(r"\needspace{5\baselineskip}", rendered)

    def test_render_asset_rewrite_replaces_webp_source_with_png_render_path(self):
        source_root = Path("/tmp/cybermancy-step4-source")
        reference = "assets/adversaries/example.webp"
        source = self.builder._source_asset_path(source_root, reference).resolve()
        render = Path("/tmp/cybermancy-step6-render/example.png").resolve()
        tex = rf"\includegraphics{{{self.builder.esc(source.as_posix())}}}"
        rewritten = self.builder._rewrite_render_asset_paths(
            tex,
            {reference: str(render)},
            source_root,
        )
        self.assertNotIn(self.builder.esc(source.as_posix()), rewritten)
        self.assertIn(self.builder.esc(render.as_posix()), rewritten)
        self.assertNotIn(".webp", rewritten)
        self.assertIn(".png", rewritten)

    def test_selected_publication_art_references_are_deduplicated(self):
        sidecar = {
            "entities": [
                {
                    "semanticId": "entity:adversaries:A",
                    "publicationData": {"publicationArt": {"image": "assets/a.webp"}},
                },
                {
                    "semanticId": "entity:adversaries:B",
                    "publicationData": {"image": "assets/a.webp"},
                },
                {
                    "semanticId": "entity:adversaries:C",
                    "publicationData": {"publicationArt": {"image": "assets/c.png"}},
                },
            ]
        }
        refs = self.builder._selected_publication_art_references(
            sidecar,
            ["entity:adversaries:A", "entity:adversaries:B"],
        )
        self.assertEqual(refs, ["assets/a.webp"])


if __name__ == "__main__":
    unittest.main()
