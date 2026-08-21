# Decision V3 Graded Evidence V2 — Structural Replay Runner Implementation

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_TESTED_NO_HISTORICAL_REPLAY_INDEPENDENT_RUNNER_AUDIT_REQUIRED`

Controlling Decision rule: `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`.

Controlling implementation code HEAD before runner work: `c89ecb4f88e98cc23c140f15dee13ca423a92f5c`.

Validated runner code HEAD: `c8c964a65d43c343803125f398c0665e6cc5cdf9`.

Frozen replay contract: `docs/specs/decision_v3_graded_evidence_structural_replay_contract_v2.json`.

Frozen replay contract canonical SHA-256: `4d16f2f8ca1a274e7d98cc8be24daaa0f4eb77bfc6e56ecf90c6f42f1b13239f`.

## Implemented

- strict pinned historical source loader with exact manifest/score hashes, row/session counts and naive Top10 comparator;
- parquet projection restricted to `ticker`, `date`, `fold`, `mode`, and `alpha_consensus`;
- `alpha_consensus` is used only to reconstruct deterministic `rank_consensus`; Decision policy receives only `ticker` and `rank_consensus`;
- no H5/H10 head values, return/target/outcome columns, providers or network are read by the authorized runner path;
- exact index-0 Top10 bootstrap, no pre-roll, exact score-session `(t-1,t)` adjacency, continuous rule-bound state and no fold resets;
- same-source/same-policy two-pass determinism check;
- independent A/B/C vacancy-priority and permission validator rather than trusting only state-machine outputs;
- independent stale-state, first-mild-retention, severe-exit, universe-exit and Tier-A gap-5 validation;
- independent post-replay ledger/rank-path integrity guard that aborts artifact promotion on phantom targets, target-without-buy, buy-without-target, previous-absent entry, target rank `>50`, or missing universe-exit intent;
- churn, holding, rank-quality, capacity, state-attribution and six-block/fold descriptive metrics;
- frozen comparators: naive `3127`, Decision V1 `2686`, Decision V2 `1435`;
- Tier-C lifecycle diagnostics including holding duration, next-session state, next-session severe exits and downstream replacement-seat changes;
- high-churn attribution reports component presence/shares without assigning a post-hoc single causal label;
- Tier-C/high-churn diagnostics are descriptive only and cannot alter gates or verdict;
- fail-closed staged artifact output with SHA-256 manifest;
- CLI process interlock checked before contract or source access.

## Validation

Final GitHub Actions run #1128 on validated runner code HEAD:

- `526 passed`;
- `26 warnings`;
- `0 failed`.

Warnings are pre-existing pandas/NumPy and GitHub Actions Node deprecation warnings unrelated to Decision V3.

## Required output artifacts

- `summary.json`;
- `decision_session_ledger.csv`;
- `decision_membership_ledger.csv`;
- `decision_intent_ledger.csv`;
- `decision_state_ledger.csv`;
- `holding_spells.csv`;
- `fold_boundary_transitions.csv`;
- `MANIFEST.json`.

## Scientific boundary

No Decision V3 600-OOS historical replay has been executed.

No returns/PnL, protected/fresh-forward outcomes, H5/H10 rescue, alternative threshold/policy simulation, alpha refit/retune, sizing, execution or paper activation occurred.

Historical replay remains unauthorized until a separate adversarial runner audit accepts the exact final runner lineage.
