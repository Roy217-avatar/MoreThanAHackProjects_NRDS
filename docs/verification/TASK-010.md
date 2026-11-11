# TASK-010 — External-only tuning protocol (pre-registered 2026-11-10)

## Frozen before search

Source: [`SkillCorner/opendata`](https://github.com/SkillCorner/opendata) revision
`4340d274572876239c154c90bc507a9b3250a656`. Its per-frame possession and
in-play phase team fields are automatic provider references, not independent ground truth.
The match is broadcast-tracked at 10 fps; the challenge is tactical-tracked at 25 fps.

- Development set (already analyzed under TASK-006): `2017461 2016236 2015213 2013725
  2011166 2010085 2007721 2007448 2006363 1996435`.
- Held-out set (not yet analyzed for model selection): `2006229 1996436 1986691
  1959846 1927964 1925299 1899585 1886347 1874553`.
- Primary selection metric: pooled exact H/A agreement on development frames for which
  `possession.group` supplies home/away. A predicted `D` or `X` counts as disagreement.
  Secondary tie-break: pooled agreement on provider in-play phase H/A frames. Remaining
  ties prefer the larger control-confirmation duration, then lexicographic configuration.
- Candidate grid, expressed on the challenge's 25 fps timeline: `control_distance_m` in
  `{1.5, 2.0, 2.5, 3.0}`; `opponent_margin_m` in `{0.25, 0.5, 0.75, 1.0}`;
  `control_frames` in `{8, 12, 16}`; `evidence_gap_frames` in `{0, 5, 10}`.
  This is 144 candidates. The 10 fps adapter scales frame counts with `round(n*10/25)`.
- Keep all dead-ball and set-piece settings fixed at v2 values. This avoids maximizing
  team agreement by disabling `D` where the provider has no reliable dead-ball reference.
  The grid's shortest confirmation is 8 tactical frames (about 0.32 s), preserving a
  minimum of sustained opposing evidence before switching teams.
- Search only the development set. Write the chosen configuration before evaluating the
  nine held-out matches. Evaluate holdout once, without a second tuning round. Report
  coverage, phase agreement, H/A/D/X distribution and transition diagnostics. A roughly
  90% holdout agreement is a user target; if it is not reached, report the measured result.
- No BAR-ATH public-window labels, private labels or hand corrections are used to choose
  parameters. The official scorer is not a tuning tool. The tuned configuration remains
  an external-provider prototype until independently annotated matches support it.

Results, exact commands, code and input fingerprints, test evidence and limitations will
be added after execution. Raw tracking remains ignored under `data/external/skillcorner/`.

## Development-only follow-up declared before holdout scoring

The 144-setting search selected 2.5 m reach, 0.75 m margin, 12 control frames and zero
gap frames: 253,574 / 314,964 (80.5%) provider H/A agreement on development matches.
Analysis of these same development matches found a confirmation delay that may assign the
old team for the first frames of a genuine turnover. One additional, general offline
candidate will be checked before holdout: after sustained control is confirmed, backfill
the new H/A label to the first frame of that uninterrupted candidate run. Incidental
touches remain unconfirmed and unchanged. No new threshold values are searched. If this
candidate improves pooled development H/A agreement, it will be the frozen candidate for
the single holdout evaluation; otherwise the grid-selected setting remains the candidate.
This follow-up was added after seeing development scores and must be reported as exploratory.

The backfill candidate (`model/config_v4.json`, SHA-256
`9df346247df6dbbbbd5860a375bd2d601bc01a899c5fe0ecbc4733553df36a49`)
matched 253,833 / 314,964 per-frame provider H/A labels (80.6%), 259 more than v3.
Its live-phase agreement was 268,266 / 309,236 (86.8%), versus 266,134 / 309,236
for v3. Under the stated development-only rule, **v4 is frozen for the nine-match
holdout evaluation**. No holdout result has informed that choice.

## Held-out results and decision

The frozen v4 was evaluated once on the nine additional matches, then v2 was scored on
the same files as a benchmark. The first v4 run stopped before scoring because five
source tracking files end one frame before their metadata's last-period end frame.
The adapter now accepts exactly one missing terminal frame, shortens only its in-memory
period block to the last observed row and records `missing_terminal_frames: 1` in the
per-match audit. It never creates an observation or submission row. Larger shortfalls still
raise an error. This source-alignment fix did not alter the selected configuration.

| ID | Date (UTC) | Home | Away | Provider H/A frames | v2 agreement | Frozen v4 agreement |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 2006229 | 2025-03-07 | Melbourne City FC | Macarthur FC | 32,452 | 83.9% | 84.2% |
| 1996436 | 2025-02-01 | Auckland FC | Macarthur FC | 27,576 | 77.9% | 78.7% |
| 1986691 | 2025-01-26 | Western Sydney Wanderers FC | Auckland FC | 32,060 | 83.4% | 83.7% |
| 1959846 | 2025-01-10 | Melbourne Victory Football Club | Western United | 31,073 | 81.4% | 81.7% |
| 1927964 | 2024-12-22 | Western Sydney Wanderers FC | Wellington Phoenix FC | 37,398 | 87.1% | 86.5% |
| 1925299 | 2024-12-21 | Brisbane Roar FC | Perth Glory Football Club | 35,589 | 83.3% | 83.2% |
| 1899585 | 2024-12-07 | Auckland FC | Wellington Phoenix FC | 29,576 | 78.5% | 79.3% |
| 1886347 | 2024-11-30 | Auckland FC | Newcastle United Jets FC | 32,100 | 82.7% | 83.2% |
| 1874553 | 2024-11-23 | Brisbane Roar FC | Adelaide United Football Club | 32,901 | 83.6% | 84.5% |

- Pooled per-frame team agreement: **v4 241,131 / 290,725 = 82.94%**, versus
  **v2 240,264 / 290,725 = 82.64%**. Improvement: 867 matches, or 0.30 percentage
  points. Seven of nine matches improved; two did not. The ~90% per-frame target was **not met**.
- Provider live-phase team agreement: **v4 255,367 / 287,842 = 88.72%**, versus
  **v2 251,280 / 287,842 = 87.30%**. This is a different, automatically derived
  reference and is not a substitute for the per-frame target or official `spellF1`.
- On available provider H/A frames, v4 predicted H/A 97.83% of the time, versus
  96.76% for v2. Agreement conditional on predicting H/A declined from 85.41% to
  84.78%; the higher overall agreement partly reflects higher coverage.
- The nine matches contain 537,444 tracking rows. V4 produced 2,337 direct H/A
  transitions versus 1,957 for v2, and 99,867 `D` frames versus 107,036. It marked
  `D` on 5,756 provider live-phase frames versus 8,459 for v2. More transitions could
  mean faster turnovers or excess flicker; these aggregate diagnostics cannot distinguish
  the two. Nine source phase rows crossing half boundaries were excluded with explicit
  audit, as in TASK-006. Five terminal source rows were absent, also audited.

The provider fields are automatic and share the same broadcast tracking as the model's
inputs. They are not independent ground truth; the challenge uses a different tactical
timeline and ranks by `spellF1`. Consequently the external improvement does not establish
a BAR-ATH accuracy or ranking gain. No further parameters were changed after holdout scoring.

## Challenge output and reproducibility

V4 is an **experimental external-tuned variant**. It retains v2's dead-ball and set-piece
thresholds, changes proximity/confirmation settings as recorded above, and enables offline
control backfill only after sustained candidate evidence confirms control. A short opposing
touch cannot trigger backfill. State and pending evidence reset at dead balls and halftime.
Diagnostics keep `control_backfilled` reasons separate from H/A/D/X output labels.

The exact BAR-ATH output is the ignored `evaluation/results/temporal_v4.csv`, with separate
ignored `evaluation/reports/temporal_v4_diagnostics.csv`. The official validator accepted
**199,319 ordered frames 0–199318**, exactly `frame,label` and legal H/A/D/X labels.
Counts were H 75,978; A 72,140; D 10,549; X 40,652. Two identical generations matched
SHA-256 `9b14309313b4d5e163d8513b06c1c87afcfbb489b3259f3f7f647d5a4955a655`.
Relative to v2, 8,759 labels changed; direct H/A transitions within halves rose from
259 to 294. This is a fragmentation diagnostic, not proof of improved possession quality.

Run from the repository root. The ten development downloads are documented in
[`TASK-006.md`](TASK-006.md). The additional nine public files can be fetched at the same
pinned SkillCorner revision; all raw inputs remain ignored under `data/`.

```bash
set -e
holdout=(2006229 1996436 1986691 1959846 1927964 1925299 1899585 1886347 1874553)
revision=4340d274572876239c154c90bc507a9b3250a656
for id in "${holdout[@]}"; do
  mkdir -p "data/external/skillcorner/$id"
  for suffix in match.json phases_of_play.csv; do
    curl -L --fail --retry 5 --retry-all-errors \
      -o "data/external/skillcorner/$id/${id}_${suffix}" \
      "https://raw.githubusercontent.com/SkillCorner/opendata/$revision/data/matches/$id/${id}_${suffix}"
  done
  curl -L --fail --retry 5 --retry-all-errors \
    -o "data/external/skillcorner/$id/${id}_tracking_extrapolated.jsonl" \
    "https://media.githubusercontent.com/media/SkillCorner/opendata/$revision/data/matches/$id/${id}_tracking_extrapolated.jsonl"
done
development=(2017461 2016236 2015213 2013725 2011166 2010085 2007721 2007448 2006363 1996435)
.venv/bin/python -m model.tune_skillcorner \
  --data-root data/external/skillcorner --match-ids "${development[@]}" \
  --base-config model/config_v2.json --config-out model/config_v3.json \
  --output docs/verification/TASK-010-search.json
.venv/bin/python -m model.compare_skillcorner \
  --data-root data/external/skillcorner --match-ids "${development[@]}" \
  --config model/config_v3.json --output docs/verification/TASK-010-development.json
.venv/bin/python -m model.compare_skillcorner \
  --data-root data/external/skillcorner --match-ids "${development[@]}" \
  --config model/config_v4.json --output docs/verification/TASK-010-development-backfill.json
.venv/bin/python -m model.compare_skillcorner \
  --data-root data/external/skillcorner --match-ids "${holdout[@]}" \
  --config model/config_v4.json --output docs/verification/TASK-010-holdout.json
.venv/bin/python -m model.compare_skillcorner \
  --data-root data/external/skillcorner --match-ids "${holdout[@]}" \
  --config model/config_v2.json --output docs/verification/TASK-010-holdout-v2.json
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python model/run.py --config model/config_v4.json \
  --output evaluation/results/temporal_v4.csv \
  --diagnostics evaluation/reports/temporal_v4_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v4.csv
shasum -a 256 evaluation/results/temporal_v4.csv
.venv/bin/python model/run.py --config model/config_v4.json \
  --output /private/tmp/temporal_v4_repeat.csv \
  --diagnostics /private/tmp/temporal_v4_repeat_diagnostics.csv
cmp evaluation/results/temporal_v4.csv /private/tmp/temporal_v4_repeat.csv
```

The v4 JSON file is checked in because the search runner generates v3 only; v4 adds the
documented offline backfill option. Repeat the BAR-ATH generation to a distinct output and
compare hashes before delivery. Raw external file hashes are in `TASK-010-search.json` and
`TASK-010-holdout.json`; tactical input SHA-256 values are recorded below.

## Verification identity

- Base Git commit: `a91fda11f113671a72b8e2b196ee523cee575bfc`, plus the TASK-010
  working-tree changes. Official challenge snapshot remains
  `f8f2629ff1e0985f81d7e59d8413678514ee1530`. No official scorer, baseline or
  submission validator code was modified. No challenge public labels were used for tuning.
- Python 3.9.6; dependencies from `requirements-lock.txt`. No randomness or seed.
- Development search: 144 settings, selected v3 search report SHA-256
  `87c1ab59f90a6fa8b654d1d54d4933ac5d566ca8744fca3139faae1cc25a9a13`;
  rerunning search selected the same settings and produced byte-identical report and v3
  config. V3 config SHA-256 `65b6f87511accf0d1cd1715cbbc8a2ec7db747858e89aabbc64edae3fc923005`.
- V4 config SHA-256 `9df346247df6dbbbbd5860a375bd2d601bc01a899c5fe0ecbc4733553df36a49`.
- Current code SHA-256: `model/inference.py`
  `ebea618e99b71cd0c2bae14748796165a6bb01d81da08d7edcc9c29ea245dccb`;
  `model/temporal.py`
  `c9448fb904d900391938d4f95a2e8d2cb3cacdc8d29cd803e984aebe4a82e737`;
  `model/external_skillcorner.py`
  `97a293fc53adcc155f63d04e7c2ff19b7a9aea824135f171667d025cd02e0ac7`;
  `model/tune_skillcorner.py`
  `77a0124f2d5921a63f222a0b49abf3e3b1a1e55e4dc80fc817a2ba565693a4e8`.
- `.venv/bin/python -m unittest discover -s tests -v`: **PASS, 50 tests**.
  `git diff --check`: **PASS**. The raw external directory is ignored by Git.
  The exact nine-match holdout JSON repeated byte-for-byte with SHA-256
  `d80eb68a27f4117de9d59a1ac1a452c83132d2d358b6a5dd1894e6b4b1a18289`.
  The exact BAR-ATH v4 CSV repeated byte-for-byte with the hash recorded above;
  the official validator passed on that file.
- Installed versions: `numpy==2.0.2`, `pandas==2.3.3`, `python-dateutil==3.0.0`,
  `pytz==2026.6`, `six==1.17.0`, `tzdata==2026.6`.
- Authorized tactical inputs SHA-256: ATD metadata
  `327e35e32e46a647389b88f883d4f9a2ab931e3e6148aef2fcf8f22b1e93c43a`,
  ATD text `f130e350d2bfdf734b7e32f072931fccc6d015c1e837d082064875fe0a700431`,
  Smart Tagging XML `0594d35e3df01b9c5002372d8615e2e8ef5379ac8f4e84c5ef7a53f4304c9019`.
- The official public-window scorer was **not run** for this tuning task. Its labels
  were not used for training, threshold choice or model selection. No private-match score
  or independent human-annotation validation is available.
