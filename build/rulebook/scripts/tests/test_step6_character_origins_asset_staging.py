from __future__ import annotations

import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.character_origins_integration import compose_character_origins_stage


class Step6CharacterOriginsAssetStagingTests(unittest.TestCase):
    def test_composer_uses_inherited_prose_asset_stager(self) -> None:
        ancestry_titles = [f"Ancestry {index:02d}" for index in range(1, 19)]
        community_titles = [f"Community {index:02d}" for index in range(1, 10)]
        stage_calls: list[int] = []

        def extract_target_chapters(_prose, _source_text):
            return {
                10: {"markdown": "chapter-ten\n"},
                11: {"markdown": "chapter-eleven\n"},
            }

        def annotate_chapter(_markdown, chapter, _entry_kind):
            titles = ancestry_titles if chapter == 10 else community_titles
            feature_count = 2 if chapter == 10 else 1
            entries = [
                {
                    "title": title,
                    "features": [
                        {"name": f"Feature {feature_index}", "description": "Rules."}
                        for feature_index in range(feature_count)
                    ],
                }
                for title in titles
            ]
            return f"annotated-{chapter}\n", entries

        origin = types.SimpleNamespace(
            RAW_MKDOCS_RE=re.compile(r"$^"),
            extract_target_chapters=extract_target_chapters,
            annotate_chapter=annotate_chapter,
        )

        def stage_markdown_assets(annotated, chapter, _asset_root, _asset_cache, missing):
            self.assertEqual(missing, [])
            stage_calls.append(chapter)
            count = 18 if chapter == 10 else 9
            return annotated + f"staged-{chapter}\n", count

        prose = types.SimpleNamespace(stage_markdown_assets=stage_markdown_assets)

        config = {
            "schema": "cybermancy-rulebook-character-origins-layout-v1",
            "version": "1.0",
            "status": "ACCEPTED",
            "expectedCorpus": {
                "10": {"entries": ancestry_titles},
                "11": {"entries": community_titles},
            },
            "freeze": {
                "status": "frozen",
                "version": "v1.0",
                "acceptanceCorpus": {
                    "ancestories": 18,
                    "communities": 9,
                    "stagedArtwork": 27,
                },
            },
        }
        contract = {
            "transformationOrder": [
                {"order": 40, "stage": "character-origins", "chapters": [10, 11]}
            ],
            "regressionExpectations": {
                "characterOrigins": {
                    "ancestories": 18,
                    "communities": 9,
                    "artwork": 27,
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = root / "character-origins.py"
            prose_builder = root / "prose.py"
            config_path = root / "config.json"
            lua_filter = root / "filter.lua"
            complete_source = root / "complete.md"
            player_source = root / "player.md"
            asset_root = root / "assets"
            work_dir = root / "work"

            builder.write_text("# fake\n", encoding="utf-8")
            prose_builder.write_text("# fake\n", encoding="utf-8")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            lua_filter.write_text("-- fake\n", encoding="utf-8")
            complete_source.write_text("same\n", encoding="utf-8")
            player_source.write_text("same\n", encoding="utf-8")
            asset_root.mkdir()

            def module_loader(_path, name):
                if name == "cybermancy_character_origins_integration_source":
                    return origin
                if name == "cybermancy_prose_integration_source":
                    return prose
                raise AssertionError(name)

            with patch(
                "rulebook_layout.character_origins_integration._load_module",
                side_effect=module_loader,
            ), patch(
                "rulebook_layout.character_origins_integration._pandoc_latex",
                side_effect=lambda markdown, *_args: f"\\CMFragment{{{markdown.strip()}}}\n",
            ):
                payload, report = compose_character_origins_stage(
                    builder,
                    prose_builder,
                    config_path,
                    lua_filter,
                    complete_source,
                    player_source,
                    asset_root,
                    work_dir,
                    contract,
                    "pandoc",
                    "markdown",
                )

        self.assertIsNotNone(payload)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["assetStagingOwner"], "long-form-prose-v1")
        self.assertEqual(stage_calls, [10, 11])
        self.assertEqual(payload.artwork, 27)
        self.assertEqual(payload.ancestories, 18)
        self.assertEqual(payload.communities, 9)


if __name__ == "__main__":
    unittest.main()
