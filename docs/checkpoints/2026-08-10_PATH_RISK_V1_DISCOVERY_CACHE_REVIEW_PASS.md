# Path Risk V1 Discovery Cache Review — PASS

Date: 2026-08-10 (Asia/Jakarta)
Status: **CACHE/AUDIT REVIEW PASS — PR-001 F1-F4 MAY RUN ONLY AFTER LOCAL PYTEST PASSES**

## Decision

The outcome-blind Path Risk V1 discovery feature cache is accepted.

Frozen cache evidence:

- rows/tickers/dates: `254,383 / 679 / 965`;
- signal sessions: `20..984`;
- cache SHA-256: `74c300390dce542dad95ae204dd7663f5f780b09dd33c3514c5dd264f15cca08`;
- manifest SHA-256: `054ccff7676a744871b1f82a5b263898f9fa53c2d1ae1ac20a5659485466bed0`;
- audit SHA-256: `1bb6fecbae1733f7ab62022c5f50389ffdd2bfe1dcc68f98c9853c9d123d2807`;
- exact 33-feature-order SHA-256: `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- duplicate rows: `0`;
- infinity cells: `0`;
- constant/all-null features: none;
- forbidden outcome columns: none.

The lowest Structure-Lite finite rates remain acceptable under the frozen imputation contract: support distance about `91.12%`, support touch count about `91.30%`, resistance distance about `96.42%`. No feature is all-null and no feature is pruned after the audit.

No real H10 label, adverse-excursion target, PR-001 fit, Path Risk metric, F5/F6 Path Risk outcome, or fresh-forward outcome was viewed during cache preparation.

## Independent code review before outcome access

A code review identified one pre-outcome hardening requirement: the existing target primitive validates barrier levels against the label row, but it does not itself require the label frame to contain and match the globally frozen `horizon=10`, `sl_atr_multiple=1.0`, and `reward_risk=1.5` constants.

Because no real Path Risk outcome has yet been opened, this can be hardened without contaminating model selection.

The discovery runner implemented after this review therefore adds strict pre-target checks for:

- `horizon == 10` on every loaded discovery label row;
- `sl_atr_multiple == 1.0`;
- `reward_risk == 1.5`;
- physical Parquet filtering to `signal_session_index <= 984` for label rows;
- price-path reads bounded to the latest H10 endpoint required by session `984`, i.e. official session `994`;
- exact F1-F4 fold identity only;
- exact frozen cache/manifest/panel/calendar/label identities;
- no session `985+` in feature, target, model, or prediction frames.

Implemented by ChatGPT architect in:

- `src/idx_trade/path_risk_v1_discovery_run.py`;
- `tests/test_path_risk_v1_discovery_run.py`.

This does not change the frozen Path Risk hypothesis, target formula, quantile, feature set, model, folds, metric, or gate. It only makes the already-frozen contract fail closed before real outcome use.

## Conditional PR-001 F1-F4 authorization

PR-001 may be run once on historical discovery folds F1-F4 **only if** the latest branch is clean/synchronized and full local pytest reports zero failures after pulling the new runner/tests.

The run must use exactly:

- candidate `PATH-RISK-A-Q75-HGB-001`;
- exact 33 frozen V3-B features;
- q75 HGB regressor frozen in `docs/PATH_RISK_V1_SPEC.md`;
- exact F1-F4 boundaries;
- frozen training-q75 constant comparator;
- frozen pinball/Spearman/risk-quintile diagnostics and discovery gate;
- H10 label SHA `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`;
- frozen feature cache and manifest hashes above.

PR-001 becomes permanently viewed once the real run completes and metrics are inspected, regardless of PASS or FAIL.

## Still prohibited

- any source/spec/model/feature/fold/threshold edit after real outcome access;
- Path Risk F5/F6 access;
- a second PR-001 discovery attempt;
- quantile/model/feature rescue;
- alpha-ranker changes;
- risk-veto or alpha+risk integration rules;
- post-2026-07-31 fresh-forward outcome access;
- `FORWARD_OUTCOME_ACCESS_STARTED`;
- calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.

## Execution responsibility

Repository implementation is owned by ChatGPT architect. The local Codex task for this phase is execution-only: pull, run full pytest, execute the already-implemented runner once if tests pass, and return artifacts/metrics without editing source or research documentation.
