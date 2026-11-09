# Task board — 2026-11-08

The upstream public starter is pinned at `f8f2629ff1e0985f81d7e59d8413678514ee1530`.
Statuses describe completed work in this checkout; no private-match score or organizer submission exists.

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
- Verification: commands in README and `docs/verification/TASK-004.md` when inputs arrive.
- Evidence: `docs/verification/TASK-004.md` records official validator result, diagnostics, and matching repeat hashes.
- Blocker: none for generation; model quality remains unvalidated against eligible external labels.
- Last updated: 2026-11-08
- Handoff: evaluate dead-ball detection and turnovers on eligible external games; do not tune to the public five minutes.
