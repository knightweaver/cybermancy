import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

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

    def test_equipment_block_html_description_is_omitted_and_warned(self):
        doc = self._weapon(description='<p>Legacy description.</p>')
        md, meta = render_entity('weapons', doc, [])
        self.assertNotIn('Legacy description.', md)
        self.assertIn('SOURCE_DESCRIPTION_HTML', {w['code'] for w in meta['warnings']})

    def test_action_html_is_still_normalized(self):
        doc = self._weapon(actions={
            'smartlink': {
                'name': 'Smartlink',
                'description': '<p>Reroll one attack die.</p>',
            },
            'critical': {
                'name': 'Critical Effect: Pinpoint',
                'description': '<p>Ignore cover.</p>',
            },
        })
        md, meta = render_entity('weapons', doc, [])
        self.assertIn('Reroll one attack die.', md)
        self.assertIn('Ignore cover.', md)
        self.assertIn('data-feature-type="action"', md)
        self.assertIn('data-feature-type="critical-effect"', md)
        self.assertNotIn('**Critical Effect: Pinpoint**', md)
        self.assertEqual(meta['weaponSemantics']['actions'], ['Smartlink'])
        self.assertEqual(meta['weaponSemantics']['criticalEffects'], ['Pinpoint'])

    def test_non_weapon_critical_effect_like_name_is_not_reclassified(self):
        kind, display = classify_action('features', {'name': 'Critical Effect: Example'})
        self.assertEqual(kind, 'action')
        self.assertEqual(display, 'Critical Effect: Example')


if __name__ == '__main__':
    unittest.main()
