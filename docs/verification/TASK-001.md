# TASK-001 verification — 2026-11-08

- Upstream revision: `f8f2629ff1e0985f81d7e59d8413678514ee1530`.
- Local starting revision: `fb14a0f84eb0634e807f10e2ee04464689d81676`; working tree has uncommitted additions.
- Environment: Python 3.9.6 in `.venv`; `pip install -r requirements.txt` succeeded after network approval. Installed versions are in `requirements-lock.txt` (SHA-256 `a3c002eb810057e3b0e64c89b5e0dc7cfe570d53f40aec4df19df78ab500a9ff`).
- `./.venv/bin/python evaluation/run_evaluation.py`: PASS, exit 0; four supplied baseline CSVs scored on 7,500 public graded frames. The pairs below are public-window `(macroF1, spellF1)`, for pipeline checking only:
  - `baseline_raw`: `(0.5972, 0.0378)`
  - `baseline_smooth25`: `(0.6200, 0.2868)`
  - `baseline_smooth50`: `(0.6207, 0.3256)`
  - `baseline_smooth125`: `(0.5812, 0.4242)`
- `./.venv/bin/python evaluation/validate_submission.py evaluation/results/baseline_smooth50.csv`: PASS, 199,319 ordered rows, 72,957 H / 54,842 A / 71,520 D / 0 X. Supplied CSV SHA-256 `6d4e04b80b9016cc16ada99697bf219d3a74b58750dd6d5ec5a4cd5fc32ab4b9`.
- Generated `evaluation/scoreboard.csv` and `evaluation/reports/` are ignored local diagnostics. No generator reproduction is claimed.
- `diff -qr` of `starter/` and supplied baseline CSV directory, plus `cmp` of `games.py` and three official evaluation scripts against the pinned checkout: PASS, no differences.
