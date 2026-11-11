"""End-to-end tactical possession prediction and CSV serialization.

Frame evidence and temporal inference are separate so each can be tested with
synthetic inputs. No labels or thresholds are learned from the supplied match.
"""

import csv
import json
import os
from collections import Counter

from games import GAME, half_video_blocks
from model.evidence import (add_set_piece_evidence, evidence_from_line,
                            load_tactical_evidence, point, track_teams)
from model.inference import infer


def load_config(path):
    with open(path) as handle:
        config = json.load(handle)
    for name in ("control_distance_m", "opponent_margin_m", "pitch_tolerance",
                 "set_piece_stationary_radius_m"):
        if config[name] < 0:
            raise ValueError("{} must be nonnegative".format(name))
    for name in ("control_frames", "evidence_gap_frames", "out_of_bounds_frames",
                 "set_piece_stationary_frames"):
        if not isinstance(config[name], int) or config[name] < (0 if name == "evidence_gap_frames" else 1):
            raise ValueError("{} must be a nonnegative frame count".format(name))
    if not isinstance(config.get("set_piece_backfill", False), bool):
        raise ValueError("set_piece_backfill must be a boolean")
    return config


def write_submission(path, labels):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("frame", "label"))
        writer.writerows((frame, label) for frame, label in enumerate(labels))


def run(config_path, output, diagnostics, data_dir=None):
    """Generate tactical-timeline labels from an authorized local bundle."""
    if os.path.realpath(os.fspath(output)) == os.path.realpath(os.fspath(diagnostics)):
        raise ValueError("submission and diagnostics require different paths")
    config = load_config(config_path)
    evidence, team_names = load_tactical_evidence(config, data_dir)
    labels, reasons = infer(evidence, half_video_blocks(GAME), config)
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(diagnostics)), exist_ok=True)
    write_submission(output, labels)
    with open(diagnostics, "w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("frame", "label", "reason", "ball_seen", "players_seen", "candidate", "stationary_set_piece"))
        writer.writerows((i, labels[i], reasons[i], int(row["ball_seen"]), row["players_seen"], row["candidate"] or "",
                          int(row["stationary_set_piece"]))
                         for i, row in enumerate(evidence))
    print("teams H/A:", team_names, "labels:", dict(Counter(labels)))
    print("outputs:", output, diagnostics)
