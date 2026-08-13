# STAGE2_SPEC_GO - research specification and validation design

Date: 2026-08-09 (Asia/Jakarta)
Branch: `data/idx-data-002c`
Source head before documentation commit:
`057d7c2df57ebe259f8b93642128e91ad294b146`

## Decision

`STAGE2_SPEC_GO`

This is a specification and validation-design decision only. It does not
authorize modelling, `IDX-VAL-002`, holdout inspection, paper/live trading, raw
data changes, or a merge to `main`.

## Immutable input

The input remains the independently verified `SIGNAL_RESEARCH_HLCV` panel:

- window: `2021-04-29 -> 2026-07-31`;
- official sessions: 1,260;
- ACTIVE rows: 981,940;
- panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- manifest: `valid=true`, 15/15 artifacts.

The strict execution-grade 1260 contract remains FAIL and is not weakened.
Open remains nullable in the signal layer and is never synthesized.

## Frozen contract

- question: whether post-close causal technical/market structure contains
  information about favorable/adverse future excursion;
- signal time: after official close of `t`;
- label reference: `SIGNAL_REFERENCE_CLOSE = Close_t`, never a fill price;
- primary label: first-touch barrier, H=10, ATR14, `k_sl=1.0`, `RR=1.5`;
- sensitivity: H=5/H=20 barriers, MFE/MAE, and normalized close return;
- ambiguity: `AMBIGUOUS_SAME_BAR`, no guessed ordering, excluded from primary
  binary calibration and retained diagnostically;
- primary universe: point-in-time common shares that are ACTIVE at `t`, have
  at least 20 valid observations in the trailing 60 sessions, and have at
  least IDR 1 billion median official Regular-Market Value;
- sensitivity universes: all valid common shares and causal top-100/top-300;
- primary metric: mean fold PR-AUC with fixed base-rate and momentum
  comparisons; Brier/ECE, ROC-AUC, excursion, and coverage are also reported;
- semantic separation: probability, Opportunity Score, and Estimate Reliability
  remain distinct outputs.

## Exact temporal validation

- development: sessions 1-1008, `2021-04-29 -> 2025-07-14`;
- locked holdout: sessions 1009-1260, `2025-07-15 -> 2026-07-31`;
- sessions 1241-1260 (`2026-07-06 -> 2026-07-31`) are the H=20 horizon-end
  buffer and cannot receive a complete label within the immutable panel;
- F1: train 1-504, gap 505-524, validation 525-650;
- F2: train 1-650, gap 651-670, validation 671-796;
- F3: train 1-796, gap 797-816, validation 817-942;
- development tail 943-1008 is not an unplanned validation fold.

Training labels whose forward interval intersects a validation boundary are
purged. The 20-session gaps are also explicit embargo periods. All
preprocessing, feature selection, modelling, and calibration must fit only on
earlier training dates. The final holdout is read once only after all
development choices are frozen.

## Review and validation

An independent read-only adversarial review was completed against the exact
Stage-2 drafts. It checked hidden lookahead, execution assumptions, nullable
Open, holdout contamination, ambiguous daily-bar paths, liquidity rules,
purge/embargo, and testability. One fold-table inconsistency was corrected
before the final review; no material unresolved finding remained.

The source test suite was already green after the last executable change
(`157 passed, 0 failed`, with three pre-existing pandas warnings). This task
changed documentation only; no executable code or runtime artifact was added.

## Next action

`STAGE 3 - LABEL / FEATURE PIPELINE + BASELINE MODELS` may be proposed in a
separate approval. It must not begin from this checkpoint automatically.
