# IDX Decision V2 Minimal — Structural Replay Runner Claim

Date: 2026-08-21 Asia/Jakarta

Status: `ACTIVE`

Owner: `ChatGPT/Decision-V2-Minimal-Structural-Replay-Runner`

Branch: `research/idx-decision-v2-minimal-structural-replay-runner-v1`

## Scope

Implement and test the outcome-blind exact 600-OOS structural replay runner for the already preregistered and independently audited Decision V2 Minimal policy.

This lane owns only replay orchestration, structural metrics, frozen mechanical acceptance gates, deterministic output/manifest generation, and fail-closed source/session/state invariants.

## Required invariants before first replay

- source manifest SHA-256 exactly `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score parquet SHA-256 exactly `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exactly 600 score sessions and 172,697 rows;
- bootstrap only at ledger index 0;
- later calls use exact adjacent score sessions `(t-1,t)`;
- no skipped score session, fold reset, or pre-roll;
- shadow state advances only through `DecisionV2ShadowState.from_plan(...)` and remains rule-bound;
- all preregistered mechanical gates are encoded before first replay;
- no return/PnL/target-outcome/provider/network/protected/fresh-forward/model-fit access.

## Boundary

This claim does **not** authorize running the 600-OOS replay yet. Runner implementation and tests must be reviewed first.
