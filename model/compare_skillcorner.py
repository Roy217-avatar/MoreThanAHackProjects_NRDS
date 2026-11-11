"""Compare fixed temporal inference with public SkillCorner provider fields.

This is an aggregate external diagnostic, not the official challenge evaluator.
It writes no frame-level labels or tracking data.
"""

import argparse
import hashlib
import json
from pathlib import Path

from model.external_skillcorner import evaluate_match
from model.temporal import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--match-ids", required=True, nargs="+", type=int)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if len(set(args.match_ids)) != len(args.match_ids):
        parser.error("match IDs must be unique")
    config = load_config(args.config)
    results = []
    for match_id in args.match_ids:
        folder = args.data_root / str(match_id)
        result = evaluate_match(folder / "{}_match.json".format(match_id),
                                folder / "{}_tracking_extrapolated.jsonl".format(match_id),
                                folder / "{}_phases_of_play.csv".format(match_id),
                                config)
        if result["id"] != match_id:
            raise ValueError("metadata ID disagrees with requested match ID")
        results.append(result)

    def aggregate(key):
        counts = {name: sum(item[key][name] for item in results)
                  for name in ("reference_team_frames", "reference_missing_frames",
                               "team_prediction_frames", "matching_team_frames")}
        reference = counts["reference_team_frames"]
        covered = counts["team_prediction_frames"]
        matched = counts["matching_team_frames"]
        counts.update({"agreement_all_reference": matched / reference if reference else None,
                       "agreement_when_team_predicted": matched / covered if covered else None,
                       "team_prediction_coverage": covered / reference if reference else None})
        return counts

    payload = {"source": "SkillCorner/opendata",
               "source_revision": "4340d274572876239c154c90bc507a9b3250a656",
               "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
               "matches": results, "total": aggregate("temporal"),
               "instantaneous_total": aggregate("instantaneous_proximity"),
               "live_phase_total": aggregate("live_phase"),
               "instantaneous_live_phase_total": aggregate("instantaneous_live_phase")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("compared", len(results), "matches; provider team frames",
          payload["total"]["reference_team_frames"])
    print("temporal agreement", payload["total"]["agreement_all_reference"])
    print("output", args.output)


if __name__ == "__main__":
    main()
