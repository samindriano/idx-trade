# Ranking V3-C Review PASS + V3-D Post-V3-C Amendment

Date: 2026-08-10 (Asia/Jakarta)

Status: **V3-C CLOSED / REVIEW PASS; V3-D AMENDED PRE-OUTCOME / NOT AUTHORIZED TO SCORE**

## V3-C independent review

The authoritative V3-C F1-F4 result is accepted as methodologically valid.

- final result: `V3_C_REGIME_KILL_KEEP_V2_CONTROL`;
- exact V2 control equivalence: PASS on 84,732 rows, maximum score/metric difference `0.0`;
- fragmentation gate: PASS for V2F1-V2F4;
- candidate absolute sanity: PASS;
- overall paired promotion: FAIL;
- regime-specific gate: FAIL;
- cumulative V3 evaluated candidate count: `7`.

The final merged repository tree after preserving concurrent V3-D pre-outcome engineering passed `277` tests with `0` failures and `3` existing warnings. No V3-D cache or V3-D outcome run occurred during that validation.

## Interpretation

The tested explicit two-expert regime architecture failed broadly, not merely by a narrow threshold miss.

Overall candidate-minus-control medians:

- PR-delta improvement: approximately `-0.012317`;
- ROC change: approximately `-0.008792`;
- Q5-Q1 change: approximately `-0.020754`.

The degradation was concentrated especially in the STRESS partition:

- NORMAL median PR improvement approximately `-0.001471`;
- STRESS median PR improvement approximately `-0.028965`.

The correct conclusion is narrow: **sample-fragmenting NORMAL/STRESS HGB specialization is rejected**. It does not justify rescuing V3-C with new thresholds, expert counts, blending, or score alignment.

The frozen regime state remains useful as an evaluation partition because it exposes conditional fragility that aggregate metrics can hide.

## V3-D amendment decision

The one allowed post-V3-C, pre-V3-D-outcome amendment is exercised now.

Controlling amendment:

`docs/RANKING_V3_SECTOR_RELATIVE_POST_V3C_AMENDMENT_V1.md`

The V3-D candidate itself is unchanged:

- exact V2 global control ordinal 008;
- exact V2 25 features + six PIT sector-relative features ordinal 009;
- one global HGB;
- no regime feature/router/expert;
- no Structure-Lite inheritance.

Only the evaluation contract is strengthened.

## Added V3-D regime robustness guard

The final V3-D verdict must evaluate candidate-minus-control behavior inside the exact frozen V3-C `NORMAL` and `STRESS` partitions using the immutable V3-C discovery cache SHA:

`1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`

Promotion requires the original V3-D data/control/absolute/paired gates and additionally:

- NORMAL median PR improvement >= `-0.005`;
- STRESS median PR improvement >= `-0.005`;
- NORMAL median ROC change >= `-0.005`;
- STRESS median ROC change >= `-0.005`;
- NORMAL median Q5-Q1 change >= `-0.005`;
- STRESS median Q5-Q1 change >= `-0.005`;
- worst fold/state PR improvement >= `-0.015`.

Top-decile lift remains diagnostic only.

## Implementation

A separate wrapper preserves the original base V3-D implementation and makes the amendment auditable:

`src/idx_trade/ranking_v3_sector_amended.py`

Behavior:

1. verifies the final V3-D authorization includes the amendment SHA and exact V3-C regime-cache SHA;
2. runs the existing base V3-D F1-F4 discovery implementation;
3. attaches only frozen V3-C regime metadata to the resulting prediction rows;
4. computes fold/state paired diagnostics;
5. applies the frozen non-degradation guard;
6. writes a separate final amended verdict that controls over the base V3-D preliminary verdict.

Focused amendment tests:

`tests/test_ranking_v3_sector_amended.py`

No full pytest result is claimed for commits added after the user's final merged-tree V3-C validation. A new full pytest is mandatory before V3-D PIT data work.

## V3-D current boundary

V3-D is still **not authorized to score**.

Next legal work is outcome-independent only:

1. full pytest on amended tree;
2. locate/build defensible PIT historical sector history;
3. independently verify every source document/archive hash;
4. validate intervals and availability;
5. build V3-D cache through session 984 only;
6. inspect coverage/provenance only;
7. stop for final outcome authorization.

V2F5/V2F6 and reserved post-2026-07-31 forward outcomes remain sealed.
