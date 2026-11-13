import unittest

from model.cross_validate_v8 import (_live_dead_confusion, leave_one_match_out, merge_official_scores,
                                     select_candidate, validate_manifest)
from model.tune_stoppage import official_score


class CrossValidateV8Tests(unittest.TestCase):
    def test_leave_one_match_out_never_places_heldout_match_in_training(self):
        folds = leave_one_match_out(['a', 'b', 'c'])
        self.assertEqual(folds, [
            {'test': 'a', 'train': ['b', 'c']},
            {'test': 'b', 'train': ['a', 'c']},
            {'test': 'c', 'train': ['a', 'b']},
        ])

    def test_selection_enforces_accuracy_and_controlling_team_safeguards(self):
        rows = [
            {'name': 'v7_baseline', 'metrics': {'spell_f1_mean': .40, 'macro_f1': .70,
                                                'accuracy': .80, 'team_acc_both_alive': .90}},
            {'name': 'unsafe', 'metrics': {'spell_f1_mean': .60, 'macro_f1': .80,
                                           'accuracy': .79, 'team_acc_both_alive': .89}},
            {'name': 'safe', 'metrics': {'spell_f1_mean': .50, 'macro_f1': .75,
                                         'accuracy': .799, 'team_acc_both_alive': .899}},
        ]
        selected = select_candidate(rows, 'v7_baseline', -.005, -.005)
        self.assertEqual(selected['name'], 'safe')

    def test_manifest_rejects_benchmark_or_final_test_in_development(self):
        valid = {'sources': {
            'idsse': {'role': 'development_cross_validation', 'matches': [{'id': 'dev'}]},
            'wcsf': {'role': 'historical_benchmark_excluded_from_v8_selection',
                     'matches': ['old']},
            'challenge_public': {'role': 'pipeline_check_only_excluded_from_v8_selection',
                                 'matches': ['public']}},
            'untouched_final_test': []}
        self.assertEqual(validate_manifest(valid), ['dev'])
        valid['untouched_final_test'] = ['dev']
        with self.assertRaisesRegex(ValueError, 'overlap'):
            validate_manifest(valid)

    def test_merge_preserves_match_boundaries_and_exact_counts(self):
        first = official_score(['H', 'H', 'D'], ['H', 'H', 'D'], [(1, 0, 2)])
        second = official_score(['A', 'A'], ['A', 'A'], [(1, 0, 1)])
        merged = merge_official_scores([first, second])
        self.assertEqual(merged['accuracy'], 1.0)
        self.assertEqual(merged['macro_f1'], 1.0)
        self.assertEqual(merged['spell_f1_mean'], 1.0)
        self.assertEqual(merged['n_gt_spells'], 2)
        self.assertEqual(merged['n_pred_spells'], 2)

    def test_live_dead_confusion_sums_both_live_reference_rows(self):
        result = _live_dead_confusion([
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [0, 0, 0, 0],
        ])
        self.assertEqual(result['counts'], [[14, 10, 12], [19, 11, 12]])


if __name__ == '__main__':
    unittest.main()
