"""Timestamp-aware causal ball-motion features shared by data adapters."""
import math


def add_ball_motion_evidence(evidence, blocks, pitch):
    """Add speed/acceleration without bridging missing frames or half boundaries."""
    for row in evidence:
        row['ball_speed_mps'] = None
        row['ball_acceleration_mps2'] = None
    for _, first, last in blocks:
        previous_speed = None
        for frame in range(first + 1, last + 1):
            previous = evidence[frame - 1]
            current = evidence[frame]
            before, after = previous['ball_xy'], current['ball_xy']
            if before is None or after is None:
                previous_speed = None
                continue
            dt = current['timestamp_s'] - previous['timestamp_s']
            if not math.isfinite(dt) or dt <= 0:
                raise ValueError('ball-motion timestamp must increase within each half')
            speed = math.hypot((after[0] - before[0]) * pitch[0],
                               (after[1] - before[1]) * pitch[1]) / dt
            current['ball_speed_mps'] = speed
            if previous_speed is not None:
                current['ball_acceleration_mps2'] = (speed - previous_speed) / dt
            previous_speed = speed
