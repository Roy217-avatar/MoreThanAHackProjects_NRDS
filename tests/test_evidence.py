"""Synthetic checks for tactical evidence extraction and strict indexing."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from model.evidence import add_set_piece_evidence, evidence_from_line, load_tactical_evidence, track_teams


CONFIG = {"control_distance_m": 2.0, "opponent_margin_m": 0.75,
          "pitch_tolerance": 0.005, "set_piece_stationary_frames": 3,
          "set_piece_stationary_radius_m": 0.5}


def frame(ball="0.5,0.5,0", home="0.5,0.5,0", away="0.8,0.8,0", frame_id=1):
    return f"{frame_id}:{home};{away}:{ball}\n"


class EvidenceTests(unittest.TestCase):
    def test_metadata_team_ids_determine_home_away_slots(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meta.xml"
            path.write_text('<Root><Team id="10"><Name>Home</Name></Team>'
                            '<Team id="20"><Name>Away</Name></Team>'
                            '<Player teamId="20"/><Player teamId="10"/></Root>')
            slots, names = track_teams(path)
            self.assertEqual(slots, ["A", "H"])
            self.assertEqual(names, ("Home", "Away"))

    def test_frame_ids_and_slot_counts_must_match(self):
        self.assertEqual(evidence_from_line(frame(), 0, ["H", "A"], CONFIG, (105.3, 68))["candidate"], "H")
        with self.assertRaises(ValueError):
            evidence_from_line(frame(frame_id=3), 0, ["H", "A"], CONFIG, (105.3, 68))
        with self.assertRaises(ValueError):
            evidence_from_line(frame(), 0, ["H"], CONFIG, (105.3, 68))

    def test_missing_coordinates_remain_absent_not_outside(self):
        missing_ball = evidence_from_line(frame(ball="NaN,NaN,NaN"), 0, ["H", "A"], CONFIG, (105.3, 68))
        missing_players = evidence_from_line(frame(home="NaN,NaN,NaN", away="NaN,NaN,NaN"), 0,
                                             ["H", "A"], CONFIG, (105.3, 68))
        self.assertEqual((missing_ball["candidate"], missing_ball["ball_xy"], missing_ball["players_seen"], missing_ball["outside"]),
                         (None, None, 2, False))
        self.assertEqual((missing_players["candidate"], missing_players["players_seen"], missing_players["ball_seen"]),
                         (None, 0, True))

    def test_distance_uses_pitch_metres_and_requires_team_margin(self):
        near = evidence_from_line(frame(home="0.51,0.5,0", away="0.8,0.8,0"), 0,
                                  ["H", "A"], CONFIG, (105.3, 68))
        far = evidence_from_line(frame(home="0.52,0.5,0", away="0.8,0.8,0"), 0,
                                 ["H", "A"], CONFIG, (105.3, 68))
        contested = evidence_from_line(frame(home="0.5,0.5,0", away="0.501,0.5,0"), 0,
                                       ["H", "A"], CONFIG, (105.3, 68))
        self.assertEqual(near["candidate"], "H")
        self.assertIsNone(far["candidate"])
        self.assertIsNone(contested["candidate"])

    def test_set_piece_requires_observed_stationarity_and_resets_at_half(self):
        evidence = [evidence_from_line(frame(frame_id=i + 1), i, ["H", "A"], CONFIG, (105.3, 68))
                    for i in range(7)]
        evidence[3]["ball_xy"] = None
        evidence[3]["ball_seen"] = False
        events = [{"code": "SET PIECES", "start_frame": 0, "end_frame": 7}]
        add_set_piece_evidence(evidence, events, [(1, 0, 2), (2, 3, 6)], CONFIG, (105.3, 68))
        self.assertEqual([i for i, row in enumerate(evidence) if row["stationary_set_piece"]], [2, 6])

    def test_confirmed_stationary_window_backfills_only_observed_frames(self):
        config = dict(CONFIG, set_piece_backfill=True)
        evidence = [evidence_from_line(frame(frame_id=i + 1), i, ["H", "A"], config, (105.3, 68))
                    for i in range(6)]
        evidence[3]["ball_xy"] = None
        evidence[3]["ball_seen"] = False
        events = [{"code": "SET PIECES", "start_frame": 0, "end_frame": 6}]
        add_set_piece_evidence(evidence, events, [(1, 0, 5)], config, (105.3, 68))
        self.assertEqual([i for i, row in enumerate(evidence) if row["stationary_set_piece"]],
                         [0, 1, 2])

    def test_stationary_backfill_does_not_cross_halftime(self):
        config = dict(CONFIG, set_piece_backfill=True)
        evidence = [evidence_from_line(frame(frame_id=i + 1), i, ["H", "A"], config, (105.3, 68))
                    for i in range(5)]
        events = [{"code": "SET PIECES", "start_frame": 0, "end_frame": 5}]
        add_set_piece_evidence(evidence, events, [(1, 0, 1), (2, 2, 4)], config, (105.3, 68))
        self.assertEqual([i for i, row in enumerate(evidence) if row["stationary_set_piece"]],
                         [2, 3, 4])

    def test_loader_rejects_short_and_extra_raw_files(self):
        with tempfile.TemporaryDirectory() as directory:
            tactical = Path(directory) / "tactical"
            tactical.mkdir()
            (tactical / "BAR-ATH_tactical_atd.xml").write_text(
                '<Root><Team id="10"><Name>Home</Name></Team><Team id="20"><Name>Away</Name></Team>'
                '<Player teamId="10"/><Player teamId="20"/></Root>')
            raw = tactical / "BAR-ATH_tactical_atd.txt"
            (tactical / "BAR-ATH_tactical_smart_tagging.xml").write_text("<Root/>")
            with patch("model.evidence.source_frames", return_value=2), patch("model.evidence.half_video_blocks", return_value=((1, 0, 1),)):
                raw.write_text(frame(frame_id=1))
                with self.assertRaisesRegex(ValueError, "expected 2"):
                    load_tactical_evidence(CONFIG, directory)
                raw.write_text(frame(frame_id=1) + frame(frame_id=2) + frame(frame_id=3))
                with self.assertRaisesRegex(ValueError, "more than 2"):
                    load_tactical_evidence(CONFIG, directory)
                raw.write_text(frame(frame_id=1) + frame(frame_id=2))
                evidence, names = load_tactical_evidence(CONFIG, directory)
                self.assertEqual((len(evidence), names), (2, ("Home", "Away")))
                self.assertEqual([row["candidate"] for row in evidence], ["H", "H"])


if __name__ == "__main__":
    unittest.main()
