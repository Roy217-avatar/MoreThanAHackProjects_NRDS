"""Tracking evidence and a causal possession state machine.

No labels or thresholds are learned from the provided match. Frame evidence is
deliberately sparse: proximity is considered only when the closest player is
within reach and has a clear advantage over the other team.
"""

import csv
import json
import math
import os
import xml.etree.ElementTree as ET
from collections import Counter

from games import GAME, GAMES, half_video_blocks, require, source_frames
from starter.load_smart_tagging import load as load_smart_tagging


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
    return config


def track_teams(meta_path):
    root = ET.parse(meta_path).getroot()
    teams = list(root.iter("Team"))
    if len(teams) != 2:
        raise ValueError("expected exactly two teams")
    home_id, away_id = (team.get("id") for team in teams)
    players = list(root.iter("Player"))
    if not players:
        raise ValueError("no track slots in metadata")
    mapping = []
    for player in players:
        team_id = player.get("teamId")
        if team_id not in (home_id, away_id):
            raise ValueError("unknown track teamId")
        mapping.append("H" if team_id == home_id else "A")
    return mapping, [team.findtext("Name") for team in teams]


def point(group):
    values = group.split(",")
    if len(values) < 2:
        raise ValueError("coordinate group has fewer than two fields")
    x, y = float(values[0]), float(values[1])
    return (x, y) if math.isfinite(x) and math.isfinite(y) else None


def evidence_from_line(line, expected_frame, team_slots, config, pitch):
    parts = line.strip().split(":")
    if len(parts) != 3 or int(parts[0]) != expected_frame + 1:
        raise ValueError("ATD frame mismatch at video frame {}".format(expected_frame))
    players = parts[1].split(";")
    if len(players) != len(team_slots):
        raise ValueError("ATD slot count mismatch at video frame {}".format(expected_frame))
    ball = point(parts[2])
    observed = 0
    closest = {"H": math.inf, "A": math.inf}
    if ball is not None:
        for group, team in zip(players, team_slots):
            player = point(group)
            if player is None:
                continue
            observed += 1
            distance = math.hypot((player[0] - ball[0]) * pitch[0],
                                  (player[1] - ball[1]) * pitch[1])
            closest[team] = min(closest[team], distance)
    else:
        observed = sum(point(group) is not None for group in players)
    tolerance = config["pitch_tolerance"]
    outside = ball is not None and (ball[0] < -tolerance or ball[0] > 1 + tolerance
                                     or ball[1] < -tolerance or ball[1] > 1 + tolerance)
    candidate = None
    if ball is not None and not outside:
        winner = "H" if closest["H"] < closest["A"] else "A"
        loser = "A" if winner == "H" else "H"
        if (closest[winner] <= config["control_distance_m"]
                and closest[loser] - closest[winner] >= config["opponent_margin_m"]):
            candidate = winner
    return {"candidate": candidate, "outside": outside, "ball_seen": ball is not None,
            "ball_xy": ball, "stationary_set_piece": False,
            "players_seen": observed}


def add_set_piece_evidence(evidence, events, blocks, config, pitch):
    """Mark sustained stationary ball during an automatic set-piece interval.

    A tag alone never means the entire interval is dead. The ball must remain
    observed in a small region for the configured duration. The window resets
    at half boundaries and when any observation is absent.
    """
    tagged = [False] * len(evidence)
    for event in events:
        if (event["code"] or "").strip().upper() != "SET PIECES":
            continue
        first = max(0, event["start_frame"])
        last = min(len(evidence), event["end_frame"])
        for frame in range(first, last):
            tagged[frame] = True
    window_size = config["set_piece_stationary_frames"]
    radius = config["set_piece_stationary_radius_m"]
    for _, first, last in blocks:
        positions = []
        for frame in range(first, last + 1):
            ball = evidence[frame]["ball_xy"]
            if not tagged[frame] or ball is None or evidence[frame]["outside"]:
                positions = []
                continue
            positions.append(ball)
            if len(positions) > window_size:
                positions.pop(0)
            if len(positions) == window_size:
                xs = [(point[0] - positions[0][0]) * pitch[0] for point in positions]
                ys = [(point[1] - positions[0][1]) * pitch[1] for point in positions]
                if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) <= radius:
                    evidence[frame]["stationary_set_piece"] = True


def infer(evidence, blocks, config):
    """Return (labels, reason codes); each half starts with no carried state."""
    n = len(evidence)
    labels = ["X"] * n
    reasons = ["outside_half"] * n
    for _, first, last in blocks:
        if first < 0 or last >= n or last < first:
            raise ValueError("invalid half boundary")
        state = None
        pending = None
        votes = gap = outside_run = 0
        for frame in range(first, last + 1):
            row = evidence[frame]
            candidate = row["candidate"]
            if row["outside"]:
                outside_run += 1
            else:
                outside_run = 0
            if outside_run >= config["out_of_bounds_frames"] or row.get("stationary_set_piece", False):
                state = "D"
                pending, votes, gap = None, 0, 0
                reason = "sustained_out_of_bounds" if outside_run >= config["out_of_bounds_frames"] else "stationary_set_piece"
                labels[frame], reasons[frame] = "D", reason
                continue
            if candidate is not None and candidate != state:
                if candidate != pending:
                    pending, votes, gap = candidate, 0, 0
                votes += 1
                gap = 0
                if votes >= config["control_frames"]:
                    state = candidate
                    pending, votes = None, 0
                    reason = "control_confirmed"
                else:
                    reason = "control_pending"
            elif candidate == state:
                pending, votes, gap = None, 0, 0
                reason = "control_held"
            else:
                if pending is not None:
                    gap += 1
                    if gap > config["evidence_gap_frames"]:
                        pending, votes, gap = None, 0, 0
                reason = "missing_ball" if not row["ball_seen"] else "contested_or_loose"
            labels[frame] = state or "X"
            reasons[frame] = reason if state != "D" else "awaiting_restart"
    return labels, reasons


def write_submission(path, labels):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("frame", "label"))
        writer.writerows((frame, label) for frame, label in enumerate(labels))


def run(config_path, output, diagnostics):
    config = load_config(config_path)
    meta, raw = require(["atd_meta", "atd_raw"])
    slots, team_names = track_teams(meta)
    n = source_frames("tactical", GAME)
    evidence = []
    with open(raw) as handle:
        for frame, line in enumerate(handle):
            if frame >= n:
                raise ValueError("ATD has more than {} frames".format(n))
            evidence.append(evidence_from_line(line, frame, slots, config, GAMES[GAME]["pitch"]))
    if len(evidence) != n:
        raise ValueError("ATD has {} frames; expected {}".format(len(evidence), n))
    blocks = half_video_blocks(GAME)
    events = load_smart_tagging()
    add_set_piece_evidence(evidence, events, blocks, config, GAMES[GAME]["pitch"])
    labels, reasons = infer(evidence, blocks, config)
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
    print("inputs:", meta, raw)
    print("outputs:", output, diagnostics)
