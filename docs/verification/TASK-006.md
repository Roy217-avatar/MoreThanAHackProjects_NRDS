# TASK-006 — Public external-match comparison (2026-11-10)

## Scope and source

Ten **closed** Australian A-League matches from
[`SkillCorner/opendata`](https://github.com/SkillCorner/opendata) at revision
`4340d274572876239c154c90bc507a9b3250a656` were processed. The repository's
[MIT license](https://github.com/SkillCorner/opendata/blob/4340d274572876239c154c90bc507a9b3250a656/LICENSE)
and [README schema](https://github.com/SkillCorner/opendata/tree/4340d274572876239c154c90bc507a9b3250a656)
are public. The manifest lists 20 matches, 19 marked closed. Ten are included here; extending
this same source would allow at most 19 closed matches at this revision.

Source files per ID: `<id>_match.json`, `<id>_tracking_extrapolated.jsonl`, and
`<id>_phases_of_play.csv`. The tracking is broadcast-derived at 10 fps, with pitch-centred
metre coordinates and detected or extrapolated positions. `possession.group` gives a provider
H/A reference when available; it is absent on 333,156 of 648,120 frames. The phase CSV supplies
a team only in intervals it labels as live. Both are provider-generated references, **not
independently verified human possession annotations**. No absent reference was treated as `D`.

The adapter maps metadata team IDs to H/A, converts pitch-centred metres to normalized
coordinates for diagnostics, and uses metre distances for tentative control. It preserves
continuous source frame numbering and the metadata's inclusive period boundaries; outside-period
frames remain `X`. It scales 25 fps frame durations to 10 fps (12 control frames → 5,
5 gap frames → 2, 25 out-of-bounds frames → 10). It does not supply challenge Smart Tagging,
so `stationary_set_piece` is false. The fixed `model/config_v2.json` was chosen before this
comparison; no thresholds were fitted or selected here. Because SkillCorner has no mapped
Smart Tagging set-piece input, this check also cannot distinguish v1 from v2's set-piece
backfill. No BAR-ATH public labels were read.

Six phase rows in the source cross a recorded first-half boundary. The adapter excludes each
whole ambiguous row from the phase comparison and records 6 excluded rows / 615 source-row
frames in the JSON audit. It does not trim tracking, shift frames or turn those gaps into `D`.

## Matches and observed agreement

Dates below are the UTC dates in match metadata. Percentages are exact team-label agreement on
frames where that provider reference supplies H/A; `D` and `X` predictions count as disagreement.
This is **not** official challenge accuracy, `spellF1`, or evidence of a better ranking.

| ID | Date (UTC) | Home | Away | Per-frame H/A frames | Per-frame agreement | Live-phase agreement |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 2017461 | 2025-05-17 | Melbourne Victory Football Club | Auckland FC | 28,888 | 72.1% | 80.3% |
| 2016236 | 2025-05-09 | Western United | Adelaide United Football Club | 33,134 | 78.7% | 84.1% |
| 2015213 | 2025-05-03 | Western United | Auckland FC | 31,349 | 78.2% | 84.0% |
| 2013725 | 2025-04-27 | Western United | Sydney Football Club | 31,775 | 78.4% | 82.2% |
| 2011166 | 2025-04-12 | Wellington Phoenix FC | Melbourne Victory Football Club | 27,658 | 76.0% | 80.8% |
| 2010085 | 2025-04-05 | Melbourne City FC | Central Coast Mariners Football Club | 32,972 | 81.7% | 87.5% |
| 2007721 | 2025-03-16 | Auckland FC | Central Coast Mariners Football Club | 34,069 | 82.6% | 87.5% |
| 2007448 | 2025-03-15 | Perth Glory Football Club | Brisbane Roar FC | 29,675 | 82.3% | 87.0% |
| 2006363 | 2025-03-08 | Melbourne Victory Football Club | Central Coast Mariners Football Club | 32,854 | 82.9% | 89.0% |
| 1996435 | 2025-02-01 | Sydney Football Club | Adelaide United Football Club | 32,590 | 82.6% | 87.5% |

Across the ten matches, the temporal model matched 250,979 / 314,964 per-frame provider H/A
references (79.7%); it predicted H/A on 301,871 / 314,964 of those frames (95.8% coverage).
The instantaneous proximity candidate matched 133,396 / 314,964 (42.4%) with only 50.1%
H/A coverage. On the 309,236 provider live-phase frames, temporal agreement was
263,178 / 309,236 (85.1%); instantaneous proximity agreement was 140,658 / 309,236 (45.5%).
The temporal model labeled `D` on 11,150 live-phase frames (3.6%); this is a useful disagreement
diagnostic, subject to the provider's phase errors. Conditional agreement on frames where each
method predicts H/A is lower for the temporal model than for the instantaneous candidate, so
the headline agreement difference largely reflects how much of the reference each covers.

The source's missing references, extrapolated tracking, 10 fps broadcast viewpoint and different
possession semantics prevent interpreting these figures as accuracy against the challenge's
hidden tactical-video labels. In particular, gaps in phases cannot validate dead-ball recall.
The fixed model was not changed after seeing these results. The next highest-value evidence is
an accessible, independently annotated match with a compatible live/dead possession definition.

## Reproduce

Run from the repository root using the existing `.venv` and
`requirements-lock.txt`. Public downloads total roughly 1 GB and stay under ignored `data/`.
Do not commit raw files or frame-level derivatives.

```bash
ids=(2017461 2016236 2015213 2013725 2011166 2010085 2007721 2007448 2006363 1996435)
revision=4340d274572876239c154c90bc507a9b3250a656
for id in "${ids[@]}"; do
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
.venv/bin/python -m model.compare_skillcorner \
  --data-root data/external/skillcorner --match-ids "${ids[@]}" \
  --config model/config_v2.json \
  --output docs/verification/TASK-006-results.json
.venv/bin/python -m unittest discover -s tests -v
shasum -a 256 docs/verification/TASK-006-results.json
```

## Verification record

- Base Git revision: `248e7de35dbc0c9a84a6f84fcb7d5a51ef95327d`, with the TASK-006
  changes in the working tree. SkillCorner source revision above. Input SHA-256 values for all
  30 match files and the config are in [`TASK-006-results.json`](TASK-006-results.json).
- Python 3.9.6; `numpy==2.0.2`, `pandas==2.3.3`, `python-dateutil==3.0.0`,
  `pytz==2026.6`, `six==1.17.0`, `tzdata==2026.6`. The adapter uses Python standard library
  and existing model code. Deterministic algorithm; no random seed.
- `model/config_v2.json` SHA-256:
  `c2d99e256141d56c168c7ae172e639272aa085f76a7bf336efcfcaaeacc3b36d`.
- Adapter and runner SHA-256, respectively:
  `069e60fe6144e63964b004a58514cfd849b59fa737a73a0ab2d869c0c6b4944a` and
  `9912a010621371c139b93c69f83c3f52eb0ec9d879fd31327528b90744cb4eba`.
- `.venv/bin/python -m unittest discover -s tests -v`: **PASS, 40 tests**, including ten
  external-adapter tests. The exact comparison command above: **PASS, 10 matches**, 648,120
  source frames. Repeated generation to `/private/tmp/TASK-006-results-repeat.json` matched
  byte-for-byte; both SHA-256 hashes:
  `70d119164aeab6e1a57a86066612fcff7e1769c9b43a6e827d7c33927c08ef6f`.
- The already-generated BAR-ATH `evaluation/results/temporal_v2.csv` passed the official
  submission validator: **199,319 ordered rows, frame 0–199318, legal labels**. No new
  BAR-ATH submission was generated in TASK-006. The official evaluator and starter were not
  modified or run to select this comparison.

## Re-verification after TASK-010 adapter extension

TASK-010 added cached nearest-distance evidence, a count of H/A transitions, and an explicit
audit for a missing terminal source frame. The ten TASK-006 development files have no missing
terminal frame; the original agreement counts remain unchanged. Re-running the command above
now writes two additional aggregate fields per match and produces SHA-256
`1493abcafa28487da0fbd710e7187e9c41347fda08ae65c7f857d1ab1a85ccc8` for the current
`TASK-006-results.json`. The earlier `70d119...` hash documents the prior schema; the current
code and artifact use the new hash. No source tracking or frame labels were changed.
