# V4 CA Targeted Schedule Evidence V1 — pytest import remediation

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`

## Trigger

The first user-run local validation stopped before provider access during pytest collection:

`ModuleNotFoundError: No module named 'run_v4_ca_schedule_acquisition'`

`py_compile`, dependency import preflight, and `git diff --check` passed. No KSEI/provider request and no output root were created by the failed pytest collection.

## Root cause

`run_v4_ca_targeted_schedule_evidence.py` is a direct script and intentionally imports the existing sibling runner `run_v4_ca_schedule_acquisition` by its direct-script module name. Direct execution (`python scripts/...py`) puts the `scripts` directory on Python's import path. Pytest instead imports the targeted runner via the `scripts.*` namespace, so the sibling direct-script module was not visible during collection.

## Remediation

Only `tests/test_v4_ca_targeted_schedule_evidence.py` was changed. The test harness now adds the repository `scripts/` directory to `sys.path` before importing the targeted direct runner, matching its actual local execution environment.

No provider/scientific source, selected event identity, parser, CA semantic, gate, target, model, evaluator, config, or artifact pin changed.

Remediation commit: `4f3ecf8f5d433c8835d0581dfb0f6664c4281074`.

Expected focused validation remains `11 passed`.

## Additional local hygiene finding

The user's primary checkout contained an unrelated untracked `apps/` directory. The handoff requires a clean worktree, so the provider run must not proceed from that dirty checkout. Use a fresh dedicated worktree for this branch; do not delete or stash `apps/` as part of this lane.

## Boundary

This is a pre-provider engineering/test-harness correction. No result was exposed and no post-result rescue was performed. The frozen seven-event acquisition/replay policy remains unchanged.
