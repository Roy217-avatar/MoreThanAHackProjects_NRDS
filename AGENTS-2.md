# AGENTS.md

Repository rules for the More than a Hack 2027 ball-possession project. Apply these instructions whenever working in this repository.

## SetUp

- Read the user's current request, this file, README, and any applicable directory instructions. Inspect the repository and Git status before editing; preserve unrelated work.
- Identify the relevant modules, existing implementation, configuration, and tests. State material assumptions instead of guessing missing data or requirements.
- Consult the official challenge source: https://github.com/metrica-sports/more-than-a-hack-2027/ . Read CHALLENGE.md, DATA.md, RULES.md, EVALUATION.md, SUBMISSION.md and FAQ.md during initial setup; revisit relevant sections when requirements are uncertain. Record the upstream revision and check for changes before final submission preparation.
- Use the repository's documented Python environment and dependency files. Prefer existing starter loaders, games.py, and asset-path helpers over replacements. Locate authorized inputs through MTAH_DATA_DIR or project configuration.
- Inspect actual input schemas and alignment before implementing inference. Treat Excel as a possible export, not an assumed official format. Do not require large video downloads merely to inspect tracking data.
- Start with the smallest useful implementation and relevant checks. Ask only when missing information blocks a consequential decision; continue independent work where possible.

## Standards

- Goal: generate possession labels for every tactical-video frame, using a reproducible algorithm. The current official contract is 199,319 frames at 25 fps.
- Export labels: H = home possession while live; A = away possession while live; D = dead ball; X = abstention. Barcelona is home; Athletic Club is away.
- A possession changes only when the opponent gains control. Loose or contested live balls remain with the last controlling team. An incidental touch or deflection alone is not a turnover.
- Prioritize coherent possession intervals: spellF1 determines ranking; macroF1 is the first tie-break. Use the official scorer unchanged for reported competition metrics.
- Keep ingestion, frame alignment, features, temporal inference, and export separate. Use explicit configuration for thresholds and mappings. Document units and justify assumptions.
- Make outputs deterministic. Record input fingerprints, configuration, seeds, dependencies, upstream revision, and code version.
- Keep changes focused and reviewable. Update documentation when commands, behavior, dependencies, or assumptions change.
- Keep source data read-only. Exclude restricted assets, reconstructive exports, caches, and credentials from Git. Keep Drive tokens private; fetch only needed inputs.

## Checks

Before reporting completion:

1. Review the actual diff against the user's request. Check for omissions, unintended edits, stale comments, hardcoded paths, and unsupported assumptions.
2. Run relevant existing tests and checks. For inference or alignment changes, cover synthetic cases involving missing observations, frame boundaries, team changes, stoppages, and halftime. Fix failures and rerun affected checks.
3. Exercise the changed workflow with available authorized inputs. Inspect generated artifacts rather than assuming a successful process produced correct results. Check time coverage, NaNs, label distributions, and implausible fragmentation as diagnostics, not answer keys.
4. For a generated submission, verify exactly two columns, frame,label; 199,319 data rows; ordered unique frames 0–199318; labels only H/A/D/X; no blank values or extra index. Run the official validator on the exact file to be delivered:
   `python evaluation/validate_submission.py <team_name>.csv`
5. Use `python evaluation/run_evaluation.py` only for permitted public pipeline checks, never parameter or model selection. Label public-window scores accurately.
6. For final delivery, rerun the documented generation command with the same inputs and configuration and compare output hashes. Check dependency and reproduction instructions.
7. Check for data leakage, secrets, restricted files, and accidental edits to official evaluation code. Confirm compliance with the rules below.
8. Report what changed, what was actually checked, results, and remaining limitations. If checks could not run, name the missing input or dependency and mark the work unverified. Never invent test results or claim completion with unresolved failures. Apply relevant checks to each task; do not claim submission validation when no submission was generated.

## Watch-outs

- Do not hand-label or manually correct this match, its tracking, or predictions, even for validation. Do not turn video inspection into frame-specific answer constants.
- Do not train, tune, or select models using the public five-minute labels. They are pipeline checks only. Do not use private ground truth or human-produced annotations/events about this match. Eligible labeled external games must have documented, accessible provenance.
- Do not confuse tracking IDs with video frames: ATD uses `video_frame = frame_id - 1`; homography is already zero-based; tagging maps using `round(seconds * 25)`. Verify loader conventions before converting twice.
- Do not index submissions by broadcast frames; broadcast is not synchronized to tactical. Use official half boundaries and prevent temporal processing from leaking across halftime.
- Do not treat normalized coordinates as metres, track slots as stable player identities, nearest-player proximity as proof of control, or automatic tags as ground truth.
- Missing ball observations do not imply dead ball. Do not interpolate blindly through long gaps or smooth away genuine turnovers.
- X is not cost-free on graded frames: macroF1 penalizes it; temporal scoring fills abstentions within halves. Follow the official implementation for details.
- Do not infer full-match performance from the public window or substitute accuracy for spellF1.
- Do not publish restricted match assets or reconstructive derivatives. Final submission requires a public code repository, but publishing, pushing, or submitting must be authorized.
- Do not expand into a website, cloud backend, or replacement tracker unless the requested work needs it.

## Done

- For each task: the requested change is implemented, relevant checks pass, the diff is reviewed, documentation is current, and limitations are disclosed. Blocked work is reported as blocked, not finished.
- For the complete project: the final CSV passes the official validator and is reproducible from the provided data using one documented command and pinned dependencies.
- Submission materials include the CSV, a public code repository without restricted data, and a short technical document explaining the approach, assets, training-data provenance, possession rules, limitations, and reproduction.
- Diagnostics remain separate from the two-column submission. Deliver the exact checked artifact and identify its path. Do not imply organizer acceptance or a private-match score that has not been observed.
