# Ranking V4-A Participation Quality — Pre-Outcome Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **PRE-OUTCOME DESIGN/IMPLEMENTATION REVIEW PASS — FEATURE-CACHE AUDIT REQUIRED BEFORE OUTCOME RUN**

## Reviewed scope

Reviewed against:

- `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`;
- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_EXPERIMENT_MAP_V1.md`;
- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`;
- frozen V3-B 33-feature champion contract;
- current V4-A feature/model/cache-preparation/atomic-run implementation.

No V4-A candidate outcome has been inspected during this review.

## Review conclusion

The V4-A first-pass design is sufficiently bounded and distinct from generic abnormal-volume research to proceed to **outcome-independent local feature-cache preparation and diagnostics only**.

The first-pass architecture remains exactly:

1. ordinal `012`: exact frozen V3-B control;
2. ordinal `013`: V3-B + A1 Impact/Absorption three-feature bundle;
3. ordinal `014`: V3-B + A2 Persistent Directional Participation four-feature bundle.

A1 and A2 are frozen before either result is viewed. No A1+A2 integration candidate is present in the first-pass implementation.

## Why A1 is a distinct hypothesis

A1 does not merely ask whether current volume/value is abnormal. V3-B already contains current relative volume/value and market-relative/cross-sectional forms.

A1 instead encodes **price displacement per unit of regular-market traded value**, normalized to the stock's own causal history, plus short persistence of unusually high range impact.

The implementation correctly labels close-to-close return/value as a proxy rather than canonical intraday Amihud because the project does not require historical Open and therefore cannot perfectly align the return and regular-session participation windows.

## Why A2 is a distinct hypothesis

A2 asks about the **temporal and directional structure of participation**:

- persistence of above-baseline traded value;
- recent participation acceleration;
- short and medium price-signed traded-value balance.

The signed-value terms are correctly described as price-signed participation proxies, not buyer-initiated flow, broker net buy, or ownership flow.

## Causality / gap review

PASS subject to local data diagnostics:

- all feature windows are right-aligned;
- adjacent return requires the immediately preceding official exchange session for that ticker;
- exact-five-session features fail closed if one of the five required session observations is absent;
- broader baselines use explicit minimum valid-observation rules rather than treating missing rows as zero;
- sessions `1225+` are hard-blocked from the historical V4-A implementation;
- feature builder rejects label/outcome columns;
- historical Open is not a dependency.

## Complexity / overfit review

PASS.

The first pass contains only two challenger architectures and one exact common control. There is no formula tournament, model-family tournament, hyperparameter search, threshold search or first-pass integration candidate.

The existing seven-family V4 arena is not an authorization to score all seven families. This review covers V4-A only.

## Required outcome-independent local audit

Before V4-A F1-F6 scoring is authorized, prepare the frozen V4-A feature cache from the immutable signal panel and exact frozen V3-B late-development cache, then inspect **without labels/outcome metrics**:

1. cache/source/spec hashes and exact V3-B prefix preservation;
2. row/ticker/session identity and session `1225+` absence;
3. finite/missing coverage for each of the seven V4-A feature columns overall and, if useful, by signal-date/fold range without labels;
4. feature distributions for gross numerical pathologies;
5. pairwise correlation/redundancy among V4-A features and against existing V3-B volume/value features;
6. whether any feature is effectively constant or has unusably low coverage;
7. runtime profile after cache reuse, per the existing runtime-optimization notes.

Any mechanical correction must preserve the frozen mathematics. If the data audit shows that a frozen feature is not materially observable under the stated data contract, stop and document a pre-outcome data/design block rather than silently substituting another formula.

## Outcome authorization boundary

This addendum does **not** authorize the atomic F1-F6 model run yet.

The next permitted action is V4-A cache preparation plus outcome-independent coverage/redundancy/runtime diagnostics. Only after that cache is reviewed and frozen may a separate checkpoint authorize one atomic first-pass run of control + A1 + A2.

Fresh-forward outcomes, session `1225+`, calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live and main merge remain out of scope.
