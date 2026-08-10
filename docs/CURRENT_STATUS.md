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
- V4-B Price-Path Quality: **CLOSED — NO SURVIVOR**;
- V4-C Cross-Sectional Opportunity Context: **CLOSED — NO SURVIVOR**;
- cumulative historical evaluated-candidate count is now `17`;
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

Frozen arena: `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`.

The arena retains seven information families but intends a bounded executable set, normally three main families. V4-A, V4-B and V4-C form the current main executable sequence. Scoring remains narrow, with no model zoo or post-result rescue.

## V4-A — CLOSED

- ordinal `012` exact V3-B control: equivalence PASS;
- ordinal `013` A1 Impact/Absorption: `FAIL`;
- ordinal `014` A2 Persistent Directional Participation: `FAIL`;
- survivors: `[]`;
- no integration and no rescue.

Result checkpoint: `docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`.

## V4-B — CLOSED — NO SURVIVOR

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

The Windows-local pre-outcome cache/audit completed without outcome access:

- final reported local HEAD after concurrent V4-C merge: `147b6a4f665ecfea9117b58f10c81bc5747fe034`;
- final full pytest: `357 passed`, `0 failed`, `3 warnings`;
- cache status: `RANKING_V4_B_PRICE_PATH_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256: `8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68`;
- cache manifest SHA-256: `d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f`;
- audit SHA-256: `b8facff42be8231e263c261f97e4c02d6b9db92e64ceee831d9ff27b5c7586d6`;
- all six V4-B features non-constant;
- finite coverage `98.0775%..99.5751%`;
- no feature below the `80%` finite-rate rule;
- no absolute Spearman pair at or above the frozen `0.95` mechanical-review threshold;
- highest pair `0.940791493`, `v4b_range_acceptance_mean_5` versus `v4b_extreme_close_balance_5`.

The high B2 internal correlation remains a diagnostic warning only. It is below the frozen threshold and is not a mechanical mismatch; the frozen B2 bundle is not changed.

Independent review checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_B_PRICE_PATH_AUDIT_REVIEW_PASS.md`.

The authorized atomic first pass viewed ordinals `015..017`: exact control
equivalence passed, but both B1 `016` and B2 `017` failed the unchanged paired
gate. Survivors are `[]`; no B1+B2 integration exists.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_B_C_FIRST_PASS_OUTCOME_RESULT.md`.

Result handoff:

`coordination/handoffs/IDX-RANKING-V4-B-C-FIRST-PASS-OUTCOME-RESULT.md`.

### Final first-pass result

V4-B is closed with no survivor. The frozen result is not an invitation to
rescue, change the feature bundle, or create B1+B2 integration.

## V4-C — CLOSED — NO SURVIVOR

Hypothesis: `V4-C-CROSS-SECTIONAL-CONTEXT-V1`.

V4-C was frozen **before any V4-B outcome was viewed**.

Candidates:

- `018` exact V3-B control;
- `019` V3-B + one compact four-feature cross-sectional opportunity-dispersion bundle.

Frozen V4-C features:

1. `v4c_market_return_iqr_5`;
2. `v4c_market_return_iqr_20`;
3. `v4c_market_atr_iqr`;
4. `v4c_market_close_position_iqr_20`.

Each is computed per date from the full causal primary-liquid universe, not only label-resolved/model rows. V4-C intentionally excludes volume/value dispersion so it does not become a hidden V4-A rescue.

Controlling spec Git blob: `43f222f31c7c0ea15e870d22b066aae95858c81f`.

Implementation and the authorized first pass are complete. Exact control
equivalence passed; ordinal `019` failed the unchanged paired gate. Survivors
are `[]`, and no cross-family integration exists.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_B_C_FIRST_PASS_OUTCOME_RESULT.md`.

Result handoff:

`coordination/handoffs/IDX-RANKING-V4-B-C-FIRST-PASS-OUTCOME-RESULT.md`.

## Immediate next action

Stop for ChatGPT interpretation. Do not rescue, rerun, or integrate V4-B or
V4-C automatically:

`coordination/handoffs/IDX-RANKING-V4-B-C-FIRST-PASS-OUTCOME-RESULT.md`

The V4-B/C first-pass result is recorded above. Stop for ChatGPT review.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- treat V2F1..V2F6 as independent V4 validation;
- bypass V3-D PIT sector-history block;
- rescue/reformulate V4-A;
- change V4-B after its blind-audit review;
- adapt V4-C to any later V4-B outcome;
- rerun or adapt V4-B/V4-C after outcome access without a separate review;
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
