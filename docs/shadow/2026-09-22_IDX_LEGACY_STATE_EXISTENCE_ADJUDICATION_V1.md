# IDX-Trade Legacy-State Existence and Operational History Adjudication V1

Date: 2026-09-22 (Asia/Jakarta)

Status: **LEGACY_STATE_CREATED_AND_RECOVERABLE / NONZERO HISTORY NOT EVIDENCED / PRE-CANARY NO-GO**

## Executive adjudication

The bounded audit found direct, hash-verified, loader-verified evidence that a
real paper-runtime state was created in the active runtime on 2026-09-21 at
18:35:04 WIB. The state is a fresh zero-holding T0 package: IDR 50,000,000,
zero positions, zero pending buys/sells, and zero receivables. It is therefore
recoverable as a real runtime state, and the required primary classification is:

`LEGACY_STATE_CREATED_AND_RECOVERABLE`

This classification must not be overread. The audit did **not** find evidence
of a nonzero historical portfolio, an execution/fill vector, prepared
execution, pending obligation, dividend settlement, or a prior snapshot chain.
The narrower question “did nonzero legacy economic history ever exist?” remains
`NOT_EVIDENCED` / `UNKNOWN`; it is not converted into a positive claim by the
fresh T0.

The earlier shadow census saying that no paper-state artifact was located was
accurate for its stated cutoff, 2026-09-21 16:10 WIB. The active runtime wrote
the new T0 and snapshot later at 18:35:04 WIB. This document is an amendment to
that historical census, not a rewrite of its prior observation.

## Scope and lane boundary

- Shadow branch: `codex/idx-shadow-runtime-precanary-20260921`
- Shadow worktree: `C:\Users\Sam\.codex\worktrees\idx-shadow-runtime-precanary-20260921`
- Active runtime root inspected read-only:
  `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1`
- Immutable evidence copy:
  `C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260922-legacy-state-adjudication`
- Active runtime code checkout was not changed.
- No provider call, scheduler mutation, cloud/R2 mutation, canonical-data
  rewrite, protected-outcome access, model refit/rescore, counter reset, or
  active-state overwrite was performed.
- The source state was copied once for audit evidence; source/copy hashes were
  matched after copying.

## Direct positive state evidence

| Artifact | Source size | Source SHA-256 | Creation / last-write UTC | Relevant facts |
|---|---:|---|---|---|
| `forward_execution_v1_1/state_snapshots/2026-09-21.json` | 1,174 bytes | `8258e9b39327252ecc252d5ffe2c1e19b636d9f625ffb629f6893f8fe2a5d006` | `2026-09-21T11:35:04Z` | schema `idx_trade_forward_dividend_runtime_state_v1_1`; session `2026-09-21`; previous snapshot `null`; cash `50000000.0`; positions/pending/receivables all zero |
| `t0/T0.json` | 691 bytes | `21781131e426c776c01bf27ea7eff79d21321b05a85abb7ce63c281aebf67791` | `2026-09-21T11:35:04Z` | schema `idx_trade_e2e_paper_t0_v1`; initial NAV `50000000.0`; historical dividend credit `false`; zero holdings; zero pending orders; zero receivables |

The T0 points to snapshot SHA `8258e9b39327252ecc252d5ffe2c1e19b636d9f625ffb629f6893f8fe2a5d006`.
The snapshot's embedded hashes are:

- base paper state: `d50b8c1ff45e3e369f27fa31b696c16f92ee7246fbd4fb219eb49f78f16dc5de`
- certified registry: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`
- dividend-aware state: `c7b6d6651fca6b2e2181fe60ab2fa091d6377f8e353ae0b31aaebd868a510cc8`
- dividend ledger: `f43dff0fabc508bec26ee9bc25430060c4fd2f5a64b49c9f89b303b1fac6e4f1`
- runtime state: `310a79450662c54e45c7c99238f0b5a185dbb3041e59190961c14a1e0dfabc46`

Source/copy equality was verified for the snapshot, T0, current operational
metadata, official-open metadata, and the three process summaries. The copied
snapshot and T0 retained the source hashes above.

## Loader verification

The copied snapshot was loaded through the runtime loader without writing to
the active root. The result was:

```text
runtime_schema_expected = idx_trade_forward_dividend_runtime_state_v1_1
loader_session = 2026-09-21
loader_file_sha256 = 8258e9b39327252ecc252d5ffe2c1e19b636d9f625ffb629f6893f8fe2a5d006
t0_pointer_matches = True
t0_payload_hash_matches = True
t0_state_hash_matches = True
previous_snapshot_path = None
positions = 0
pending_buys = 0
pending_sells = 0
receivables = 0
```

This is positive evidence of a valid recoverable zero-state artifact, not
evidence that an economic trade occurred.

## Migration classification, read-only

The pure builder was run against the immutable copied snapshot with an
audit-only policy (`allow_legacy_mode=false`, `outcome_access=false`). No
decision file was persisted.

| Field | Result |
|---|---|
| Runtime provenance classification | `LEGACY_POSITION_ONLY` |
| Provenance disposition | `MIGRATION_REQUIRES_LEGACY_MODE` |
| Activation status | `REQUIRES_AUTHORIZATION` |
| Reason | `LEGACY_MODE_NOT_AUTHORIZED_BY_POLICY` |
| Source artifact SHA | `8258e9b39327252ecc252d5ffe2c1e19b636d9f625ffb629f6893f8fe2a5d006` |
| Provenance payload SHA | `3131ab162c4408dc3bff335359df3361374097f484319e44e61207c01e80533f` |
| Decision payload SHA | `ac0305ae248110cd55adbdab574d92581861a97c55921bd10535a2619430ec18` |

The classifier's legacy-position label is a runtime migration disposition; it
does not prove that the zero-holding snapshot contains positions. Explicit
activation authorization remains absent and no activation was performed.

## Operational timeline and why execution stalled

| Time / period | Evidence | Adjudication |
|---|---|---|
| 2026-08-22 | Active runtime root exists; no state snapshot chain was found in the earlier bounded inventory | Runtime root existed before the new T0, but state existence was not yet proven |
| 2026-08-24 onward | Active pinned checkout contains `bootstrap_t0`, snapshot writer, dividend runtime, dual-calendar controller, and scheduled runner | Capability existed; capability is not proof of invocation |
| 2026-09-18 to 2026-09-19 | Task Scheduler event records include `2147942401` failures | Operational execution was intermittent/blocked; no state artifact is inferred from task events alone |
| 2026-09-20 | Several scheduled runs returned 0 | Controller health improved, but no nonzero portfolio state was found |
| 2026-09-21 18:35:04 WIB | `T0.json` and `2026-09-21.json` were created together | Real zero-holding T0/snapshot was created |
| 2026-09-21 18:35:54 WIB | Process summary `20260921T113554272198Z_ca_capture_post_eod.json` records CA capture return code 1 | The run failed after T0 bootstrap and before a prepared execution was available |
| 2026-09-21 19:35:48 / 20:35:44 WIB | Two later `ca_capture_post_eod` process summaries also return 1 | Repeated post-EOD CA-stage failure; no retry was initiated by this audit |
| 2026-09-22 morning | `WAITING_PREPARED_EXECUTION`, reason `NO_PREPARED_EXECUTION_FOR_TODAY`; Official Open `AFTER_WINDOW_NO_EXECUTION_GRADE` | No prepared execution or execution-grade state was created |

The controller source explains the sequence: `bootstrap_t0()` writes the
snapshot and T0 before `_ensure_ca_phase` and prepared-output handling. Thus
the exact observed failure mode is “fresh T0 created, then CA/post-EOD stage
failed before prepared execution”, not “T0 creation failed”.

## Historical session and artifact reconstruction

The retained session corpus contains input/EOD evidence for 29 sessions, but
input availability is not paper-state completion.

- 2026-08-03 and 2026-09-22: `MISSED / BLOCKED` based on no valid execution-grade
  session.
- 2026-09-21: `POST_EOD_ONLY / T0_CREATED / BLOCKED_BEFORE_PREPARED`.
- Other retained dates from 2026-08-10 through 2026-09-18: strongest direct
  evidence is `DATA_READY` input/EOD evidence only; classify as
  `POST_EOD_ONLY`, not as completed POST_EOD controller execution.
- No session has an admitted prepared execution, fill vector, pending ledger,
  nonzero holdings, settlement/receivable ledger, or recovery chain.
- Official Open records contain no execution-grade positive result; where an
  execution-grade field is present it is `false`.

The current active runtime root has 203 files and 311,914 bytes. It contains
one T0, one snapshot, operational metadata, logs, and process summaries, but no
`prepared` directory, `executions` directory, `.transactions` directory, or
older snapshot chain. The absence of a deleted artifact cannot prove that it
never existed; it only limits what is recoverable now.

## Capability versus observed runtime history

The active checkout is:

- worktree `C:\Users\Sam\.codex\worktrees\idx-e2e-baseline-paper-pinned-20260824`
- branch `runtime/idx-e2e-baseline-paper-v1-pinned-20260824`
- HEAD `32eaaa8e50d0521de7faef98faa8081219bc667b`
- clean worktree

Relevant capability history includes durable dividend state (`612d934b`,
2026-08-21), paper orchestration and CA lifecycle (`95c49c0e`, 2026-08-23),
dual-calendar controller/runner (`c24059a6`, `d32aaa25`, 2026-08-24), missed-open
continuity (`70da7968`), and runtime lineage enforcement (`30d5a808`). These
commits establish that the active revision could create and maintain state.
They do not establish that it previously did so. The only direct positive state
creation found in this audit is the 2026-09-21 zero-holding T0/snapshot pair.

## Retention and deletion audit

No cleanup, rotation, deletion, or backup package for the active runtime state
was found. No additional real state root was found in the bounded AppData and
project-root scans beyond the active runtime root and explicitly synthetic or
test-shaped roots. This supports “not currently recoverable” for any absent
nonzero history, but cannot distinguish “never created” from “created then
deleted” for bytes that are no longer present.

## Consequences and gates

1. The global primary classification is `LEGACY_STATE_CREATED_AND_RECOVERABLE`.
2. A fresh-T0 package exists and must be preserved; do not overwrite or
   recreate it automatically.
3. Nonzero legacy migration, replay, recovery, CA settlement, and old-vs-new
   differential remain blocked because no eligible nonempty state or transaction
   history was admitted.
4. The current runtime remains pre-canary `NO-GO`: there is no prepared
   execution, execution-grade Official Open, live observability package, or
   explicit activation/scheduler/provider authorization.
5. A fresh-T0 restart may be technically redundant and is not authorized by
   this audit. Any policy decision must reference this exact T0 and snapshot.
6. The isolated CA parser fix is separately extracted on
   `codex/idx-ca-fix-extraction-20260922` at commit `0a9ded49`. It changes only
   scalar-NaN optional share-count handling, adds one regression test, and adds
   provenance documentation. Focused provider tests passed 8/8; the copied
   38-row CA registry parsed 38/38 with 22 known and 16 unknown ratios; the
   extraction branch full suite completed with exit code 0 and 906 collected
   tests. It was not merged, deployed, or applied to the active runtime.

## Final disposition

`LEGACY_STATE_CREATED_AND_RECOVERABLE`

Evidence-backed scope: one valid recoverable zero-holding T0/snapshot pair.
Unresolved scope: whether any nonzero legacy economic state ever existed.
Operational blocker: CA/post-EOD capture returned code 1 after T0 bootstrap,
so the run stalled before prepared execution and never produced execution-grade
portfolio history.

