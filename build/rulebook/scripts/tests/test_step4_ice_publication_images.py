import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_step4_ice_publication_images import _mapped_logical_image


class TestStep4IcePublicationImages(unittest.TestCase):
    def test_foundry_runtime_image_maps_to_logical_publication_asset(self):
        mappings = [
            {
                "prefix": "modules/cybermancy/",
                "repoPrefix": "",
            }
        ]
        logical, error = _mapped_logical_image(
            "modules/cybermancy/assets/icons/ice/black-ice.webp",
            mappings,
        )
        self.assertIsNone(error)
        self.assertEqual(logical, "assets/icons/ice/black-ice.webp")

    def test_unmapped_runtime_prefix_fails_closed(self):
        logical, error = _mapped_logical_image(
            "modules/cybermancy/assets/icons/ice/black-ice.webp",
            [],
        )
        self.assertIsNone(logical)
        self.assertEqual(error, "unmapped-runtime-prefix")

    def test_remote_image_is_not_a_staged_publication_source(self):
        logical, error = _mapped_logical_image("https://example.test/ice.webp", [])
        self.assertIsNone(logical)
        self.assertEqual(error, "remote")


if __name__ == "__main__":
    unittest.main()
