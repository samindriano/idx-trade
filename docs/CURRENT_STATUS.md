# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 frozen control remains exact `HGB_XS_MARKET`;
- Ranking V3 historical-development architecture search is **CLOSED**;
- final V3 historical-development architecture is **`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`**;
- one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- cumulative evaluated V3 architecture-candidate count remains `9`; V3-D ordinals `008/009` remain unviewed;
- V2F1..V2F6 are now development knowledge and may not be relabeled independent holdouts for V4;
- sessions `1225+` remain sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Frozen V3 conclusion

Final review checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REVIEW_PASS_CLOSED.md`

Late-development result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_RESULT.md`

Defensible conclusion:

> Adding the frozen compact eight-feature causal Structure-Lite geometry bundle to the exact V2 HGB ranker produced robust incremental historical-development ranking value across F1-F6. This remains ranking evidence only, not calibrated probability, execution/PnL evidence, live readiness, or independent future validation.

V3-B paired PR improvement versus exact V2 control was positive on all six development folds. F1-F4 median paired PR improvement was `+0.0039258450`; F5/F6 median was `+0.0075911303`. Top-decile behavior remains a diagnostic caveat rather than a promotion target.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Immutable V2 prepared cache:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`.

Frozen V3-B late-development cache used as the V4 base:

- status `RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN`;
- SHA-256 `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA-256 `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- rows/tickers/sessions `286,453 / 737 / 20..1224`;
- no session `1225+` materialized.

## V4 — final alpha program

V4 is now the project's **final bounded alpha-generation round** before primary attention moves to fresh-forward validation and then separate risk/uncertainty/portfolio/execution layers.

The design arena is frozen in:

`docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`

Seven information families are retained as a design shortlist, not seven automatic model runs:

1. Liquidity & Participation Quality;
2. Price-Path Quality;
3. Cross-Sectional Opportunity Context;
4. Peer / Sector Relative Strength, conditional on PIT sector history;
5. Systematic-Adjusted / Idiosyncratic Strength;
6. Catalyst / Fundamental Context, conditional on PIT provenance;
7. Flow / Ownership Information, conditional on data readiness.

Normal executable budget remains narrow: normally three main families plus at most one defensible conditional wildcard, one frozen bundle per family, no model zoo, and at most one preregistered integration after independent family results.

## Current V4-A family

Current family:

**`V4-A-PARTICIPATION-V1` — Participation Quality / Price Impact.**

Controlling files:

- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_EXPERIMENT_MAP_V1.md`;
- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`;
- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_REVIEW_ADDENDUM_V1.md`;
- `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`.

Reserved first-pass candidates are frozen before V4 outcome access:

- ordinal `012`: exact V3-B 33-feature control;
- ordinal `013`: V3-B + three-feature **A1 Impact/Absorption** bundle;
- ordinal `014`: V3-B + four-feature **A2 Persistent Directional Participation** bundle.

A1 and A2 are specified together and are intended to be scored atomically/parallel-equivalently. There is **no first-pass A1+A2 integration candidate**. One integration may be considered only if both challengers independently pass their frozen gates.

Implementation exists for:

- causal A1/A2 feature construction;
- exact candidate feature/model definitions using frozen V3-B HGB parameters;
- V4-A cache preparation on exact frozen V3-B rows;
- atomic control+A1+A2 historical runner with frozen V3-B reference-equivalence checks and promotion gates;
- focused causal/model/gate tests.

No V4-A model outcome has been viewed yet; V4 evaluated-candidate count remains `0`, cumulative historical evaluated count remains `9`.

The authorized outcome-blind cache/audit is complete:

- cache status: `RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- cache manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`;
- all seven V4-A features have finite rate at least `98.5785%`;
- no constant feature, no feature below 80% finite coverage, and no
  `abs_spearman >= 0.95` pair;
- audit status: `RANKING_V4_A_PARTICIPATION_OUTCOME_BLIND_AUDIT_COMPLETE`;
- audit SHA-256: `c89a19d1cce390b4734dc1de8c2cc08994217248478fd2e8025d94e90f93d31a`;
- no V4-A outcome metric, fit, score, or verdict was produced.

Result checkpoint:
`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_CACHE_AUDIT_RESULT.md`.

## Immediate next action

The next permitted action is a **separate authorization review for the atomic
V4-A control+A1+A2 historical outcome run**. The cache/data audit itself is
complete; no outcome run is authorized automatically:

- review the checkpoint and handoff;
- preserve the frozen cache and audit hashes;
- authorize the one atomic F1-F6 control+A1+A2 outcome run only through a
  separate controlling handoff.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- treat V2F5/V2F6 as independent V4 holdouts;
- bypass V3-D PIT sector-history block;
- modify A1/A2 formulas based on V4 outcome metrics;
- materialize/score session `1225+` for V4 development;
- access post-2026-07-31 fresh-forward outcomes or write `FORWARD_OUTCOME_ACCESS_STARTED` without separate future authorization;
- create A1+A2 integration before both independently pass;
- conflate future path-risk/uncertainty targets with the frozen opportunity ranking target;
- start calibration/Stage 6/`IDX-VAL-002`/execution-PnL/Kelly/paper/live/main automatically.
