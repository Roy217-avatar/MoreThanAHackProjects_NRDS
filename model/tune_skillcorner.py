"""Search fixed temporal settings using external SkillCorner development matches.

Only the IDs supplied to this command are read. Run it on the predeclared
development matches, write the chosen config, then evaluate untouched holdouts
with model.compare_skillcorner. No challenge labels are accessed here.
"""

import argparse
import hashlib
import json
from itertools import product
from pathlib import Path

from model.external_skillcorner import (load_match, load_phase_reference,
                                        scale_config)
from model.inference import infer
from model.temporal import load_config


def assign_candidates(evidence, control_distance_m, opponent_margin_m):
    """Recompute tentative team evidence from cached metre distances in memory."""
    for row in evidence:
        nearest = row["nearest_distance_m"]
        home, away = nearest["H"], nearest["A"]
        winner = "H" if home < away else "A"
        closest = min(home, away)
        other = away if winner == "H" else home
        row["candidate"] = (winner if not row["outside"]
                            and closest <= control_distance_m
                            and other - closest >= opponent_margin_m else None)


def grid_configs(base):
    """Predeclared 144-setting spatial/temporal grid; all dead cues stay fixed."""
    configs = []
    for distance, margin, control, gap in product(
            (1.5, 2.0, 2.5, 3.0), (0.25, 0.5, 0.75, 1.0),
            (8, 12, 16), (0, 5, 10)):
        config = dict(base)
        config.update({"control_distance_m": distance,
                       "opponent_margin_m": margin,
                       "control_frames": control,
                       "evidence_gap_frames": gap})
        configs.append(config)
    return configs


def select_best(choices):
    """Rank exact team matches, then live-phase matches and conservative duration."""
    if not choices:
        raise ValueError("no tuning results")
    return min(choices, key=lambda item: (
        -item["team_matches"], -item["phase_matches"],
        -item["config"]["control_frames"],
        item["config"]["control_distance_m"],
        item["config"]["opponent_margin_m"],
        item["config"]["evidence_gap_frames"]))


def score_setting(matches, config):
    """Pool exact agreement over frames with provider H/A references."""
    counts = {name: 0 for name in ("team_matches", "team_frames",
                                  "team_prediction_frames", "phase_matches",
                                  "phase_frames", "phase_prediction_frames",
                                  "dead_on_live_phase_frames")}
    scaled = scale_config(config, 10)
    for match in matches:
        labels, _ = infer(match["evidence"], match["blocks"], scaled)
        for label, team, phase in zip(labels, match["reference"],
                                      match["phase_reference"]):
            if team in ("H", "A"):
                counts["team_frames"] += 1
                counts["team_matches"] += label == team
                counts["team_prediction_frames"] += label in ("H", "A")
            if phase in ("H", "A"):
                counts["phase_frames"] += 1
                counts["phase_matches"] += label == phase
                counts["phase_prediction_frames"] += label in ("H", "A")
                counts["dead_on_live_phase_frames"] += label == "D"
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--match-ids", required=True, nargs="+", type=int)
    parser.add_argument("--base-config", required=True, type=Path)
    parser.add_argument("--config-out", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if len(set(args.match_ids)) != len(args.match_ids):
        parser.error("development match IDs must be unique")
    if args.config_out.resolve() == args.base_config.resolve():
        parser.error("new configuration must not overwrite the base configuration")
    if args.config_out.resolve() == args.output.resolve():
        parser.error("configuration and report need separate paths")
    base = load_config(args.base_config)
    matches = []
    inputs = []

    def digest(path):
        sha = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha.update(chunk)
        return sha.hexdigest()

    for match_id in args.match_ids:
        folder = args.data_root / str(match_id)
        metadata = folder / "{}_match.json".format(match_id)
        tracking = folder / "{}_tracking_extrapolated.jsonl".format(match_id)
        phases = folder / "{}_phases_of_play.csv".format(match_id)
        evidence, blocks, reference, match = load_match(metadata, tracking, base)
        if match["id"] != match_id or match["status"] != "closed":
            raise ValueError("development match ID/status mismatch")
        phase_audit = {}
        phase_reference = load_phase_reference(phases, match, len(evidence),
                                               audit=phase_audit)
        matches.append({"evidence": evidence, "blocks": blocks,
                        "reference": reference, "phase_reference": phase_reference})
        inputs.append({"id": match_id, "frames": len(evidence),
                       "metadata_sha256": digest(metadata),
                       "tracking_sha256": digest(tracking),
                       "phase_sha256": digest(phases), "phase_audit": phase_audit})

    results = []
    configs = grid_configs(base)
    for distance in (1.5, 2.0, 2.5, 3.0):
        for margin in (0.25, 0.5, 0.75, 1.0):
            for match in matches:
                assign_candidates(match["evidence"], distance, margin)
            for config in configs:
                if (config["control_distance_m"] != distance
                        or config["opponent_margin_m"] != margin):
                    continue
                counts = score_setting(matches, config)
                results.append({"config": config, **counts})
    selected = select_best(results)
    chosen = dict(selected["config"])
    chosen["version"] = 3
    payload = {"source": "SkillCorner/opendata",
               "source_revision": "4340d274572876239c154c90bc507a9b3250a656",
               "development_match_ids": args.match_ids,
               "base_config_sha256": digest(args.base_config),
               "inputs": inputs, "candidates": results,
               "selected_config": chosen,
               "selected_counts": {k: value for k, value in selected.items()
                                   if k != "config"}}
    args.config_out.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.config_out.write_text(json.dumps(chosen, indent=2) + "\n")
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("development matches", len(matches), "candidates", len(results))
    print("selected", {name: chosen[name] for name in
                       ("control_distance_m", "opponent_margin_m",
                        "control_frames", "evidence_gap_frames")})
    print("provider agreement", selected["team_matches"], "/",
          selected["team_frames"])


if __name__ == "__main__":
    main()
