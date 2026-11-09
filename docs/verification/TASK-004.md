# TASK-004 verification — 2026-11-08, resumed after tactical folder link

- Initial run stopped at `games.require()` while ATD inputs were absent. Inputs were then obtained from the user-linked tactical subfolder; hashes are in `docs/DATA_AUDIT.md`. Local base revision is `fb14a0f84eb0634e807f10e2ee04464689d81676` plus uncommitted work.
- `./.venv/bin/python model/run.py --config model/config.json`: PASS. Config SHA-256 `aaa0c55c43a6f241ecceb861b1a24c12a6aa5b15073fe2bad4079b3bd0e5f3fa`; no seed.
- `./.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v1.csv`: PASS. Exactly 199,319 ordered frames, two columns, H 78,057 / A 69,659 / D 10,850 / X 40,753, no blanks. Of X, 40,462 are outside the graded halves and 291 within.
- The generation command was repeated with identical inputs and config. Output SHA-256 before and after: `fe13eb9a04a544532c757bac2e6df0cc3f63f68c40f48384ca218a0e9b677c78` both times.
- Diagnostics: 113,488 ball observations, 388 label transitions, 324 reported possession intervals, median 9.26 s, 13 possession intervals shorter than 1 s, 62 D intervals. Dead reasons were 2,420 `sustained_out_of_bounds` frames and 902 `stationary_set_piece` frames; another 7,528 D frames were awaiting restart. These are defect checks, not accuracy evidence.
- Output: ignored `evaluation/results/temporal_v1.csv`; diagnostics: ignored `evaluation/reports/temporal_v1_diagnostics.csv`. Public-window scorer was not run on the new model, so no public score is claimed. External-match label validation was unavailable; model quality remains unverified.
