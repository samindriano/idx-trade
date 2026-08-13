# Ranking V4-B Price-Path Blind-Audit Review Pass

Date: 2026-08-10 (Asia/Jakarta)
Status: **INDEPENDENT BLIND-AUDIT REVIEW PASS / OUTCOME RUN DELIBERATELY HELD**

## Decision

`V4_B_PRICE_PATH_BLIND_AUDIT_REVIEW_PASS`

The completed V4-B cache preparation and restricted outcome-blind audit are sufficient for the frozen first-pass design. No mechanical defect, coverage failure, causal-boundary violation, or preregistered redundancy-review trigger was found.

This checkpoint does **not** authorize V4-B outcome scoring yet. The deliberate sequencing rule is to complete and independently review the already-frozen V4-C outcome-blind cache audit before opening V4-B outcomes. This is a research-process guard only; it does not change any V4-B feature, model, fold, promotion threshold, or candidate definition.

## Reviewed identities

- branch at reported local completion: `research/idx-ranking-v2-spec-v1`;
- final reported local HEAD after concurrent V4-C merge: `147b6a4f665ecfea9117b58f10c81bc5747fe034`;
- frozen V4-B spec Git blob: `a750c28831b95b1c88640c5879289da5f2c05446`;
- V4-B prepared cache SHA-256: `8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68`;
- V4-B cache manifest SHA-256: `d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f`;
- V4-B blind-audit SHA-256: `b8facff42be8231e263c261f97e4c02d6b9db92e64ceee831d9ff27b5c7586d6`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`.

The exact frozen panel, calendar, V3-B cache, and V3-B manifest identities were verified by the Windows-local run and are recorded in the prior audit-result checkpoint.

## Independent audit interpretation

All six frozen V4-B features are non-constant and have high finite coverage (`98.0775%..99.5751%`). No feature violates the frozen `80%` finite-rate floor.

No absolute Spearman pair reached the preregistered `0.95` mechanical-review threshold. The largest pair is:

- `v4b_range_acceptance_mean_5` versus `v4b_extreme_close_balance_5`;
- Spearman `0.940791493`.

This is high redundancy and should remain a diagnostic warning, but it is below the frozen review threshold and does not indicate a mechanical implementation mismatch. The V4-B spec explicitly forbids formula/lookback rescue absent a mechanical bug. Therefore B2 is kept exactly frozen rather than dropping or reformulating a feature after seeing outcome-blind correlation structure.

Correlations against existing V3-B features are materially lower than the B2 internal maximum. Nothing in the audit justifies reopening B1/B2 mathematics.

## Boundary verification

The audit records:

- `binary_target_loaded=false`;
- `outcome_columns_loaded=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`;
- no model fit or score;
- no PR-AUC, ROC-AUC, Q5-Q1, top-decile, paired, or promotion verdict;
- no B1+B2 integration;
- ordinals `015..017` remain unviewed;
- cumulative historical evaluated-candidate count remains `12`;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten.

## Sequencing decision

V4's frozen arena intended a bounded executable set, normally three main families. V4-A is already closed. V4-B and V4-C are the remaining frozen main families, and V4-C was fully specified and implemented before any V4-B outcome was viewed.

To preserve that blindness as strongly as practical, the next permitted action is **only** the already-prepared V4-C Windows-local cache preparation + restricted outcome-blind audit:

`coordination/handoffs/IDX-RANKING-V4-C-CROSS-SECTIONAL-CONTEXT-CACHE-AUDIT.md`

Do not run V4-B scoring while that audit is pending. After V4-C's blind audit returns and is independently reviewed, ChatGPT may issue a separate atomic outcome-run authorization for V4-B and/or V4-C without changing their frozen designs.

## Hard boundary

Until a later explicit authorization:

- do not execute `python -m idx_trade.ranking_v4_price_path_cli run`;
- do not fit/score V4-B ordinals `015..017`;
- do not create B1+B2 integration;
- do not change V4-B formulas, lookbacks, model parameters, folds, or gates;
- do not materialize/score session `1225+`;
- do not access post-2026-07-31 fresh-forward outcomes;
- do not start calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.
