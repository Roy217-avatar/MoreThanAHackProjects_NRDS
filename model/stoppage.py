"""Observed stationary, unattended ball as conservative stoppage evidence."""
import math


def add_stoppage_evidence(evidence, blocks, config, pitch):
    duration = config.get('stationary_unattended_frames')
    for row in evidence:
        row['stationary_unattended'] = False
        row['stationary_observed'] = False
    if duration is not None:
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

    observed_duration = config.get('stationary_observed_frames')
    if observed_duration is None:
        return
    observed_radius = config['stationary_observed_radius_m']
    freeze_epsilon = config['tracking_freeze_epsilon_m']
    for _, first, last in blocks:
        window = []
        for frame in range(first, last + 1):
            row = evidence[frame]
            distances = row['nearest_distance_m']
            if (row['ball_xy'] is None or row['outside'] or row['players_seen'] == 0
                    or not all(math.isfinite(distances[team]) for team in ('H', 'A'))):
                window = []
                continue
            window.append((frame, row['ball_xy'], dict(distances)))
            if len(window) > observed_duration:
                window.pop(0)
            if len(window) != observed_duration:
                continue
            xs = [(xy[0] - window[0][1][0]) * pitch[0] for _, xy, _ in window]
            ys = [(xy[1] - window[0][1][1]) * pitch[1] for _, xy, _ in window]
            if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) > observed_radius:
                window = [window[-1]]
                continue
            coordinated_freeze = all(
                max(item[2][team] for item in window) - min(item[2][team] for item in window)
                <= freeze_epsilon for team in ('H', 'A'))
            if not coordinated_freeze:
                for index, _, _ in window:
                    evidence[index]['stationary_observed'] = True
