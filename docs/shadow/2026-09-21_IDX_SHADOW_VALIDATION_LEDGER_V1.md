# IDX-Trade Shadow Validation Ledger V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **CURRENT SHADOW SOURCE VALIDATION PASS / QUALIFICATION STILL FAIL-CLOSED**

## Source identity

- Shadow branch: `codex/idx-shadow-runtime-precanary-20260921`
- Documentation/source HEAD at validation start: `59a937fe38129123353865bf270e9a5159949434`
- Candidate code revision under review: `5c14b036ee179532903e1d0fd32d486db06cf3c7`
- Candidate code was not changed by this validation; only read-only tests and
  collection were run.

## Test validation

| Check | Command/result |
|---|---|
| Full suite | `PYTHONPATH=...\\src python -m pytest -q` |
| Full suite outcome | 100% completion, exit code `0` |
| Collected tests | `907` tests across `128` test files |
| Collection outcome | `python -m pytest --collect-only -q`, exit code `0` |
| Warnings | 3 pre-existing pandas `FutureWarning`s; no new failure or error |

The full suite was run against the pinned shadow source path. No live runtime,
provider, scheduler, cloud/R2, protected outcome, counter, alpha, or canonical
data surface was accessed.

## Documentation consistency validation

- Required durable-output references: `15/15` present;
- Phase coverage rows: exact `0` through `18` (`19/19`);
- `git diff --check`: pass;
- branch HEAD and remote shadow branch: equal;
- worktree: clean after the documentation commit.

## Qualification boundary

This ledger proves current source/test and documentation integrity only. It does
not promote synthetic tests to real-state evidence and does not clear the real
migration, historical replay, CA composition, recovery, identity authority,
pre-canary, or production gates.
