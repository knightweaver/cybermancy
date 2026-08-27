import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_normalize.markdown import (
    ensure_image_heading_block_boundaries,
    select_named_sections,
)
from rulebook_normalize.validate import add_check, new_report
from rulebook_step4_prose_boundaries import (
    _assert_authoritative_package,
    _normalize_and_validate_assembled_profiles,
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

    def test_step4_package_origin_is_authoritative_scripts_package(self):
        details = _assert_authoritative_package()
        self.assertEqual(
            Path(details["loadedPackageDirectory"]),
            Path(details["expectedPackageDirectory"]),
        )
        self.assertIn("build", details["loadedPackageDirectory"])
        self.assertIn("rulebook_normalize", details["loadedPackageDirectory"])

    def test_actual_assembled_output_is_normalized_and_validated(self):
        with tempfile.TemporaryDirectory() as td:
            outroot = Path(td) / "rulebook"
            assembled = outroot / "source" / "assembled"
            metadata = outroot / "source" / "metadata"
            assembled.mkdir(parents=True)
            metadata.mkdir(parents=True)

            profile = assembled / "complete-rulebook.md"
            profile.write_text(
                "---\n"
                "title: Test\n"
                "---\n\n"
                "![Corp](../assets/corp.webp)\n"
                "### Corp Name\n"
                "Body.\n",
                encoding="utf-8",
            )

            report = new_report()
            _normalize_and_validate_assembled_profiles(
                outroot,
                report,
                add_check=add_check,
            )

            normalized = profile.read_text(encoding="utf-8")
            self.assertIn(
                "![Corp](../assets/corp.webp)\n\n### Corp Name",
                normalized,
            )
            codes = {item["code"]: item for item in report["checks"]}
            self.assertEqual(
                codes["ASSEMBLED_IMAGE_HEADING_BOUNDARIES"]["status"],
                "PASS",
            )
            self.assertEqual(
                codes["ASSEMBLED_IMAGE_HEADING_BOUNDARIES"]["details"]["normalizedBoundaryCount"],
                1,
            )
            self.assertTrue((metadata / "validation.json").is_file())


if __name__ == "__main__":
    unittest.main()
