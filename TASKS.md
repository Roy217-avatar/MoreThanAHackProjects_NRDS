# Task board — 2026-11-08 handoff

The upstream public starter is pinned at `f8f2629ff1e0985f81d7e59d8413678514ee1530`.
Statuses describe completed work in this checkout; no private-match score or organizer submission exists.

## Start here tomorrow (2026-11-09)

The next ready task is **TASK-005**. Review the current model's dead-ball and turnover logic,
add focused synthetic tests, and improve the algorithm only where a general rule justifies it.
Do not use the public five-minute labels or this match's output diagnostics to choose thresholds.
After a change, generate the ignored CSV twice, compare hashes, validate the exact final file,
and update the task's verification record. Exact commands are in `README.md`.

Current local output: `evaluation/results/temporal_v1.csv` (ignored by Git), SHA-256
`fe13eb9a04a544532c757bac2e6df0cc3f63f68c40f48384ca218a0e9b677c78`.
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

### TASK-005 — Strengthen temporal possession inference
- Status: ready
- Priority: P1
- Owner: unassigned
- Depends on: TASK-004
- Goal: Improve general dead-ball, restart, and controlled-turnover behavior without fitting to this match's public labels.
- Scope: `model/`, versioned configuration, synthetic tests, model rationale and diagnostics.
- Acceptance criteria: new behavior has a general rule and synthetic edge-case tests; missing ball never implies dead play; incidental touches do not flip possession; halftime state resets; full-length output validates and repeats with an identical hash.
- Verification: unit tests, official validator on the exact generated CSV, two generation hashes, aggregate diagnostics and diff review; record results in `docs/verification/TASK-005.md`.
- Evidence: pending; current prototype and six passing tests are recorded under TASK-003/004.
- Blocker: none for synthetic and algorithm work; accuracy claims require TASK-006.
- Last updated: 2026-11-08
- Handoff: claim TASK-005 first tomorrow; preserve `temporal_v1.csv` as the existing reference and version any changed output/configuration separately.

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
- Evidence: pending; current `temporal_v1.csv` is a validated prototype, not a final team-named submission.
- Blocker: team name and final method selection are outstanding; publication and form submission require separate authorization.
- Last updated: 2026-11-08
- Handoff: check upstream revision before final preparation; ask the owner for the registered team name and submission authorization when the package is ready.
