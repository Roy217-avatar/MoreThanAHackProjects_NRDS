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
It has an external provider-agreement diagnostic on nineteen SkillCorner matches, but no independent
human-labeled validation or demonstrated competition-score gain over the official baseline.
See [data audit](docs/DATA_AUDIT.md), [tasks](TASKS.md), and verification records in `docs/verification/`.

## External-match comparison (TASK-006)

`model/compare_skillcorner.py` maps public SkillCorner 10 fps broadcast tracking to the same
evidence contract. It scales only the frame-count durations from 25 fps to 10 fps; pitch distances
stay in metres. The TASK-006 comparison used fixed v2 settings. The comparison uses
SkillCorner's automatic per-frame possession field and its
in-play phase intervals as **provider references**, not verified ground truth. Gaps in either
reference are unknown, not dead-ball labels. The output contains aggregate counts and input
fingerprints only; no tracking or frame-level prediction export is committed.

Download the ten public matches at the pinned SkillCorner revision and run the exact commands in
[`docs/verification/TASK-006.md`](docs/verification/TASK-006.md). The aggregate result is
[`docs/verification/TASK-006-results.json`](docs/verification/TASK-006-results.json). This is
not the official `spellF1` scorer, and its agreement figures must not be used to claim a higher
challenge ranking. The comparison makes no parameter choice and uses no challenge public labels.

## Experimental external-tuned variant (TASK-010)

`model/tune_skillcorner.py` searched 144 configurations on the ten TASK-006 matches.
It selected `model/config_v3.json`; a separately tested offline control-backfill rule is
recorded in `model/config_v4.json`. Nine additional SkillCorner matches were held out
until v4 was frozen. On their available provider team labels, v4 agreed on 82.94% of
frames, versus 82.64% for v2; on provider live-phase frames, agreement was 88.72%.
The requested roughly 90% per-frame agreement was not reached. These are noisy-provider
comparisons, not official competition accuracy or `spellF1`.

The v4 rule backfills H/A to the first frame of a sustained candidate run **only after**
that run confirms control. Brief opposing touches remain with the last controlling team;
the backfill requires an uninterrupted run (`evidence_gap_frames: 0`), and dead-ball and
halftime boundaries reset pending evidence. V1 and v2 retain their earlier
behavior. The official baseline and evaluator remain unchanged. The tuned variant may
transfer differently from 10 fps broadcast tracking to 25 fps tactical tracking, so it
is an experimental option rather than a proven final selection. Commands, source split,
input hashes, BAR-ATH v4 output validation and limitations are in
[`docs/verification/TASK-010.md`](docs/verification/TASK-010.md).

## Additional sources and external tuning (TASK-012)

The [ten-source catalog](docs/POSSESSION_DATA_RESEARCH.md) distinguishes usable tracking
and possession references from sparse events, gated data and tracking-only resources.
Seven new IDSSE/Sportec matches were used in a fixed five-development/two-test split.
`model/external_idsse.py` maps their 25 Hz XML into evidence while keeping provider
possession/live-dead fields exclusively in scoring references. `model/tune_idsse.py`
searched 128 settings and saved the candidate in `model/config_v5_external.json`.

On the two reserved matches, full H/A/D reference accuracy was **64.09%**, versus
**63.75% for v4**; live-team agreement was **88.08%**, versus **87.69%**. The >95%
target was not achieved. Dead-ball recall was 30.01%, and candidate intervals were
more fragmented. V5 is an experimental artifact, with no demonstrated challenge
ranking gain. The earlier configurations and inference implementation are preserved.

The [methods and accuracy report](docs/verification/TASK-012.md) contains match dates
and teams, exact counts/formulas, download and execution commands, hashes and limitations.
The candidate tactical CSV is ignored at `evaluation/results/temporal_v5_external.csv`;
it passed the official format validator and repeat generation matched byte for byte.

## Observed unattended stoppage candidate (TASK-013)

`model/config_v6_stoppage.json` keeps the v4 control settings and adds an optional
dead-ball cue. When the ball remains within a 0.5 m area for two seconds and the
nearest observed player on **each** team stays at least 3 m away, the confirmed
interval becomes D. It is computed within each half, needs actual ball and player
observations, and cannot bridge missing frames. After D, the model waits for
confirmed control before assigning H or A. This addresses a specific failure mode
where a stationary, unattended ball remained assigned to a team during a stoppage.

The [TASK-013 record](docs/verification/TASK-013.md) contains the external development
diagnostic and tactical output checks. The new artifact is
`evaluation/results/temporal_v6_stoppage.csv` (ignored).

On five already-used IDSSE development matches, full H/A/D provider agreement rose
from 63.72% to 80.92%, while live-team agreement fell from 83.74% to 81.87% and
transitions increased. These are exploratory diagnostics, not independent test
results or evidence of a better competition ranking.

Run the tactical candidate with:

```bash
.venv/bin/python model/run.py --config model/config_v6_stoppage.json \
  --output evaluation/results/temporal_v6_stoppage.csv \
  --diagnostics evaluation/reports/temporal_v6_stoppage_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v6_stoppage.csv
```
