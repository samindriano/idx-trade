# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 frozen control remains exact `HGB_XS_MARKET`;
- Ranking V3 historical-development architecture search is **CLOSED**;
- final V3 historical-development architecture: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- V3-B one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- V2F1..V2F6 are development knowledge and are not independent V4 holdouts;
- V4-A Participation Quality / Price Impact: **CLOSED — no survivor**;
- V4-B Price-Path Quality: **IMPLEMENTED PRE-OUTCOME — CACHE/AUDIT NEXT**;
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

These are a design shortlist, not seven automatic model runs. Scoring remains narrow: one frozen bundle per executed family, no model zoo, and only preregistered integration after independent survivor evidence.

## V4-A family — CLOSED

`V4-A-PARTICIPATION-V1` first-pass results:

- ordinal `012` exact V3-B control: equivalence PASS;
- ordinal `013` A1 Impact/Absorption: `FAIL`;
- ordinal `014` A2 Persistent Directional Participation: `FAIL`;
- survivors `[]`;
- no integration authorized/executed;
- no rescue or redesign permitted.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`

Closure checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_REVIEW_CLOSED_V4_B_SPEC_AUTHORIZED.md`

## V4-B family — IMPLEMENTED PRE-OUTCOME

Family:

`V4-B-PRICE-PATH-V1`

Primary question:

> Conditional on frozen V3-B state and geometry, does coherent versus jump-concentrated price travel or repeated daily-range acceptance/rejection add robust ranking information?

Frozen first-pass candidates:

- ordinal `015`: exact V3-B 33-feature control;
- ordinal `016`: V3-B + B1 Path Coherence / Jump Concentration;
- ordinal `017`: V3-B + B2 Range Acceptance / Rejection.

B1 exact appended features:

1. `v4b_path_efficiency_5`;
2. `v4b_path_efficiency_20`;
3. `v4b_largest_move_share_20`.

B2 exact appended features:

1. `v4b_range_acceptance_mean_5`;
2. `v4b_range_acceptance_mean_20`;
3. `v4b_extreme_close_balance_5`.

Controlling files:

- `docs/RANKING_V4_B_PRICE_PATH_EXPERIMENT_MAP_V1.md`;
- `docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md`;
- frozen spec Git blob `a750c28831b95b1c88640c5879289da5f2c05446`;
- `docs/RANKING_V4_B_PRICE_PATH_SPEC_REVIEW_ADDENDUM_V1.md`;
- `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`;
- implementation checkpoint `docs/checkpoints/2026-08-10_RANKING_V4_B_PRICE_PATH_IMPLEMENTED_PRE_OUTCOME.md`.

Implementation exists for:

- causal B1/B2 feature construction using only High/Low/Close + official sessions;
- exact V3-B-prefix candidate/model definitions;
- outcome-independent cache preparation with column-projected panel read;
- outcome-blind audit against all exact V3-B 33 features;
- atomic control+B1+B2 runner with exact V3-B reference equivalence and the unchanged V4-A challenger gate;
- CLI and focused tests.

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

## Immediate next action

Stop for independent ChatGPT review of the outcome-blind V4-B cache audit.
Any V4-B control/B1/B2 outcome run requires the separate atomic first-pass
authorization and must not be inferred from this audit.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- treat V2F1..V2F6 as independent V4 validation;
- bypass V3-D PIT sector-history block;
- rescue/reformulate V4-A;
- modify V4-B formulas/lookbacks/model/gates after V4-B outcome access;
- fit/score V4-B before blind-audit review and separate authorization;
- create/run B1+B2 integration before both independently PASS and a separate integration spec exists;
- materialize/score session `1225+` for V4 development;
- access post-2026-07-31 fresh-forward outcomes or write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge automatically.
