# PRD — Agent Workflow and Task Management

Status: Draft for implementation
Project: More than a Hack 2027 — Ball Possession
Audience: Repository contributors and coding agents

## 1. Purpose

Establish a lightweight, repository-based workflow that turns a user request into scoped tasks, verified changes, and an evidence-backed handoff. Support collaboration between contributors without losing decisions, duplicating work, or reporting unverified results as complete.

AGENTS.md defines how agents must behave. This PRD defines the workflow to implement and its acceptance criteria. TASKS.md, once created, records current execution state. Official competition rules remain authoritative for challenge requirements. This PRD does not itself create a task tracker, implement a classifier, or authorize publication.

## 2. Goals and scope

The workflow must:
- Make the next actionable task, its dependencies, and its completion criteria clear.
- Preserve progress and decisions across agent sessions.
- Require verification before work is marked done.
- Keep source data and credentials out of repository history.
- Support a reproducible possession pipeline and submission package.

The first version uses Markdown and Git. It does not require a dashboard, project-management service, cloud backend, or autonomous multi-agent orchestration. A single agent can execute the full workflow. Delegation occurs only when explicitly authorized by the user or applicable instructions.

## 3. Users and responsibilities

| Role | Responsibility |
| --- | --- |
| Project owner | Sets priorities, resolves consequential ambiguity, reviews delivered work, authorizes publication/submission |
| Implementing contributor or agent | Scopes tasks, maintains status, implements changes, runs checks, records evidence |
| Reviewer | Reviews scope, diff, verification and limitations; may be the project owner |

Agent self-review is required even when a separate reviewer participates. User review does not replace verification. Routine reversible work within an existing request must continue without repeated approval requests.

## 4. Repository records

Create these during workflow initialization; paths below describe intended files, not existing artifacts:

| File | Purpose |
| --- | --- |
| AGENTS.md | Agent rules and project safeguards |
| PRD.md | Workflow requirements and acceptance criteria |
| TASKS.md | Single source of truth for task state and dependencies |
| docs/DECISIONS.md | Material choices, rationale, alternatives and consequences |
| docs/verification/ | Per-task verification notes and safe, concise evidence |
| README.md | Setup, input configuration, execution and reproduction commands |

Do not duplicate the task board in multiple files. Exclude restricted data and verbose/raw logs from tracked evidence. Existing equivalent files may be reused after documenting the mapping.

## 5. Task contract

Every substantive task must include:

```markdown
### TASK-001 — Short outcome-based title
- Status: planned
- Priority: P1
- Owner: unassigned
- Depends on: none
- Goal: observable behavior or artifact
- Scope: included changes and relevant paths
- Acceptance criteria: concrete, checkable conditions
- Verification: checks or commands; expected outcomes
- Evidence: pending
- Blocker: none
- Last updated: YYYY-MM-DD
- Handoff: next step and remaining limitations
```

Use stable unique IDs. P0 means a correctness/compliance blocker, P1 means required for the project, and P2 means optional improvement. Priority never overrides dependencies. Split work when outcomes can be delivered independently; avoid tasks that are only vague activities such as “improve the model.”

## 6. Lifecycle and execution

Allowed statuses: planned, ready, in_progress, verifying, done, blocked, cancelled.

| Transition | Required condition |
| --- | --- |
| planned → ready | Scope and acceptance criteria are clear; dependencies and required inputs are available |
| ready → in_progress | Owner claims the task and checks current repository state |
| in_progress → verifying | Implementation is complete enough to exercise acceptance criteria |
| verifying → done | Required applicable checks pass, evidence is recorded, and the diff has been reviewed |
| verifying → in_progress | A check fails or review finds a defect |
| Any unfinished status → blocked | A specific missing dependency or unresolved decision prevents progress |
| blocked → ready | Blocker is resolved and dependencies are rechecked |
| done → ready | New evidence invalidates completion or a related change requires rework |
| Any status → cancelled | Cancellation or superseding scope is recorded with a reason |

Do not mark partial work done. Record completed independent work separately when one part is blocked. “Done” means technically verified for that task, not user approval, deployment, or organizer acceptance.

At session start, read AGENTS.md, PRD.md, TASKS.md and relevant decisions; inspect Git status and existing work. Choose the highest-priority ready task within the authorized request. Record ownership before editing. If scope changes, update acceptance criteria before continuing and record any material decision.

At handoff, update task state, evidence, blockers and the next action. A new session must be able to resume without relying on chat history. Before overlapping edits, agree on file ownership; preserve others' changes and resolve shared-file edits sequentially.

## 7. Verification gate

For each task:
1. Compare the actual diff with scope and acceptance criteria.
2. Run relevant existing checks and meaningful tests for changed behavior.
3. Inspect produced artifacts and edge cases, rather than relying only on exit status.
4. Fix failures; rerun affected checks after the final edit.
5. Record the command, input/configuration identity, code revision or working-tree state, result, and artifact path in docs/verification/TASK-ID.md.
6. Keep skipped checks explicit. If required evidence is unavailable, mark the task blocked/unverified and explain why.

Documentation-only tasks require content and consistency review, not fabricated execution tests. A submission task additionally requires the official validator on the exact delivered CSV and a repeated generation with matching output hashes. Verification notes must distinguish passed, failed, not run, and not applicable.

The final user response must briefly state what changed, checks performed and their results, deliverable paths, and material limitations. Never claim full-match scores, successful tests, or organizer acceptance without observed evidence.

## 8. Possession-project safeguards

Apply all current AGENTS.md rules. In particular:
- Preserve the official tactical frame contract and H/A/D/X export labels.
- Keep official evaluation code unchanged for reported metrics.
- Do not create manual labels/corrections for the provided match or use its public labels for training, tuning or model selection.
- Use synthetic cases for logic checks and eligible external games for supervised validation.
- Treat public-window scoring only as a pipeline check.
- Do not commit restricted assets, reconstructive derivatives or credentials.
- Do not silently change the agreed possession definition or frame alignment.

Keep diagnostics separate from the submission file. Store parameter-selection rationale and training-data provenance alongside the implementation. Do not use public-window scores as a task acceptance target for choosing between algorithms.

## 9. Initial backlog

These tasks are proposals; none is claimed complete by this document.

| ID | Outcome | Dependencies | Acceptance evidence |
| --- | --- | --- | --- |
| TASK-001 | Initialize workflow records and reproducible environment | None | Task board, documented setup, dependency installation check |
| TASK-002 | Verify upstream baseline/scorer pipeline | TASK-001 | Unmodified scorer executes on included examples; check results recorded |
| TASK-003 | Audit authorized tracking/Excel inputs and frame alignment | TASK-001; data access | Schema/coverage report and synthetic indexing tests |
| TASK-004 | Generate a reproducible initial full-length prediction | TASK-002, TASK-003 | Official validator passes; exact generation command recorded |
| TASK-005 | Add robust temporal possession inference | TASK-004 | Missingness/transition tests pass; legal selection rationale documented |
| TASK-006 | Evaluate additional tagging/motion evidence | TASK-005 | Reproducible experiments and eligible evidence justify retention or rejection |
| TASK-007 | Prepare final reproducible submission package | TASK-005; TASK-006 resolved or explicitly deferred | Validated CSV, matching reproduction hashes, code and technical document |

TASK-006 is optional; do not delay a valid submission solely to expand features. Keep publication and form submission as separate authorized actions after package preparation.

## 10. Workflow acceptance criteria

The workflow is ready when:
- Every active substantive task has an ID, owner, scope, dependencies and acceptance criteria.
- The task board permits a new session to identify the next action and blockers.
- No task is marked done while required checks are failed or unrun.
- Evidence identifies the checked code/configuration and the actual artifact delivered.
- A failed check returns work to implementation or blocked status.
- Synthetic exercises cover one successful task, one failed verification, one blocked task, and one session handoff.
- The final project package can be regenerated without redistributing restricted data.

Measure success by traceability and reproducibility, not task counts or unsupported accuracy targets. Reopen any completed task whose evidence becomes stale after relevant changes.
