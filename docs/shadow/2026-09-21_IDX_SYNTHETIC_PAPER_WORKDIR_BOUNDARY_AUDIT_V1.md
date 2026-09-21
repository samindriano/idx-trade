# IDX-Trade Synthetic Paper-Workdir Boundary Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **SYNTHETIC EXCLUSION CONFIRMED / NOT REAL-STATE INPUT**

## Why this audit exists

The local project directory contains workdirs whose names and filenames look
like historical paper runtime roots. Several contain `state_snapshots`,
`prepared`, `executions`, and transaction JSON files. The goal requires
classifying provenance before admitting any such artifact as real historical
E2E paper state.

This audit reads only small acceptance/progress metadata and file metadata. It
does not copy, mutate, or execute these roots, and it does not read protected
outcomes or provider content.

## Roots inspected

| Root | Files | Bytes | Provenance marker |
|---|---:|---:|---|
| `D:\Documents\Project\idx-e2e-paper-production-replay-20260823-v1` | 139 | 331,917 | `synthetic_only=True`, 5 sessions |
| `D:\Documents\Project\idx-e2e-paper-cold-restart-20260823-v1` | 140 | 332,996 | `synthetic_only=True`, 5 sessions, cold restart |
| `D:\Documents\Project\idx-historical-e2e-synthetic-production-replay-20260824-v1` | 139 | 334,842 | `synthetic_only=True`, 5 sessions |
| `D:\Documents\Project\idx-e2e-paper-deterministic-oracle-20260823-v1` | 3 | 6,348 | oracle/test output only |
| `D:\Documents\Project\idx-historical-e2e-replay-readiness-20260823-v3` | 14 | 5,384,276 | `status=HISTORICAL_E2E_REPLAY_BLOCKED_BY_DATA` |

The three replay-shaped roots use the same acceptance schema identifier:
`idx_trade_e2e_paper_production_replay_v1`. Their acceptance summaries
explicitly set `synthetic_only=True`; this is direct provenance evidence, not
an inference from directory names.

## State-like files found, and disposition

The replay-shaped roots contain files such as:

- `forward_execution_v1_1/state_snapshots/<session>.json`;
- `prepared/<session>.json`;
- `executions/<session>.json` and `executions/.transactions/<session>.json`;
  and
- `state/decisions/<session>.json`.

Their JSON schema names are internally coherent (`idx_trade_forward_dividend_runtime_state_v1_1`,
`idx_trade_e2e_paper_prepared_execution_v1`,
`idx_trade_e2e_paper_execution_transaction_v1`, and
`idx_trade_e2e_paper_meta_v1`), but the enclosing acceptance provenance is
explicitly synthetic. The files are therefore useful synthetic fixtures only.

They are **not** admitted into the real immutable shadow manifest, are not
counted as real V1/V2 snapshots, and are not evidence of real migration,
historical replay, CA composition, or recovery.

The replay-readiness root is separately blocked by data according to its own
manifest status. It also is not a real-state admission.

## Bounded test-family directory scan

A metadata-only scan of top-level roots explicitly labelled
`idx-dual-calendar-*`, `idx-e2e-*`, or `idx-trade-test-tmp-*` found:

- 45 test/pytest/e2e roots containing runtime-shaped directories;
- 737 `state_snapshots` directories; and
- 453 `prepared` directories.

These paths are nested under `test_*`, `pytest`, `test-tmp`, or
dual-calendar/e2e fixture roots. They are retained as test evidence only and
were not admitted as real history because no historical-runtime provenance,
real session binding, or immutable source/copy package was established for
them. The scan did not open file contents.

A second path-only scan over the full local project tree matched 3,490 files
under `state_snapshots`, `prepared`, `.transactions`, `paper_state*`, or
`runtime_state*`. They belonged to 58 top-level roots; all 58 were explicitly
test/pytest/e2e/dual-calendar roots and `non_test_roots=0`. This broader scan
also opened no file contents and did not promote any match to real state.

## Result

This audit closes a potential false-positive inventory path: state-like
filenames alone do not establish historical runtime provenance. The accessible
local inventory now has an explicit exclusion record for these synthetic roots.

`REAL ARTIFACT DISCOVERY = PASS WITH LIMITATION`

`REAL MIGRATION = BLOCKED BY ABSENT ADMITTED PAPER STATE`

`SYNTHETIC CONTINUATION = PASS / KEPT SEPARATE`

`PRE-CANARY READINESS = NO-GO`
