# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 frozen control remains exact `HGB_XS_MARKET`;
- Ranking V3 architecture search is **CLOSED**;
- final V3 historical-development architecture: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- V3-B one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- V2F1..V2F6 are development knowledge and are not independent V4 holdouts;
- V4-A Participation Quality / Price Impact: **CLOSED — no survivor**;
- V4-B Price-Path Quality: **IMPLEMENTED PRE-OUTCOME — CACHE/AUDIT NEXT**;
- V4-C Cross-Sectional Opportunity Context: **IMPLEMENTED PRE-OUTCOME — CACHE/AUDIT NEXT**;
- cumulative historical evaluated-candidate count remains `12`;
- sessions `1225+` remain sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Frozen V3 conclusion

Final V3 architecture:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Across V3-B historical-development F1-F6, paired PR improvement versus exact V2 control was positive on all six folds. F1-F4 median paired PR improvement was `+0.0039258450`; F5/F6 median was `+0.0075911303`. This is ranking evidence only, not calibrated probability, execution/PnL evidence, live readiness, or independent future validation.

Frozen signal-research identities:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Frozen V3-B late-development cache used as V4 base:

- cache SHA-256 `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA-256 `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- rows/tickers/sessions `286,453 / 737 / 20..1224`;
- no session `1225+` materialized.

## V4 — final alpha program

Frozen arena:

`docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`

Seven retained information families:

1. Liquidity & Participation Quality;
2. Price-Path Quality;
3. Cross-Sectional Opportunity Context;
4. Peer / Sector Relative Strength, conditional on PIT sector history;
5. Systematic-Adjusted / Idiosyncratic Strength;
6. Catalyst / Fundamental Context, conditional on PIT provenance;
7. Flow / Ownership Information, conditional on data readiness.

These are a design shortlist, not seven automatic runs. Scoring remains narrow, with no model zoo or post-result rescue.

## V4-A — CLOSED

First-pass ordinals:

- `012` exact V3-B control: equivalence PASS;
- `013` A1 Impact/Absorption: `FAIL`;
- `014` A2 Persistent Directional Participation: `FAIL`.

Survivors: `[]`. No integration exists. No rescue is permitted.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`

## V4-B — IMPLEMENTED PRE-OUTCOME

Hypothesis: `V4-B-PRICE-PATH-V1`.

Frozen first-pass candidates:

- `015` exact V3-B control;
- `016` B1 Path Coherence / Jump Concentration;
- `017` B2 Range Acceptance / Rejection.

Frozen B1 features:

- `v4b_path_efficiency_5`;
- `v4b_path_efficiency_20`;
- `v4b_largest_move_share_20`.

Frozen B2 features:

- `v4b_range_acceptance_mean_5`;
- `v4b_range_acceptance_mean_20`;
- `v4b_extreme_close_balance_5`.

Spec Git blob: `a750c28831b95b1c88640c5879289da5f2c05446`.

Implementation checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_B_PRICE_PATH_IMPLEMENTED_PRE_OUTCOME.md`

CI on the V4-B implementation: `348 passed, 0 failed`.

CI on implementation commit `1d409c7f88faa2069d0a7ffc4d2402c9cce76c8a`:

- `348 passed`;
- `0 failed`;
- pytest `12.25s` in CI;
- warnings are existing/deprecation-warning volume.

No V4-B candidate has been fitted/scored yet. Ordinals `015..017` remain unviewed. No B1+B2 integration candidate exists.

## Outcome-blind cache audit result

The Windows-local V4-B cache preparation and feature audit authorized by
`coordination/handoffs/IDX-RANKING-V4-B-PRICE-PATH-CACHE-AUDIT.md` completed on
2026-08-10 at branch `research/idx-ranking-v2-spec-v1`, HEAD
`f5c83022678030dc5d3894982136aa365aeb2dac`.

- full pytest: `348 passed`, `0 failed`, `3 warnings`;
- cache status: `RANKING_V4_B_PRICE_PATH_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256:
  `8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68`;
- cache manifest SHA-256:
  `d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f`;
- audit SHA-256:
  `b8facff42be8231e263c261f97e4c02d6b9db92e64ceee831d9ff27b5c7586d6`.

The restricted audit loaded identity, the exact V3-B 33-feature prefix, and
the six frozen V4-B features only. All six features were non-constant and at
least `98.0775%` finite; no feature was below the `80%` finite-rate rule. The
largest absolute Spearman correlation involving a V4-B feature was
`0.940791493` (`v4b_range_acceptance_mean_5` versus
`v4b_extreme_close_balance_5`), below the `0.95` mechanical-review threshold.

No target or outcome columns were loaded; no candidate was fitted or scored;
no V4-B outcome metric or verdict was computed. Ordinals `015..017` remain
`UNVIEWED_RESERVED`, cumulative historical evaluated-candidate count remains
`12`, session `1225+` remains sealed, and fresh-forward outcomes plus
`FORWARD_OUTCOME_ACCESS_STARTED` remain untouched.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_B_PRICE_PATH_CACHE_AUDIT_RESULT.md`

Result handoff:

`coordination/handoffs/IDX-RANKING-V4-B-PRICE-PATH-CACHE-AUDIT-RESULT.md`

### V4-B audit next action

Stop for independent ChatGPT review of the outcome-blind V4-B cache audit.
Any V4-B control/B1/B2 outcome run requires the separate atomic first-pass
authorization and must not be inferred from this audit.
No V4-B model has been fitted/scored. Next permitted action is only:

`coordination/handoffs/IDX-RANKING-V4-B-PRICE-PATH-CACHE-AUDIT.md`

## V4-C — IMPLEMENTED PRE-OUTCOME

Hypothesis: `V4-C-CROSS-SECTIONAL-CONTEXT-V1`.

V4-C was frozen **before any V4-B outcome was viewed**, preventing adaptation to V4-B results.

Unlike A/B, V4-C intentionally has only one challenger:

- `018` exact V3-B control;
- `019` V3-B + one compact four-feature cross-sectional opportunity-dispersion bundle.

Frozen V4-C features:

1. `v4c_market_return_iqr_5`;
2. `v4c_market_return_iqr_20`;
3. `v4c_market_atr_iqr`;
4. `v4c_market_close_position_iqr_20`.

Each is computed per date from the **full causal primary-liquid universe**, not only label-resolved/model rows. Exact V2 baseline-feature semantics are reused; minimum finite cross-section is 50 and quantiles are linear IQRs.

V4-C intentionally excludes volume/value dispersion so it does not become a hidden V4-A rescue.

Controlling files:

- `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_EXPERIMENT_MAP_V1.md`;
- `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`;
- spec Git blob `43f222f31c7c0ea15e870d22b066aae95858c81f`;
- `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_REVIEW_ADDENDUM_V1.md`;
- `docs/checkpoints/2026-08-10_RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_IMPLEMENTED_PRE_OUTCOME.md`.

Implemented:

- causal full-primary-universe context builder;
- exact V3-B-prefix challenger/model contract;
- outcome-independent cache preparation with projected raw-panel read;
- outcome-blind row-level + date-level redundancy audit;
- future atomic control+019 runner with exact V3-B equivalence and unchanged V4-A/V4-B gate;
- CLI and focused tests.

GitHub Actions on all V4-C code through focused-test commit `70818d509903749b9656ed994afda9976955c0a3`:

- `357 passed`;
- `0 failed`;
- pytest `16.85s`.

No V4-C model has been fitted/scored. Next permitted action is only:

`coordination/handoffs/IDX-RANKING-V4-C-CROSS-SECTIONAL-CONTEXT-CACHE-AUDIT.md`

## Immediate next action

V4-B and V4-C cache/audit work is outcome-blind and may proceed independently or in parallel on Windows-local data. Neither audit authorizes model scoring.

For each family:

1. prepare exact SHA-pinned cache;
2. run restricted outcome-blind audit;
3. return report to ChatGPT;
4. STOP;
5. obtain separate authorization before any F1-F6 scoring.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- treat V2F1..V2F6 as independent V4 validation;
- bypass V3-D PIT sector-history block;
- rescue/reformulate V4-A;
- adapt V4-C to later V4-B outcomes;
- fit/score V4-B or V4-C before their blind-audit reviews and separate authorizations;
- create integrations that are not separately preregistered and result-eligible;
- materialize/score session `1225+` for V4 development;
- access post-2026-07-31 fresh-forward outcomes or write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge automatically.

## V3-D PIT sector-history recheck — 2026-08-10

The post-V3-C V3-D data-gate review was rerun on final branch HEAD
`147b6a4f665ecfea9117b58f10c81bc5747fe034`.

- full pytest: `357 passed`, `0 failed`, `3 warnings` in `15.77s`;
- frozen panel/calendar/security-master/V2 prepared/V2 manifest hashes all
  matched exactly;
- no defensible immutable ticker-by-date IDX-IC history was located locally
  or established from the official public pages;
- `validate-history`: not run because no admissible sector-history artifact
  exists;
- `prepare`: not run;
- data-gate result: `BLOCKED_PIT_SECTOR_HISTORY`.

The official IDX stocks page confirms IDX-IC starts on 2021-01-25 and describes
the taxonomy, but it is a current classification page. The current IDX stock
list is dynamic and exposes no historical effective/availability intervals.
The previously inspected monthly stock-price listing contains report-month
sector labels but does not establish exact classification change dates or
public `available_at` semantics. A publicly indexed 2021 initial-list lead is
not a complete change history or a verified first-party immutable source.

The local current sector snapshots under
`D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX\List Emiten\Sectors`
were explicitly rejected as PIT evidence and were not used. No normalized
history, cache, manifest, or sector assignment artifact was created. V3-C
remains final `V3_C_REGIME_KILL_KEEP_V2_CONTROL`; V3-D ordinals `008/009`
remain unviewed and the outcome boundary is unchanged.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PIT_DATA_GATE_BLOCKED_RERUN.md`

Result handoff:

`coordination/handoffs/IDX-RANKING-V3-SECTOR-PRE-RUN-REVIEW-RESULT.md`
