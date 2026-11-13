"""IDSSE/Sportec external data adapter. Reference fields never become features.

Coordinates are centred pitch metres; N is a raw frame number at 25 Hz.
Each half gets its own explicit offset and inference block. Missing observations
stay missing, including raw-frame gaps. No event annotations enter inference.
"""
from collections import Counter
from datetime import datetime
import hashlib
import math
import xml.etree.ElementTree as ET

from model.tune_skillcorner import assign_candidates
from model.motion import add_ball_motion_evidence

SECTIONS = {'firstHalf': 1, 'secondHalf': 2}
SOURCE_REVISION = 'a715a38dfbaf5f58e431727c2b78d174101a703c'


def digest(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def _groups(path):
    for _, element in ET.iterparse(path, events=('end',)):
        if element.tag == 'FrameSet':
            yield element
            element.clear()


def _xy(row):
    x, y = row.get('X'), row.get('Y')
    if x in (None, '') or y in (None, ''):
        return None
    point = float(x), float(y)
    return point if all(math.isfinite(v) for v in point) else None


def load_match(metadata_path, tracking_path, config):
    metadata = ET.parse(metadata_path).getroot()
    general = metadata.find('.//General').attrib
    pitch = metadata.find('.//Environment').attrib
    length, width = float(pitch['PitchX']), float(pitch['PitchY'])
    home, away = general['HomeTeamId'], general['GuestTeamId']
    if home == away or not all(math.isfinite(v) and v > 0 for v in (length, width)):
        raise ValueError('invalid team/pitch metadata')
    sides = {home: 'H', away: 'A'}
    players = {p.get('PersonId'): t.get('TeamId') for t in metadata.findall('.//Team')
               for p in t.findall('.//Player')}
    balls, ranges, anchors, sets = {}, {}, {}, set()
    # First pass validates all object timelines and reads ball observations.
    for group in _groups(tracking_path):
        period = SECTIONS.get(group.get('GameSection'))
        team, person = group.get('TeamId'), group.get('PersonId')
        if period is None or group.get('MatchId') != general['MatchId']:
            raise ValueError('unknown period or mismatched match')
        if team not in (*sides, 'BALL', 'referee'):
            raise ValueError('unknown tracked team')
        if team in sides and players.get(person) != team:
            raise ValueError('player metadata/team mismatch')
        key = (period, team, person)
        if key in sets:
            raise ValueError('duplicate object period')
        sets.add(key)
        previous = -1
        for row in group:
            frame = int(row.get('N'))
            if frame <= previous:
                raise ValueError('duplicate or unordered raw frame')
            previous = frame
            timestamp = datetime.fromisoformat(row.get('T'))
            if period not in anchors:
                anchors[period] = frame, timestamp
            n0, t0 = anchors[period]
            if abs((timestamp - t0).total_seconds() - (frame - n0) / 25) > 0.002:
                raise ValueError('timestamp/frame alignment is not 25 Hz')
            if team == 'referee':
                continue
            lo, hi = ranges.get(period, (frame, frame))
            ranges[period] = min(lo, frame), max(hi, frame)
            if team == 'BALL':
                ball_key = (period, frame)
                if ball_key in balls:
                    raise ValueError('duplicate ball frame')
                status, possession = row.get('BallStatus'), row.get('BallPossession')
                if status not in (None, '', '0', '1') or possession not in (None, '', '0', '1', '2'):
                    raise ValueError('unknown ball reference code')
                reference = ('D' if status == '0' else
                             {'1': 'H', '2': 'A'}.get(possession) if status == '1' else None)
                balls[ball_key] = _xy(row), reference
    if not ranges:
        raise ValueError('empty tracking')
    evidence, references, blocks, offsets, raw_ranges = [], [], [], {}, []
    tolerance = config['pitch_tolerance']
    for period, (lo, hi) in sorted(ranges.items()):
        first = len(evidence)
        offsets[period] = first - lo
        blocks.append((period, first, first + hi - lo))
        raw_ranges.append({'half': period, 'first_raw': lo, 'last_raw': hi, 'frames': hi-lo+1})
        for frame in range(lo, hi + 1):
            ball, target = balls.get((period, frame), (None, None))
            outside = ball is not None and (abs(ball[0]) > length*(0.5+tolerance)
                                            or abs(ball[1]) > width*(0.5+tolerance))
            evidence.append({'candidate': None, 'outside': outside, 'ball_seen': ball is not None,
                             'ball_xy': (ball[0]/length+0.5, ball[1]/width+0.5) if ball else None,
                             'players_seen': 0, 'stationary_set_piece': False,
                             'nearest_distance_m': {'H': math.inf, 'A': math.inf},
                             'timestamp_s': (frame - lo) / 25.0})
            references.append(target)
    # Second pass consumes only positions and metadata. Reference labels are separate.
    for group in _groups(tracking_path):
        team = group.get('TeamId')
        if team not in sides:
            continue
        period, side = SECTIONS[group.get('GameSection')], sides[team]
        for row in group:
            frame = int(row.get('N'))
            point = _xy(row)
            if point is None:
                continue
            item = evidence[frame + offsets[period]]
            item['players_seen'] += 1
            ball = balls.get((period, frame), (None, None))[0]
            if ball is not None:
                item['nearest_distance_m'][side] = min(item['nearest_distance_m'][side], math.dist(point, ball))
    assign_candidates(evidence, config['control_distance_m'], config['opponent_margin_m'])
    add_ball_motion_evidence(evidence, blocks, (length, width))
    if (config.get('stationary_unattended_frames') is not None
            or config.get('stationary_observed_frames') is not None):
        from model.stoppage import add_stoppage_evidence
        add_stoppage_evidence(evidence, blocks, config, (length, width))
    audit = {'frames': len(evidence), 'fps': 25, 'raw_ranges': raw_ranges,
             'ball_missing_frames': sum(not r['ball_seen'] for r in evidence),
             'no_players_frames': sum(r['players_seen'] == 0 for r in evidence),
             'reference_counts': dict(Counter(r or 'unknown' for r in references)),
             'metadata_sha256': digest(metadata_path), 'tracking_sha256': digest(tracking_path)}
    return {'id': general['MatchId'], 'home': general['HomeTeamName'],
            'away': general['GuestTeamName'], 'date': general['KickoffTime'].split('T')[0],
            'evidence': evidence, 'reference': references, 'blocks': blocks, 'audit': audit}


def _metrics(confusion, unknown):
    eligible = sum(sum(row.values()) for row in confusion.values())
    correct = sum(confusion[c][c] for c in 'HAD')
    live = sum(sum(confusion[c].values()) for c in 'HA')
    live_correct = sum(confusion[c][c] for c in 'HA')
    abstentions = sum(confusion[c]['X'] for c in 'HAD')
    f1 = {}
    for c in 'HAD':
        tp = confusion[c][c]
        fp = sum(confusion[other][c] for other in 'HAD' if other != c)
        fn = sum(confusion[c][other] for other in 'HADX' if other != c)
        f1[c] = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0
    return {'confusion': confusion, 'unknown': unknown, 'eligible': eligible, 'correct': correct,
            'accuracy': correct/eligible if eligible else None, 'class_f1': f1,
            'macro_f1': sum(f1.values())/3, 'live_frames': live, 'live_correct': live_correct,
            'live_accuracy': live_correct/live if live else None,
            'abstentions': abstentions,
            'prediction_coverage': 1-abstentions/eligible if eligible else None}


def score_labels(labels, reference):
    """Exact H/A/D reference accuracy; X counts as an error on known frames."""
    if len(labels) != len(reference):
        raise ValueError('prediction/reference length mismatch')
    confusion = {c: {p: 0 for p in 'HADX'} for c in 'HAD'}
    unknown = 0
    for label, target in zip(labels, reference):
        if label not in ('H', 'A', 'D', 'X') or target not in ('H', 'A', 'D', None):
            raise ValueError('invalid label/reference')
        if target is None:
            unknown += 1
        else:
            confusion[target][label] += 1
    return _metrics(confusion, unknown)


def merge_scores(scores):
    confusion = {c: {p: sum(s['confusion'][c][p] for s in scores) for p in 'HADX'} for c in 'HAD'}
    return _metrics(confusion, sum(s['unknown'] for s in scores))
