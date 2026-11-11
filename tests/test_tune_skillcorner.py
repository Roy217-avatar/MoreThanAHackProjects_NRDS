"""Tests for reproducible external-only configuration search."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from model import tune_skillcorner as tuner


class TuneSkillCornerTests(unittest.TestCase):
    def test_reassigns_proximity_without_using_provider_labels(self):
        rows = [{"candidate": None, "outside": False,
                 "nearest_distance_m": {"H": 1.0, "A": 3.0}},
                {"candidate": "H", "outside": False,
                 "nearest_distance_m": {"H": 1.0, "A": 1.5}},
                {"candidate": "H", "outside": True,
                 "nearest_distance_m": {"H": 0.1, "A": 3.0}}]
        tuner.assign_candidates(rows, 2.0, 0.75)
        self.assertEqual([row["candidate"] for row in rows], ["H", None, None])
        tuner.assign_candidates(rows, 0.5, 0.75)
        self.assertEqual([row["candidate"] for row in rows], [None, None, None])

    def test_grid_keeps_dead_ball_settings_fixed(self):
        base = {"control_distance_m": 2.0, "opponent_margin_m": 0.75,
                "control_frames": 12, "evidence_gap_frames": 5,
                "out_of_bounds_frames": 25, "set_piece_stationary_frames": 25}
        configs = tuner.grid_configs(base)
        self.assertEqual(len(configs), 144)
        self.assertIn(base, configs)
        self.assertEqual({item["out_of_bounds_frames"] for item in configs}, {25})

    def test_selection_uses_team_agreement_then_phase_then_duration(self):
        choices = [{"config": {"control_frames": 8, "control_distance_m": 2.0,
                                "opponent_margin_m": 0.5, "evidence_gap_frames": 5},
                    "team_matches": 10, "phase_matches": 8},
                   {"config": {"control_frames": 12, "control_distance_m": 2.0,
                                "opponent_margin_m": 0.5, "evidence_gap_frames": 5},
                    "team_matches": 10, "phase_matches": 8},
                   {"config": {"control_frames": 16, "control_distance_m": 2.0,
                                "opponent_margin_m": 0.5, "evidence_gap_frames": 5},
                    "team_matches": 9, "phase_matches": 9}]
        self.assertEqual(tuner.select_best(choices)["config"]["control_frames"], 12)

    def test_scores_temporal_team_agreement_on_labeled_frames(self):
        rows = [{"candidate": candidate, "outside": False, "ball_seen": True,
                 "stationary_set_piece": False} for candidate in
                ("H", "H", None, "A", "A", "A")]
        data = [{"evidence": rows, "blocks": [(1, 0, 5)],
                 "reference": ["H", "H", "H", "A", "A", "A"],
                 "phase_reference": ["H", "H", "H", "A", "A", "A"]}]
        config = {"control_frames": 5, "evidence_gap_frames": 0,
                  "out_of_bounds_frames": 25}
        result = tuner.score_setting(data, config)
        self.assertEqual((result["team_matches"], result["team_frames"],
                          result["phase_matches"], result["phase_frames"]),
                         (4, 6, 4, 6))

    def test_command_selects_config_and_writes_aggregate_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "7"
            folder.mkdir()
            metadata = {"id": 7, "status": "closed", "date_time": "2025-01-01T00:00:00Z",
                        "home_team": {"id": 1, "name": "Home"},
                        "away_team": {"id": 2, "name": "Away"},
                        "pitch_length": 100, "pitch_width": 60,
                        "players": [{"id": 11, "team_id": 1}, {"id": 22, "team_id": 2}],
                        "match_periods": [{"period": 1, "start_frame": 0,
                                           "end_frame": 4}]}
            (folder / "7_match.json").write_text(json.dumps(metadata))
            with (folder / "7_tracking_extrapolated.jsonl").open("w") as handle:
                for frame in range(5):
                    row = {"frame": frame, "period": 1, "timestamp": None,
                           "possession": {"group": "home team", "player_id": 11},
                           "ball_data": {"x": 0, "y": 0, "z": 0, "is_detected": True},
                           "player_data": [{"player_id": 11, "x": 1, "y": 0,
                                            "is_detected": True},
                                           {"player_id": 22, "x": 8, "y": 0,
                                            "is_detected": True}]}
                    handle.write(json.dumps(row) + "\n")
            with (folder / "7_phases_of_play.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(("match_id", "period", "frame_start", "frame_end",
                                 "team_in_possession_id"))
                writer.writerow((7, 1, 0, 5, 1))
            report = Path(temp) / "report.json"
            output = Path(temp) / "config.json"
            run = subprocess.run([sys.executable, "-m", "model.tune_skillcorner",
                                  "--data-root", temp, "--match-ids", "7",
                                  "--base-config", "model/config_v2.json",
                                  "--config-out", str(output), "--output", str(report)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(output.exists())
            chosen = json.loads(output.read_text())
            summary = json.loads(report.read_text())
            self.assertEqual(chosen["version"], 3)
            self.assertEqual(chosen["out_of_bounds_frames"], 25)
            self.assertEqual(chosen["control_frames"], 8)
            self.assertEqual(summary["development_match_ids"], [7])
            self.assertEqual(len(summary["candidates"]), 144)
            self.assertNotIn("predictions", summary)


if __name__ == "__main__":
    unittest.main()
