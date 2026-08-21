import json, tempfile, unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_normalize.markdown import (
    segment_before_heading, segment_rules_index, drop_include_matching,
    mkdocs_admonitions_to_divs
)
from rulebook_normalize.structured import stable_id, semantic_entity_id, render_entity, is_foundry_folder
from rulebook_normalize.xrefs import audience_reference_allowed
from rulebook_normalize.assemble import assemble_profile, GM_DIVIDER
from rulebook_normalize.validate import tree_hash_manifest, sum_expected_family_counts
from rulebook_normalize.snapshot import (
    STRUCTURED_DIGEST_ALGORITHM, structured_family_snapshot
)
from rulebook_normalize.structured import collect_publication_asset_refs

class TestNormalization(unittest.TestCase):
    def test_player_index_segment(self):
        src = "# Intro\nKeep me.\n\n# The Event: The Resonance Cascade\nDrop me.\n"
        out = segment_before_heading(src, 1, "The Event: The Resonance Cascade")
        self.assertIn("Keep me.", out)
        self.assertNotIn("Resonance Cascade", out)
        self.assertNotIn("Drop me.", out)

    def test_rules_segmentation(self):
        src = (
            "# Rules\nIntro\n\n"
            "## Core rules\n{% include-markdown \"core.md\" %}\n\n"
            "## Critical fails\nKeep critical.\n\n"
            "## Armor slots\nKeep armor.\n\n"
            "## Conditions\n{% include-markdown \"conditions.md\" %}\n"
        )
        out = segment_rules_index(
            src,
            {"Core rules", "Critical fails", "Armor slots"},
            {"Conditions"}
        )
        self.assertIn("Core rules", out)
        self.assertIn("Keep critical.", out)
        self.assertIn("Keep armor.", out)
        self.assertNotIn("Conditions", out)

    def test_timeline_drops_resonance_include(self):
        src = '# Timeline\n{% include-markdown "../../_shared/world/the-resonance.md" %}\n## GM\nKeep.\n'
        out = drop_include_matching(src, "_shared/world/the-resonance.md")
        self.assertNotIn("include-markdown", out)
        self.assertIn("## GM", out)

    def test_folder_not_entity(self):
        self.assertTrue(is_foundry_folder({"_key": "!folders!ABC"}))

    def test_stable_id(self):
        self.assertEqual(stable_id({"_id": "abc"}), "abc")
        self.assertEqual(stable_id({"_key": "!items!xyz"}), "xyz")

    def test_name_collision_is_family_safe(self):
        doc = {"_id": "SAME", "name": "Reactive Shrapnel Shells"}
        self.assertNotEqual(semantic_entity_id("ammo", doc), semantic_entity_id("mods", doc))

    def test_fast_play_is_separate(self):
        doc = {
            "_id": "A1",
            "name": "Test",
            "flags": {"cybermancy": {"fastPlay": {
                "prompts": [{"label": "Default", "text": "Act.", "featureRefs": []}],
                "goal": "Pressure."
            }}}
        }
        md, meta = render_entity("adversaries", doc, ["flags.cybermancy.fastPlay"])
        self.assertIn('::: {.fast-play data-audience="gm"}', md)
        self.assertIn("**Goal:** Pressure.", md)
        self.assertEqual(meta["fastPlay"]["sourcePath"], "flags.cybermancy.fastPlay")

    def test_audience_leak(self):
        self.assertFalse(audience_reference_allowed("player", "gm"))
        self.assertFalse(audience_reference_allowed("shared", "gm"))
        self.assertTrue(audience_reference_allowed("gm", "player"))

    def test_profiles(self):
        frags = [
            {"audience": "player", "markdown": "# P", "semanticId": "section:p", "title": "P"},
            {"audience": "gm", "markdown": "# G", "semanticId": "section:g", "title": "G"},
        ]
        complete = assemble_profile(frags, "complete-rulebook")
        player = assemble_profile(frags, "player-guide")
        self.assertEqual(complete.count(GM_DIVIDER), 1)
        self.assertNotIn("# G", player)
        self.assertNotIn(GM_DIVIDER, player)

    def test_admonition(self):
        src = '!!! note "Rule"\n    Keep this.\n'
        out = mkdocs_admonitions_to_divs(src)
        self.assertIn("::: {.admonition .note}", out)
        self.assertIn("Keep this.", out)

class TestManifestIntegration(unittest.TestCase):
    def _config(self):
        return {
            'baseline': {'commit':'X','expectedLogicalEntities':1},
            'families': {'things': {'expected':1}},
            'manifestAdapter': {
                'publication': {
                    'baselineCommitPointer':'/repository/gitCommit',
                    'authoredIncludeRecordsPointer':'/publicationInputs/authoredDocuments',
                    'structuredFamilyRecordsPointer':'/publicationInputs/structuredFamilies'
                },
                'assembly': {'sectionsPointer':'/bookStructure','profilesPointer':'/buildProfiles'}
            },
            'semantics': {'gmDivider':'GM MATERIAL — SPOILERS BEYOND THIS POINT'},
            'structured': {'familyDigestAlgorithm': STRUCTURED_DIGEST_ALGORITHM}
        }

    def test_manifest_join_detects_swapped_authored_input(self):
        from rulebook_normalize.pipeline import manifest_contract_report
        pub={'repository':{'gitCommit':'X'},'publicationInputs':{'authoredDocuments':[{'path':'a.md','disposition':'INCLUDE','decisionStatus':'DECIDED'}],'structuredFamilies':[{'generatorFamily':'things','entityCount':1,'disposition':'INCLUDE','decisionStatus':'DECIDED','contentDigestAlgorithm':STRUCTURED_DIGEST_ALGORITHM}]}}
        asm={'authority':{'sourceCommit':'X'},'authoredInputs':[{'assemblyInputId':'auth.b','path':'b.md'}],'structuredFamilies':[{'familyId':'things','entityCount':1}], 'bookStructure':[{'id':'p','order':1,'chapters':[{'id':'c','number':1,'contentRefs':['auth.b','family:things']}]}], 'buildProfiles':[{'id':'complete-rulebook'},{'id':'player-guide'}], 'gmDivider':{'title':'GM MATERIAL — SPOILERS BEYOND THIS POINT','requiredInCompleteBuild':True,'omittedInPlayerBuild':True}}
        r=manifest_contract_report(pub,asm,self._config())
        self.assertEqual(r['status'],'FAIL')
        codes={x['code']:x for x in r['checks']}
        self.assertEqual(codes['AUTHORED_MANIFEST_JOIN']['status'],'ERROR')
        self.assertEqual(codes['AUTHORED_MANIFEST_JOIN']['details']['publicationOnly'],['a.md'])
        self.assertEqual(codes['AUTHORED_MANIFEST_JOIN']['details']['assemblyOnly'],['b.md'])

    def test_assembly_selector_frame_rules_obeys_step3(self):
        from rulebook_normalize.markdown import apply_assembly_selector
        src='# Rules\nLead.\n\n## Core rules\nDrop core.\n\n## Critical fails\nKeep critical.\n\n## Armor slots\nDrop armor.\n'
        rec={'assemblyMode':'segment','selector':{'include':['document lead',"heading 'Critical Fails' and its descendant headings"]}}
        out=apply_assembly_selector('docs/player-facing/rules/index.md',src,rec)
        self.assertIn('Lead.',out)
        self.assertIn('Keep critical.',out)
        self.assertNotIn('Drop core.',out)
        self.assertNotIn('Drop armor.',out)

class TestFrontMatterPlacement(unittest.TestCase):
    def _config(self):
        return {
            'baseline': {'commit':'X','expectedLogicalEntities':1},
            'families': {'things': {'expected':1}},
            'manifestAdapter': {
                'publication': {
                    'baselineCommitPointer':'/repository/gitCommit',
                    'authoredIncludeRecordsPointer':'/publicationInputs/authoredDocuments',
                    'structuredFamilyRecordsPointer':'/publicationInputs/structuredFamilies'
                },
                'assembly': {'sectionsPointer':'/bookStructure','profilesPointer':'/buildProfiles'}
            },
            'semantics': {'gmDivider':'GM MATERIAL — SPOILERS BEYOND THIS POINT'},
            'structured': {'familyDigestAlgorithm': STRUCTURED_DIGEST_ALGORITHM}
        }

    def _docs(self, divider_refs=None, opener_refs=None):
        divider_refs=['auth.gm-guide-index'] if divider_refs is None else divider_refs
        opener_refs=['auth.gm-guide-index'] if opener_refs is None else opener_refs
        pub={
            'repository':{'gitCommit':'X'},
            'publicationInputs':{
                'authoredDocuments':[{'path':'gm.md','disposition':'INCLUDE','decisionStatus':'DECIDED'}],
                'structuredFamilies':[{'generatorFamily':'things','entityCount':1,'disposition':'INCLUDE','decisionStatus':'DECIDED','contentDigestAlgorithm':STRUCTURED_DIGEST_ALGORITHM}]
            }
        }
        asm={
            'authority':{'sourceCommit':'X'},
            'authoredInputs':[{'assemblyInputId':'auth.gm-guide-index','path':'gm.md'}],
            'structuredFamilies':[{'familyId':'things','entityCount':1}],
            'bookStructure':[
                {'id':'player','order':1,'audience':'player','chapters':[{'id':'c1','number':1,'contentRefs':['family:things']}]},
                {'id':'gm','order':2,'audience':'gm','openerRefs':opener_refs,'chapters':[]},
            ],
            'buildProfiles':[{'id':'complete-rulebook'},{'id':'player-guide'}],
            'gmDivider':{
                'beforePart':'gm',
                'title':'GM MATERIAL — SPOILERS BEYOND THIS POINT',
                'requiredInCompleteBuild':True,
                'omittedInPlayerBuild':True,
                'afterDividerFrontMatterRefs':divider_refs,
            }
        }
        return pub,asm

    def test_part_opener_is_primary_authored_placement(self):
        from rulebook_normalize.pipeline import manifest_contract_report
        pub,asm=self._docs()
        r=manifest_contract_report(pub,asm,self._config())
        codes={x['code']:x for x in r['checks']}
        self.assertEqual(codes['AUTHORED_PRIMARY_PLACEMENT']['status'],'PASS')
        self.assertEqual(codes['GM_FRONT_MATTER_ROUTING']['status'],'PASS')
        self.assertEqual(r['status'],'PASS')

    def test_divider_routing_must_match_part_opener(self):
        from rulebook_normalize.pipeline import manifest_contract_report
        pub,asm=self._docs(divider_refs=['auth.other'])
        r=manifest_contract_report(pub,asm,self._config())
        codes={x['code']:x for x in r['checks']}
        self.assertEqual(codes['GM_FRONT_MATTER_ROUTING']['status'],'ERROR')


class TestSnapshotAndAssets(unittest.TestCase):
    def test_same_name_records_remain_distinct_in_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fam=root/'src'/'packs'/'system'/'features'
            fam.mkdir(parents=True)
            (fam/'one.json').write_text(json.dumps({'_id':'A','name':'Same'}),encoding='utf-8')
            (fam/'two.json').write_text(json.dumps({'_id':'B','name':'Same'}),encoding='utf-8')
            (fam/'folder.json').write_text(json.dumps({'_key':'!folders!F','name':'Same'}),encoding='utf-8')
            snap=structured_family_snapshot(root,'src/packs/system/features')
            self.assertEqual(snap.entity_count,2)
            self.assertEqual(snap.foundry_folder_count,1)
            self.assertEqual({r.source_id for r in snap.logical_records},{'A','B'})

    def test_digest_is_deterministic_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fam=root/'src'/'packs'/'items'/'mods'
            fam.mkdir(parents=True)
            p=fam/'one.json'
            p.write_text(json.dumps({'_id':'A','name':'One','system':{'x':1}}),encoding='utf-8')
            a=structured_family_snapshot(root,'src/packs/items/mods').digest_sha256
            b=structured_family_snapshot(root,'src/packs/items/mods').digest_sha256
            self.assertEqual(a,b)
            p.write_text(json.dumps({'_id':'A','name':'One','system':{'x':2}}),encoding='utf-8')
            c=structured_family_snapshot(root,'src/packs/items/mods').digest_sha256
            self.assertNotEqual(a,c)

    def test_runtime_icon_is_not_publication_asset(self):
        doc={'_id':'A','name':'Test','img':'assets/icons/features/test.webp','system':{'description':'Rule text.'}}
        md,meta=render_entity('features',doc,[])
        self.assertEqual(meta['assetRefs'],[])
        self.assertIn('assets/icons/features/test.webp',meta['runtimeAssetRefs'])

    def test_rendered_markdown_image_is_publication_asset(self):
        refs=collect_publication_asset_refs('Text\n\n![Art](assets/art/example.png)\n')
        self.assertEqual(refs,['assets/art/example.png'])


if __name__ == "__main__":
    unittest.main()
