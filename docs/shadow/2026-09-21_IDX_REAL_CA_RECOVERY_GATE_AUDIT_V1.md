# IDX-Trade Real CA and Recovery Gate Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **REAL EVENT-INTERFACE PASS / REAL CA COMPOSITION AND RECOVERY BLOCKED**

## Scope and boundary

This record closes the parser-level audit for the immutable real-artifact copy
and reconciles it with the real recovery gate. It is evidence for the isolated
shadow lane only. It does not convert event rows into paper state and does not
authorize migration, replay, canary, provider access, scheduler access, cloud
mutation, protected-outcome access, or active-runtime writes.

Input copy:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-extended-evidence\inputs\corporate_actions\idx_actions.csv`

Input SHA-256:

`40c0ade2a3d2f4a73483d7016c61eef751eda961ead3f9c6a6cfaa7217a20aa6`

The input was read from the already-attested shadow copy. The parser was called
with an in-memory `{"data": [...]}` payload reconstructed from that CSV; no
network or provider fetch was performed.

## Deterministic parser result

| Check | Result |
|---|---:|
| CSV input rows | 38 |
| Parser output rows | 38 |
| Rows retained | 38/38 |
| Action family | `stockSplit`: 38 |
| Distinct tickers | 35 |
| Valid effective dates | 38/38 |
| `old_shares` known | 22 |
| `new_shares` known | 22 |
| `ratio` known | 22 |
| `old_shares` / `new_shares` / `ratio` unknown | 16 |
| Parser source identity | `IDX_LISTING_ACTIVITY_ISSUED_HISTORY` |
| Effective-date range | 2023-01-06 through 2026-07-21 |

The 16 unknown rows remain unknown because the copied source has no usable
share-count values for them. No share count, ratio, price, entitlement, or
settlement result was fabricated. The isolated NaN handling remediation is
recorded in `2026-09-21_IDX_REAL_CA_INTERFACE_REMEDIATION_V1.md`.

## CA composition gate

The parser proves only that the copied IDX event registry is compatible with
the candidate interface. The copied evidence does not contain the state needed
to compose an entitlement or settlement transition:

| Required real state surface | Evidence in admitted copy | Gate result |
|---|---|---|
| Holdings / position lots at the event boundary | absent | BLOCKED |
| Entitlement ledger | absent | BLOCKED |
| Open obligation / pending transaction | absent | BLOCKED |
| Receivable / payment record | absent | BLOCKED |
| Cash / settlement state | absent | BLOCKED |
| CA-adjusted position transition | absent | BLOCKED |
| Restart ancestor containing the above state | absent | BLOCKED |

The 38 rows therefore remain `REAL_CA_EVENT_REGISTRY`, not a CA ledger or
settlement state. The separate Yahoo comparison remains corroborative only:
22 `MATCH`, 16 `IDX_RATIO_UNAVAILABLE`, and 5 `YAHOO_ONLY`; Yahoo-only rows
were not promoted to IDX events.

**CA COMPOSITION = BLOCKED REAL / INTERFACE PASS.**

## Recovery gate reconciliation

The current recovery matrix contains verified synthetic contracts for ancestor
selection, tamper quarantine, fork rejection, prepared restart, partial
execution, CA settlement restart, and the controller recovery fence. The real
copy contains none of the corresponding state chains:

| Recovery surface | Synthetic evidence | Real evidence | Real gate |
|---|---|---|---|
| Verified ancestor selection | pass | no snapshot chain | BLOCKED |
| Latest/tampered-state quarantine | pass | no latest state | BLOCKED |
| Fork rejection | pass | no competing chain | BLOCKED |
| Restart after preparation | pass | no prepared parent | BLOCKED |
| Restart after partial execution | pass | no fill vector | BLOCKED |
| CA settlement restart | pass | no CA ledger | BLOCKED |
| Controller recovery fence | pass | no real prepared execution | BLOCKED |

The active runtime's terminal no-prepared-execution observation is operational
metadata, not a recovery chain. It was not converted into one.

**RECOVERY = PASS SYNTHETIC / BLOCKED REAL.**

## Explicit non-inference rule

The 479,471 execution-anchor rows, 504 successful session-report rows, 516
calendar rows, and 38 CA event rows are separate input evidence classes. None
of them establishes a paper portfolio, fill vector, pending obligation,
entitlement, cash settlement, restart ancestor, or recovery chain. The real
migration, historical E2E replay, real CA composition, and real recovery gates
therefore remain closed.

## Safety and verification

- Source and copy hashes were already equal in the extended 32-file manifest.
- Parser audit was read-only against the isolated copy.
- No provider/network/live-runtime invocation occurred.
- No prompt, transcript, protected outcome, PnL, counter, cloud/R2, scheduler,
  or active-model surface was accessed or modified.
- This record does not change the pre-canary `NO-GO` verdict.
