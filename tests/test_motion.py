import unittest

from model.motion import add_ball_motion_evidence


class BallMotionTests(unittest.TestCase):
    def test_uses_actual_timestamps_and_resets_derivatives_at_gaps_and_halves(self):
        evidence = [
            {'ball_xy': (.50, .5), 'timestamp_s': 0.0},
            {'ball_xy': (.51, .5), 'timestamp_s': .1},
            {'ball_xy': (.52, .5), 'timestamp_s': .3},
            {'ball_xy': None, 'timestamp_s': .4},
            {'ball_xy': (.60, .5), 'timestamp_s': 10.0},
        ]
        add_ball_motion_evidence(evidence, [(1, 0, 3), (2, 4, 4)], (100, 60))
        self.assertIsNone(evidence[0]['ball_speed_mps'])
        self.assertAlmostEqual(evidence[1]['ball_speed_mps'], 10.0)
        self.assertAlmostEqual(evidence[2]['ball_speed_mps'], 5.0)
        self.assertAlmostEqual(evidence[2]['ball_acceleration_mps2'], -25.0)
        self.assertIsNone(evidence[3]['ball_speed_mps'])
        self.assertIsNone(evidence[4]['ball_speed_mps'])

    def test_rejects_nonincreasing_observed_timestamps(self):
        evidence = [
            {'ball_xy': (.5, .5), 'timestamp_s': 1.0},
            {'ball_xy': (.6, .5), 'timestamp_s': 1.0},
        ]
        with self.assertRaisesRegex(ValueError, 'timestamp'):
            add_ball_motion_evidence(evidence, [(1, 0, 1)], (100, 60))


if __name__ == '__main__':
    unittest.main()
