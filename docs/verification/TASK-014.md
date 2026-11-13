# TASK-014 verification — frozen v7 candidate

Date: 2026-11-12  
Base revision: `60349431a7d8d40a9466758d87ff93f8948f5d42` plus the TASK-014 working-tree diff  
Python: 3.9.6 with `requirements-lock.txt`  
Official challenge snapshot: `f8f2629ff1e0985f81d7e59d8413678514ee1530`

The official upstream HEAD was rechecked on 2026-11-12 and still matched this revision.

## Latest model analysis

> **Most recent independent H/A/D agreement: 76.47%**  
> Measured on the frozen 57,374-frame WCSF external match. This is the most relevant current
> accuracy-style result because the match was reserved before v7 was frozen and was not used to
> choose its parameters.

> **IDSSE development H/A/D agreement: 84.07%**  
> Measured across 713,489 development frames used to select the stoppage thresholds. It is a
> development result and therefore must not be presented as unseen-test accuracy.

The challenge itself ranks submissions by **spellF1**, not raw accuracy. On the independent WCSF
match, v7 achieved **0.47698 spellF1**, compared with 0.45041 for v6 and 0.42923 for v4. Its
independent macro-F1 was **0.76044**. No private full-match challenge labels are available, so the
project does not have an official full-match challenge accuracy or private spellF1 score.

| Latest v7 measurement | Value | Interpretation |
| --- | ---: | --- |
| Independent WCSF H/A/D agreement | **76.47%** | Current unseen external provider-reference result |
| Independent WCSF spellF1 | **0.47698** | Primary model-selection result |
| Independent WCSF macro-F1 | **0.76044** | Challenge tie-break style diagnostic |
| Independent WCSF live-team agreement | **88.38%** | Team correctness on provider-live frames; excludes the dead-ball problem |
| Independent WCSF dead-ball recall | **62.89%** | Fraction of provider-dead frames detected as D |
| IDSSE development H/A/D agreement | **84.07%** | Parameter-selection result, not held-out accuracy |
| Tactical submission format | **PASS** | 199,319 ordered H/A/D/X rows accepted by the official validator |

The requested approximately 90% whole-label accuracy has **not** been demonstrated. Live-team
agreement is closer to that target, but it answers a narrower question because dead-ball errors
are excluded.

## 1. Fresh-test reservation

Before downloading or scoring it, `model/wcsf_protocol.json` reserved the single anonymized
professional European-league match from
[`MatKempeGroningen/WCSF_SolutionRoom`](https://github.com/MatKempeGroningen/WCSF_SolutionRoom)
at revision `1c9ba798f98a9fffb16081a5d3965774d4e5662c`.

The two sealed inputs were:

- first half: SHA-256 `e7e5d753dba30549a01f2e37695556dc3cdf62043e8e3e6447a71e77da30fede`;
- second half: SHA-256 `8653a296952a717eb1f106fce77bf497f28e34cae673f7e3ae6baa61908751ae`.

The source deliberately withholds the match date and both team names. It documents optical
tracking at 25 Hz, downsampled and smoothed to 10 Hz; group 1 is home and group 2 is away. Each
team's coordinates are mirrored so its own goal is at -52.5 m. Player-to-ball distances and ball
displacement remain invariant under that reflection, so the adapter computes each player's
distance against the ball copy on the same row and never compares absolute player positions
between the two teams.

## 2. Development-only selection

The grid in `model/stoppage_search.json` contains 75 combinations of confirmation duration,
stationary radius and nearest-player clearance. Only the five IDSSE development IDs `J03WMX`,
`J03WN1`, `J03WOH`, `J03WOY`, and `J03WPY` selected parameters. Neither the WCSF references nor
the challenge public labels were used. Selection maximized the unchanged official
`spell_f1_mean`, then macro-F1 and H/A/D accuracy.

```bash
.venv/bin/python -m model.tune_stoppage \
  --data-root data/external/idsse \
  --config-out model/config_v7_stoppage.json \
  --output docs/verification/TASK-014-development.json
```

V7 selected 25 frames (1 s), 0.5 m and 2 m. Across 713,489 development frames:

| Model | spellF1 | macro-F1 | H/A/D agreement | dead recall | live-team agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| v6 settings | 0.42157 | 0.80133 | 80.92% | 79.81% | 81.87% |
| v7 selected | 0.43125 | 0.82925 | 84.07% | 87.04% | 81.51% |

The full deterministic search report is `TASK-014-development.json`, SHA-256
`b696b7b97ad7f381d97a461a9fa49fb5e306e16653ce39d4e23ddeef4acd1cf8`. The frozen v7 config is
SHA-256 `c28b2df9e0dab945663f3d0bd2e0d8319b948e834a3d2fc597f9e03205f0ff67`.

## 3. One-shot external assessment

The WCSF adapter streams the zipped CSVs, keeps halves separate, scales only frame durations from
25 Hz to 10 Hz, uses `AliveFlag`/`PossessionFlag` only as scoring references, and never puts them
into evidence. The first scoring attempt stopped before inference or metric calculation because
111 second-half timestamps had conflicting row copies of a frame-level reference. Investigation
found a unique majority at every conflict and no ties. The tested adapter now uses that strict
majority, audits all 111 timestamps, and still rejects a tie. No parameters changed after the
candidate was frozen.

```bash
.venv/bin/python -m model.evaluate_wcsf \
  --data-root data/external/wcsf \
  --output docs/verification/TASK-014-wcsf.json
```

The successful run covered 57,374 frames with no missing ball/player frames. Results from the one
predeclared comparison were:

| Model | spellF1 | macro-F1 | H/A/D agreement | D recall | live-team agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| v4 | 0.42923 | 0.57204 | 58.57% | 24.23% | 88.66% |
| v6 | 0.45041 | 0.66048 | 66.42% | 41.04% | 88.66% |
| v7 | **0.47698** | **0.76044** | **76.47%** | **62.89%** | 88.38% |

V7 was selected because spellF1 is the competition ranking metric. The safe aggregate report is
`TASK-014-wcsf.json`, SHA-256
`ceaa85dd6ed4209a2b145f9539cc62a7671747a1827364fa8ee070b37062a191`.
The reference contained 411 possession spells averaging 7.44 s. V7 predicted 358 averaging
11.20 s, closer than v6's 319 averaging 14.47 s and v4's 287 averaging 17.66 s. These durations
are computed from live-frame counts divided by spell counts at the documented 10 Hz.

## 4. Tactical artifact and checks

```bash
.venv/bin/python model/run.py --config model/config_v7_stoppage.json \
  --output evaluation/results/temporal_v7_stoppage.csv \
  --diagnostics evaluation/reports/temporal_v7_stoppage_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v7_stoppage.csv
.venv/bin/python -m unittest discover -s tests -v
```

- 81 tests passed.
- The official validator accepted exactly 199,319 ordered rows, frames 0–199318, and only H/A/D/X.
- Two independent generations and diagnostics matched byte for byte.
- CSV SHA-256: `5637746fccb19822b17a377fad53f340e31cf8c047580bcadea68651e75e9e35`.
- Diagnostic SHA-256: `282e61cc46373ff45e4535f54f00154a0f1468923d2f22ab6b3478e4d5fab9ad`.
- Labels: H 75,367; A 70,913; D 12,387; X 40,652. X occurs outside the two official half blocks.
- Within halves: 431 transitions and 433 intervals; minimum 13, median 169, maximum 6,167 frames.
- `git diff --check` passed. Official baseline and evaluator files were not edited.

Artifacts under `evaluation/` and all raw external/tactical inputs are ignored and remain local.

## Limitations

- The independent result is one anonymous provider-reference match, not human-adjudicated ground
  truth. It does not establish official challenge accuracy, a private score, or 90% accuracy.
- V7 improves dead-ball recall but slightly reduces strict live-team agreement on both external
  datasets. The tradeoff is accepted because spellF1 was predeclared as primary.
- The WCSF match is 10 Hz and mirrored; the challenge is 25 Hz tactical tracking. Duration scaling
  preserves seconds, but domain shift remains.
- The challenge public five-minute labels were not scored or used for selection in this task.
