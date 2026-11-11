"""Strict tactical ATD ingestion and tentative per-frame possession evidence.

Coordinates stay normalized in output records. Distances used to nominate a
nearby team are converted to pitch metres; a nomination is not possession.
"""

import math
import xml.etree.ElementTree as ET

from games import GAME, GAMES, half_video_blocks, require, source_frames
from starter.load_smart_tagging import load as load_smart_tagging


def track_teams(meta_path):
    """Return slot sides and ordered team names from ATD metadata."""
    root = ET.parse(meta_path).getroot()
    teams = list(root.iter("Team"))
    if len(teams) != 2:
        raise ValueError("expected exactly two teams")
    home_id, away_id = (team.get("id") for team in teams)
    if not home_id or not away_id or home_id == away_id:
        raise ValueError("invalid team IDs in metadata")
    players = list(root.iter("Player"))
    if not players:
        raise ValueError("no track slots in metadata")
    slots = []
    for player in players:
        team_id = player.get("teamId")
        if team_id not in (home_id, away_id):
            raise ValueError("unknown track teamId")
        slots.append("H" if team_id == home_id else "A")
    return slots, tuple(team.findtext("Name") for team in teams)


def point(group):
    """Read finite normalized xy; NaN is an absent observation."""
    values = group.split(",")
    if len(values) < 2:
        raise ValueError("coordinate group has fewer than two fields")
    x, y = float(values[0]), float(values[1])
    return (x, y) if math.isfinite(x) and math.isfinite(y) else None


def evidence_from_line(line, expected_frame, team_slots, config, pitch):
    """Parse one ATD record; its one-based ID must match the zero-based frame."""
    parts = line.strip().split(":")
    if len(parts) != 3 or int(parts[0]) != expected_frame + 1:
        raise ValueError("ATD frame mismatch at video frame {}".format(expected_frame))
    players = parts[1].split(";")
    if len(players) != len(team_slots):
        raise ValueError("ATD slot count mismatch at video frame {}".format(expected_frame))
    ball = point(parts[2])
    seen = 0
    closest = {"H": math.inf, "A": math.inf}
    for group, team in zip(players, team_slots):
        player = point(group)
        if player is None:
            continue
        seen += 1
        if ball is not None:
            distance = math.hypot((player[0] - ball[0]) * pitch[0],
                                  (player[1] - ball[1]) * pitch[1])
            closest[team] = min(closest[team], distance)
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
            "ball_xy": ball, "players_seen": seen, "stationary_set_piece": False}


def add_set_piece_evidence(evidence, events, blocks, config, pitch):
    """Flag confirmed stationarity inside tags; optionally mark its full window offline."""
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
                xs = [(xy[0] - positions[0][0]) * pitch[0] for xy in positions]
                ys = [(xy[1] - positions[0][1]) * pitch[1] for xy in positions]
                if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) <= radius:
                    first_confirmed = frame - window_size + 1 if config.get("set_piece_backfill", False) else frame
                    for confirmed_frame in range(first_confirmed, frame + 1):
                        evidence[confirmed_frame]["stationary_set_piece"] = True


def load_tactical_evidence(config, data_dir=None):
    """Load every tactical frame, rejecting missing, duplicate, or extra ATD IDs."""
    meta_path, raw_path = require(["atd_meta", "atd_raw"], GAME, data_dir)
    slots, team_names = track_teams(meta_path)
    count = source_frames("tactical", GAME)
    pitch = GAMES[GAME]["pitch"]
    evidence = []
    with open(raw_path) as handle:
        for frame, line in enumerate(handle):
            if frame >= count:
                raise ValueError("ATD has more than {} frames".format(count))
            evidence.append(evidence_from_line(line, frame, slots, config, pitch))
    if len(evidence) != count:
        raise ValueError("ATD has {} frames; expected {}".format(len(evidence), count))
    events = load_smart_tagging(GAME, data_dir)
    add_set_piece_evidence(evidence, events, half_video_blocks(GAME), config, pitch)
    return evidence, team_names
