# IDX-Trade — Pinned Runtime Synthetic Validation V1

Date: 2026-09-20 (Asia/Jakarta)

Status: `BOUNDED TEST PASS / CRASH-RECOVERY GAPS REMAIN`

## Snapshot and isolation

The tests were run from a temporary extraction of the pinned runtime commit:

`045e25a19d9f71170d2c863e768102937e59ad73`

The active research worktree was not checked out, modified, staged, or used as
the test cwd. No provider, cloud, capture, telemetry, canonical data, or
protected outcome was accessed.

## Commands and results

Command group 1 — Decision/Sizing/Execution contracts:

```text
python -m pytest -p no:cacheprovider --disable-warnings \
  tests/test_v4_x1_execution_v1.py \
  tests/test_v4_x1_execution_v1_allocator_edge.py \
  tests/test_v4_x1_sizing_v1_decision_v2_adapter.py \
  tests/test_v4_x1_execution_v1_decision_v2_adapter.py
```

Result: `20 passed in 1.50s`.

Command group 2 — E2E orchestration/controller/runtime/CA contracts:

```text
python -m pytest -p no:cacheprovider --disable-warnings \
  tests/test_e2e_paper_orchestration_v1.py \
  tests/test_e2e_paper_operational_controller_v1.py \
  tests/test_e2e_paper_runtime_config_v1.py \
  tests/test_e2e_paper_preopen_ca_cloud_v1.py
```

Result: `66 passed in 6.80s`.

Combined bounded validation: `86 passed`.

## What the PASS establishes

The pinned source has passing local tests for the tested paths, including:

- fee, lot, cash, and capacity arithmetic;
- Decision V2 to Sizing V1 provenance and underfill semantics;
- pending-buy/pending-sell reversal cases covered by the suite;
- execution artifact and orchestration contracts;
- operational-controller and runtime-config cases represented by existing
  tests;
- CA preopen/parent contract cases represented by existing tests.

## What the PASS does not establish

The test suite does not prove that every multi-file write sequence is
crash-recoverable. In particular, it does not close the previously identified
fault windows for:

- snapshot written before T0 marker;
- continuity snapshot written before missed-execution audit/metadata;
- controller side effect started while RUNNING/attempt state is only in memory;
- malformed prepared artifacts being surfaced as explicit corruption rather
  than skipped/waiting.

The suite also does not create empirical broker fills, historical ADV/spread/
queue evidence, tax authority, portfolio-risk overlays, or protected predictive
outcomes.

## Verdict

`PINNED_COMPONENT_TESTS_PASS`

`SYSTEM_RESTART_SAFETY_AND_EXECUTABLE_ECONOMICS = NOT PROVEN`

The next useful implementation-quality test is fault injection at each durable
write and external side-effect boundary, not another ordinary regression run.

## Direct fault-injection observation

In the same temporary pinned extraction, `_atomic_write` was monkeypatched to
raise once during `bootstrap_t0`, after `write_runtime_snapshot` had completed
but before `T0.json` was written.

Observed output:

```text
first= RuntimeError INJECTED_AFTER_SNAPSHOT
retry= E2EPaperOrchestrationError E2E_T0_PREEXISTING_RUNTIME_STATE
```

This reproduces the T0 crash window as an actual synthetic failure: an
interrupted bootstrap leaves a runtime snapshot that the next invocation cannot
reconcile into the matching T0 marker. The test was isolated, outcome-blind,
and did not modify the repository checkout.

A second fault injection patched the missed-Open continuity writer to fail once
after the advanced runtime snapshot but before the missed-execution audit. The
same prepared synthetic session was then retried.

Observed output:

```text
first= RuntimeError INJECTED_AFTER_CONTINUITY_SNAPSHOT
retry= E2EPaperOrchestrationError E2E_MISSED_EXECUTION_STATE_SESSION_MISMATCH
```

This independently reproduces the continuity crash gap: the retry sees the
advanced execution-date snapshot but no audit artifact and refuses to reconcile
it. The correct future fix is a recoverable snapshot/audit transaction or an
explicit reconciliation record, not a retry loop.
