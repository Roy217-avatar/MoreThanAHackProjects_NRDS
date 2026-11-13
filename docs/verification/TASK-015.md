# TASK-015 — Dead-ball generalization and grouped development evaluation

Date: 2026-11-12  
Code base before work: `2dadaf6a531ac287e26317cb6272fa44e64be7e6`  
Official challenge revision: `f8f2629ff1e0985f81d7e59d8413678514ee1530`

Environment: Python 3.9.6, NumPy 2.0.2, pandas 2.3.3; the complete pinned environment is
`requirements-lock.txt` at SHA-256
`a3c002eb810057e3b0e64c89b5e0dc7cfe570d53f40aec4df19df78ab500a9ff`. The pipeline has no
random component (`seed: null`).

## Outcome

The frozen v8 candidate adds a general observed-stationary-ball cue while retaining v7's
controlling-team logic. On seven previously inspected IDSSE development matches, its pooled
H/A/D agreement is **88.55%**, official `spell_f1_mean` is **0.4785**, and dead-ball recall is
**96.82%**. The match-grouped out-of-fold model-selection estimate is **88.77%** agreement and
**0.4841** spellF1. These are development/provider-reference results, not independent accuracy
and not an official challenge score. No untouched compatible match remains, so the requested
85% independent claim is **unverified**.

The candidate challenge CSV has 199,319 ordered rows, passed the official format validator, and
two generations matched SHA-256
`97bf92b0c189c01d0b27b5bce897e3f5713ea5904cdb6b3edd524d0b29a0ff19`.

## Dataset roles and leakage controls

`model/dataset_manifest_v8.json` assigns every collected source before the v8 experiment:

- Seven complete 25 Hz IDSSE/Sportec matches are development groups. A fold holds out an entire
  match; frames and windows are never randomly divided.
- The WCSF match is a historical benchmark because TASK-014 already inspected its result.
- Nineteen SkillCorner matches are previously inspected, use incomplete/noisy provider fields,
  and are excluded from v8 selection.
- The BAR–ATH public five-minute labels remain pipeline-check-only and were not opened by this
  experiment.
- The untouched-final-test list is empty. There are no known duplicate IDSSE recordings; the
  match ID is the indivisible group.

No preprocessing is learned. Coordinates are converted to metres only for distance and motion;
temporal state and confirmed windows reset at each half. The candidate grid, safeguards, metric
order, and 12-run budget were frozen in `model/v8_protocol.json` before evaluation. There was no
adaptive second grid.

## Metric definitions

- **H/A/D agreement** is correct H, A, or D divided by all provider-graded H/A/D frames. An X on
  a graded frame is an error.
- **Controlling-team agreement on ground-truth live frames** (`team_acc_gt_alive`) counts dead or
  X predictions on a live reference frame as errors.
- **Conditional live-team agreement** (`team_acc_both_alive`) compares H versus A only where both
  reference and prediction are live. It can remain high while dead/live mistakes are poor.
- **spellF1** is the unchanged official implementation in `evaluation/possession_metrics.py`,
  pooled without joining spells across match or half boundaries. `spell_f1_mean` is the mean over
  its official IoU thresholds; the 0.5-IoU headline is also retained in the JSON report.
- Confusion matrices below use **rows = reference H, A, D, X** and **columns = predicted H, A, D,
  X**.

The historical WCSF estimate is arithmetically correct: it had 27,027 correct live-team frames,
30,582 reference-live frames, 26,792 D frames, and 57,374 graded frames. Reaching 85% with live
correct unchanged would require `ceil(.85 × 57,374) - 27,027 = 21,741` correct D frames, or
**81.15% D recall**, 4,892 more than its historical 16,849. That is a diagnostic counterfactual,
not a guaranteed route or a tuning target; WCSF was excluded from v8 development.

## Baseline reproduction and diagnosis

The v7 baseline was reproduced on all seven IDSSE matches with the same evaluator used for v8:

| Metric | v7 |
| --- | ---: |
| Graded frames | 1,002,644 |
| Pooled H/A/D agreement | 84.11% |
| Macro mean per-match agreement | 84.08% |
| `spell_f1_mean` | 0.4432 |
| Macro-F1 | 0.8327 |
| D precision / recall | 91.37% / 85.94% |
| Strict live-team agreement | 82.62% |
| Conditional live-team agreement | 88.51% |

Baseline confusion matrix:

```text
              predicted H       A       D     X
reference H        245886   29802   18025   218
reference A         29514  211069   18469   122
reference D         30361   32833  386343     2
reference X             0       0       0    14
```

There were 63,196 dead frames predicted live and 36,494 live frames predicted dead. Of the false
dead frames, 35,806 were retained in `awaiting_restart`, showing that delayed restart release was
the dominant false-dead mechanism. Twenty-one reference dead segments were entirely missed. The
baseline detected dead onset 42.1 frames late on average and release 83.5 frames late on average.
The large 59,316 H/A confusion count also confirms that dead-ball detection is not the only error
source.

## Implementation

- `model/motion.py` supplies causal speed and acceleration from actual timestamp differences. It
  never bridges a missing ball observation or a half boundary and rejects non-increasing time.
- All relevant adapters now expose timestamps, and 25-to-10 Hz scaling includes the new duration.
- `model/stoppage.py` can confirm a stationary observed ball even when players remain nearby. A
  window must have valid ball and both-team player-distance observations, remain inside the pitch,
  and stay within 0.5 m for 75 frames (3 s at 25 Hz). The confirmed window is backfilled only
  inside its half. Exact coordinated freezes in both nearest-team distance signals suppress this
  cue. Missing tracking never implies D.
- `model/inference.py` supports independently configurable restart confirmation and motion gating.
  Those variants were evaluated, but are not enabled in frozen v8.
- `model/cross_validate_v8.py` validates the manifest and hashes, performs whole-match
  leave-one-out candidate selection, uses the official scorer, records class metrics, boundaries,
  runtimes and input fingerprints, and writes aggregate-only results.

Inference is **offline** because confirmed stationary and control windows may backfill earlier
frames. The configured stationary cue therefore has up to 3 s lookahead. It never crosses
halftime. Ball speed itself is causal, but the frozen candidate does not use the speed-gated
restart option.

## Controlled experiment

The safeguard allowed no more than a 0.5 percentage-point loss versus v7 in either overall H/A/D
agreement or conditional live-team agreement. Selection ranked eligible candidates by official
spellF1, then macro-F1, then agreement.

| Candidate/ablation | H/A/D | spellF1 | both-live team | D recall |
| --- | ---: | ---: | ---: | ---: |
| v7 baseline | 84.11% | 0.4432 | 88.51% | 85.94% |
| restart 3, speed 0.2 | 89.42% | 0.5112 | 87.96% | 92.29% |
| observed stationary 50 | 88.55% | 0.4780 | 88.48% | 97.43% |
| **observed stationary 75 (frozen)** | **88.55%** | **0.4785** | **88.54%** | **96.82%** |
| observed stationary 100 | 88.47% | 0.4767 | 88.54% | 96.56% |
| combined restart 3 + observed 50 | 91.21% | 0.5215 | 87.82% | 97.25% |
| combined restart 3 + observed 75 | 91.15% | 0.5220 | 87.91% | 96.67% |

The 91% combined results are all-development comparisons and violate the predeclared
controlling-team tolerance, so they were not selected. Six of seven outer folds selected
`observed75`; one selected `restart3_motion02`. The merged held-out-fold predictions scored 88.77%
agreement, 0.4841 spellF1, and 88.37% conditional live-team agreement.

Frozen v8 confusion matrix:

```text
              predicted H       A       D     X
reference H        242903   29460   21350   218
reference A         29131  209712   20209   122
reference D          7380    6925  435232     2
reference X             0       0       0    14
```

Live/dead collapse, rows reference and columns prediction:

```text
                     predicted live   predicted D   predicted X
reference live               511206         41559           340
reference D                   14305        435232             2
```

| Match (date; home—away) | v7 H/A/D | v8 H/A/D | v8 spellF1 | v8 D recall |
| --- | ---: | ---: | ---: | ---: |
| J03WMX (2023-05-27; Köln—Bayern) | 86.85% | 89.30% | 0.4628 | 96.56% |
| J03WN1 (2023-05-27; Bochum—Leverkusen) | 80.65% | 87.45% | 0.4333 | 97.50% |
| J03WOH (2022-08-26; Düsseldorf—Regensburg) | 83.90% | 88.79% | 0.4991 | 97.06% |
| J03WOY (2022-09-10; Düsseldorf—Rostock) | 83.64% | 87.04% | 0.4743 | 96.21% |
| J03WPY (2022-10-15; Düsseldorf—Nürnberg) | 85.15% | 88.85% | 0.4657 | 97.27% |
| J03WQQ (2022-11-05; Düsseldorf—St. Pauli) | 82.97% | 88.57% | 0.5249 | 96.28% |
| J03WR9 (2022-11-11; Düsseldorf—Kaiserslautern) | 85.41% | 89.80% | 0.4984 | 96.70% |

Frozen v8 class precision/recall/F1 is H 86.93/82.64/84.73%, A 85.22/80.92/83.01%, and D
91.28/96.82/93.97%. It predicts 1,977 spells for 3,061 reference spells (fragmentation ratio
0.702). Fourteen dead segments remain entirely missed. Among 699 detected dead segments, onset is
19.0 frames late on average; release is 114.0 frames late on average. Release timing is the next
major temporal issue.

The report's inference-only runtime was 0.25 s for 1,002,644 v8 frames after features were built.
IDSSE load/feature preparation took 135.3 s; the complete 12-candidate command took roughly three
minutes on this machine. Each full 199,319-frame tactical generation took about 4.7 s. These are
single local observations, not benchmarks.

## Tactical artifact verification

Input SHA-256:

```text
f130e350d2bfdf734b7e32f072931fccc6d015c1e837d082064875fe0a700431  BAR-ATH_tactical_atd.txt
327e35e32e46a647389b88f883d4f9a2ab931e3e6148aef2fcf8f22b1e93c43a  BAR-ATH_tactical_atd.xml
0594d35e3df01b9c5002372d8615e2e8ef5379ac8f4e84c5ef7a53f4304c9019  BAR-ATH_tactical_smart_tagging.xml
```

The exact v8 output contains H 75,339; A 70,868; D 12,460; X 40,652 and 431 adjacent label
transitions. It has exactly `frame,label`, 199,319 data rows, unique ordered frames 0–199318, and
only H/A/D/X. Diagnostics are separate. The repeat submission and diagnostic CSVs both matched
byte for byte. A v7 regression generation also matched its earlier SHA-256
`5637746fccb19822b17a377fad53f340e31cf8c047580bcadea68651e75e9e35`.

## Reproduction

```bash
# Baseline and grouped development experiment (authorized IDSSE files required)
.venv/bin/python -m model.cross_validate_v8 \
  --data-root data/external/idsse \
  --output docs/verification/TASK-015-development.json \
  --config-out model/config_v8.json

# Tests
.venv/bin/python -m unittest discover -s tests -v

# Tactical generation, deterministic repeat, and format validation
.venv/bin/python model/run.py --config model/config_v8.json \
  --output evaluation/results/temporal_v8.csv \
  --diagnostics evaluation/reports/temporal_v8_diagnostics.csv
.venv/bin/python model/run.py --config model/config_v8.json \
  --output evaluation/results/temporal_v8_repeat.csv \
  --diagnostics evaluation/reports/temporal_v8_repeat_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v8.csv
shasum -a 256 evaluation/results/temporal_v8*.csv
```

## Limitations and next task

- All seven IDSSE matches had been inspected in prior tasks. Grouped folds prevent frame leakage
  and estimate selection stability, but they do not restore pristine independence.
- Provider BallStatus/BallPossession fields are treated as references, not human-verified truth.
- The freeze safeguard uses exact nearest-distance constancy; more subtle coordinated tracking
  freezes may remain. Stationary live situations can still produce false D.
- Restart release remains delayed and short possession spells remain underproduced. A future
  candidate should learn or calibrate restart evidence inside new development matches while
  retaining a genuinely untouched multi-match final test.
- The development result exceeds 85%; **independent 85% accuracy remains unverified**. The exact
  missing input is several compatible, legally usable, labelled matches whose labels and metrics
  have never been inspected. Freeze the evaluation protocol before opening them and do not tune
  after final-test results are viewed.

Safe aggregate details, input fingerprints, all 12 candidates, per-match results and folds are in
`TASK-015-development.json`. The frozen artifact record is `model/v8_frozen.json`.
