# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 frozen control remains exact `HGB_XS_MARKET`;
- Ranking V3 historical-development architecture search is **CLOSED**;
- final V3 historical-development architecture is `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- V3-B one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- V2F1..V2F6 are development knowledge and are not independent V4 holdouts;
- V4-A Participation Quality / Price Impact: **CLOSED — no survivor**;
- cumulative historical evaluated-candidate count is `12`;
- sessions `1225+` remain sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Frozen V3 conclusion

Final V3 architecture:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Across V3-B historical-development F1-F6, paired PR improvement versus exact V2 control was positive on all six folds. F1-F4 median paired PR improvement was `+0.0039258450`; F5/F6 median was `+0.0075911303`. This is ranking evidence only, not calibrated probability, execution/PnL evidence, live readiness, or independent future validation.

Key checkpoints:

- `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REVIEW_PASS_CLOSED.md`;
- `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_RESULT.md`.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Frozen V3-B late-development cache used as the V4 base:

- SHA-256 `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA-256 `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- rows/tickers/sessions `286,453 / 737 / 20..1224`;
- no session `1225+` materialized.

## V4 — final alpha program

V4 is the final bounded alpha-generation round before primary attention moves to fresh-forward validation and separate risk/uncertainty/portfolio/execution layers.

Frozen seven-family design arena:

`docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`

Families are a design shortlist, not seven automatic model runs:

1. Liquidity & Participation Quality;
2. Price-Path Quality;
3. Cross-Sectional Opportunity Context;
4. Peer / Sector Relative Strength, conditional on PIT sector history;
5. Systematic-Adjusted / Idiosyncratic Strength;
6. Catalyst / Fundamental Context, conditional on PIT provenance;
7. Flow / Ownership Information, conditional on data readiness.

Normal executable budget remains narrow: one frozen bundle per family, no model zoo, and only preregistered integration after independent survivor evidence.

## V4-A family — CLOSED

Family:

`V4-A-PARTICIPATION-V1` — Participation Quality / Price Impact.

Frozen first-pass candidates:

- ordinal `012`: exact V3-B 33-feature control;
- ordinal `013`: V3-B + three-feature A1 Impact/Absorption bundle;
- ordinal `014`: V3-B + four-feature A2 Persistent Directional Participation bundle.

The authorized outcome-blind cache audit passed before scoring. The single atomic first-pass run then completed exactly once with exact control equivalence.

Final V4-A result:

- control equivalence: `PASS` on `144,223` rows, max score diff `0.0`;
- A1 Impact/Absorption ordinal `013`: `FAIL`;
- A2 Persistent Directional Participation ordinal `014`: `FAIL`;
- survivors: `[]`;
- integration authorized by result: `false`;
- integration executed: `false`;
- no rescue or redesign is permitted.

A1 paired PR was nonnegative on only `3/6` folds, median PR improvement `+0.0000801749`, median Q5-Q1 change `-0.0028469425`, and V2F6 PR change `-0.0116775888`.

A2 was closer on PR and had positive paired PR in V2F5/V2F6, but still failed broad robustness: nonnegative PR on `4/6` folds, median PR improvement `+0.0010168334` below the frozen threshold, median ROC change `-0.0030273322`, and median Q5-Q1 change `-0.0067399084`.

The defensible family conclusion is limited to the tested frozen daily-EOD definitions: they did not add sufficiently robust incremental ranking alpha beyond V3-B.

Controlling result/review checkpoints:

- `docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`;
- `docs/checkpoints/2026-08-10_RANKING_V4_A_REVIEW_CLOSED_V4_B_SPEC_AUTHORIZED.md`.

## Current V4-B lane

Next family:

**`V4-B — Price-Path Quality` — SPECIFICATION FIRST.**

Research question:

> Conditional on frozen V3-B state and geometry information, does the way the current setup was formed — coherent versus jump-concentrated movement, and acceptance versus rejection within daily ranges — add robust cross-sectional ranking information?

Preferred pre-outcome conceptual split, subject to exact overlap review before freeze:

1. **Path Coherence / Jump Concentration** — persistent/distributed movement versus one/few extreme sessions or noisy reversals;
2. **Range Acceptance / Rejection Quality** — repeated favorable closes within daily high-low ranges versus rejection/excursion-heavy behavior.

Tail asymmetry, trend coherence, spike concentration, candle/range quality and related ideas belong inside these merged questions rather than becoming many scored variants.

No V4-B candidate ordinal is yet reserved and no V4-B outcome scoring is authorized.

## Immediate next action

Prepare and independently review a compact V4-B Price-Path specification only. Before implementation/scoring, audit overlap against the exact frozen V3-B 33-feature set and freeze exact formulas, windows, missingness semantics, candidate budget, ordinals and gates.

If two genuinely distinct V4-B sub-hypotheses survive the pre-outcome design audit, both must be fully specified before either outcome is viewed and should be scored atomically/parallel-equivalently later under a separate authorization.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- treat V2F1..V2F6 as independent V4 validation;
- bypass V3-D PIT sector-history block;
- rescue/reformulate V4-A based on viewed results;
- create or run a V4-A integration candidate;
- score V4-B before a separately frozen/reviewed specification and run authorization;
- materialize/score session `1225+` for V4 development;
- access post-2026-07-31 fresh-forward outcomes or write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge automatically.
