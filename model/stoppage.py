"""Observed stationary, unattended ball as conservative stoppage evidence."""
import math


def add_stoppage_evidence(evidence, blocks, config, pitch):
    duration = config.get('stationary_unattended_frames')
    for row in evidence:
        row['stationary_unattended'] = False
    if duration is None:
        return
    radius = config['stationary_unattended_radius_m']
    minimum = config['stationary_unattended_min_player_m']
    for _, first, last in blocks:
        window = []
        for frame in range(first, last + 1):
            row = evidence[frame]
            ball = row['ball_xy']
            distances = row['nearest_distance_m']
            closest = min(distances.values())
            if (ball is None or row['outside'] or row['players_seen'] == 0
                    or not all(math.isfinite(distances[team]) for team in ('H', 'A'))
                    or closest < minimum):
                window = []
                continue
            window.append((frame, ball))
            if len(window) > duration:
                window.pop(0)
            if len(window) == duration:
                xs = [(xy[0] - window[0][1][0])*pitch[0] for _, xy in window]
                ys = [(xy[1] - window[0][1][1])*pitch[1] for _, xy in window]
                if math.hypot(max(xs)-min(xs), max(ys)-min(ys)) <= radius:
                    for index, _ in window:
                        evidence[index]['stationary_unattended'] = True
                else:
                    window = [window[-1]]
