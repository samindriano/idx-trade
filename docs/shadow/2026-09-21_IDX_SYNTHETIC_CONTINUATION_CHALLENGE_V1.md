# IDX-Trade Synthetic Shadow Continuation Challenge V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS SYNTHETIC / REAL QUALIFICATION STILL BLOCKED**

## Scope and boundary

This is a bounded local contract challenge in the isolated shadow worktree
only. It is not a real-runtime migration, historical replay, fallback
rehearsal, canary, or production test.

The selected tests use pytest-managed temporary directories (`tmp_path`) and
synthetic fixtures. They do not read or write the active E2E runtime, forward
monitoring state, provider roots, protected outcomes, counters, cloud/R2,
scheduler state, canonical data, or the alpha/model lane.

## Exact reproduction

Worktree:

`C:\Users\Sam\.codex\worktrees\idx-shadow-runtime-precanary-20260921`

Branch before this documentation update:

`codex/idx-shadow-runtime-precanary-20260921` at `d0306a19`

Command:

```text
pytest -q tests/test_idx_authoritative_runtime_shadow_migration_v1.py tests/test_forward_dividend_runtime_v1_1.py tests/test_e2e_paper_operational_controller_v1.py tests/test_e2e_paper_orchestration_v1.py
```

The selected files collected 86 tests:

| Test file | Collected |
|---|---:|
| `test_idx_authoritative_runtime_shadow_migration_v1.py` | 2 |
| `test_forward_dividend_runtime_v1_1.py` | 31 |
| `test_e2e_paper_operational_controller_v1.py` | 19 |
| `test_e2e_paper_orchestration_v1.py` | 34 |
| **Total** | **86** |

Observed result: **86 passed, exit code 0**. No retry was performed.

## Contract surfaces exercised

- shadow migration state-hash/replay preservation;
- immutable partial-record behavior after a write failure;
- snapshot tamper, parent-chain, fork, quarantine, and verified-ancestor
  recovery guards;
- dividend/corporate-action entitlement and receivable/restart contracts;
- operational-controller timeout, child-failure, no-op, prepared-selection,
  terminal-recovery, and side-effect/replay-fence contracts;
- orchestration T0/next-session, identity, replay-tamper, recovery, CA,
  pending-buy, and missing-open contracts.

These are contract-level synthetic checks. Passing them demonstrates that the
candidate's local test surfaces remain internally coherent; it does not prove
that any corresponding real artifact exists or that the active runtime can be
migrated.

## Gate impact

| Gate | Result after this challenge | Reason |
|---|---|---|
| SHADOW CONTINUATION | PASS SYNTHETIC / BLOCKED REAL | Synthetic continuation/recovery contracts pass; the later operational shadow root contains synthetic outputs only and admits no real operational state |
| RECOVERY | PASS SYNTHETIC / BLOCKED REAL | Synthetic tamper/fork/ancestor tests pass; no real recovery chain was admitted |
| FORWARD FALLBACK | DESIGN ONLY | These tests do not constitute a forward fallback rehearsal or runtime repin |
| PRE-CANARY READINESS | NO-GO | Missing real paper-state, CA, calendar-lineage, differential, and recovery evidence remains unchanged |

## Non-goals and safety result

No production entrypoint, provider/outcome access, scheduler invocation,
counter mutation, cloud/R2 operation, canonical-data rewrite, alpha/model
operation, or active-runtime write was performed. The challenge therefore
adds synthetic evidence only and leaves all real gates fail-closed.
