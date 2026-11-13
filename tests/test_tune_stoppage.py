import unittest

from model.tune_stoppage import official_score, select_best


class TuneStoppageTests(unittest.TestCase):
    def test_selection_prioritizes_official_spell_metric_then_macro_f1(self):
        candidates = [
            {'metrics': {'spell_f1_mean': .50, 'macro_f1': .80, 'accuracy': .95}},
            {'metrics': {'spell_f1_mean': .60, 'macro_f1': .70, 'accuracy': .70}},
            {'metrics': {'spell_f1_mean': .60, 'macro_f1': .75, 'accuracy': .60}},
        ]
        self.assertIs(select_best(candidates), candidates[2])
        with self.assertRaises(ValueError):
            select_best([])

    def test_official_score_keeps_halves_separate(self):
        labels = ['H', 'H', 'H', 'H']
        reference = ['H', 'H', 'H', 'H']
        score = official_score(labels, reference, [(1, 0, 1), (2, 2, 3)])
        self.assertEqual(score['n_gt_spells'], 2)
        self.assertEqual(score['n_pred_spells'], 2)
        self.assertEqual(score['spell_f1_mean'], 1.0)
        self.assertEqual(score['accuracy'], 1.0)

    def test_official_score_maps_unknown_reference_to_ungraded(self):
        score = official_score(['H', 'A', 'D'], ['H', None, 'D'], [(1, 0, 2)])
        self.assertEqual(score['n_graded'], 2)
        self.assertEqual(score['accuracy'], 1.0)


if __name__ == '__main__':
    unittest.main()
