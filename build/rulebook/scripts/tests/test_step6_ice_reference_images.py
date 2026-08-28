import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.ice_reference_images import (
    attach_ice_reference_images,
    ice_reference_publication_images,
)
from rulebook_layout.ice_reference_refined import render_ice_reference_tex


class TestStep6IceReferenceImages(unittest.TestCase):
    def _view(self):
        return {
            "chapter": 29,
            "title": "ICE Reference",
            "partLabel": "GM ENCOUNTER TOOLKIT",
            "chapterIntro": "Reference text.",
            "groups": [
                {
                    "iceType": "sentry",
                    "title": "Sentry ICE",
                    "entries": [
                        {
                            "semanticId": "entity:features:test",
                            "name": "Test ICE",
                            "iceType": "sentry",
                            "rulesMarkdown": "Reader-facing rules.",
                            "actions": [],
                        }
                    ],
                }
            ],
        }

    def _sidecar(self, image="assets/icons/ice/test.webp", status="PASS"):
        publication = {}
        if image is not None:
            publication["image"] = image
        return {
            "icePublicationImageSemantics": {
                "schema": "cybermancy-step4-ice-publication-images-v1.0",
                "status": status,
                "iceCount": 1,
                "publicationImageCount": 1 if image else 0,
            },
            "entities": [
                {
                    "semanticId": "entity:features:test",
                    "publicationData": publication,
                }
            ],
        }

    def _config(self):
        return {
            "prototypePolicy": {
                "requirePublicationImageSemanticsPass": False,
                "requireStagedImages": False,
                "allowMissingImagesWithBlankFallback": True,
            },
            "composition": {
                "pageColumns": 2,
                "missingImageFallback": "blank-block",
            },
            "style": {
                "entryIdentityImageHeightIn": 0.38,
                "entryIdentityImageGapIn": 0.07,
            },
        }

    def test_image_layer_is_optional_when_package_does_not_enable_it(self):
        view = self._view()
        report = {"status": "PASS", "errors": [], "warnings": [], "checks": []}
        attach_ice_reference_images(
            view,
            {"entities": []},
            {"prototypePolicy": {}, "composition": {}, "style": {}},
            report,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"][-1]["code"], "ICE_REFERENCE_IMAGES")
        self.assertEqual(report["checks"][-1]["details"], {"enabled": False})
        self.assertNotIn("image", view["groups"][0]["entries"][0])

    def test_selected_ice_receives_only_staged_publication_image_path(self):
        view = self._view()
        report = {"status": "PASS", "errors": [], "warnings": [], "checks": []}
        attach_ice_reference_images(view, self._sidecar(), self._config(), report)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(view["groups"][0]["entries"][0]["image"], "assets/icons/ice/test.webp")
        self.assertEqual(ice_reference_publication_images(view), ["assets/icons/ice/test.webp"])

    def test_missing_image_uses_blank_block_without_failing_package(self):
        view = self._view()
        report = {"status": "PASS", "errors": [], "warnings": [], "checks": []}
        attach_ice_reference_images(view, self._sidecar(None, status="FAIL"), self._config(), report)
        entry = view["groups"][0]["entries"][0]
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(entry.get("imageFallback"), "blank-block")
        self.assertNotIn("image", entry)
        self.assertEqual(ice_reference_publication_images(view), [])
        self.assertTrue(report["warnings"])

    def test_runtime_image_path_uses_blank_block_instead_of_leaking_runtime_reference(self):
        view = self._view()
        report = {"status": "PASS", "errors": [], "warnings": [], "checks": []}
        attach_ice_reference_images(
            view,
            self._sidecar("modules/cybermancy/assets/icons/ice/test.webp", status="FAIL"),
            self._config(),
            report,
        )
        entry = view["groups"][0]["entries"][0]
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(entry.get("imageFallback"), "blank-block")
        self.assertNotIn("image", entry)

    def test_renderer_places_image_only_in_identity_row(self):
        view = self._view()
        view["groups"][0]["entries"][0]["image"] = "assets/icons/ice/test.webp"
        tex = render_ice_reference_tex(
            view,
            self._config(),
            {"assets/icons/ice/test.webp": "C:/render/test.png"},
        )
        self.assertIn(r"\usepackage{graphicx}", tex)
        self.assertIn(r"\includegraphics[height=0.380in,width=0.380in,keepaspectratio]", tex)
        self.assertIn(r"\begin{minipage}[c]{\dimexpr\linewidth-0.450in\relax}", tex)
        identity_end = tex.index(r"\end{minipage}\par")
        rules_pos = tex.index("Reader-facing rules.")
        self.assertGreater(rules_pos, identity_end)

    def test_renderer_uses_soft_blank_block_in_same_identity_slot(self):
        view = self._view()
        view["groups"][0]["entries"][0]["imageFallback"] = "blank-block"
        tex = render_ice_reference_tex(view, self._config(), {})
        self.assertIn(r"\colorbox{CMSoft}{\parbox[c][0.380in][c]{0.380in}{}}", tex)
        self.assertIn(r"\begin{minipage}[c]{\dimexpr\linewidth-0.450in\relax}", tex)
        identity_end = tex.index(r"\end{minipage}\par")
        rules_pos = tex.index("Reader-facing rules.")
        self.assertGreater(rules_pos, identity_end)


if __name__ == "__main__":
    unittest.main()
