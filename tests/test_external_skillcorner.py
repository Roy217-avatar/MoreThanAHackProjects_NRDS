"""Contract tests for the public, external SkillCorner comparison adapter."""

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from model import external_skillcorner as adapter


class ExternalSkillCornerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.meta = Path(self.temp.name) / "match.json"
        self.tracking = Path(self.temp.name) / "tracking.jsonl"
        self.phases = Path(self.temp.name) / "phases.csv"
        self.config = {"control_distance_m": 2, "opponent_margin_m": 0.75,
                       "control_frames": 12, "evidence_gap_frames": 5,
                       "out_of_bounds_frames": 25}
        self.metadata = {"id": 7, "status": "closed", "date_time": "2025-01-01T00:00:00Z",
                         "pitch_length": 100, "pitch_width": 60,
                         "home_team": {"id": 11, "name": "Home"},
                         "away_team": {"id": 22, "name": "Away"},
                         "players": [{"id": 101, "team_id": 11}, {"id": 202, "team_id": 22}],
                         "match_periods": [{"period": 1, "start_frame": 1, "end_frame": 3},
                                           {"period": 2, "start_frame": 5, "end_frame": 6}]}
        self.rows = [self.row(i, 1 if 1 <= i <= 3 else 2 if 5 <= i <= 6 else None)
                     for i in range(7)]

    @staticmethod
    def row(frame, period, group=None, player_id=None, ball=(0, 0), players=None):
        return {"frame": frame, "period": period, "timestamp": None,
                "possession": {"group": group, "player_id": player_id},
                "ball_data": {"x": ball[0], "y": ball[1], "z": 0,
                              "is_detected": True} if ball else
                             {"x": None, "y": None, "z": None, "is_detected": None},
                "player_data": players if players is not None else
                               [{"player_id": 101, "x": 1, "y": 0, "is_detected": True},
                                {"player_id": 202, "x": 8, "y": 0, "is_detected": True}]}

    def write_fixture(self):
        self.meta.write_text(json.dumps(self.metadata))
        self.tracking.write_text("".join(json.dumps(row) + "\n" for row in self.rows))

    def write_phases(self, rows=None):
        rows = rows if rows is not None else [(7, 1, 1, 3, 11), (7, 2, 5, 7, 22)]
        with self.phases.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("match_id", "period", "frame_start", "frame_end",
                             "team_in_possession_id"))
            writer.writerows(rows)

    def test_scales_temporal_durations_from_25_to_10_fps(self):
        scaled = adapter.scale_config(self.config, 10)
        self.assertEqual((scaled["control_frames"], scaled["evidence_gap_frames"],
                          scaled["out_of_bounds_frames"]), (5, 2, 10))
        self.assertEqual(self.config["control_frames"], 12)

    def test_maps_metric_coordinates_teams_and_inclusive_periods(self):
        self.rows[2] = self.row(2, 1, "home team", 101)
        self.rows[3] = self.row(3, 1, "away team", 202, ball=(51, 0))
        self.rows[5] = self.row(5, 2, ball=None, players=[])
        self.write_fixture()
        evidence, blocks, reference, match = adapter.load_match(self.meta, self.tracking,
                                                                 self.config)
        self.assertEqual(blocks, [(1, 1, 3), (2, 5, 6)])
        self.assertEqual(reference, [None, None, "H", "A", None, None, None])
        self.assertEqual(evidence[2]["candidate"], "H")
        self.assertEqual(evidence[2]["nearest_distance_m"], {"H": 1.0, "A": 8.0})
        self.assertEqual(evidence[2]["ball_xy"], (0.5, 0.5))
        self.assertTrue(evidence[3]["outside"])
        self.assertEqual((evidence[5]["ball_seen"], evidence[5]["players_seen"]),
                         (False, 0))
        self.assertEqual(match["id"], 7)

    def test_rejects_gaps_and_wrong_team_reference(self):
        self.rows.pop(2)
        self.write_fixture()
        with self.assertRaisesRegex(ValueError, "frame mismatch"):
            adapter.load_match(self.meta, self.tracking, self.config)
        self.rows.insert(2, self.row(2, 1, "home team", 202))
        self.write_fixture()
        with self.assertRaisesRegex(ValueError, "possession player team"):
            adapter.load_match(self.meta, self.tracking, self.config)

    def test_preserves_trailing_outside_period_frames(self):
        self.rows.append(self.row(7, None, ball=None, players=[]))
        self.write_fixture()
        evidence, blocks, reference, _ = adapter.load_match(self.meta, self.tracking,
                                                             self.config)
        self.assertEqual(len(evidence), 8)
        self.assertEqual(blocks[-1], (2, 5, 6))
        self.assertIsNone(reference[7])

    def test_reports_one_missing_terminal_tracking_frame_without_fabricating_it(self):
        self.rows.pop()
        self.write_fixture()
        evidence, blocks, reference, match = adapter.load_match(self.meta,
                                                                 self.tracking,
                                                                 self.config)
        self.assertEqual(len(evidence), 6)
        self.assertEqual(len(reference), 6)
        self.assertEqual(blocks[-1], (2, 5, 5))
        self.assertEqual(match["_tracking_audit"]["missing_terminal_frames"], 1)
        self.rows.pop()
        self.write_fixture()
        with self.assertRaisesRegex(ValueError, "tracking ends before"):
            adapter.load_match(self.meta, self.tracking, self.config)

    def test_maps_half_open_live_phases_without_inventing_dead_labels(self):
        self.write_phases()
        reference = adapter.load_phase_reference(self.phases, self.metadata, 7)
        self.assertEqual(reference, [None, "H", "H", None, None, "A", "A"])
        self.write_phases([(7, 1, 1, 3, 11), (7, 1, 2, 4, 22)])
        with self.assertRaisesRegex(ValueError, "overlapping phases"):
            adapter.load_phase_reference(self.phases, self.metadata, 7)

    def test_excludes_phase_crossing_period_boundary_and_audits_it(self):
        self.write_phases([(7, 1, 2, 5, 11)])
        audit = {}
        reference = adapter.load_phase_reference(self.phases, self.metadata, 7,
                                                 audit=audit)
        self.assertEqual(reference, [None] * 7)
        self.assertEqual(audit["excluded_cross_period_phases"], 1)
        self.assertEqual(audit["excluded_cross_period_frames"], 3)

    def test_comparison_counts_only_provider_team_frames(self):
        result = adapter.compare_labels(["H", "A", "D", "X", "H", "A"],
                                        ["H", "H", None, "A", None, "A"])
        self.assertEqual(result["reference_team_frames"], 4)
        self.assertEqual(result["team_prediction_frames"], 3)
        self.assertEqual(result["matching_team_frames"], 2)
        self.assertEqual(result["reference_missing_frames"], 2)
        self.assertEqual(result["confusion"], {"H": {"H": 1, "A": 1, "D": 0, "X": 0},
                                                "A": {"H": 0, "A": 1, "D": 0, "X": 1}})

    def test_comparison_rejects_invalid_prediction_cleanly(self):
        with self.assertRaisesRegex(ValueError, "invalid model label"):
            adapter.compare_labels([None], ["H"])

    def test_evaluates_match_without_challenge_labels(self):
        self.config["control_frames"] = 2
        self.rows[2] = self.row(2, 1, "home team", 101)
        self.rows[3] = self.row(3, 1, "away team", 202, ball=(51, 0))
        self.write_fixture()
        self.write_phases()
        result = adapter.evaluate_match(self.meta, self.tracking, self.phases,
                                        self.config)
        self.assertEqual((result["id"], result["date"], result["frames"]),
                         (7, "2025-01-01", 7))
        self.assertEqual(result["temporal"]["matching_team_frames"], 1)
        self.assertEqual(result["temporal"]["reference_team_frames"], 2)
        self.assertEqual(result["instantaneous_proximity"]["team_prediction_frames"], 1)
        self.assertEqual(result["temporal_labels"]["X"], 2)
        self.assertIn("tracking_sha256", result)
        self.assertEqual(result["live_phase"]["reference_team_frames"], 4)

    def test_counts_only_within_period_confirmed_team_transitions(self):
        self.config["control_frames"] = 2
        self.rows[3] = self.row(3, 1, "away team", 202,
                                players=[{"player_id": 101, "x": 8, "y": 0,
                                          "is_detected": True},
                                         {"player_id": 202, "x": 1, "y": 0,
                                          "is_detected": True}])
        self.write_fixture()
        self.write_phases()
        result = adapter.evaluate_match(self.meta, self.tracking, self.phases,
                                        self.config)
        self.assertEqual(result["home_away_transitions"], 1)

    def test_command_writes_aggregate_json_only(self):
        self.write_fixture()
        folder = Path(self.temp.name) / "7"
        folder.mkdir()
        shutil.copyfile(self.meta, folder / "7_match.json")
        shutil.copyfile(self.tracking, folder / "7_tracking_extrapolated.jsonl")
        self.write_phases()
        shutil.copyfile(self.phases, folder / "7_phases_of_play.csv")
        out = Path(self.temp.name) / "comparison.json"
        command = [sys.executable, "-m", "model.compare_skillcorner", "--data-root",
                   self.temp.name, "--match-ids", "7", "--config", "model/config_v2.json",
                   "--output", str(out)]
        run = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(out.read_text())
        self.assertEqual([item["id"] for item in result["matches"]], [7])
        self.assertEqual(result["total"]["reference_team_frames"], 0)
        self.assertNotIn("predictions", result)


if __name__ == "__main__":
    unittest.main()
