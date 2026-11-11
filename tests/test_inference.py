"""Synthetic behavior checks for tactical possession inference."""

import unittest

from model.inference import infer as model_infer


CONFIG = {"control_frames": 3, "evidence_gap_frames": 1,
          "out_of_bounds_frames": 2}


def evidence(candidate=None, *, outside=False, ball_seen=True,
             players_seen=2, stationary_set_piece=False):
    return {"candidate": candidate, "outside": outside,
            "ball_seen": ball_seen,
            "ball_xy": (0.5, 0.5) if ball_seen else None,
            "players_seen": players_seen,
            "stationary_set_piece": stationary_set_piece}


def infer(sequence, blocks):
    return model_infer(sequence, blocks, CONFIG)


class InferenceTests(unittest.TestCase):
    def test_control_confirmation_and_outside_half(self):
        sequence = [evidence("H") for _ in range(5)]
        labels, reasons = infer(sequence, [(1, 1, 3)])
        self.assertEqual(labels, ["X", "X", "X", "H", "X"])
        self.assertEqual(reasons[3], "control_confirmed")
        self.assertEqual(reasons[4], "outside_half")

    def test_missing_observations_keep_last_control_without_dead_ball(self):
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence(ball_seen=False, players_seen=0) for _ in range(7)]
        sequence += [evidence(players_seen=0)]
        labels, reasons = infer(sequence, [(1, 0, 10)])
        self.assertEqual(labels, ["X", "X"] + ["H"] * 9)
        self.assertEqual(reasons[3], "missing_ball")
        self.assertEqual(reasons[10], "contested_or_loose")

    def test_all_missing_half_abstains(self):
        sequence = [evidence(ball_seen=False, players_seen=0) for _ in range(4)]
        labels, reasons = infer(sequence, [(1, 0, 3)])
        self.assertEqual(labels, ["X", "X", "X", "X"])
        self.assertEqual(reasons, ["missing_ball"] * 4)

    def test_outside_frame_cannot_count_as_control_evidence(self):
        sequence = [evidence("H"), evidence("H"),
                    evidence("H", outside=True), evidence("H")]
        labels, _ = infer(sequence, [(1, 0, 3)])
        self.assertEqual(labels, ["X", "X", "X", "H"])

    def test_pass_and_incidental_opponent_touch_retain_control(self):
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence(), evidence(), evidence("H"), evidence("A"), evidence("H")]
        labels, _ = infer(sequence, [(1, 0, 7)])
        self.assertEqual(labels, ["X", "X"] + ["H"] * 6)

    def test_opposing_control_confirms_turnover_across_brief_gap(self):
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence("A"), evidence("A"), evidence(ball_seen=False), evidence("A")]
        labels, reasons = infer(sequence, [(1, 0, 6)])
        self.assertEqual(labels, ["X", "X", "H", "H", "H", "H", "A"])
        self.assertEqual(reasons[6], "control_confirmed")

    def test_opposing_evidence_expires_after_long_gap(self):
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence("A"), evidence(), evidence(), evidence("A"), evidence("A")]
        labels, _ = infer(sequence, [(1, 0, 7)])
        self.assertEqual(labels, ["X", "X"] + ["H"] * 6)

    def test_dead_ball_and_confirmed_restart(self):
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence(outside=True), evidence(outside=True)]
        sequence += [evidence(ball_seen=False), evidence("A"), evidence("A"), evidence("A")]
        labels, reasons = infer(sequence, [(1, 0, 8)])
        self.assertEqual(labels, ["X", "X", "H", "H", "D", "D", "D", "D", "A"])
        self.assertEqual(reasons[4], "sustained_out_of_bounds")
        self.assertEqual(reasons[5], "awaiting_restart")
        self.assertEqual(reasons[8], "control_confirmed")

    def test_stationary_set_piece_is_dead_even_with_candidate(self):
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence("H", stationary_set_piece=True)]
        labels, reasons = infer(sequence, [(1, 0, 3)])
        self.assertEqual(labels[-1], "D")
        self.assertEqual(reasons[-1], "stationary_set_piece")

    def test_halftime_resets_control_and_pending_votes(self):
        sequence = [evidence("H") for _ in range(4)]
        sequence += [evidence("A"), evidence("A")]
        sequence += [evidence(ball_seen=False), evidence("A"), evidence("A"), evidence("A")]
        labels, _ = infer(sequence, [(1, 0, 5), (2, 7, 9)])
        self.assertEqual(labels, ["X", "X", "H", "H", "H", "H", "X", "X", "X", "A"])

    def test_invalid_and_overlapping_blocks_fail_loudly(self):
        sequence = [evidence() for _ in range(5)]
        for blocks in ([(1, -1, 2)], [(1, 2, 5)], [(1, 3, 2)],
                       [(1, 0, 2), (2, 2, 4)], [(2, 3, 4), (1, 0, 2)],
                       [(1, 0)], [(1, "0", 2)]):
            with self.subTest(blocks=blocks), self.assertRaises(ValueError):
                infer(sequence, blocks)

    def test_invalid_candidate_cannot_become_submission_label(self):
        sequence = [evidence("D") for _ in range(3)]
        with self.assertRaises(ValueError):
            infer(sequence, [(1, 0, 2)])

    def test_offline_backfill_starts_only_confirmed_control(self):
        config = dict(CONFIG, control_backfill=True, evidence_gap_frames=0)
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence("A"), evidence("H")]
        sequence += [evidence("A") for _ in range(3)]
        labels, reasons = model_infer(sequence, [(1, 0, 7)], config)
        self.assertEqual(labels, ["H"] * 5 + ["A"] * 3)
        self.assertEqual(reasons[5:7], ["control_backfilled"] * 2)

    def test_offline_backfill_resets_at_dead_ball_and_halftime(self):
        config = dict(CONFIG, control_backfill=True, evidence_gap_frames=0)
        sequence = [evidence("H") for _ in range(3)]
        sequence += [evidence("A"), evidence("A")]
        sequence += [evidence("H", stationary_set_piece=True)]
        sequence += [evidence("A") for _ in range(3)]
        labels, _ = model_infer(sequence, [(1, 0, 5), (2, 6, 8)], config)
        self.assertEqual(labels, ["H"] * 5 + ["D"] + ["A"] * 3)

    def test_offline_backfill_requires_uninterrupted_candidate_run(self):
        config = dict(CONFIG, control_backfill=True, evidence_gap_frames=1)
        with self.assertRaisesRegex(ValueError, "control_backfill"):
            model_infer([evidence("H") for _ in range(3)], [(1, 0, 2)], config)


if __name__ == "__main__":
    unittest.main()
