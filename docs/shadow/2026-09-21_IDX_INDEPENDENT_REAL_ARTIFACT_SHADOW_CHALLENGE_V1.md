# IDX-Trade Independent Real-Artifact Shadow Challenge V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS WITH LIMITATION / REAL QUALIFICATION STILL BLOCKED**

## Purpose

This is the Phase 18 challenge against the immutable 29-session discovery
copy. It was constructed independently of the candidate migration builders and
does not invoke a migration, replay, controller, provider, or production
entrypoint.

The challenge reads only the already admitted shadow copy at:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-all-sessions\inputs`

No active runtime, scheduler, provider root, protected outcome, counter,
cloud/R2 surface, canonical-data root, or alpha/model lane was read or
modified. The checker reported hashes, schemas, key names, and row counts; it
did not print or persist payload values.

## Independent checks and results

| Check | Result | Evidence |
|---|---|---|
| Shadow root/session inventory | PASS | root exists; 29 session directories; 237 files |
| Manifest child-hash claims | PASS | 29/29 `model_input`, `session_evidence`, and `idx_stock_summary` claims match their copied files; zero failures |
| Outcome-blind flags | PASS | 29/29 manifests have `outcome_blind=true` and `forward_outcomes_accessed=false` |
| Model/evidence row counts | PASS | all 29 copied model-input and evidence counts equal their manifest counts |
| Stock-summary row count | NOT APPLICABLE | the manifests do not carry a stock-summary row-count field; no mismatch was inferred |
| Parquet state-like columns | PASS WITH LIMITATION | 89 copied Parquet files scanned; no `position`, `pending`, `fill`, `execution`, `prepared`, `portfolio`, `cash`, `order`, `obligation`, `entitlement`, `receivable`, `dividend`, `corporate`, or `reconciliation` column appeared |
| JSON metadata-key challenge | PASS WITH LIMITATION | four files contained non-state matching metadata keys: two open-enrichment source-hash/volume-reconciliation surfaces and two calendar `ordered_consecutive` attestations; no paper-state key was found |
| Runtime/config identity fields | BLOCKED | none of the 29 session manifests has a top-level `config`, `runtime`, `checkout`, `commit`, `runner`, `schedule`, `task`, or `revision` field; no identity was inferred |
| Calendar binding | BLOCKED | copied current calendar SHA `8a5fd51630c331b651fcd41bd024a70c6f8fad6dcc9fe9d5393429e16766a6fe` matches only 1/29 manifests; 28 historical bindings remain unresolved |

## Challenge interpretation

The independent checks find no hash drift, row-count mismatch, outcome-access
flag, or hidden paper-state schema in the admitted discovery copy. They also
do not turn capture/model/evidence packages into E2E paper state. The result
is therefore a bounded challenge pass with the same explicit real blockers:

- no real snapshot, prepared parent, fill vector, pending obligation, CA
  ledger, or recovery chain is present in the admitted class;
- 28/29 session calendar bindings do not match the current copied calendar;
- the one matching 2026-09-18 binding still fails the next-session boundary;
- no old-vs-candidate real differential can be run without a real state pair.

No material locally fixable defect was discovered by this challenge. The
existing real migration, replay, CA, recovery, and pre-canary gates remain
unchanged and fail-closed.

## Gate impact

| Gate | Result |
|---|---|
| Phase 18 independent shadow challenge | PASS WITH LIMITATION |
| REAL ARTIFACT DISCOVERY | PASS WITH LIMITATION |
| REAL MIGRATION | BLOCKED |
| HISTORICAL REPLAY | BLOCKED / INPUT-LEVEL ONLY |
| PRE-CANARY READINESS | NO-GO |
