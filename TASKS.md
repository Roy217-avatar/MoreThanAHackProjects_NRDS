# Task board — 2026-11-10

The upstream public starter is pinned at `f8f2629ff1e0985f81d7e59d8413678514ee1530`.
Statuses describe completed work in this checkout; no private-match score or organizer submission exists.

## Coordinated work (2026-11-09)

The lead established `docs/INTERFACE.md` before delegating. On 2026-11-09, the data agent owned
`model/evidence.py`, `tests/test_evidence.py`, and data-audit notes (TASK-008).
The model agent owned `model/inference.py` and `tests/test_inference.py` (TASK-009).
The lead handled integration, and a read-only review agent inspected the result. The
2026-11-10 TASK-005 extension is lead-owned. Official starter/evaluator files are unchanged.
Public-window scores were never used for selection.

Current local output: `evaluation/results/temporal_v2.csv` (ignored by Git), SHA-256
`dce2ebdb60ecf31967907e7fdb031eafb5533c5642561239cdc285ca149a0c9f`.
The v1 output remains byte-identical to its 2026-11-09 artifact. V2 changes only
confirmed stationary set-piece timing and has no established accuracy gain.
The tactical ATD and tagging inputs are present only under ignored `data/tactical/` in this
workspace; a fresh clone needs the authorized bundle. External labeled match data, a registered
team name, and a final technical document are not yet available. No performance improvement over
the official baseline has been established.

### TASK-001 — Establish official scorer and isolated environment
- Status: done
- Priority: P1
- Owner: Codex
- Depends on: none
- Goal: Execute the supplied public baseline scorer without gated data.
- Scope: official starter snapshot, dependency lock, local setup instructions.
- Acceptance criteria: isolated install; official scorer executes four supplied CSVs; one CSV validates.
- Verification: `docs/verification/TASK-001.md`.
- Evidence: public scorer and validator passed on 2026-11-08.
- Blocker: none
- Last updated: 2026-11-08
- Handoff: repeat after any upstream update; do not use public scores for selection.

### TASK-002 — Audit actual tracking and regenerate baseline
- Status: done
- Priority: P1
- Owner: Codex
- Depends on: TASK-001; authorized tactical ATD bundle
- Goal: Verify input alignment and regenerate the official baseline from match data.
- Scope: metadata/raw schema, frame counts, missingness, Excel comparison if supplied, baseline CSV.
- Acceptance criteria: verified 1..199319 ATD IDs, correct H/A metadata, four regenerated files validated and fingerprinted.
- Verification: `starter.load_atd.check_alignment_raw()`, `starter/baseline.py`, official validator, input/output hashes.
- Evidence: `docs/verification/TASK-002.md` records input hashes, alignment, four matching baseline hashes and validation; audit in `docs/DATA_AUDIT.md`.
- Blocker: none for ATD baseline; no Excel file to compare.
- Last updated: 2026-11-08
- Handoff: retain input fingerprints and do not commit restricted source assets.

### TASK-003 — Implement and synthetically verify temporal prototype
- Status: done
- Priority: P1
- Owner: Codex
- Depends on: TASK-001
- Goal: Explainable temporal possession labels with strict frame ingestion and no public-label tuning.
- Scope: `model/`, `tests/`, configuration and behavior documentation.
- Acceptance criteria: synthetic boundary, missingness, pass, incidental touch, turnover, dead/restart, halftime and serialization tests pass.
- Verification: `docs/verification/TASK-003.md`.
- Evidence: six synthetic unit tests pass after tactical set-piece evidence was added.
- Blocker: none for prototype; actual-match behavior remains unverified.
- Last updated: 2026-11-08
- Handoff: consider external-match validation before claiming any improvement in scoring.

### TASK-004 — Validate and reproduce full-length prototype output
- Status: done
- Priority: P1
- Owner: Codex
- Depends on: TASK-002, TASK-003
- Goal: Generate the exact 199,319-row prototype CSV twice with matching hashes.
- Scope: input fingerprints, official validator, label and transition diagnostics, reproduction record.
- Acceptance criteria: exact CSV contract passes validator; identical runs hash alike; diagnostics inspected.
- Verification: commands in README and `docs/verification/TASK-004.md`.
- Evidence: `docs/verification/TASK-004.md` records official validator result, diagnostics, and matching repeat hashes.
- Blocker: none for generation; model quality remains unvalidated against eligible external labels.
- Last updated: 2026-11-08
- Handoff: evaluate dead-ball detection and turnovers on eligible external games; do not tune to the public five minutes.

### TASK-005 — Harden and extend temporal possession inference
- Status: done
- Priority: P1
- Owner: lead (integration)
- Depends on: TASK-004, TASK-008, TASK-009
- Goal: Keep the verified separated pipeline and add a general offline timing rule that starts a confirmed stationary set-piece dead interval at the beginning of its observed window.
- Scope: `model/evidence.py`, model docstrings, `model/temporal.py`, versioned configuration, synthetic tests, model rationale and diagnostics; preserve the v1 files and official starter/evaluator.
- Acceptance criteria: a short or interrupted stationary/tagged run remains insufficient; a sustained observed run can backfill only within the same half; existing v1 predictions remain reproducible; new full-length output validates and repeats with an identical hash; diff review finds no unresolved correctness issue.
- Verification: `.venv/bin/python -m unittest discover -s tests -v`; `.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v2.csv`; repeat v2 generation and compare SHA-256; inspect aggregate diagnostics and diff. Full record: `docs/verification/TASK-005.md`.
- Evidence: PASS, 30 tests and official validation of 199,319 ordered H/A/D/X rows. Two v2 runs matched SHA-256 `dce2ebdb60ecf31967907e7fdb031eafb5533c5642561239cdc285ca149a0c9f`; the v1 re-run matched its prior hash. Exactly 689 labels changed to `D` under confirmed stationary set-piece evidence. No public-window or private-match score was used to select v2. The diff was reviewed.
- Artifact: ignored `evaluation/results/temporal_v2.csv`; separate diagnostics at `evaluation/reports/temporal_v2_diagnostics.csv`; configuration `model/config_v2.json`.
- Blocker: none for TASK-005 completion. Accuracy claims remain unverified without eligible external labeled data (TASK-006).
- Last updated: 2026-11-10
- Handoff: TASK-006 is next: obtain an eligible labeled match from another game, document its provenance, then assess possession and dead-ball timing. Do not infer an accuracy gain from the 689 changed frames or transition counts.

### TASK-008 — Extract and audit tactical frame evidence
- Status: done
- Priority: P1
- Owner: data agent
- Depends on: TASK-004; `docs/INTERFACE.md`
- Goal: Return strict, documented per-frame tracking and tagging evidence for inference.
- Scope: `model/evidence.py`, `tests/test_evidence.py`, data-audit notes only.
- Acceptance criteria: exact tactical frame count and 1→0 indexing; metadata-based H/A slot mapping; normalized-to-metre distance scaling; explicit missingness; set-piece evidence requires observed stationary ball; malformed input fails loudly.
- Verification: red/green synthetic tests, full Python test suite, official raw alignment check, aggregate input audit; report commands/results to lead.
- Evidence: six focused tests and the 26-test suite passed on 2026-11-09; real tactical scan returned 199,319 ordered records, correct team names, and 113,488 observed balls. Audit and input hashes are in `docs/DATA_AUDIT.md`; the later 30-test TASK-005 check is in `docs/verification/TASK-005.md`.
- Blocker: none; authorized tactical ATD/tagging files are local and ignored.
- Last updated: 2026-11-09
- Handoff: interface integrated in `model/temporal.py`; homography and Excel remain unavailable locally.

### TASK-009 — Extract and harden temporal inference
- Status: done
- Priority: P1
- Owner: model agent
- Depends on: TASK-004; `docs/INTERFACE.md`
- Goal: Convert agreed evidence records into coherent H/A/D/X labels with reason codes.
- Scope: `model/inference.py`, `tests/test_inference.py` only.
- Acceptance criteria: same-team passes retain control; incidental opposing touches do not switch it; sustained opposing control does; missing ball is not dead; dead/restart and halftime state reset work; invalid block boundaries fail loudly.
- Verification: red/green synthetic tests and full Python test suite; report commands/results to lead.
- Evidence: 12 focused tests and the 26-test suite passed on 2026-11-09, including malformed boundaries/candidates, missingness, turnover and restart behavior; the later 30-test TASK-005 check is in `docs/verification/TASK-005.md`.
- Blocker: none; synthetic evidence follows the interface.
- Last updated: 2026-11-09
- Handoff: interface integrated in `model/temporal.py`; no performance claim until eligible external validation.

### TASK-006 — Validate model choices on eligible external data
- Status: blocked
- Priority: P1
- Owner: unassigned
- Depends on: TASK-005; accessible external labeled match data
- Goal: Compare model variants and select parameters using a match other than the provided BAR-ATH game.
- Scope: external-data provenance, mapping into the same possession definition, evaluation and parameter-selection record.
- Acceptance criteria: source, license/access, annotation provenance and quantity are documented; comparisons use external labels only; results and the chosen configuration are reproducible.
- Verification: record dataset identity, code/configuration hashes, commands and results in `docs/verification/TASK-006.md`.
- Evidence: pending; no eligible external labeled data has been identified.
- Blocker: accessible labeled external game with compatible possession definitions is unavailable.
- Last updated: 2026-11-08
- Handoff: identify eligible data or explicitly defer supervised validation; do not claim the current model beats the baseline.

### TASK-007 — Prepare the reproducible submission package
- Status: planned
- Priority: P1
- Owner: unassigned
- Depends on: TASK-005; TASK-006 completed or explicitly deferred; registered team name
- Goal: Produce an exact validated team-named CSV and short technical document from one documented command.
- Scope: final configuration, input/code/dependency fingerprints, technical document, restricted-data review and delivery checklist.
- Acceptance criteria: exact team-named CSV passes the official validator; repeated generation hashes match; document covers approach, assets, training-data provenance, possession rules, limitations and reproduction; no restricted assets or reconstructive exports are tracked.
- Verification: official validator, repeat hash, clean-clone reproduction instructions, diff and Git content review; record in `docs/verification/TASK-007.md`.
- Evidence: pending; current `temporal_v2.csv` is a validated prototype, not a final team-named submission.
- Blocker: team name and final method selection are outstanding; publication and form submission require separate authorization.
- Last updated: 2026-11-10
- Handoff: check upstream revision before final preparation; ask the owner for the registered team name and submission authorization when the package is ready.
