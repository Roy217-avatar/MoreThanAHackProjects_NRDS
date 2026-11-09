# TASK-003 verification — 2026-11-08

- Code state: local base `fb14a0f84eb0634e807f10e2ee04464689d81676` plus uncommitted `model/`, `tests/`, docs and upstream snapshot.
- Config: `model/config.json`, SHA-256 `aaa0c55c43a6f241ecceb861b1a24c12a6aa5b15073fe2bad4079b3bd0e5f3fa`. Defaults chosen as conservative generic reach/persistence/stationarity assumptions, with no public-window optimization. No random seed or learned model.
- `./.venv/bin/python -m unittest discover -s tests -v`: PASS, 6 tests. Cases cover strict ATD frame and slot checks, missing ball/players, all-missing intervals, passes, incidental touches, controlled turnovers, dead-ball restart, halftime reset, set-piece stationarity and exact CSV serialization.
- `PYTHONPYCACHEPREFIX=/private/tmp/mtah2027-pycache .venv/bin/python -m compileall -q model tests`: PASS. The first compilation attempt used macOS's protected default bytecode cache and failed for permissions; rerun with the temporary cache succeeded.
- `git diff --check`: PASS. `model/run.py --help`: PASS.
- Actual tactical data run and official validation: PASS; see TASK-004.
