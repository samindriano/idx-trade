# Path Risk Hypothesis Ledger V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **PR-001 RESERVED / UNVIEWED — REAL PATH-RISK OUTCOMES NOT ACCESSED**

Path Risk is a separate research lane from alpha ranking. Ranking historical evaluated-candidate count remains permanently `17` and is not modified by this ledger.

## Candidate ledger

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| PR-001 | `PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1` | `PATH-RISK-A-Q75-HGB-001` | exact frozen V3-B 33 causal features -> HGB q75 pre-resolution adverse-excursion R | `RESERVED_PRE_OUTCOME` | `false` | `PENDING_FEATURE_CACHE_GATE` |

Comparator `TRAIN-Q75-CONSTANT-BASELINE` is not a learned candidate ordinal.

## Frozen target

`adverse_excursion_r = max(0, (signal_reference_close - min_future_low_to_tau) / stop_distance)`

where `tau` is the first frozen H10 barrier-touch date or H10 endpoint when no barrier is touched. Full semantics are controlled by `docs/PATH_RISK_V1_SPEC.md`.

## Current boundary

The only authorized next task is implementation plus outcome-blind discovery feature-cache preparation/audit through signal session `984`.

No real H10 label artifact may be loaded and PR-001 must remain unviewed until a later explicit authorization.

F5/F6 Path Risk outcomes, post-2026-07-31 fresh-forward outcomes, risk/ranker integration, calibration, execution/PnL, Kelly, paper/live, and main merge remain unauthorized.

## Accounting rule

Once PR-001 real outcome metrics are viewed, it remains permanently counted in the Path Risk denominator regardless of PASS or FAIL. A mechanical/data/provenance block before target/model scoring remains documented as a block and does not become a fabricated model failure.

## Feature-cache preparation result — 2026-08-10

The implementation and outcome-blind discovery feature-cache phase is complete.
PR-001 remains reserved and unviewed pending a separate outcome authorization.
The frozen cache contains `254,383` rows, `679` tickers, and sessions `20..984`;
its cache/manifest/audit SHA-256 identities are recorded in the controlling
checkpoint:

`docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_CACHE_AUDIT_RESULT.md`

No real H10 labels, adverse-excursion targets, PR-001 fit, performance metric,
F5/F6 outcome, fresh-forward outcome, or risk/ranker integration was accessed.
