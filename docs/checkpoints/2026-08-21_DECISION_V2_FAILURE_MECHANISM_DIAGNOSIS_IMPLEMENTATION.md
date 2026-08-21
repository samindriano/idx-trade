# Decision V2 — Failure-Mechanism Diagnosis Implementation

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_NOT_EXECUTED_REVIEW_REQUIRED`

Branch: `research/idx-decision-v2-failure-mechanism-diagnosis-v1-final`

Implemented the preregistered outcome-blind forensic diagnosis of the frozen Decision V2 Minimal structural rejection.

The runner consumes the already-created structural result ledgers and the same pinned historical alpha rank source. It does **not** rerun Decision V2.

It produces four analyses:

1. exit-grace severity/recovery by fixed descriptive rank strata;
2. rejected fresh Top-10 supply and next-session rank persistence on underfilled sessions;
3. residual churn attribution from the frozen intent reasons;
4. the same mechanism summaries across six 100-session blocks.

Safety boundaries:

- exact structural result manifest SHA `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`;
- exact structural artifact hashes revalidated from its manifest;
- exact plan digest `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`;
- exact source manifest/score hashes and 600/172,697 shape;
- no Decision replay rerun;
- no alternative Decision rule or threshold simulation;
- no return/PnL/protected-forward/provider/model access;
- output directory is fail-closed and non-overwriting;
- CLI remains locked pending independent review.

Execution token, after review only:

`DECISION_V2_FAILURE_MECHANISM_DIAGNOSIS_REVIEW_ACCEPTED_V1`
