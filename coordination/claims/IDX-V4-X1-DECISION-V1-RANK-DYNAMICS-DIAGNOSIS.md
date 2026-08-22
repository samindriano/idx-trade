# IDX-V4-X1 Decision V1 Rank-Dynamics Diagnosis

- Status: `ACTIVE`
- Owner: `ChatGPT/Decision-V1-Rank-Dynamics-Diagnosis`
- Date: 2026-08-21 Asia/Jakarta
- Planned branch: `research/idx-v4-x1-decision-v1-rank-dynamics-diagnosis`

## Scope

Outcome-blind forensic diagnosis of why frozen Decision V1 passed static/adversarial invariant tests yet exhibited excessive churn in the exact 600-date historical OOS trajectory.

Measure only score/rank dynamics and Decision V1 transition behavior: consecutive-session rank persistence, raw-score vs percentile-rank movement, Top10/Top20 survival, hard-exit transition mechanics, exit/re-entry whipsaw, universe churn, and fold-boundary effects.

## Explicit exclusions

- no realized returns / target ledger / historical PnL;
- no Decision V2 implementation or parameter search yet;
- no V4-X1 refit/retune/model change;
- no provider/network acquisition;
- no prospective/protected outcome access;
- no Sizing/Execution/Paper changes.

The result should end in a small set of evidence-backed hypotheses that can later be preregistered as Decision V2 candidates.
