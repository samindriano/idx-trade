# Ranking V3 Final Review — PASS / Historical-Development Architecture Closed

Date: 2026-08-10 (Asia/Jakarta)

Status: **FINAL V3 REVIEW PASS — HISTORICAL-DEVELOPMENT ARCHITECTURE CLOSED**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

## Review decision

The one-shot V2F5/V2F6 late-development confirmation is accepted as valid.

Final historical-development Ranking V3 architecture:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

This closes the V3 ranking architecture search on the currently consumed historical-development data. No V3 rescue, additional ranking-model tournament, alternate Structure-Lite parameterization, or second F5/F6 attempt is authorized.

This is **not independent fresh-forward validation** and does not authorize probability calibration, execution/PnL claims, paper/live trading, Stage 6, `IDX-VAL-002`, Kelly sizing, or merge to `main`.

## Why the result is accepted

### 1. Exact-control integrity passed

On the atomic F5/F6 confirmation, the exact frozen V2 `HGB_XS_MARKET` control reproduced immutable V2 reference predictions and all required metrics on 59,491 validation rows with maximum score and metric difference `0.0`.

Therefore the observed Structure-Lite deltas are not attributable to a changed split, row set, target, control implementation, or evaluation code.

### 2. Structure-Lite improved the primary ranking metric in both late folds

Paired PR improvement versus exact V2 control:

- F5: `+0.0016661426`;
- F6: `+0.0135161180`;
- median: `+0.0075911303`;
- worst: `+0.0016661426`.

Both late folds are nonnegative and the frozen median threshold `>= +0.001` is passed.

### 3. Secondary ranking separation also improved in both folds

Paired Q5-Q1 change:

- F5: `+0.0215800814`;
- F6: `+0.0038483525`;
- median: `+0.0127142169`;
- worst: `+0.0038483525`.

Paired ROC change:

- F5: `+0.0026017659`;
- F6: `+0.0118806168`;
- median: `+0.0072411913`.

This matters because the candidate did not pass only through one headline PR metric while degrading overall ordering geometry.

### 4. F6 is especially informative

The exact V2 control on F6 had ROC-AUC `0.4931017075`, below 0.5, despite positive PR delta and Q5-Q1. Structure-Lite moved F6 to:

- PR delta `0.0321593843` vs control `0.0186432663`;
- ROC-AUC `0.5049823243` vs control `0.4931017075`;
- Q5-Q1 `0.0487045129` vs control `0.0448561604`.

So the late confirmation is not merely preserving an already-strong control. The added causal price-structure geometry recovered meaningful ranking separation in the weakest late V2 fold.

This is historical-development evidence only; it does not establish that the same recovery will persist in unseen future data.

### 5. Top-decile behavior remains a diagnostic warning, not a failure

F5 top-decile lift improved by `+0.0164814105`; F6 decreased by `-0.0043770061`.

Top-decile Jaccard versus control was approximately `0.3335` on F5 and `0.3632` on F6, showing that Structure-Lite materially changes which names occupy the extreme top bucket.

The preregistered contract correctly kept top-decile lift diagnostic-only. This warning must remain visible in future portfolio/candidate-selection research. It must not trigger post-hoc Structure-Lite tuning.

## V3 ladder closure

- V3-A Recency: killed;
- V3-B Structure-Lite: promoted and late-development confirmed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, never outcome-tested;
- V3-E True Ranking: killed;
- optional integration experiment: skipped because there is only one independently surviving component.

Cumulative evaluated V3 architecture-candidate count remains `9`. F5/F6 reused existing V3-B ordinals 004/005 and did not create new candidate identities.

## Frozen V3 conclusion

The defensible conclusion is:

> Adding a compact, causal eight-feature support/resistance and structure-geometry bundle to the frozen V2 HGB ranking model produced robust incremental historical-development ranking value across F1-F4 and independently reserved late-development folds F5-F6.

Do **not** generalize this to:

- calibrated TP probability;
- realized portfolio profitability;
- transaction-cost robustness;
- execution quality;
- live-trading readiness;
- independent future validation.

## Next research phase

The V3 ranking model should now become a **fixed benchmark**, not a moving target.

While the separate 100-session post-2026-07-31 fresh-forward block accumulates and remains outcome-sealed, the preferred next research lane is orthogonal to alpha ranking:

**V4-A Path Risk / Adverse Excursion — specification first.**

The V4-A research question should be whether a second model can characterize adverse path risk, drawdown/excursion, and resolution behavior conditional on a setup, without replacing or retuning the frozen V3-B opportunity rank.

V4-A must remain a separate lane. It must not use its results to retroactively change V3-B or consume the reserved fresh-forward V3 outcomes.

## Protected boundary

- V2F5/V2F6 are consumed and must never be rerun for model selection;
- sessions `1225+` remain outside the consumed late-development confirmation;
- post-2026-07-31 fresh-forward outcomes remain untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no fresh-forward authorization exists yet;
- no calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge is authorized by this review.
