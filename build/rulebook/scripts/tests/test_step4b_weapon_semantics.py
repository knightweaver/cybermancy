import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

from rulebook_normalize.markdown import html_to_plain_text
from rulebook_normalize.structured import (
    classify_action,
    collect_source_warnings,
    publication_trait,
    render_entity,
    source_sort_value,
)


class TestStep4BWeaponSemantics(unittest.TestCase):
    def _weapon(self, *, source_id='W1', name='Test Weapon', tier=1, trait='Finesse',
                description='Clean description.', actions=None, weapon_features=None):
        return {
            '_id': source_id,
            'name': name,
            'system': {
                'tier': tier,
                'description': description,
                'attack': {
                    'roll': {'trait': trait} if trait is not None else {},
                    'range': 'Close',
                    'damage': {'parts': []},
                },
                'actions': {} if actions is None else actions,
                'weaponFeatures': [] if weapon_features is None else weapon_features,
            },
        }

    def test_weapon_trait_resolves_nested_attack_trait(self):
        doc = self._weapon(trait='Finesse')
        self.assertEqual(publication_trait('weapons', doc), 'Finesse')

    def test_weapon_sort_is_case_insensitive_by_trait(self):
        a = self._weapon(source_id='A', name='Zulu', trait='agility')
        b = self._weapon(source_id='B', name='Alpha', trait='Finesse')
        c = self._weapon(source_id='C', name='Beta', trait='strength')
        docs = [c, b, a]
        docs.sort(key=lambda d: source_sort_value('weapons', d, 'Tier 1/test.json', ['tier', 'trait', 'name']))
        self.assertEqual([d['name'] for d in docs], ['Zulu', 'Alpha', 'Beta'])

    def test_missing_weapon_trait_sorts_last_and_warns(self):
        populated = self._weapon(source_id='A', name='Alpha', trait='Strength')
        missing = self._weapon(source_id='B', name='Beta', trait=None)
        docs = [missing, populated]
        docs.sort(key=lambda d: source_sort_value('weapons', d, 'Tier 1/test.json', ['tier', 'trait', 'name']))
        self.assertEqual([d['name'] for d in docs], ['Alpha', 'Beta'])
        warnings = collect_source_warnings('weapons', missing)
        self.assertIn('WEAPON_TRAIT_MISSING', {w['code'] for w in warnings})

    def test_ordinary_weapon_action_remains_action(self):
        kind, display = classify_action('weapons', {'name': 'Smartlink'})
        self.assertEqual(kind, 'action')
        self.assertEqual(display, 'Smartlink')

    def test_critical_effect_prefix_becomes_semantic_type_and_clean_name(self):
        kind, display = classify_action('weapons', {'name': 'Critical Effect:  Pinpoint'})
        self.assertEqual(kind, 'critical-effect')
        self.assertEqual(display, 'Pinpoint')

    def test_empty_actions_do_not_synthesize_mechanics(self):
        doc = self._weapon(actions={})
        md, meta = render_entity('weapons', doc, [])
        self.assertNotIn('#### Actions', md)
        self.assertNotIn('#### Critical Effects', md)
        self.assertEqual(meta['weaponSemantics']['actions'], [])
        self.assertEqual(meta['weaponSemantics']['criticalEffects'], [])

    def test_weapon_feature_value_is_preserved_semantically(self):
        doc = self._weapon(
            weapon_features=[{'value': 'retractable', 'effectIds': [], 'actionIds': []}],
        )
        md, meta = render_entity('weapons', doc, [])
        self.assertIn('data-feature-type="weapon-feature"', md)
        self.assertIn('**retractable**', md)
        self.assertEqual(meta['weaponSemantics']['weaponFeatures'], ['retractable'])

    def test_equipment_block_html_description_is_retained_as_plain_text(self):
        doc = self._weapon(description='<p>Legacy description.</p>')
        md, meta = render_entity('weapons', doc, [])
        self.assertIn('Legacy description.', md)
        self.assertNotIn('<p>', md)
        self.assertNotIn('SOURCE_DESCRIPTION_HTML', {w['code'] for w in meta['warnings']})

    def test_description_paragraphs_collapse_to_one_line(self):
        doc = self._weapon(description='<p>First sentence.</p><p>Second sentence.</p>')
        md, _ = render_entity('weapons', doc, [])
        self.assertIn('First sentence. Second sentence.', md)
        self.assertNotIn('First sentence.\n\nSecond sentence.', md)

    def test_description_formatting_tags_are_removed_not_markdownized(self):
        doc = self._weapon(description='<p>A <strong>very</strong> dangerous <em>weapon</em>.</p>')
        md, _ = render_entity('weapons', doc, [])
        self.assertIn('A very dangerous weapon.', md)
        self.assertNotIn('**very**', md)
        self.assertNotIn('*weapon*', md)

    def test_description_breaks_lists_links_and_entities_become_plain_text(self):
        source = (
            '<p>A &amp; B<br>Line two.</p>'
            '<ul><li>First effect</li><li>Second effect</li></ul>'
            '<p>See <a href="https://example.com">the reference</a>.</p>'
        )
        self.assertEqual(
            html_to_plain_text(source),
            'A & B Line two. First effect Second effect See the reference.',
        )

    def test_description_ignores_script_and_style_content(self):
        source = '<p>Visible.</p><script>bad()</script><style>.x{}</style><p>Still visible.</p>'
        self.assertEqual(html_to_plain_text(source), 'Visible. Still visible.')

    def test_plain_description_whitespace_is_collapsed(self):
        self.assertEqual(html_to_plain_text('  Plain\n description\ttext.  '), 'Plain description text.')

    def test_action_html_is_normalized_to_plain_text(self):
        doc = self._weapon(actions={
            'smartlink': {
                'name': 'Smartlink',
                'description': '<p>You may <strong>reroll</strong> one attack die.</p>',
            },
            'critical': {
                'name': 'Critical Effect: Pinpoint',
                'description': '<p>Ignore <em>all</em> cover.</p>',
            },
        })
        md, meta = render_entity('weapons', doc, [])
        self.assertIn('You may reroll one attack die.', md)
        self.assertIn('Ignore all cover.', md)
        self.assertNotIn('**reroll**', md)
        self.assertNotIn('*all*', md)
        self.assertIn('data-feature-type="action"', md)
        self.assertIn('data-feature-type="critical-effect"', md)
        self.assertNotIn('**Critical Effect: Pinpoint**', md)
        self.assertEqual(meta['weaponSemantics']['actions'], ['Smartlink'])
        self.assertEqual(meta['weaponSemantics']['criticalEffects'], ['Pinpoint'])

    def test_embedded_item_description_is_plain_text(self):
        doc = {
            '_id': 'A1',
            'name': 'Actor',
            'items': [{
                '_id': 'F1',
                'name': 'Embedded Feature',
                'type': 'feature',
                'system': {'description': '<p>A <strong>compact</strong> embedded description.</p>'},
            }],
        }
        md, _ = render_entity('adversaries', doc, [])
        self.assertIn('A compact embedded description.', md)
        self.assertNotIn('**compact**', md)

    def test_non_weapon_critical_effect_like_name_is_not_reclassified(self):
        kind, display = classify_action('features', {'name': 'Critical Effect: Example'})
        self.assertEqual(kind, 'action')
        self.assertEqual(display, 'Critical Effect: Example')


if __name__ == '__main__':
    unittest.main()
