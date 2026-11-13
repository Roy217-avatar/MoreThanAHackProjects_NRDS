import hashlib
import tempfile
import unittest
from pathlib import Path

from model.evaluate_wcsf import evaluate_models, reserved_paths, select_final


def evidence(candidate):
    return {'candidate': candidate, 'outside': False, 'ball_seen': True,
            'ball_xy': (.5, .5), 'players_seen': 2,
            'stationary_set_piece': False,
            'nearest_distance_m': {'H': 1 if candidate == 'H' else 8,
                                   'A': 1 if candidate == 'A' else 8}}


class EvaluateWCSFTests(unittest.TestCase):
    def test_evaluates_candidates_and_selects_by_spell_then_macro(self):
        match = {'evidence': [evidence(value) for value in ['H', 'H', 'A', 'A']],
                 'reference': ['H', 'H', 'A', 'A'], 'blocks': [(1, 0, 3)]}
        base = {'control_distance_m': 2.5, 'opponent_margin_m': .75,
                'control_frames': 10, 'evidence_gap_frames': 0,
                'out_of_bounds_frames': 10, 'control_backfill': True}
        exact = dict(base, control_frames=5)
        results = evaluate_models(match, [('slow', base), ('exact', exact)])
        self.assertEqual(results['exact']['accuracy'], 1.0)
        self.assertEqual(results['exact']['spell_f1_mean'], 1.0)
        self.assertEqual(select_final(results), 'exact')

    def test_selection_rejects_empty_results(self):
        with self.assertRaises(ValueError):
            select_final({})

    def test_reserved_inputs_must_match_frozen_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'half.zip'
            path.write_bytes(b'frozen')
            checksum = hashlib.sha256(b'frozen').hexdigest()
            protocol = {'matches': [{'files': ['half.zip'],
                                     'input_sha256': {'half.zip': checksum}}]}
            self.assertEqual(reserved_paths(protocol, Path(tmp)), [path])
            protocol['matches'][0]['input_sha256']['half.zip'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'archive hash mismatch'):
                reserved_paths(protocol, Path(tmp))


if __name__ == '__main__':
    unittest.main()
