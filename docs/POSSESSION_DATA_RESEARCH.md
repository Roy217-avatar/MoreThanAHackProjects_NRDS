# Ten additional public resources for possession research

Checked 2026-11-11. These are ten resources beyond the SkillCorner matches already
used by this project. They are **not ten interchangeable possession ground-truth
datasets**. Availability below distinguishes public downloads from access requests.
Only IDSSE was downloaded and used in this experiment; the other nine were assessed
from their published documentation. A public description does not establish a usable
frame-by-frame reference or authorize accepting access terms on someone else's behalf.

| # | Resource and primary source | Available data/access | Use for this model and decision |
| --- | --- | --- | --- |
| 1 | [IDSSE / DFL / Sportec](https://huggingface.co/datasets/pysport/idsse-data), [original dataset DOI](https://doi.org/10.6084/m9.figshare.28196177) | Seven German league matches, 25 Hz tracking, match metadata and synchronized events; public mirror, CC BY 4.0. | **Used.** Ball records include `BallPossession` and `BallStatus`. Five matches develop settings; two reserved for testing. References are used only for scoring. |
| 2 | [Metrica Sports sample data](https://github.com/metrica-sports/sample-data) | Three anonymized games; synchronized tracking/events, CSV and EPTS/JSON formats; public files, source acknowledgement requested. | Strong next source. Events need a documented conversion to possession intervals; event ownership is not a complete live/dead answer key. Team names and dates are anonymized and must not be invented. |
| 3 | [University of Groningen / WCSF Solution Room](https://github.com/MatKempeGroningen/WCSF_SolutionRoom) | One anonymized professional match, zipped position CSVs at 10 Hz, `PossessionFlag`, `AliveFlag`; publicly downloadable, acknowledgement requested. | Promising second provider. Each team's coordinates are mirrored relative to its own goal; ball coordinates are relative to the player row's orientation. Requires a dedicated adapter and provenance review of derived flags. |
| 4 | [Hudl StatsBomb Open Data](https://github.com/hudl/open-data) | Public event JSON, lineups, matches, and selected 360 snapshots; use subject to repository terms and attribution. | Useful for possession sequences and event analysis. Snapshots are not continuous all-player/ball tracking, so the current temporal model cannot be scored over a full match directly. Exclude the challenge match from any future use. |
| 5 | [Wyscout soccer match event dataset](https://figshare.com/collections/Soccer_match_event_dataset/4415000) | Public event collection covering seven competitions; times, locations, players and outcomes; cite the dataset papers and follow each item's licence. | Useful event sequences, but no matching continuous tracking in this release. Do not interpolate event owners into an asserted frame-level ground truth. |
| 6 | [PFF FC 2022 World Cup release](https://www.blog.fc.pff.com/blog/pff-fc-release-2022-world-cup-data) | Tracking, events and metadata for 64 matches; provider asks users to complete an access form. [Loader documentation](https://kloppy.pysport.org/user-guide/loading-data/pff/) describes the formats. | High-value future comparison once access is obtained. No form submitted, assets downloaded or PFF accuracy claimed in this task. |
| 7 | [SoccerTrack v2](https://huggingface.co/datasets/atomscott/soccertrack-v2), [project](https://atomscott.github.io/SoccerTrack-v2/) | Ten university matches, panoramic footage, pitch positions and ball-action events; CC BY 4.0 with Hugging Face access acknowledgement. | Potential synchronized external source. The release explicitly says auxiliary ball positions are reconstructed from event anchors and interpolated: testing against those same event labels risks circular evidence. Do not treat the reconstructed ball as independent measurements. |
| 8 | [SoccerNet Ball Action Spotting](https://www.soccer-net.org/tasks/ball-action-spotting), [access](https://huggingface.co/datasets/SoccerNet/SN-BAS-2023) | Pass/drive and later additional ball-action annotations on broadcast videos. The 2023 release is gated and requires approval. | Useful for future event/restart models. Timestamped actions are not continuous team-possession labels; it also needs a tracking/feature pipeline. Not used here. |
| 9 | [Last Row](https://github.com/Friends-of-Tracking-Data-FoTD/Last-Row) | Public 20 Hz position samples for 19 Liverpool goals from 2019; author requests credit. | Small qualitative/synthetic-style exercise only. Source warns that accuracy is insufficient for research and players are omitted. Goal-only sampling cannot validate full-match possession or dead-ball accuracy. |
| 10 | [Alfheim, Simula](https://datasets.simula.no/alfheim/) | Player positions at 20 Hz and corresponding stadium videos; public research resource with noncommercial-use and identification restrictions. | Movement/video resource, not a ready possession benchmark: the described release lacks a continuous ball/possession reference suitable for this model. No video downloaded or manual labels created. |

## Why IDSSE was selected

It is immediately downloadable, comes from different games and a different provider
than the earlier SkillCorner experiment, and supplies both tracking and frame reference
fields. This supports a full H/A/D comparison without inventing event-to-frame labels.
Its 25 Hz sampling also matches the challenge's rate. Its provider definitions and
tracking quality may still differ from the competition's tactical data.

Downloaded metadata and tracking are pinned to mirror revision
`a715a38dfbaf5f58e431727c2b78d174101a703c` and remain under ignored
`data/external/idsse/` (approximately 2.5 GiB). Source attribution: Bassek et al.,
*An integrated dataset of synchronized spatiotemporal and event data in elite soccer*,
Scientific Data 12, 195 (2025), [paper DOI](https://doi.org/10.1038/s41597-025-04505-y).
The original DOI endpoint returned an access error in this session; the public mirror's
actual files were downloaded successfully.

The dataset card's last two IDs differ from its actual file listing. The experiment uses
**J03WQQ and J03WR9**, as verified in filenames and XML metadata, not the card's J03WPF/J03WQF.
Team mapping (`1` home, `2` away) and live status (`1` live) were cross-checked against
the [Kloppy Sportec reader](https://github.com/PySport/kloppy/blob/master/kloppy/infra/serializers/tracking/sportec/deserializer.py).
Unknown codes/references are handled explicitly rather than mapped to an opponent or dead play.

See [TASK-012 methods and accuracy calculations](verification/TASK-012.md) for the
fixed split, actual matches, tuning protocol, results and commands.
