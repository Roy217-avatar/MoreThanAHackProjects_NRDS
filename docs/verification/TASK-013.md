# TASK-013 — Observed unattended stoppage cue

This experimental rule targets a concrete error: a controlling-team label continuing
while an observed ball sits unattended during a stoppage. The earlier inference
already outputs D for sustained out-of-bounds evidence or a confirmed tagged
stationary set piece. It had no generic cue for an in-bounds, untagged stoppage.

`model/stoppage.py` now requires 50 continuous 25 Hz frames (2 s) with the observed
ball inside a 0.5 m region and the nearest observed player of each team at least
3 m away. The values encode a deliberately long pause and a gap larger than normal
touching distance; they were chosen from general play reasoning and synthetic
behavior checks, not a search over challenge or external test labels. Missing ball,
missing one team, a near player, ball motion, an out-of-bounds ball or halftime
breaks the cue. Once confirmed, it marks that observed window D within the same
half. A restart needs confirmed team control. The output reason
`stationary_unattended` stays in diagnostics, separate from H/A/D/X labels.

The new configuration preserves the v4 control thresholds. Older configurations
ignore the new cue even if an external adapter has computed it. A synthetic
regression test caught that isolation issue during development. The official
starter baseline and evaluator were not changed. The code reads tracking
coordinates only; external `BallStatus` and `BallPossession` remain scoring
references and never enter evidence or inference.

## Verification

- `python -m unittest discover -s tests`: 70 passed, including new stoppage,
  missing-observation, halftime, restart, and old-configuration isolation tests.
- Official validator accepted the exact tactical output:
  `evaluation/results/temporal_v6_stoppage.csv`, 199,319 ordered frames,
  `frame,label`, H/A/D/X only. Counts: H 75,468; A 71,373; D 11,826; X 40,652.
- Two identical tactical generations matched SHA-256
  `a6857d51e8a46628c154a9d0bbfa0ebb1ecb7ed4827f4794686cecb5c9588980`.
- The unchanged v4 configuration still regenerated its previous SHA-256
  `9b14309313b4d5e163d8513b06c1c87afcfbb489b3259f3f7f647d5a4955a655`.
- Exactly 1,277 tactical labels changed relative to v4, all H/A → D
  (510 H, 767 A). This is an output diagnostic, not an accuracy claim.
- The same local tactical input fingerprints are recorded in TASK-012; no source
  assets or frame-level tracking exports were added to Git.

## External development diagnostic

Five previously designated IDSSE development matches were used only to assess
aggregate behavior. Their provider possession/live-dead fields are scoring
references, not independent challenge labels. The previously inspected two
IDSSE test matches and public five-minute challenge labels were not used for
further tuning or selection. Aggregate counts and each input SHA-256 are in
`TASK-013-development.json` (SHA-256
`ea1025dfb20113cac6cff9da93886bfe5c3ca9fbeea0215b127072b5847bccbb`).
All five development matches improved in full H/A/D provider agreement; pooled
v4 was **454,615 / 713,489 = 63.72%**, and the fixed v6 rule was
**577,328 / 713,489 = 80.92%**. Dead-ball recall rose from **40.46% to 79.81%**.
Live-team agreement fell from **83.74% to 81.87%**, and the total number of
label transitions rose from 1,636 to 2,049. These tradeoffs are why v6 is still experimental.
The development data had already been used for earlier model selection, so this
is an exploratory diagnostic, not an independent test or a challenge accuracy
estimate. No post-result threshold changes were made.

### Descriptive total across all seven IDSSE matches

After the user asked for the whole-dataset figure, the frozen v6 configuration
was also run on J03WQQ and J03WR9. It matched 110,690 / 142,345 frames (77.76%)
and 120,770 / 146,810 frames (82.26%), respectively. Pooling these with the five
development matches gives **808,788 / 1,002,644 = 80.67%** full H/A/D provider
agreement. The exact aggregate and input fingerprints are in
`TASK-013-all-seven-descriptive.json`.

The last two matches had already been inspected during TASK-012. This total is
therefore a descriptive calculation, not an independent holdout estimate. It is
also not the challenge's 199,319-frame accuracy or ranking `spellF1`. No
parameters were changed after this calculation.

## Reproduction

From the project root with the documented `.venv` and authorized tactical inputs:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python model/run.py --config model/config_v6_stoppage.json \
  --output evaluation/results/temporal_v6_stoppage.csv \
  --diagnostics evaluation/reports/temporal_v6_stoppage_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v6_stoppage.csv
.venv/bin/python model/run.py --config model/config_v6_stoppage.json \
  --output /private/tmp/temporal_v6_stoppage_repeat.csv \
  --diagnostics /private/tmp/temporal_v6_stoppage_repeat_diagnostics.csv
cmp evaluation/results/temporal_v6_stoppage.csv /private/tmp/temporal_v6_stoppage_repeat.csv
```

This cue only identifies stationary, unattended stoppages. A dead ball held near
a player or missing from tracking remains difficult to detect. A stationary ball
far from players could also be live in unusual situations. It is therefore a
candidate rule, not a validated challenge improvement. The ranking metric
`spellF1` was not estimated from external provider labels.
