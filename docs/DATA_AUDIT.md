# Data audit — 2026-11-08

Source: official `DATA.md`, `games.py`, and starter loaders at upstream commit
`f8f2629ff1e0985f81d7e59d8413678514ee1530`, plus the authorized tactical ATD and Smart
Tagging files supplied through the OTWBARCA Drive folder. These files are local and ignored by Git.
No Excel file was found. The tactical homography appears in Drive without a `.csv` extension;
its actual format was not inspected and the model does not require it.

| Asset | Published shape and alignment | Notes |
| --- | --- | --- |
| Tactical ATD | FIFA/EPTS metadata XML and raw TXT, 199,319 records, `frame_id` 1–199319 confirmed | `video_frame = frame_id - 1`; raw line has `frame_id:player;...:ball`, coordinates normalized 0–1, `NaN` for missing. |
| Tactical video | 199,319 frames at 25 fps | Submission timeline 0–199318. |
| Homography | CSV, 199,319 zero-based `frame` rows | 3×3 normalized-pitch-to-pixel matrix, `valid`, `reprojection_error`; no index shift. |
| Smart Tagging | SportsCode XML, 638 instances confirmed | `round(seconds * 25)` gives tactical frame; both tagged kickoff intervals contain the published kickoff positions. Phase/team tags are automatic and noisy. |
| Broadcast | Separate 164,488-frame timeline | No tactical synchronization table; excluded from prototype. |
| Excel | None found | Cannot establish whether a spreadsheet exports official tracking. |

Metadata assigns 46 tactical track slots to a team: 24 Barcelona (H) and 22 Atletic Club (A).
Slots are tracklets, not stable player identities. The pitch size in `games.py` is 105.3 × 68.0 m.
The actual raw file has 113,488 frames with an observed ball (56.9%), matching the upstream count.
The published graded count is 94,214/158,857; player presence is published as an average 20.5
on graded frames and may exceed 22 due to duplicate tracks. Player-gap statistics were not
independently recomputed.

Input SHA-256: metadata `327e35e32e46a647389b88f883d4f9a2ab931e3e6148aef2fcf8f22b1e93c43a`,
raw tracking `f130e350d2bfdf734b7e32f072931fccc6d015c1e837d082064875fe0a700431`,
tagging `0594d35e3df01b9c5002372d8615e2e8ef5379ac8f4e84c5ef7a53f4304c9019`.
If an Excel export is later supplied, compare frame range, team mapping, units, missingness, and
numeric values before treating it as equivalent. Tactical homography alignment remains unchecked.
