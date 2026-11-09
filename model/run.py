"""Generate the temporal prototype from the official tactical ATD."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.temporal import run  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.path.join(ROOT, "model", "config.json"))
    parser.add_argument("--output", default=os.path.join(ROOT, "evaluation", "results", "temporal_v1.csv"))
    parser.add_argument("--diagnostics", default=os.path.join(ROOT, "evaluation", "reports", "temporal_v1_diagnostics.csv"))
    args = parser.parse_args()
    run(args.config, args.output, args.diagnostics)
