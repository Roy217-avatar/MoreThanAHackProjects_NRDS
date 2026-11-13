import unittest

from model.stoppage import add_stoppage_evidence
from model.inference import infer


CONFIG = {'stationary_unattended_frames': 3,
          'stationary_unattended_radius_m': .5,
          'stationary_unattended_min_player_m': 3.,
          'control_frames': 2, 'evidence_gap_frames': 0,
          'out_of_bounds_frames': 25, 'control_backfill': True}


def row(x=.5, nearest=5., candidate=None, seen=True):
    return {'ball_xy': (x, .5) if seen else None, 'ball_seen': seen,
            'nearest_distance_m': {'H': nearest, 'A': 8.},
            'candidate': candidate, 'outside': False,
            'stationary_set_piece': False, 'players_seen': 2}


class StoppageTests(unittest.TestCase):
    def test_confirmed_unattended_stoppage_backfills_and_restart_needs_control(self):
        evidence = [row(nearest=1, candidate='H') for _ in range(2)]
        evidence += [row() for _ in range(4)]
        evidence += [row(nearest=1, candidate='A') for _ in range(2)]
        add_stoppage_evidence(evidence, [(1, 0, 7)], CONFIG, (100, 60))
        labels, reasons = infer(evidence, [(1, 0, 7)], CONFIG)
        self.assertEqual(labels, ['H', 'H', 'D', 'D', 'D', 'D', 'A', 'A'])
        self.assertEqual(reasons[2], 'stationary_unattended')

    def test_short_pause_near_player_and_missing_ball_do_not_signal_dead(self):
        evidence = [row(), row(), row(seen=False), row(nearest=1), row(), row()]
        add_stoppage_evidence(evidence, [(1, 0, 5)], CONFIG, (100, 60))
        self.assertFalse(any(item['stationary_unattended'] for item in evidence))

    def test_no_confirmation_crosses_half_and_motion_breaks_window(self):
        evidence = [row(), row(), row(), row(), row(x=.52), row()]
        add_stoppage_evidence(evidence, [(1, 0, 1), (2, 2, 5)], CONFIG, (100, 60))
        self.assertFalse(any(item['stationary_unattended'] for item in evidence))

    def test_all_players_missing_does_not_prove_unattended_stoppage(self):
        evidence = [row() for _ in range(4)]
        for item in evidence:
            item['players_seen'] = 0
        add_stoppage_evidence(evidence, [(1, 0, 3)], CONFIG, (100, 60))
        self.assertFalse(any(item['stationary_unattended'] for item in evidence))

    def test_missing_one_team_does_not_prove_unattended_stoppage(self):
        evidence = [row() for _ in range(4)]
        for item in evidence:
            item['nearest_distance_m']['A'] = float('inf')
        add_stoppage_evidence(evidence, [(1, 0, 3)], CONFIG, (100, 60))
        self.assertFalse(any(item['stationary_unattended'] for item in evidence))

    def test_old_configuration_ignores_new_stoppage_cue(self):
        evidence = [row(nearest=1, candidate='H') for _ in range(2)]
        evidence += [row() for _ in range(3)]
        add_stoppage_evidence(evidence, [(1, 0, 4)], CONFIG, (100, 60))
        old = {key: value for key, value in CONFIG.items()
               if not key.startswith('stationary_unattended_')}
        labels, _ = infer(evidence, [(1, 0, 4)], old)
        self.assertEqual(labels, ['H'] * 5)

    def test_observed_stationary_cue_handles_nearby_players_without_using_labels(self):
        config = dict(CONFIG, stationary_observed_frames=3,
                      stationary_observed_radius_m=.5,
                      tracking_freeze_epsilon_m=.001)
        evidence = [row(nearest=value) for value in (1.0, 1.2, 1.4)]
        add_stoppage_evidence(evidence, [(1, 0, 2)], config, (100, 60))
        self.assertEqual([item['stationary_observed'] for item in evidence],
                         [True, True, True])
        labels, reasons = infer(evidence, [(1, 0, 2)], config)
        self.assertEqual(labels, ['D', 'D', 'D'])
        self.assertEqual(reasons[0], 'stationary_observed')

    def test_observed_stationary_cue_does_not_require_unattended_cue(self):
        config = {key: value for key, value in CONFIG.items()
                  if not key.startswith('stationary_unattended_')}
        config.update(stationary_observed_frames=3,
                      stationary_observed_radius_m=.5,
                      tracking_freeze_epsilon_m=.001)
        evidence = [row(nearest=value) for value in (1.0, 1.2, 1.4)]
        add_stoppage_evidence(evidence, [(1, 0, 2)], config, (100, 60))
        self.assertTrue(all(item['stationary_observed'] for item in evidence))

    def test_coordinated_tracking_freeze_does_not_prove_dead_ball(self):
        config = dict(CONFIG, stationary_observed_frames=3,
                      stationary_observed_radius_m=.5,
                      tracking_freeze_epsilon_m=.001)
        evidence = [row(nearest=1.0) for _ in range(3)]
        add_stoppage_evidence(evidence, [(1, 0, 2)], config, (100, 60))
        self.assertFalse(any(item['stationary_observed'] for item in evidence))


if __name__ == '__main__':
    unittest.main()
