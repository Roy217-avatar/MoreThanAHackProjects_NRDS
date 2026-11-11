# More than a Hack 2027 possession project

The official public starter, scorer, four baseline CSVs, and challenge documents are copied from
[`metrica-sports/more-than-a-hack-2027`](https://github.com/metrica-sports/more-than-a-hack-2027)
at commit `f8f2629ff1e0985f81d7e59d8413678514ee1530`. `games.py`, `starter/`, and
`evaluation/` are unmodified upstream code and supplied predictions. Local work is in `model/`,
`tests/`, `TASKS.md`, and `docs/`.

## Setup and public baseline check

Run from this directory. Python 3.9 or later is recommended. The pinned lock reflects the tested
environment; `requirements.txt` remains the upstream dependency list.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
baseline_dir=$(mktemp -d)
cp evaluation/results/baseline_*.csv "$baseline_dir/"
.venv/bin/python evaluation/run_evaluation.py --results "$baseline_dir" --out "$baseline_dir" --no-detail
.venv/bin/python -m unittest discover -s tests -v
```

The isolated scorer command reads only the four included baseline CSVs and the public five-minute
ground truth. The public window checks the pipeline and must never select model parameters or variants. The full
match score is private. The default results directory can contain local model CSVs, so use the
isolated directory for a baseline-only run.

## Match assets and generation

The gated assets are not tracked. Place the authorized bundle under `data/`, or set
`MTAH_DATA_DIR` to its root, containing `tactical/BAR-ATH_tactical_atd.xml` and `.txt`.
The model also requires `tactical/BAR-ATH_tactical_smart_tagging.xml`.
Do not commit the bundle or generated frame-level outputs.

```bash
export MTAH_DATA_DIR=/absolute/path/to/authorized/bundle
.venv/bin/python -c 'from starter.load_atd import check_alignment_raw; print(check_alignment_raw())'
.venv/bin/python starter/baseline.py --out evaluation/generated_baseline
.venv/bin/python evaluation/validate_submission.py evaluation/generated_baseline/baseline_smooth50.csv
.venv/bin/python model/run.py --config model/config_v2.json --output evaluation/results/temporal_v2.csv --diagnostics evaluation/reports/temporal_v2_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v2.csv
shasum -a 256 evaluation/results/temporal_v2.csv
```

Repeat generation to a second output path with identical inputs and config, then compare the two
hashes. Diagnostics are separate from the two-column prediction. Input file hashes should be
recorded alongside the run. The model uses no random seed. `model/config.json` preserves the
earlier v1 behavior and output; see `docs/verification/TASK-005.md`.

## Prototype behavior

`model/evidence.py` loads ATD and automatic tags into strict zero-based frame records;
`model/inference.py` applies the temporal state machine; `model/temporal.py` serializes labels and
separate reason-code diagnostics. The interface is in `docs/INTERFACE.md`.
`model/config_v2.json` records all thresholds and enables offline set-piece backfill. Per frame,
the model measures distances from the ball to the nearest observed player of each team after
scaling normalized pitch coordinates to metres.
A candidate must be within 2 m of the ball and at least 0.75 m nearer than the other team's closest
player. Twelve observed candidate frames are needed to establish or transfer control; gaps up to
five frames do not discard accumulated evidence. Missing ball observations never imply dead play.
An out-of-bounds ball sustained for 25 frames yields `D`. A ball observed within a 0.5 m
region for 25 frames during an automatic set-piece tag also yields `D`; a tag by itself is never
copied into the labels. In v2, once that full observed stationary window is confirmed, its earlier
frames are also labeled `D`. Short, interrupted, unobserved, and halftime-crossing windows are not
backfilled. A restart needs confirmed control.
Each half resets independently; outside the graded half blocks output is `X`.

These are general, conservative engineering defaults, **not fitted parameters**. The prototype
uses only set-piece tags from the automatic tagging; it does not yet use homography, team motion,
or video. In particular, it will miss many stoppages whose ball is missing rather than tracked
outside the pitch or stationary in a set-piece interval, and it can delay fast turnovers.
It has an external provider-agreement diagnostic on ten SkillCorner matches, but no independent
human-labeled validation or demonstrated competition-score gain over the official baseline.
See [data audit](docs/DATA_AUDIT.md), [tasks](TASKS.md), and verification records in `docs/verification/`.

## External-match comparison (TASK-006)

`model/compare_skillcorner.py` maps public SkillCorner 10 fps broadcast tracking to the same
evidence contract. It scales only the frame-count durations from 25 fps to 10 fps; pitch distances
stay in metres. The original tactical model, configuration, official baseline and evaluator are
unchanged. The comparison uses SkillCorner's automatic per-frame possession field and its
in-play phase intervals as **provider references**, not verified ground truth. Gaps in either
reference are unknown, not dead-ball labels. The output contains aggregate counts and input
fingerprints only; no tracking or frame-level prediction export is committed.

Download the ten public matches at the pinned SkillCorner revision and run the exact commands in
[`docs/verification/TASK-006.md`](docs/verification/TASK-006.md). The aggregate result is
[`docs/verification/TASK-006-results.json`](docs/verification/TASK-006-results.json). This is
not the official `spellF1` scorer, and its agreement figures must not be used to claim a higher
challenge ranking. The comparison makes no parameter choice and uses no challenge public labels.
