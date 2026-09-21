# IDX-Trade Operational Shadow Root Rehearsal V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS SYNTHETIC / REAL QUALIFICATION STILL BLOCKED**

## Purpose and lane boundary

This record documents the first operationally-shaped rehearsal in the
isolated shadow lane. It exercises multi-session continuation and the
operational controller against synthetic data only. It is not a migration,
historical replay, provider run, canary, production run, or access to the
active alpha/model lane.

The dedicated output root is:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-operational-shadow`

No files were written to the active E2E runtime, scheduler state, provider or
cloud/R2 roots, canonical data, counters, protected outcomes, or live capture.
The synthetic continuation output contains positions, pending buys,
entitlements, and settlements by design; these are test fixtures and are not
real portfolio state.

## Source identity

| Item | Exact value |
|---|---|
| Shadow worktree | `C:\Users\Sam\.codex\worktrees\idx-shadow-runtime-precanary-20260921` |
| Branch | `codex/idx-shadow-runtime-precanary-20260921` |
| HEAD used by controller attestation | `54517b4c10a88830a3fe84aeaac6a04bb979cfa7` |
| Worktree state at controller run | clean |
| Calendar input | `C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-extended-evidence\inputs\sessions\exchange_sessions.csv` |
| Calendar SHA-256 | `3a3bdb6db642e26eaee9b5d9f85b0e1ac16e9d6a70ea3ddd60c0d032e99c6279` |
| Calendar rows | 516 |

## Exact continuation command

The command was run with the shadow checkout explicitly pinned on
`PYTHONPATH`:

```powershell
$env:PYTHONPATH='C:\Users\Sam\.codex\worktrees\idx-shadow-runtime-precanary-20260921\src'
python scripts/run_e2e_paper_synthetic_replay_v1.py --output-dir C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-operational-shadow\continuation
```

The controller rehearsal used the existing controller implementation with an
isolated `runtime_root` under the operational-shadow root, the copied
historical-calendar input above, the isolated repository root, and an
isolated `official_open_root`. The controller clock was deliberately set to
`2026-08-23T12:00:00+07:00`, a Sunday, to exercise the no-official-session
no-op path without invoking a provider or execution path.

## Continuation result

| Measure | Result |
|---|---|
| Status | `SYNTHETIC_REPLAY_PASS` |
| Sessions | 5 |
| Exact rerun fence | `ALREADY_COMPLETE` |
| CA extension exercised | `true` |
| Provider calls | `false` |
| Protected outcomes accessed | `false` |
| Missing-open recovery case | Session 3 omitted synthetic `T09` Open and carried a pending buy to the next session |
| Acceptance-summary outer SHA-256 | `14ec4bab4dff41e2e683b6847b917acdac20a9c7c9f72e5585d114f78a375e1b` |
| Acceptance-summary body `summary_sha256` | `a69632e8a8bcdc7a8da3919b262b535e49ab75080598e9add1d948b986b20ba5` |
| Synthetic marker | `synthetic_only=true` |

The final synthetic state includes positions, pending/settled obligations,
and dividend entitlements. This confirms continuation serialization and
recovery behavior only; it is not evidence of a real paper-state ledger.

## Controller result

| Measure | Result |
|---|---|
| Controller status | `WEEKEND_OR_HOLIDAY_NOOP` |
| Reason | `NO_OFFICIAL_SESSION_TODAY` |
| Decision/execution session | none |
| Provider calls | `false` |
| Model refit | `false` |
| Model rescore | `false` |
| Protected outcome access | `false` |
| Persisted status path | `...\\operational-shadow\\controller\\operational\\latest.json` |
| Persisted status outer SHA-256 | `33218646bf1c7f57f49f34bd76c5d4a7e7e4bfb87b862b7a464efe5c30512a4c` |

The persisted status attests the shadow branch, clean checkout, expected
commit, and 516-row calendar input. The status JSON intentionally has no
internal status hash field; the value above is the hash of the persisted file
itself.

## Output inventory

The initial continuation/controller rehearsal contained 72 files and 788,621
bytes:

| Subroot | Files | Bytes |
|---|---:|---:|
| `continuation` | 70 | 787,675 |
| `controller` | 2 | 946 |
| **Total** | **72** | **788,621** |

The same dedicated root was then extended, without touching the initial
subroots, by the separate fallback and identity-interface challenges. Its
current total is 89 files and 810,687 bytes:

| Current subroot | Files | Bytes |
|---|---:|---:|
| `continuation` | 70 | 787,675 |
| `controller` | 2 | 946 |
| `fallback` (fixture stopped before snapshot) | 1 | 25 |
| `fallback-v2` (fixture stopped before snapshot) | 1 | 25 |
| `fallback-v3` (successful rehearsal) | 10 | 17,136 |
| `identity-interface` | 5 | 4,880 |
| **Current total** | **89** | **810,687** |

## Gate impact

| Gate | Result | Boundary |
|---|---|---|
| SHADOW CONTINUATION | PASS SYNTHETIC / BLOCKED REAL | Five-session continuation and exact-rerun fence passed; no real operational state was admitted |
| RECOVERY | PASS SYNTHETIC / BLOCKED REAL | Missing-open/pending-buy path was exercised with fixtures only |
| OPERATIONAL CONTROLLER | PASS SYNTHETIC | Weekend/holiday no-op persisted without external side effects |
| FORWARD FALLBACK | PASS SYNTHETIC / BLOCKED REAL | Separate V2 freeze/stop/failure/repair/resume rehearsal is recorded in `2026-09-21_IDX_FORWARD_FALLBACK_REHEARSAL_V1.md`; no real state was available |
| PRE-CANARY READINESS | NO-GO | Missing real paper-state, CA obligation/settlement chain, calendar authority, differential, and recovery evidence remains |

This rehearsal does not change the master dossier's real-artifact verdicts.
It adds durable, hash-attested synthetic evidence while preserving the
fail-closed real qualification boundary.
