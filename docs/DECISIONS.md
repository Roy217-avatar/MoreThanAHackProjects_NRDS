# Decisions

## 2026-11-08 — Temporal tracking model with constrained tag evidence

Use the official tactical ATD and Smart Tagging only. The first model is a deterministic state
machine: a nearby player with a clear distance margin supplies candidate control, sustained
candidate evidence transfers possession, and uncertainty carries the last live controller.
Out-of-bounds tracking or a sustained stationary ball during a set-piece tag supplies dead-ball
evidence. A tag alone never defines a possession or dead interval.

The 2 m reach distance, 0.75 m opponent margin, 12 control observations, five-frame gap, one-second
out-of-bounds/stationarity durations and 0.5 m stationary radius are general engineering assumptions
chosen without consulting the supplied match's public labels. They are versioned in `model/config.json`.
No random seed or supervised training is involved. These numbers are not validated on another game;
eligible external data would be needed to justify their effect on actual possession quality.

Tactical homography, video, broadcast tracking and other automatic tag classes were deferred because
the current model works in pitch coordinates and the available set-piece tag is the only tag used
for a narrow, interpretable dead-ball cue. The model will likely miss stoppages during long ball
occlusions and can lag fast turnovers. The full-match diagnostic counts and public five-minute
ground truth are not used to choose parameters or compare variants.

## 2026-11-10 — Backfill only confirmed stationary set-piece windows

The offline v2 variant keeps the v1 thresholds and state machine. When an automatic set-piece
interval contains 25 consecutive observed ball positions within the configured 0.5 m radius,
it marks that entire confirmed window as dead evidence. The v1 model marked only the 25th and
later qualifying frames. This removes a built-in delay between the beginning of a confirmed
stationary interval and its `D` label. The evidence window resets on a missing ball, an untagged
frame, an out-of-bounds ball, or a half boundary. A tag without observed stationarity still has
no authority to define `D`.

This uses future observations within the window, so v2 is an offline model and should not be
described as real-time causal inference. The choice is a general timing rule derived from the
meaning of a sustained stationary-ball cue, not from the supplied game's public labels or
output diagnostics. The new configuration is `model/config_v2.json`; the original configuration
and v1 output remain reproducible. No eligible external labeled game was available to establish
whether this change improves possession accuracy or spellF1.

## 2026-11-10 — Keep the SkillCorner comparison diagnostic separate

Use the public SkillCorner open-data tracking and phase files for a ten-match external
agreement check, at a pinned upstream revision. Apply the existing v2 model unchanged;
scale only time-based frame counts from 25 fps to the source's 10 fps. Preserve the source
frame timeline, metadata team mapping, and half boundaries. Compare on frames where the
provider supplies H/A; never turn missing provider labels or absent phases into `D`.

SkillCorner's possession and phase fields are provider-generated, not independent human
ground truth. They have different coverage and semantics from the challenge labels. The
comparison can expose disagreements and data-quality issues, but cannot justify an official
ranking claim or establish dead-ball recall. No thresholds are changed or selected from it;
the next validation step requires a compatible independently annotated match. The adapter
and aggregate report remain separate from the challenge submission pipeline.

## 2026-11-10 — External tuning remains experimental

Use the ten previously inspected SkillCorner matches as a development set and reserve
nine additional closed matches as a held-out check. The 144-setting grid changed only
proximity and confirmation parameters; dead-ball settings remained fixed. After the
grid selected v3, one exploratory offline backfill rule was tested on development data:
once opposing control is sustained, retroactively label the confirmed run from its
first frame. An incidental touch remains with the previous team. V4 was frozen before
examining the nine held-out scores.

Held-out per-frame agreement with SkillCorner's automatic team field rose from 82.64%
for v2 to 82.94% for v4; live-phase agreement rose from 87.30% to 88.72%. The user's
roughly 90% per-frame target was not reached. These fields are not human ground truth,
and 10 fps broadcast tracking differs from the challenge's tactical input. V4 is an
experimental option with a valid full-length BAR-ATH CSV; do not infer an official
`spellF1` or ranking gain. Keep v2 available until independent validation supports
a final choice. See `docs/verification/TASK-010.md` for the frozen split, tests,
source anomalies, fingerprints and commands.
