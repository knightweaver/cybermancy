import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_step4_ice_publication_image_overrides import publication_image_override


class TestStep4IcePublicationImageOverrides(unittest.TestCase):
    def test_wall_of_static_uses_explicit_checked_in_publication_asset(self):
        logical = publication_image_override("entity:features:DtCHCxPKWAwK89kq")
        self.assertEqual(logical, "assets/icons/features/wall-of-static.webp")
        self.assertTrue(
            (REPO_ROOT / "docs/player-facing" / logical).is_file(),
            "Wall of Static publication image override must resolve to a checked-in asset.",
        )

    def test_unknown_ice_has_no_override(self):
        self.assertIsNone(publication_image_override("entity:features:not-an-exception"))


if __name__ == "__main__":
    unittest.main()
