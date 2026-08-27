import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parents[1]
ICE_REFERENCE_CLI = SCRIPT_DIR / "build-rulebook-ice-reference.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rulebook_layout.ice_reference import compose_ice_reference
from rulebook_layout.ice_reference_geometry import evaluate_ice_reference_text
from rulebook_layout.ice_reference_refined import markdown_to_tex, render_ice_reference_tex


class TestStep6IceReference(unittest.TestCase):
    def _fixture(self):
        def ice(semantic_id, source_id, name, ice_type, rules="Rules text.", *, actions=None, resource=None, audience="gm"):
            publication = {"featureCategory": "ice", "iceType": ice_type, "standalonePublication": True}
            if rules:
                publication["rulesMarkdown"] = rules
            if actions:
                publication["actions"] = actions
            if resource:
                publication["resource"] = resource
            return {"semanticId": semantic_id, "family": "features", "sourceId": source_id, "name": name, "audience": audience, "publicationData": publication}

        entities = [
            ice("entity:features:s1", "s1", "Tar Pit", "sentry", "Compact baseline rules.", resource={"type": "simple", "value": 12}),
            ice("entity:features:s2", "s2", "Heaven's Gate", "sentry", "Long rules paragraph.\n\n* Critical success outcome\n* Success outcome\n* Failure outcome"),
            ice("entity:features:s3", "s3", "Black ICE", "sentry", "Dangerous rules.", actions=[{
                "sourceId": "internal-action-id", "name": "Burn", "type": "damage", "actionType": "action",
                "rulesMarkdown": "Spend 1 Fear to deal direct damage.",
                "cost": [{"key": "Fear", "value": 1, "scalable": False, "consumeOnSuccess": False}],
                "damage": {"parts": [{"applyTo": "hitPoints", "types": [], "value": {"customFormula": "1"}}]},
            }]),
            ice("entity:features:w1", "w1", "Wall of Static", "wall", "", actions=[{
                "name": "Zap", "actionType": "action", "rulesMarkdown": "The wall sends feedback down the line.",
                "damage": {"parts": [{"applyTo": "stress", "types": [], "value": {"customFormula": "1"}}]},
            }], resource={"type": "simple", "value": 10}),
            ice("entity:features:w2", "w2", "Sleaze Gate", "wall", "The outcomes are:\n\n* Critical success\n* Failure\n  * Advance alert by 2\n  * Hacking attempts are at -2", resource={"type": "simple", "value": 14}),
            ice("entity:features:w3", "w3", "Wall of No!", "wall", "This wall says \"NO!\".\n\nAll subsequent ICE Difficulty is +3 unless this wall is disabled.", resource={"type": "simple", "value": 14}),
        ]
        sidecar = {
            "schema": "cybermancy-step4-structured-entities-v1.3",
            "iceSemantics": {
                "schema": "cybermancy-step4-ice-semantics-v1.0", "status": "PASS", "counts": {"sentry": 6, "wall": 7},
                "semanticIds": ["entity:features:s1", "entity:features:s2", "entity:features:s3", "entity:features:w1", "entity:features:w2", "entity:features:w3", "entity:features:s4", "entity:features:s5", "entity:features:s6", "entity:features:w4", "entity:features:w5", "entity:features:w6", "entity:features:w7"],
            },
            "entities": entities,
        }
        config = {
            "schema": "cybermancy-step6-ice-reference-package-config-v1.0", "chapter": 29, "chapterId": "ch29-ice-reference", "partLabel": "GM ENCOUNTER TOOLKIT", "title": "ICE Reference", "chapterIntro": "GM reference.",
            "prototype": {"mode": "representative-proof", "semanticIds": [row["semanticId"] for row in entities]},
            "composition": {"groupOrder": ["sentry", "wall"], "groupTitles": {"sentry": "Sentry ICE", "wall": "Wall ICE"}, "pageColumns": 2},
            "style": {"minimumEntryTextFontPt": 10.5, "entryBodyFontPt": 10.5, "entryBodyLeadingPt": 12.6},
            "prototypePolicy": {
                "requireStructuredSidecarSchema": "cybermancy-step4-structured-entities-v1.3", "requireIceSemanticsSchema": "cybermancy-step4-ice-semantics-v1.0", "requireIceSemanticsStatus": "PASS",
                "expectedIceTotal": 13, "expectedIceCounts": {"sentry": 6, "wall": 7}, "requireGmAudience": True, "requireReaderRules": True, "failOnRawSourceReferences": True,
            },
        }
        return sidecar, config

    def test_valid_h2_composition(self):
        sidecar, config = self._fixture()
        view, report = compose_ice_reference(sidecar, config)
        self.assertEqual(report["status"], "PASS", report)
        self.assertIsNotNone(view)
        self.assertEqual(view["schema"], "cybermancy-step6-ice-reference-package-view-v1.0")
        self.assertEqual([g["iceType"] for g in view["groups"]], ["sentry", "wall"])
        self.assertEqual([entry["name"] for entry in view["groups"][0]["entries"]], ["Black ICE", "Heaven's Gate", "Tar Pit"])
        self.assertEqual([entry["name"] for entry in view["groups"][1]["entries"]], ["Sleaze Gate", "Wall of No!", "Wall of Static"])
        raw = json.dumps(view)
        self.assertNotIn("internal-action-id", raw)
        for token in ("src/packs/", "modules/", "Compendium.", "!folders!", "systemPath"):
            self.assertNotIn(token, raw)

    def test_non_ice_or_player_audience_fails_closed(self):
        sidecar, config = self._fixture()
        sidecar["entities"][0]["audience"] = "player"
        _, report = compose_ice_reference(sidecar, config)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("ICE_REFERENCE_ENTRY_SEMANTICS", {row["code"] for row in report["errors"]})

    def test_blank_rules_and_no_action_fails_closed(self):
        sidecar, config = self._fixture()
        sidecar["entities"][0]["publicationData"]["rulesMarkdown"] = ""
        sidecar["entities"][0]["publicationData"]["actions"] = []
        _, report = compose_ice_reference(sidecar, config)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("ICE_REFERENCE_ENTRY_SEMANTICS", {row["code"] for row in report["errors"]})

    def test_action_only_entry_is_publication_complete(self):
        sidecar, config = self._fixture()
        view, report = compose_ice_reference(sidecar, config)
        self.assertEqual(report["status"], "PASS", report)
        wall_static = next(entry for group in view["groups"] for entry in group["entries"] if entry["name"] == "Wall of Static")
        self.assertEqual(wall_static["rulesMarkdown"], "")
        self.assertEqual(wall_static["actions"][0]["name"], "Zap")

    def test_markdown_nested_lists_are_preserved(self):
        tex = markdown_to_tex("* Failure\n  * Advance alert\n  * Penalty")
        self.assertEqual(tex.count(r"\begin{itemize}"), 2)
        self.assertEqual(tex.count(r"\end{itemize}"), 2)
        self.assertIn(r"\item Failure", tex)
        self.assertIn(r"\item Advance alert", tex)

    def test_renderer_uses_two_column_editorial_grammar(self):
        sidecar, config = self._fixture()
        view, report = compose_ice_reference(sidecar, config)
        self.assertEqual(report["status"], "PASS", report)
        tex = render_ice_reference_tex(view, config)
        self.assertIn("ICE REFERENCE", tex)
        self.assertIn("Sentry ICE", tex)
        self.assertIn("Wall ICE", tex)
        self.assertIn(r"\begin{multicols}{2}", tex)
        self.assertIn("Wall of No!", tex)
        self.assertIn("ACTIONS", tex)
        self.assertIn(r"\textbf{Resource:}", tex)
        self.assertNotIn("internal-action-id", tex)

    def test_rendered_text_regression_requires_each_heading_once_in_order(self):
        sidecar, config = self._fixture()
        view, report = compose_ice_reference(sidecar, config)
        self.assertEqual(report["status"], "PASS", report)
        text = "\n".join(["Sentry ICE", "Black ICE", "Heaven's Gate", "Tar Pit", "Wall ICE", "Sleaze Gate", "Wall of No!", "Wall of Static"])
        rendered = evaluate_ice_reference_text(text, view)
        self.assertEqual(rendered["status"], "PASS", rendered)

    def test_cli_validate_and_tex_only_build(self):
        sidecar, config = self._fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config_path, sidecar_path, report_path, output_dir = root / "config.json", root / "sidecar.json", root / "report.json", root / "proof"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
            validate = subprocess.run([sys.executable, str(ICE_REFERENCE_CLI), "validate", "--config", str(config_path), "--sidecar", str(sidecar_path), "--report", str(report_path)], text=True, capture_output=True)
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            self.assertEqual(validate.stdout, "build-rulebook-ice-reference.py: PASS\n")
            build = subprocess.run([sys.executable, str(ICE_REFERENCE_CLI), "build", "--config", str(config_path), "--sidecar", str(sidecar_path), "--report", str(report_path), "--output-dir", str(output_dir), "--tex-only"], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            self.assertTrue((output_dir / "ice-reference-package-view.json").is_file())
            self.assertTrue((output_dir / "Cybermancy_Chapter29_ICE_Reference_H2.tex").is_file())


if __name__ == "__main__":
    unittest.main()
