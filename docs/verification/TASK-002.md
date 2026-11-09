# TASK-002 verification — 2026-11-08, resumed after tactical folder link

- Initial run stopped because ATD XML and TXT were absent. The user subsequently linked the OTWBARCA tactical subfolder; its ATD files were downloaded into ignored `data/tactical/` under official names. No broadcast assets were accessed for modeling.
- `starter.load_atd.check_alignment_raw()`: PASS, 199,319 contiguous IDs 1–199319, mapped to video frames 0–199318.
- Metadata: Barcelona H, Atletic Club A, 46 slots (24 H / 22 A). Smart Tagging: 638 events; both kickoff intervals contain official kickoff frames. Ball observed on 113,488 frames.
- Input SHA-256 hashes are in `docs/DATA_AUDIT.md`.
- `./.venv/bin/python starter/baseline.py --out evaluation/generated_baseline`: PASS, four regenerated files. All four SHA-256 hashes exactly match the corresponding upstream supplied baseline CSVs. `baseline_smooth50.csv`: `6d4e04b80b9016cc16ada99697bf219d3a74b58750dd6d5ec5a4cd5fc32ab4b9`.
- `./.venv/bin/python evaluation/validate_submission.py evaluation/generated_baseline/baseline_smooth50.csv`: PASS, 199,319 rows.
- Excel equivalence: NOT APPLICABLE; no Excel file found. Tactical homography: NOT CHECKED; unused by this model.
