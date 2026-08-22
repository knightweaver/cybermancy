import json, tempfile, unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_normalize.markdown import (
    body_yaml_delimiter_ambiguities, drop_include_matching,
    mkdocs_admonitions_to_divs, pandoc_safe_assembled_markdown,
    rewrite_image_targets, segment_before_heading, segment_rules_index,
)
from rulebook_normalize.structured import stable_id, semantic_entity_id, render_entity, is_foundry_folder
from rulebook_normalize.xrefs import audience_reference_allowed
from rulebook_normalize.assemble import assemble_profile, GM_DIVIDER
from rulebook_normalize.validate import tree_hash_manifest, sum_expected_family_counts
from rulebook_normalize.snapshot import (
    STRUCTURED_DIGEST_ALGORITHM, structured_family_snapshot
)
from rulebook_normalize.structured import collect_publication_asset_refs
from rulebook_normalize.assets import (
    publication_asset_path, publication_markdown_reference, stage_publication_asset,
)

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


class TestPandocAndPublicationAssets(unittest.TestCase):
    def test_body_thematic_break_is_pandoc_safe(self):
        src=(
            '---\n'
            'title: "Test"\n'
            'profile: "player-guide"\n'
            '---\n\n'
            '# Chapter\n\n'
            'Before.\n\n'
            '---\n\n'
            'After.\n'
        )
        out=pandoc_safe_assembled_markdown(src)
        self.assertIn('\n***\n',out)
        self.assertEqual(body_yaml_delimiter_ambiguities(out),[])
        standalone=[line for line in out.splitlines() if line=='---']
        self.assertEqual(len(standalone),2)

    def test_rewrite_image_target_preserves_markdown_wrapper(self):
        src='![Corp Logo](../assets/icons/corps/example.webp "Logo")\n'
        out=rewrite_image_targets(src,{
            '../assets/icons/corps/example.webp':'../assets/icons/corps/example-v2.webp'
        })
        self.assertEqual(out,'![Corp Logo](../assets/icons/corps/example-v2.webp "Logo")\n')

    def test_publication_asset_path_uses_assets_tail(self):
        rel=publication_asset_path('docs/player-facing/assets/images/rules/flashbacks.png')
        self.assertEqual(rel,'assets/images/rules/flashbacks.png')
        self.assertEqual(publication_markdown_reference(rel),'../assets/images/rules/flashbacks.png')

    def test_staged_asset_resolves_from_assembled_profile(self):
        from rulebook_normalize.pipeline import _validate_assembled_assets
        from rulebook_normalize.validate import new_report

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            repo=root/'repo'; source=root/'build'/'rulebook'/'source'
            original=repo/'docs'/'player-facing'/'assets'/'icons'/'corps'/'example.webp'
            original.parent.mkdir(parents=True)
            original.write_bytes(b'publication-art')

            pub_rel='assets/icons/corps/example.webp'
            staged=stage_publication_asset(
                repo,'docs/player-facing/assets/icons/corps/example.webp',source,pub_rel
            )
            assembled=source/'assembled'/'player-guide.md'
            assembled.parent.mkdir(parents=True)
            assembled.write_text(
                '---\ntitle: "Test"\n---\n\n![Logo](../assets/icons/corps/example.webp)\n',
                encoding='utf-8'
            )
            report=new_report()
            _validate_assembled_assets(
                {'player-guide':assembled},source,{pub_rel:staged},report
            )
            codes={x['code']:x for x in report['checks']}
            self.assertEqual(codes['ASSET_RESOLUTION']['status'],'PASS')
            self.assertEqual(report['status'],'PASS')

    def test_missing_assembled_asset_is_blocking(self):
        from rulebook_normalize.pipeline import _validate_assembled_assets
        from rulebook_normalize.validate import new_report

        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source'
            assembled=source/'assembled'/'player-guide.md'
            assembled.parent.mkdir(parents=True)
            assembled.write_text(
                '---\ntitle: "Test"\n---\n\n![Logo](../assets/icons/missing.webp)\n',
                encoding='utf-8'
            )
            report=new_report()
            _validate_assembled_assets({'player-guide':assembled},source,{},report)
            codes={x['code']:x for x in report['checks']}
            self.assertEqual(codes['ASSET_RESOLUTION']['status'],'ERROR')
            self.assertEqual(report['status'],'FAIL')


    def test_full_materialization_is_self_contained_and_pandoc_safe(self):
        import hashlib
        from rulebook_normalize.pipeline import deterministic_build
        from rulebook_normalize.validate import new_report

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            repo=root/'repo'; out=root/'rulebook'
            authored=repo/'docs'/'player-facing'/'world'/'test.md'
            authored.parent.mkdir(parents=True)
            authored.write_text(
                '# Test\n\n![Logo](../assets/icons/corps/example.webp)\n\n---\n\nAfter.\n',
                encoding='utf-8'
            )
            asset=repo/'docs'/'player-facing'/'assets'/'icons'/'corps'/'example.webp'
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b'logo')

            family=repo/'src'/'packs'/'system'/'things'
            family.mkdir(parents=True)
            (family/'one.json').write_text(json.dumps({'_id':'A','name':'One'}),encoding='utf-8')
            snap=structured_family_snapshot(repo,'src/packs/system/things')
            authored_hash=hashlib.sha256(authored.read_bytes()).hexdigest()

            pub={
                'repository':{'gitCommit':'FROZEN'},
                'publicationInputs':{
                    'authoredDocuments':[{
                        'path':'docs/player-facing/world/test.md','disposition':'INCLUDE',
                        'decisionStatus':'DECIDED','sha256':authored_hash
                    }],
                    'structuredFamilies':[{
                        'generatorFamily':'things','sourcePath':'src/packs/system/things',
                        'entityCount':1,'disposition':'INCLUDE','decisionStatus':'DECIDED',
                        'contentDigestAlgorithm':STRUCTURED_DIGEST_ALGORITHM,
                        'contentDigestSha256':snap.digest_sha256
                    }]
                }
            }
            asm={
                'authority':{'sourceCommit':'FROZEN'},
                'authoredInputs':[{
                    'assemblyInputId':'auth.test','path':'docs/player-facing/world/test.md',
                    'placement':'ch1','audience':'player','title':'Test','assemblyMode':'whole-document'
                }],
                'structuredFamilies':[{
                    'familyId':'things','sourcePath':'src/packs/system/things','entityCount':1,
                    'audience':'player','title':'Things','sort':['name']
                }],
                'bookStructure':[
                    {'id':'player-part','order':1,'title':'Player','audience':'player','chapters':[
                        {'id':'ch1','number':1,'title':'Chapter','contentRefs':['auth.test','family:things']}
                    ]},
                    {'id':'gm-part','order':2,'title':'GM','audience':'gm','chapters':[]}
                ],
                'buildProfiles':[
                    {'id':'complete-rulebook','title':'Complete','includeAudiences':['shared','player','gm']},
                    {'id':'player-guide','title':'Player Guide','includeAudiences':['shared','player']}
                ],
                'gmDivider':{
                    'beforePart':'gm-part','title':'GM MATERIAL — SPOILERS BEYOND THIS POINT',
                    'requiredInCompleteBuild':True,'omittedInPlayerBuild':True
                }
            }
            config={
                'baseline':{'commit':'FROZEN','expectedLogicalEntities':1},
                'manifestAdapter':{
                    'publication':{
                        'baselineCommitPointer':'/repository/gitCommit',
                        'authoredIncludeRecordsPointer':'/publicationInputs/authoredDocuments',
                        'structuredFamilyRecordsPointer':'/publicationInputs/structuredFamilies'
                    },
                    'assembly':{'sectionsPointer':'/bookStructure','profilesPointer':'/buildProfiles'}
                },
                'structured':{
                    'familyDigestAlgorithm':STRUCTURED_DIGEST_ALGORITHM,
                    'fastPlayCandidatePaths':['flags.cybermancy.fastPlay']
                },
                'assets':{'foundryRuntimeMappings':[]},
                'semantics':{'gmDivider':'GM MATERIAL — SPOILERS BEYOND THIS POINT'},
                'families':{'things':{'expected':1}}
            }

            report=deterministic_build(repo,out,pub,asm,config,new_report())
            self.assertEqual(report['status'],'PASS',report)
            player=(out/'source'/'assembled'/'player-guide.md').read_text(encoding='utf-8')
            self.assertIn('![Logo](../assets/icons/corps/example.webp)',player)
            self.assertIn('\n***\n',player)
            self.assertEqual(body_yaml_delimiter_ambiguities(player),[])
            self.assertTrue((out/'source'/'assets'/'icons'/'corps'/'example.webp').is_file())
            codes={x['code']:x for x in report['checks']}
            self.assertEqual(codes['BODY_YAML_DELIMITER_AMBIGUITY']['status'],'PASS')
            self.assertEqual(codes['ASSET_RESOLUTION']['status'],'PASS')
            self.assertEqual(codes['ASSET_TREE_DETERMINISM']['status'],'PASS')
            self.assertEqual(codes['DETERMINISM']['status'],'PASS')


class TestSourceCorpusGovernance(unittest.TestCase):
    def _config(self):
        return {
            'baseline': {'commit':'FROZEN','expectedLogicalEntities':1},
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

    def _fixture(self, root):
        import hashlib
        authored=root/'rules.md'
        authored.write_text('# Rules\nFrozen.\n',encoding='utf-8')
        authored_hash=hashlib.sha256(authored.read_bytes()).hexdigest()

        fam=root/'src'/'packs'/'system'/'things'
        fam.mkdir(parents=True)
        entity=fam/'one.json'
        entity.write_text(json.dumps({'_id':'A','name':'One'}),encoding='utf-8')
        snap=structured_family_snapshot(root,'src/packs/system/things')

        pub={
            'repository':{'gitCommit':'FROZEN'},
            'publicationInputs':{
                'authoredDocuments':[{
                    'path':'rules.md','disposition':'INCLUDE','decisionStatus':'DECIDED',
                    'sha256':authored_hash
                }],
                'structuredFamilies':[{
                    'generatorFamily':'things','sourcePath':'src/packs/system/things',
                    'entityCount':1,'disposition':'INCLUDE','decisionStatus':'DECIDED',
                    'contentDigestAlgorithm':STRUCTURED_DIGEST_ALGORITHM,
                    'contentDigestSha256':snap.digest_sha256
                }]
            }
        }
        asm={
            'authority':{'sourceCommit':'FROZEN'},
            'authoredInputs':[{'assemblyInputId':'auth.rules','path':'rules.md'}],
            'structuredFamilies':[{'familyId':'things','sourcePath':'src/packs/system/things','entityCount':1}],
        }
        return pub,asm,authored,entity

    def test_head_advance_is_info_when_canonical_sources_match(self):
        from unittest.mock import patch
        from rulebook_normalize.pipeline import repository_preflight
        from rulebook_normalize.validate import new_report

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'.git').mkdir()
            pub,asm,_authored,_entity=self._fixture(root)
            report=new_report()
            with patch('rulebook_normalize.pipeline.subprocess.check_output',return_value='TOOLING-COMMIT\n'):
                repository_preflight(root,pub,asm,self._config(),report)

            codes={x['code']:x for x in report['checks']}
            self.assertEqual(report['status'],'PASS')
            self.assertEqual(codes['REPOSITORY_HEAD']['status'],'INFO')
            self.assertFalse(codes['REPOSITORY_HEAD']['details']['headMatchesFrozenSourceCommit'])
            self.assertEqual(codes['STRUCTURED_SOURCE_SNAPSHOT']['status'],'PASS')
            self.assertEqual(codes['SOURCE_CORPUS_INTEGRITY']['status'],'PASS')

    def test_head_match_remains_pass(self):
        from unittest.mock import patch
        from rulebook_normalize.pipeline import repository_preflight
        from rulebook_normalize.validate import new_report

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'.git').mkdir()
            pub,asm,_authored,_entity=self._fixture(root)
            report=new_report()
            with patch('rulebook_normalize.pipeline.subprocess.check_output',return_value='FROZEN\n'):
                repository_preflight(root,pub,asm,self._config(),report)

            codes={x['code']:x for x in report['checks']}
            self.assertEqual(report['status'],'PASS')
            self.assertEqual(codes['REPOSITORY_HEAD']['status'],'PASS')
            self.assertEqual(codes['SOURCE_CORPUS_INTEGRITY']['status'],'PASS')

    def test_structured_drift_still_blocks_after_head_advance(self):
        from unittest.mock import patch
        from rulebook_normalize.pipeline import repository_preflight
        from rulebook_normalize.validate import new_report

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'.git').mkdir()
            pub,asm,_authored,entity=self._fixture(root)
            # Change canonical structured content after the frozen manifest snapshot.
            entity.write_text(json.dumps({'_id':'A','name':'One','system':{'changed':True}}),encoding='utf-8')

            report=new_report()
            with patch('rulebook_normalize.pipeline.subprocess.check_output',return_value='TOOLING-COMMIT\n'):
                repository_preflight(root,pub,asm,self._config(),report)

            codes={x['code']:x for x in report['checks']}
            self.assertEqual(codes['REPOSITORY_HEAD']['status'],'INFO')
            self.assertEqual(codes['STRUCTURED_FAMILY_DIGEST']['status'],'ERROR')
            self.assertEqual(codes['SOURCE_CORPUS_INTEGRITY']['status'],'ERROR')
            self.assertEqual(report['status'],'FAIL')

if __name__ == "__main__":
    unittest.main()
