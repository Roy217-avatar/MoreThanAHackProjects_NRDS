# TASK-011 — Project Git isolation (2026-11-11)

The project previously lived in `MoreThanAHackProjects_NRDS/MoreThanAHackProjects_NRDS/`.
Its parent folder and the user's home folder each had a separate `.git` directory.
The home Git root made unrelated folders appear connected to Source Control.

The nested project's contents, including its `.git`, `.venv`, and ignored `data/`,
were moved into `/Users/nathanaelsagala/MoreThanAHackProjects_NRDS/`.
The nested project commit `97c9092fc11baf489bfa5921da188c71f4a30e42`
and its `origin` remote were preserved. The old outer placeholder README and Git data
are in `/Users/nathanaelsagala/MoreThanAHackProjects_NRDS/.git.outer-backup-20261111/`.
The home Git data was renamed to
`/Users/nathanaelsagala/.git.home-backup-20261111/`.
Both backups are recoverable; neither is an active `.git` directory.
The outer backup is locally ignored in `.git/info/exclude`.

Verification from the new project root:

```bash
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
.venv/bin/python -m unittest discover -s tests
.venv/bin/python evaluation/validate_submission.py evaluation/results/temporal_v4.csv
.venv/bin/python model/run.py --config model/config_v4.json \
  --output /private/tmp/temporal_v4_after_git_migration.csv \
  --diagnostics /private/tmp/temporal_v4_after_git_migration_diagnostics.csv
.venv/bin/python evaluation/validate_submission.py \
  /private/tmp/temporal_v4_after_git_migration.csv
shasum -a 256 evaluation/results/temporal_v4.csv \
  /private/tmp/temporal_v4_after_git_migration.csv
```

Results: Git root is `/Users/nathanaelsagala/MoreThanAHackProjects_NRDS`;
HEAD is `97c9092fc11baf489bfa5921da188c71f4a30e42`.
`git rev-parse --show-toplevel` in the home folder exits 128 (no Git repository).
All 50 tests passed. The official validator accepted both `temporal_v4.csv` and the
regenerated CSV with 199,319
ordered frames, 0–199318, and legal H/A/D/X labels. The regeneration and original
both have SHA-256 `9b14309313b4d5e163d8513b06c1c87afcfbb489b3259f3f7f647d5a4955a655`.
This confirms that relocating the files did not change the generated predictions;
it is not a model accuracy check.

No commit, push, or challenge submission was made as part of this migration.
Keep both backup directories until the new VS Code window shows only the intended
repository. To restore either former Git root, move its backup back to `.git` only
after checking that no current `.git` exists at that location.
