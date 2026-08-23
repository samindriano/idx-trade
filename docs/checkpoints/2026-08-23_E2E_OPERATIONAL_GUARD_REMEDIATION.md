# Controlled Live E2E Paper Operationalization — Guard Remediation

Date: 2026-08-23 Asia/Jakarta  
Branch: `integration/idx-e2e-baseline-paper-v1`  
Parent: `1ef978a24d8c74958e25e5d351c4c2232d9937a2`

## Scope

This checkpoint records the first bounded remediation after the independent
read-only operational audit. It does not install or modify a Windows task, call
IDX/Zapi, access outcomes, bootstrap T0, or create a second data/ledger path.

## Findings addressed

The audit found that the standalone E2E PREOPEN/POST_EOD consumers could be
invoked outside their intended phase and that the new operational path needed
an explicit deployment identity and interprocess lock. The remediation adds:

- same-Jakarta-date PREOPEN enforcement for 09:02:00 through 09:22:59;
- POST_EOD enforcement from 18:00 Jakarta onward;
- exact branch, HEAD, and clean-worktree attestation before operational work;
- an OS-level exclusive runtime lock that is released by process termination;
- atomic operational status writes;
- a deterministic controller boundary that records weekend/holiday, waiting,
  missed-window, upstream-not-ready, and missing-CA-input states without
  inventing data or silently backfilling.

The existing canonical EOD, official Open, V4-X1, and dividend components
remain the only source/runtime components. The controller currently stops at
`WAITING_CA_RECONCILIATION` until an explicitly configured existing V1.2 CA
attestation/journal is present; it does not make provider calls by itself.

## Current operational audit evidence

Read-only Windows inspection found the existing tasks:

- `IDXTrade-E2E-OfficialOpen`: enabled, five 09:02–09:22 retries plus
  `AtLogOn`, current official Open runtime, weekend result 0;
- `IDXTrade-ForwardEOD`: enabled, existing canonical EOD/V4-X1 path;
- `IDX-Trade Stockbit Intraday Daily`: separate existing task, unchanged;
- `IDXTrade-ForwardOpenArchive`: disabled legacy task, unchanged.

No task was installed or modified in this remediation. The E2E runtime root
contains official-Open evidence but no T0 or paper execution state yet. No
weekday E2E proof is therefore claimed.

## Validation

- focused guard/orchestration/runtime tests: PASS;
- `py_compile` for new guard, controller, and E2E scripts: PASS;
- `git diff --check`: PASS;
- no provider call;
- no model fit/rescore/refit;
- no outcome access;
- no scheduler mutation.

The full repository suite and a fresh deterministic operational acceptance run
remain required after this remediation is pushed. The final state remains
`CONTROLLED_LIVE_E2E_ARMED_WEEKDAY_PROOF_PENDING` only after the remaining
controller integration and deployment review are complete; this checkpoint
itself is not a live-cycle pass.
