# Reliability / Uncertainty V1 — Frozen Forward Shadow Contract

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `research/idx-reliability-uncertainty-v1-forward-shadow`  
Decision: `RELIABILITY_V1_FORWARD_SHADOW_AUTHORIZED_FROZEN`

## Purpose

Prospectively preserve the only Reliability V0 proxy that survived historical OOF testing, `score_margin_reliability`, alongside the existing frozen O2 fresh-forward program so it can later receive genuinely fresh outcome validation.

This lane is a deterministic score-only shadow. It does **not** train a reliability model, create a calibrated probability, filter trades, alter O2 ranking, size positions, create a new official counter, or authorize any forward-outcome access.

Parallelism preflight: `DIRECT`. The scientific contract is a single sequential decision inherited from one accepted V0 survivor; parallel competing specs would create conflicting contracts rather than shorten the critical path.

## Parent evidence

Controlling historical evidence:

- Reliability V0 branch: `research/idx-reliability-uncertainty-v0`;
- frozen V0 spec: `37259c68e22d5703f6fae6738785dee87886e63c`;
- V0 result HEAD: `1d01a1b21f32ba6b97d2cf3684d4f11a499f653b`;
- independent V0 acceptance: `a99d53de91dfc44f9688ba7adead5206d7c7929d`;
- accepted verdict: `RELIABILITY_V0_FEASIBILITY_GO_ACCEPTED`.

Only `score_margin_reliability` survived. Its V0 aggregates were:

- median fold session-Spearman: `0.055202`;
- q25 fold session-Spearman: `0.047736`;
- positive Spearman folds: `6/6`;
- median Q4-Q1 local-quality lift: `0.026501`;
- median top-40% selective lift: `0.011495`;
- median conditional lift after O2-score control: `0.007326`;
- all four metrics positive in `6/6` folds.

`joint_marginal_support_reliability` failed and is permanently excluded from V1. It may not be rescued, combined with P1, or silently reintroduced.

## Frozen O2 parent

V1 consumes only already-written accepted O2 score artifacts from the existing O2 fresh-forward archive.

The current accepted O2 parent pins:

- O2 model SHA-256: `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`;
- O2 feature-order SHA-256: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- first accepted O2 forward session: date `2026-08-12`, official session index `1268`;
- accepted first-session O2 score artifact SHA-256: `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d`;
- accepted first-session manifest SHA-256: `4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2`;
- O2 counter remains the sole official outcome gate and currently started at `1/100` with outcomes locked.

V1 never changes O2 eligibility. A row receives a Reliability V1 value **iff it has a finite accepted O2 score in that session**. O2-ineligible rows, including genuine flat-range zero-denominator exclusions, remain present in source evidence but have Reliability V1 status `NOT_APPLICABLE_O2_UNSCORED` and no synthetic reliability value.

## Frozen reliability formula

For each accepted O2 session independently, use only its O2-scored rows.

1. Stable-sort rows by `(O2 score, ticker)` ascending.
2. For each row compute adjacent score gaps:
   - edge row: its single adjacent gap;
   - interior row: `min(lower_gap, upper_gap)`.
3. Compute the session O2 score IQR: `Q75(score) - Q25(score)` using the same numeric quantile semantics as Reliability V0.
4. If there are fewer than two scored rows, or score IQR is zero/non-finite, Reliability V1 is `UNAVAILABLE_SESSION_GEOMETRY`; this **must not** fail O2 or alter the O2 counter.
5. Otherwise:

`score_margin_reliability = nearest_adjacent_score_gap / score_iqr`

Higher values mean greater score separation and therefore higher ex-ante reliability under the V0 hypothesis. Tied O2 scores receive raw reliability `0`.

No clipping, winsorization, smoothing, rolling normalization, historical calibration, cross-session standardization, or learned transform is allowed.

## Display percentile

A display-only `reliability_percentile` is persisted for interpretability. It is not a probability and is not the primary scientific variable.

Within each accepted session, among finite raw reliability values:

- use ascending average rank so equal raw reliability values receive the same percentile;
- `reliability_percentile = 100 * (average_rank - 1) / (n - 1)` for `n >= 2`;
- if `n < 2`, percentile is unavailable.

The scientific forward validation must use the frozen raw `score_margin_reliability`; the percentile is a monotonic display transform only.

No `LOW / MEDIUM / HIGH` thresholds are authorized in V1 shadow collection.

## Alignment and start boundary

V1 has **no independent official counter**. It inherits the accepted O2 fresh-forward cohort.

One bounded historical-in-forward backfill is authorized for the already accepted `2026-08-12 / session 1268` O2 score artifact because:

- the O2 score artifact was immutable before this V1 contract;
- no forward outcome has been accessed;
- V1 computation is deterministic and score-only;
- including it preserves exact alignment with the O2 100-session cohort.

The backfill must read only the existing accepted O2 score artifact and manifest; no provider call, recapture, O2 rescore, data repair, or outcome path is allowed.

After that one alignment backfill, every new Reliability V1 sidecar is created only from newly accepted O2 score artifacts under the unchanged formula above.

`aligned_sessions` may be reported descriptively, but it is not a second gate or counter. The only outcome-opening trigger remains the existing O2 100-session vault contract.

## Artifact contract

Do not mutate immutable O2 score artifacts. Persist Reliability V1 as a separate sidecar in the existing forward-monitoring archive, subordinate to O2.

Each session sidecar must contain at minimum:

- `date`;
- official `session_index`;
- `ticker`;
- O2 scored/eligible status;
- exact O2 score consumed;
- `score_margin_reliability` raw value;
- `reliability_percentile` display value;
- reliability status/reason;
- V1 formula/version identifier.

Each sidecar manifest must pin at minimum:

- source O2 score-artifact SHA-256;
- source O2 session-manifest SHA-256;
- O2 model SHA-256;
- O2 feature-order SHA-256;
- V1 spec/implementation commit identity;
- row counts: source rows, O2-scored rows, reliability-finite rows, O2-unscored/not-applicable rows;
- sidecar artifact SHA-256;
- runtime protection flags.

Required protection flags are all false:

- provider call;
- source recapture/repair;
- O2 refit/rescore;
- reliability model fit;
- composite reliability score creation;
- tier/threshold optimization;
- trade filtering;
- independent reliability counter registration;
- fresh-forward outcome access;
- forward-outcome-access marker write.

## Monitoring/UI boundary

Reliability V1 is subordinate metadata inside O2 detail/score rows only. It must not become a fourth primary model card, leaderboard candidate, promotion candidate, or trading recommendation.

Allowed pre-outcome display:

- raw reliability margin;
- reliability percentile;
- availability/status;
- aligned-session count inherited from O2.

Forbidden pre-outcome display/interpretation:

- hit rate, PR-AUC, returns, winners/losers, realized ranking quality;
- `X% chance correct` language;
- optimized LOW/MEDIUM/HIGH tiers;
- performance comparison conditioned on reliability.

## Future validation boundary

No forward reliability performance is evaluated during accumulation.

When the existing O2 outcome vault is eligible to open, **before any protected outcome is read**, a separate frozen Reliability V1 forward-evaluation checkpoint must be committed. That checkpoint must use the same V0 family of realized target/metrics:

1. row-level `local_pairwise_quality` based on the frozen O2 H10 binary outcome contract;
2. session Spearman between raw `score_margin_reliability` and local pairwise quality;
3. Q4-Q1 local-quality lift;
4. top-40% selective-quality lift versus full-session quality;
5. conditional reliability lift within O2-score quintiles.

The exact forward pass/fail aggregation thresholds must be preregistered in that outcome-blind checkpoint before vault access. They may not be chosen after seeing forward outcomes.

Until that later validation passes, Reliability V1 is `EXPLORATORY_FORWARD_SHADOW`, not a production confidence layer.

## Minimum implementation tests

Tests must cover at least:

- exact V0 score-margin behavior for edge rows, interior rows, and O2-score ties;
- zero/non-finite IQR produces reliability-unavailable without failing O2;
- O2-unscored rows remain reliability-null/not-applicable;
- average-rank percentile gives identical percentiles for tied raw reliability;
- source O2 score/manifest hash pinning;
- one-time 2026-08-12 outcome-blind alignment backfill from existing artifact only;
- no independent counter mutation;
- all protected runtime flags remain false;
- sidecar persistence is separate from immutable O2 score artifacts.

## Hard stop

After implementation and score-only alignment verification, stop for independent review. Do not inspect any protected forward outcome, add another proxy, revive P2, fit a model, optimize tiers/filters, or change this formula based on observed shadow values.
