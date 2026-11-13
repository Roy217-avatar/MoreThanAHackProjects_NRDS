"""Adapter for the reserved WCSF 10 Hz anonymized professional match.

The provider's AliveFlag and PossessionFlag are returned only as references.
Inference evidence is built from player and ball coordinates independently.
"""
from collections import Counter
import csv
import io
import math
from pathlib import Path
import zipfile

from model.external_idsse import digest
from model.external_skillcorner import scale_config
from model.stoppage import add_stoppage_evidence
from model.tune_skillcorner import assign_candidates
from model.motion import add_ball_motion_evidence


FPS = 10
PITCH_M = (105.0, 68.0)


def _number(value):
    if value in (None, ''):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _code(value, allowed, name):
    number = _number(value)
    if number is None:
        return None
    result = int(number)
    if number != result or result not in allowed:
        raise ValueError('invalid {}'.format(name))
    return result


def _member(handle):
    names = [name for name in handle.namelist()
             if name.lower().endswith('.csv') and not name.startswith('__MACOSX/')]
    if len(names) != 1:
        raise ValueError('archive must contain exactly one position CSV')
    return names[0]


def _finalize(rows, config):
    counts = Counter((row['alive'], row['possession']) for row in rows)
    ordered = counts.most_common()
    conflicted = len(ordered) > 1
    if conflicted and ordered[0][1] == ordered[1][1]:
        raise ValueError('inconsistent reference within timestamp: no unique majority')
    (alive, possession), _ = ordered[0]
    if alive not in (0, 1):
        raise ValueError('missing AliveFlag')
    reference = 'D' if alive == 0 else {1: 'H', 2: 'A'}.get(possession)

    closest = {'H': math.inf, 'A': math.inf}
    balls = {1: set(), 2: set()}
    players_seen = 0
    for row in rows:
        ball, player = row['ball'], row['player']
        if ball is not None:
            balls[row['group']].add(ball)
        if player is None:
            continue
        players_seen += 1
        if ball is not None:
            side = 'H' if row['group'] == 1 else 'A'
            closest[side] = min(closest[side], math.dist(player, ball))
    if any(len(values) > 1 for values in balls.values()):
        raise ValueError('inconsistent ball coordinates within team timestamp')
    # Coordinates are mirrored by team. Prefer the home-oriented copy; distances
    # and stationary displacement are invariant to the away copy's reflection.
    ball = next(iter(balls[1]), None) or next(iter(balls[2]), None)
    outside = ball is not None and (abs(ball[0]) > PITCH_M[0] * (0.5 + config['pitch_tolerance'])
                                   or abs(ball[1]) > PITCH_M[1] * (0.5 + config['pitch_tolerance']))
    evidence = {
        'candidate': None,
        'outside': outside,
        'ball_seen': ball is not None,
        'ball_xy': ((ball[0] / PITCH_M[0] + 0.5, ball[1] / PITCH_M[1] + 0.5)
                    if ball is not None else None),
        'players_seen': players_seen,
        'stationary_set_piece': False,
        'nearest_distance_m': closest,
    }
    return evidence, reference, conflicted


def _load_half(path, config):
    evidence, reference, timestamps = [], [], []
    reference_conflicts = 0
    with zipfile.ZipFile(path) as archive:
        with archive.open(_member(archive)) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig', newline=''))
            required = {'x', 'y', 'group_id', 'timestamp_ms', 'AliveFlag',
                        'PossessionFlag', 'x_ball', 'y_ball', 'player_id'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError('missing WCSF position columns')
            current = None
            rows = []
            for source in reader:
                timestamp = _code(source['timestamp_ms'], range(0, 10**12), 'timestamp_ms')
                if timestamp is None:
                    raise ValueError('missing timestamp_ms')
                if current is not None and timestamp < current:
                    raise ValueError('unordered timestamp')
                if timestamp != current and rows:
                    item, target, conflicted = _finalize(rows, config)
                    item['timestamp_s'] = current / 1000.0
                    evidence.append(item); reference.append(target); timestamps.append(current)
                    reference_conflicts += conflicted
                    if timestamp - current != 100:
                        raise ValueError('timestamps are not continuous 10 Hz')
                    rows = []
                current = timestamp
                group = _code(source['group_id'], (1, 2), 'group_id')
                x, y = _number(source['x']), _number(source['y'])
                bx, by = _number(source['x_ball']), _number(source['y_ball'])
                rows.append({
                    'group': group,
                    'player': (x, y) if x is not None and y is not None else None,
                    'ball': (bx, by) if bx is not None and by is not None else None,
                    'alive': _code(source['AliveFlag'], (0, 1), 'AliveFlag'),
                    'possession': _code(source['PossessionFlag'], (1, 2), 'PossessionFlag'),
                })
            if rows:
                item, target, conflicted = _finalize(rows, config)
                item['timestamp_s'] = current / 1000.0
                evidence.append(item); reference.append(target); timestamps.append(current)
                reference_conflicts += conflicted
    if not evidence:
        raise ValueError('empty WCSF position archive')
    assign_candidates(evidence, config['control_distance_m'], config['opponent_margin_m'])
    return evidence, reference, timestamps, reference_conflicts


def load_match(paths, config):
    """Load first/second-half archives into one timeline with explicit blocks."""
    if len(paths) != 2:
        raise ValueError('expected first- and second-half archives')
    scaled = scale_config(config, FPS)
    evidence, reference, blocks, ranges = [], [], [], []
    reference_conflicts = 0
    for half, path in enumerate(map(Path, paths), 1):
        half_evidence, half_reference, timestamps, half_conflicts = _load_half(path, scaled)
        first = len(evidence)
        evidence.extend(half_evidence); reference.extend(half_reference)
        blocks.append((half, first, len(evidence) - 1))
        ranges.append([timestamps[0], timestamps[-1]])
        reference_conflicts += half_conflicts
    add_ball_motion_evidence(evidence, blocks, PITCH_M)
    if (scaled.get('stationary_unattended_frames') is not None
            or scaled.get('stationary_observed_frames') is not None):
        add_stoppage_evidence(evidence, blocks, scaled, PITCH_M)
    audit = {
        'fps': FPS,
        'frames': len(evidence),
        'timestamps_ms': ranges,
        'reference_counts': dict(Counter(value or 'unknown' for value in reference)),
        'ball_missing_frames': sum(not row['ball_seen'] for row in evidence),
        'no_players_frames': sum(row['players_seen'] == 0 for row in evidence),
        'reference_conflict_timestamps': reference_conflicts,
        'archive_sha256': {Path(path).name: digest(path) for path in paths},
    }
    return {'id': 'wcsf-anonymous-professional-match', 'evidence': evidence,
            'reference': reference, 'blocks': blocks, 'config': scaled, 'audit': audit}
