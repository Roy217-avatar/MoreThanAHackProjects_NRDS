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
