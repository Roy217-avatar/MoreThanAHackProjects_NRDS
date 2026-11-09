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
.venv/bin/python evaluation/run_evaluation.py --no-detail
.venv/bin/python -m unittest discover -s tests -v
```

The scorer reads the four included baseline CSVs and the public five-minute ground truth. The
public window checks the pipeline and must never select model parameters or variants. The full
match score is private.

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
.venv/bin/python model/run.py --config model/config.json
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v1.csv
shasum -a 256 evaluation/results/temporal_v1.csv
```

Repeat the model generation and hash command with identical inputs and config to check byte
reproduction. `model/run.py` writes diagnostics to `evaluation/reports/temporal_v1_diagnostics.csv`;
those are separate from the two-column prediction. Input file hashes should be recorded alongside
the run. The model uses no random seed.

## Prototype behavior

`model/config.json` records all thresholds. Per frame, the model measures distances from the ball
to the nearest observed player of each team after scaling normalized pitch coordinates to metres.
A candidate must be within 2 m of the ball and at least 0.75 m nearer than the other team's closest
player. Twelve observed candidate frames are needed to establish or transfer control; gaps up to
five frames do not discard accumulated evidence. Missing ball observations never imply dead play.
An out-of-bounds ball sustained for 25 frames yields `D`. A ball observed within a 0.5 m
region for 25 frames during an automatic set-piece tag also yields `D`; a tag by itself is never
copied into the labels. A restart needs confirmed control.
Each half resets independently; outside the graded half blocks output is `X`.

These are general, conservative engineering defaults, **not fitted parameters**. The prototype
uses only set-piece tags from the automatic tagging; it does not yet use homography, team motion,
or video. In particular, it will miss many stoppages whose ball is missing rather than tracked
outside the pitch or stationary in a set-piece interval, and it can delay fast turnovers.
It has no external-match validation, so it has no demonstrated performance gain over the baseline.
See [data audit](docs/DATA_AUDIT.md), [tasks](TASKS.md), and verification records in `docs/verification/`.
