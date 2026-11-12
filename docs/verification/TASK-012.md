# TASK-012 — Additional data, tuning and accuracy calculations

Date: 2026-11-11. **The >95% target was not achieved.** On two new reserved
IDSSE matches, the frozen candidate achieved **64.09% full H/A/D accuracy against
provider references**, compared with **63.75% for v4**. On the subset whose reference
is live home/away possession, agreement was **88.08% versus 87.69%**.
These are external-reference comparisons, not the challenge's private accuracy or
official `spellF1`. V5 remains an experimental candidate; v4/v2 are preserved.

## 1. Research and data choice

[Ten-resource research catalog](../POSSESSION_DATA_RESEARCH.md) records links,
availability, contents and reasons for using or deferring each source. Only IDSSE
was used in this run. Seven additional matches were downloaded; this is not a claim
to have trained on ten datasets or ten new matches.

IDSSE supplies frame-level player/ball coordinates and possession/live-dead fields.
This avoids inventing dense reference labels from sparse event timestamps. We use
the provider fields as references; we did not establish that their label-generation
procedure is fully independent of tracking or equivalent to challenge annotation.
No events, videos or reference labels from the supplied Barcelona–Athletic match
were used for training, tuning, model choice or validation here.

## 2. Fixed split and method, in execution order

1. Read the existing model and previous external results. Check official rules:
   upstream remained `f8f2629ff1e0985f81d7e59d8413678514ee1530`. External games are
   allowed; the challenge public five minutes remain excluded from tuning.
2. Pin the IDSSE mirror to `a715a38dfbaf5f58e431727c2b78d174101a703c`.
   Record five development and two holdout IDs in `model/idsse_protocol.json`
   **before computing scores**. Entire matches stay together. Downloading a holdout
   does not expose it to the development command; a synthetic CLI test enforces this.
3. Audit and adapt the XML without reading its labels into features. Team IDs come
   from metadata; coordinates are centred metres; frame IDs and timestamps must
   agree at 25 Hz. Each half has an explicit raw-frame offset and an independent
   inference block. Missing raw indices remain explicit missing observations inside
   a half; the halftime gap is excluded and state resets. Duplicate, unordered,
   mismatched-match/team and misaligned timestamp inputs fail loudly.
4. References are `D` for `BallStatus=0`; otherwise `BallStatus=1` and possession
   1/2 map to H/A. Unknown live possession remains unknown, and never implies dead
   play. Coordinates and proximity alone feed inference. Perturbing reference flags
   in synthetic files leaves evidence and predictions unchanged.
5. Freeze a **128-configuration grid**: distance 1.5/2/2.5/3 m, opponent margin
   0.25/0.75 m, confirmation 4/8/12/20 frames, out-of-bounds 10/25/50/120 frames.
   The ranges cover tighter/looser proximity, 0.16–0.8 s control confirmation and
   0.4–4.8 s out-of-bounds confirmation. All other v4 settings stay fixed. No random
   search, random seed or supervised neural training is involved.
6. Rank by pooled development H/A/D exact accuracy, then macro F1, then stable grid
   order. Keep X as an error on every known reference frame. V4 itself is included
   in the grid, so comparison uses the same denominator and inputs.
7. Save the winning settings to `model/config_v5_external.json` before running the
   separate holdout command. It selected **1.5 m distance, 0.25 m margin, 4-frame
   control confirmation and 10-frame out-of-bounds confirmation**. Control backfill
   stays enabled with zero evidence gaps. Same-team passes/loose play retain the
   controlling team until opposing control is confirmed. This faster setting may
   mistake some short opposing touches for control.
8. Evaluate v4 and the frozen candidate on both reserved matches. Do not change
   settings in response to those scores. Generate a candidate tactical CSV, validate
   it, repeat generation, and inspect transitions/intervals as diagnostics.

## 3. Matches actually used

Dates and team names below come from the downloaded XML metadata, not guesses.
Accuracy includes H/A/D and errors on known reference frames; it is not just the
percentage of H/A frames on which the model chose to answer.

| Split | Match ID | Date | Home | Away | Frames | V4 accuracy | Candidate accuracy |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| Development | J03WMX | 2023-05-27 | 1. FC Köln | FC Bayern München | 145,967 | 71.48% | 72.94% |
| Development | J03WN1 | 2023-05-27 | VfL Bochum 1848 | Bayer 04 Leverkusen | 141,561 | 60.38% | 60.78% |
| Development | J03WOH | 2022-08-26 | Fortuna Düsseldorf | SSV Jahn Regensburg | 137,214 | 62.73% | 63.40% |
| Development | J03WOY | 2022-09-10 | Fortuna Düsseldorf | F.C. Hansa Rostock | 142,536 | 59.15% | 60.31% |
| Development | J03WPY | 2022-10-15 | Fortuna Düsseldorf | 1. FC Nürnberg | 146,211 | 64.57% | 65.64% |
| Holdout | J03WQQ | 2022-11-05 | Fortuna Düsseldorf | FC St. Pauli | 142,345 | 57.55% | 57.34% |
| Holdout | J03WR9 | 2022-11-11 | Fortuna Düsseldorf | 1. FC Kaiserslautern | 146,810 | 69.77% | 70.64% |

Total: **1,002,644 frames**. All seven files have ball positions, at least one
player observation and known H/A/D references at every evaluated index. This does
not establish that every player is always visible or that all positions are accurate.
Raw per-half ranges, input hashes and reference counts are in the aggregate JSONs.

## 4. How the accuracy is calculated

For reference-known frames `E`, with prediction `p` and reference `y`:

```text
full accuracy = sum(p[i] == y[i] for i in E) / len(E)
live agreement = matching H/A predictions on reference H/A frames / reference H/A frames
coverage = 1 - X predictions on reference-known frames / reference-known frames
F1(c) = 2 TP(c) / (2 TP(c) + FP(c) + FN(c))
macro F1 = (F1(H) + F1(A) + F1(D)) / 3
```

X contributes a false negative for the target class. D on a live reference counts
as an error. Unknown references are excluded and counted explicitly (zero in this
experiment). Counts are pooled across matches, so the average is weighted by frame
count rather than calculated as a simple average of rounded percentages.

| Measure | V4 | Frozen candidate |
| --- | ---: | ---: |
| Development exact correct / eligible | 454,615 / 713,489 = 63.72% | 461,448 / 713,489 = 64.67% |
| Holdout exact correct / eligible | 184,343 / 289,155 = 63.75% | 185,314 / 289,155 = 64.09% |
| Holdout live-team correct / live reference | 148,783 / 169,668 = 87.69% | 149,450 / 169,668 = 88.08% |
| Holdout H/A/D macro F1 | 62.17% | 62.49% |
| Holdout non-X coverage | 99.9595% | 99.9561% |

Full holdout improvement is **971 frames**, or **0.336 percentage points**. One of
the two matches became worse. We cannot claim a reliable general accuracy gain
from two matches with the same home team, or from this small pooled improvement.

The candidate's holdout confusion matrix is:

| Reference (rows) / Prediction (columns) | Predicted H | Predicted A | Predicted D | Predicted X |
| --- | ---: | ---: | ---: | ---: |
| H | 80,673 | 8,580 | 941 | 75 |
| A | 9,474 | 68,777 | 1,096 | 52 |
| D | 43,028 | 40,595 | 35,864 | 0 |

The diagonal gives `(80,673 + 68,777 + 35,864) / 289,155 = 64.0881%`.
The live calculation gives `(80,673 + 68,777) / 169,668 = 88.0838%`.
Dead-ball recall is only `35,864 / 119,487`, approximately **30.01%**.
This is the main measured limitation: proximity cannot reliably tell whether a ball
inside the pitch is live during stoppages. IDSSE has no automatic tactical set-piece
tags supplied to this adapter, so that model cue is unavailable. Feeding reference
`BallStatus` into inference would leak the answer and was deliberately excluded.

## 5. Why the target was not reached and what to do next

The data reveals a larger live/dead problem than a threshold problem. Candidate
holdout transitions rose from 614 to 1,093; minimum intervals fell to four frames.
The slightly higher exact agreement comes with much more fragmentation, which could
hurt the competition's spell metric. No official ranking improvement is claimed.
The tactical candidate has 548 reported possessions versus v4's 354 under the
validator's convention of treating X as a gap; this is a diagnostic, not ground truth.

The next useful model change is a separate live/dead evidence stage using observed
ball motion, player–ball relative motion, team motion and restart evidence, with
documented external development data. First obtain another independently measured
tracking/possession source (for example the WCSF sample, or PFF with access) and
reserve fresh matches before selecting features. These two IDSSE holdouts have now
been inspected and cannot serve as fresh test evidence for further tuning. Do not
keep changing thresholds against them to reach 95%.

## 6. Reproduce

Use the existing isolated environment, or create one using `requirements-lock.txt`.
Run from the project root. New adapter/tuner code uses only the Python standard library
and existing project modules. Downloads total approximately 2.5 GiB and remain ignored.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
mkdir -p data/external/idsse
revision=a715a38dfbaf5f58e431727c2b78d174101a703c
for match_id in J03WMX J03WN1 J03WOH J03WOY J03WPY J03WQQ J03WR9; do
  competition=000002
  case "$match_id" in J03WMX|J03WN1) competition=000001;; esac
  curl -sSL --fail --retry 3 \
    -o "data/external/idsse/$match_id.metadata.xml" \
    "https://huggingface.co/datasets/pysport/idsse-data/resolve/$revision/DFL_02_01_matchinformation_DFL-COM-${competition}_DFL-MAT-$match_id.xml" \
    -o "data/external/idsse/$match_id.tracking.xml" \
    "https://huggingface.co/datasets/pysport/idsse-data/resolve/$revision/DFL_04_03_positions_raw_observed_DFL-COM-${competition}_DFL-MAT-$match_id.xml" || exit 1
done
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m model.tune_idsse --stage tune \
  --data-root data/external/idsse --config-out model/config_v5_external.json \
  --output docs/verification/TASK-012-search.json
.venv/bin/python -m model.tune_idsse --stage evaluate \
  --data-root data/external/idsse --config model/config_v5_external.json \
  --output docs/verification/TASK-012-holdout.json
.venv/bin/python model/run.py --config model/config_v5_external.json \
  --output evaluation/results/temporal_v5_external.csv \
  --diagnostics evaluation/reports/temporal_v5_external_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v5_external.csv
.venv/bin/python model/run.py --config model/config_v5_external.json \
  --output /private/tmp/temporal_v5_external_repeat.csv \
  --diagnostics /private/tmp/temporal_v5_external_diagnostics.csv
cmp evaluation/results/temporal_v5_external.csv /private/tmp/temporal_v5_external_repeat.csv
```

The tactical commands require the authorized original bundle under `data/tactical/`
or `MTAH_DATA_DIR`, as documented in the README. They do not use the external XML files
as substitutes for challenge inputs. No public-window scorer was run for this task.

## 7. Verification evidence and provenance

Started from clean project commit `b324585f0b28fc4abf5e59eb24f8581000c7e23c`;
new/modified working-tree files are recorded in TASKS.md and this report. Source file
SHA-256 values are embedded in both aggregate JSONs; input/configuration/protocol
hashes are included as well. Environment: Python 3.9.6, numpy 2.0.2, pandas 2.3.3,
python-dateutil 3.0.0, pytz 2026.6, six 1.17.0, tzdata 2026.6. No added dependencies.

The 64-test suite passed, including new adapter, metric, split-isolation and CLI tests.
The official validator accepted the tactical candidate: exactly `frame,label`, 199,319
rows, ordered frames 0–199318, legal H/A/D/X labels. Counts: H 77,548; A 67,623;
D 13,456; X 40,692 (including frames outside official half blocks).

The entire development search was repeated: all 128 candidate metrics and the
selected configuration matched. A malformed-label validation fix landed during the
first search, so the second report records the final source fingerprints; only that
provenance field differed. The delivered search report contains final-code hashes.
The holdout report and tactical CSV each repeated byte for byte. All seven tracking
hashes matched the mirror's published LFS SHA-256 values. Source inputs remain ignored.

| Artifact | SHA-256 |
| --- | --- |
| `model/idsse_protocol.json` | `fd190defbb77021af46bfad80235287b0ea4e5b4fc773a5e765eca42877e2399` |
| `model/config_v5_external.json` | `c12ddb6cbeae0fd8a7a177d2e43d84c5832fef0f910b9460e43b9dc8483b71b4` |
| `TASK-012-search.json` | `e6826424fc0c1148851691787d9d8e3083a3138149a4fa5e48181a69b7618d71` |
| `TASK-012-holdout.json` | `25e0ebe8e41ee6060f9e8d5c32d4e370721c6a8f7fb0f9d35b7845af8912b9fe` |
| `evaluation/results/temporal_v5_external.csv` | `c896d3548af7f608491626a5c3815f91ad8b219c3c543bbb33aafef12763a999` |

Additional tactical diagnostics inside official halves: 616 label transitions,
478 direct H/A changes, 618 intervals; minimum/median/maximum duration
0.16 / 3.84 / 222.28 seconds. Both halves reset independently. Differences between
these counts and validator possessions follow their different counting conventions.

Repeat the aggregate checks with:

```bash
.venv/bin/python -m model.tune_idsse --stage tune --data-root data/external/idsse \
  --config-out /private/tmp/idsse_v5_repeat.json --output /private/tmp/idsse_search_repeat.json
cmp model/config_v5_external.json /private/tmp/idsse_v5_repeat.json
cmp docs/verification/TASK-012-search.json /private/tmp/idsse_search_repeat.json
.venv/bin/python -m model.tune_idsse --stage evaluate --data-root data/external/idsse \
  --config model/config_v5_external.json --output /private/tmp/idsse_holdout_repeat.json
cmp docs/verification/TASK-012-holdout.json /private/tmp/idsse_holdout_repeat.json
```

The report hashes include code fingerprints and therefore change if the implementation
changes. Challenge labels were not read. Official baseline/evaluator files are unchanged.
No data was published. Diff review and whitespace checks passed. No commit or push made.

Tactical source fingerprints, checked during this run:

| Input under `data/tactical/` | SHA-256 |
| --- | --- |
| `BAR-ATH_tactical_atd.xml` | `327e35e32e46a647389b88f883d4f9a2ab931e3e6148aef2fcf8f22b1e93c43a` |
| `BAR-ATH_tactical_atd.txt` | `f130e350d2bfdf734b7e32f072931fccc6d015c1e837d082064875fe0a700431` |
| `BAR-ATH_tactical_smart_tagging.xml` | `0594d35e3df01b9c5002372d8615e2e8ef5379ac8f4e84c5ef7a53f4304c9019` |
