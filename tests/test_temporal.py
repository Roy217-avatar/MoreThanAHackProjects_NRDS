import csv
import json
import tempfile
import unittest
from pathlib import Path

from model.temporal import add_set_piece_evidence, evidence_from_line, infer, load_config, write_submission
from starter.load_atd import frame_id_of, video_frame_of


CONFIG = {"control_distance_m": 2.0, "opponent_margin_m": 0.75,
          "control_frames": 3, "evidence_gap_frames": 1,
          "out_of_bounds_frames": 2, "pitch_tolerance": 0.005,
          "set_piece_stationary_frames": 3, "set_piece_stationary_radius_m": 0.5}


def row(candidate=None, outside=False, ball_seen=True):
    return {"candidate": candidate, "outside": outside,
            "ball_seen": ball_seen, "ball_xy": (0.5, 0.5) if ball_seen else None,
            "stationary_set_piece": False, "players_seen": 2}


class TemporalTests(unittest.TestCase):
    def test_backfill_configuration_requires_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(dict(CONFIG, set_piece_backfill="true")))
            with self.assertRaisesRegex(ValueError, "set_piece_backfill"):
                load_config(path)

    def test_frame_conversion_and_strict_raw_indexing(self):
        self.assertEqual(video_frame_of(1), 0)
        self.assertEqual(frame_id_of(199318), 199319)
        line = "1:0.5,0.5,0;0.8,0.8,0:0.5,0.5,0\n"
        self.assertEqual(evidence_from_line(line, 0, ["H", "A"], CONFIG, (105.3, 68))["candidate"], "H")
        with self.assertRaises(ValueError):
            evidence_from_line(line, 1, ["H", "A"], CONFIG, (105.3, 68))
        with self.assertRaises(ValueError):
            evidence_from_line(line, 0, ["H"], CONFIG, (105.3, 68))

    def test_missing_ball_and_players_are_not_dead(self):
        missing_ball = evidence_from_line("1:0.5,0.5,0;NaN,NaN,NaN:NaN,NaN,NaN", 0, ["H", "A"], CONFIG, (105.3, 68))
        missing_players = evidence_from_line("1:NaN,NaN,NaN;NaN,NaN,NaN:0.5,0.5,0", 0, ["H", "A"], CONFIG, (105.3, 68))
        self.assertIsNone(missing_ball["candidate"])
        self.assertIsNone(missing_players["candidate"])
        self.assertFalse(missing_ball["outside"])
        labels, _ = infer([row("H")] * 3 + [row(ball_seen=False)] * 8, [(1, 0, 10)], CONFIG)
        self.assertEqual(labels, ["X", "X"] + ["H"] * 9)
        self.assertEqual(infer([row(ball_seen=False)] * 5, [(1, 0, 4)], CONFIG)[0], ["X"] * 5)

    def test_pass_incidental_touch_and_turnover(self):
        sequence = [row("H")] * 3 + [row()] * 3 + [row("H")] * 2
        sequence += [row("A")] + [row("H")] * 2 + [row("A")] * 3
        labels, _ = infer(sequence, [(1, 0, len(sequence) - 1)], CONFIG)
        self.assertEqual(labels[7], "H")
        self.assertEqual(labels[8:11], ["H"] * 3)
        self.assertEqual(labels[-3:], ["H", "H", "A"])

    def test_dead_restart_and_halftime_reset(self):
        sequence = [row("H")] * 3 + [row(outside=True)] * 3 + [row("A")] * 3
        sequence += [row(ball_seen=False)] * 2 + [row("H")] * 3
        labels, _ = infer(sequence, [(1, 0, 8), (2, 11, 13)], CONFIG)
        self.assertEqual(labels[4:6], ["D", "D"])
        self.assertEqual(labels[8], "A")
        self.assertEqual(labels[9:13], ["X"] * 4)
        self.assertEqual(labels[13], "H")

    def test_stationary_set_piece_requires_tag_and_observed_ball(self):
        sequence = [row("H") for _ in range(4)] + [row("H") for _ in range(4)]
        sequence[5]["ball_xy"] = None
        sequence[5]["ball_seen"] = False
        events = [{"code": "SET PIECES", "start_frame": 0, "end_frame": 8}]
        add_set_piece_evidence(sequence, events, [(1, 0, 3), (2, 4, 7)], CONFIG, (105.3, 68))
        self.assertTrue(sequence[2]["stationary_set_piece"])
        self.assertFalse(sequence[4]["stationary_set_piece"])
        self.assertFalse(sequence[7]["stationary_set_piece"])
        labels, reasons = infer(sequence, [(1, 0, 3), (2, 4, 7)], CONFIG)
        self.assertEqual(labels[2], "D")
        self.assertEqual(reasons[2], "stationary_set_piece")
        untagged = [row("H") for _ in range(3)]
        add_set_piece_evidence(untagged, [], [(1, 0, 2)], CONFIG, (105.3, 68))
        self.assertFalse(any(r["stationary_set_piece"] for r in untagged))

    def test_backfilled_set_piece_starts_dead_interval_at_window_start(self):
        config = dict(CONFIG, set_piece_backfill=True)
        sequence = [row("H") for _ in range(6)]
        events = [{"code": "SET PIECES", "start_frame": 3, "end_frame": 6}]
        add_set_piece_evidence(sequence, events, [(1, 0, 5)], config, (105.3, 68))
        labels, reasons = infer(sequence, [(1, 0, 5)], config)
        self.assertEqual(labels, ["X", "X", "H", "D", "D", "D"])
        self.assertEqual(reasons[3:], ["stationary_set_piece"] * 3)

    def test_serialization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prediction.csv"
            write_submission(path, ["X", "H", "A", "D"])
            with path.open(newline="") as handle:
                self.assertEqual(list(csv.reader(handle)),
                                 [["frame", "label"], ["0", "X"], ["1", "H"], ["2", "A"], ["3", "D"]])


if __name__ == "__main__":
    unittest.main()
