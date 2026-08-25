# Official Open Forward Reliability Remediation V1

Date: 2026-08-25 Asia/Jakarta  
Branch: `fix/idx-e2e-forward-reliability-v1`  
Parent integration lineage: `integration/idx-e2e-baseline-paper-v1` at
`32eaaa8e50d0521de7faef98faa8081219bc667b`  
Implementation commit: `7d6a53f4`

## Scope and frozen semantics

This lane hardens the existing execution-grade Official Open path only. The
authority remains IDX `TradingSummary/GetStockSummary`, the scientific field
remains `OpenPrice`, and the transport policy remains
`DIRECT_IDX_THEN_ZAPI_RAW_V1`. `FirstTrade`, IEP, IEV, generic OHLC, and
fabricated values remain prohibited. No model, Decision, sizing, execution
mechanics, counter, or protected outcome was changed.

## Remediations

- Existing session manifests are re-verified through the real
  `verify_open_execution_inputs()` path before returning an idempotent
  `ALREADY_CAPTURED` status. A stale/tampered manifest now returns
  `PARTIAL_EVIDENCE_FAIL_CLOSED` without a network recapture.
- Direct transport retries are bounded to two attempts for request failures
  and the explicit transient 5xx allow-list. Auth/provenance failures and
  successful but malformed/incomplete HTTP 200 responses do not retry or fall
  through to Zapi.
- A successful HTTP 200 with an empty body is explicitly treated as malformed
  direct evidence and fails closed; it cannot trigger Zapi fallback.
- Zapi raw transport retries the same bounded transient classes and records
  failed physical attempts in transport metadata. Provider/project/path
  validation remains mandatory.
- The existing headless runner now invokes `official_open_capture_runtime_v2`,
  so the deployed scheduler entrypoint is bound to the remediated replay
  verification and retry implementation rather than the legacy v1 runtime.

## 2026-08-24 read-only operational evidence

Runtime root:
`C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1`

- Official Open latest status: `CAPTURE_FAIL_CLOSED`
- session: `2026-08-24`
- failure: `DIRECT=OFFICIAL_OPEN_DIRECT_IDX_REQUEST_ERROR` followed by
  `ZAPI=OFFICIAL_OPEN_ZAPI_RAW_REQUEST_ERROR`
- no accepted Open artifact was produced
- no outcome/model/provider capture was initiated by this remediation

The registered task remains the existing `IDXTrade-E2E-OfficialOpen`; this
lane does not reinstall or alter the task. Its deployed task definition is
read-only evidence and retains the existing 09:02–09:22 retries, logon
trigger, `StartWhenAvailable`, `IgnoreNew`, and network requirement.
The task currently points to a separate runtime checkout, so this code-path
binding takes effect only after the branch is independently integrated and the
runtime checkout is updated; no live proof is claimed here.

## Same-day retry and late-evidence policy

The execution-grade capture window remains 09:02–09:22 Asia/Jakarta. A later
scheduled invocation must not create or alter an order from newly observed
OpenPrice data. The existing paper orchestration expires a missed prepared
order without fills and preserves a deterministic `no_retroactive_execution`
record. Therefore this remediation does not widen the execution-grade window
or add a second late-trade scheduler. Extending source polling after 09:22 is
safe only as a separately reviewed evidence-resolution contract that requires
an already hash-bound pre-open prepared order and distinct processing/economic
timestamps; until that contract is integrated, late status remains pending and
fail-closed.

## Validation

- focused Official Open/E2E/Paper tests: 61 passed after the final remediation
- full pytest: 760 passed, 3 pre-existing pandas FutureWarnings
- `python -m py_compile` for changed modules: pass
- `git diff --check`: pass
- no Direct IDX, Zapi, Stockbit, or protected-outcome call was made by the
  synthetic validation

## Boundary

Late evidence remains resolution-only for an already prepared pre-open order;
it cannot create or mutate a missed order. A genuine scheduled run is needed
for live operational proof. This checkpoint makes no such claim.
