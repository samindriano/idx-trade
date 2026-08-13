# Checkpoint — Ranking V3-B Structure-Lite Independent Review PASS

Date: 2026-08-10 (Asia/Jakarta)

Status: **INDEPENDENT REVIEW PASS — `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8` ACCEPTED**

## Scope reviewed

Reviewed the frozen V3-B F1-F4 discovery result documented in:

`docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_F1_F4_RESULT.md`

The review does not inspect V2F5/V2F6, reserved post-2026-07-31 V2 forward outcomes, or any unregistered V3-B variant.

## Control integrity

Control equivalence is accepted:

- 84,732 F1-F4 rows;
- maximum row-level score difference `0.0`;
- maximum required metric difference `0.0`;
- tolerance `1e-12`, `rtol=0`.

Therefore the Structure-Lite comparison is against the real frozen V2 `HGB_XS_MARKET` control rather than a reconstructed approximation.

## Result interpretation

Structure-Lite produced paired PR-AUC-delta improvements versus control on all four discovery folds:

- F1 `+0.007948`;
- F2 `+0.001841`;
- F3 `+0.004879`;
- F4 `+0.002973`.

Aggregate paired PR evidence:

- median `+0.0039258450`;
- q25 `+0.0026897894`;
- worst fold `+0.0018412974`;
- not below control `4/4`.

The improvement is therefore not carried by one lucky fold or a median-only effect.

Supporting robustness also improved:

- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- Q5-Q1 not below control `4/4`.

The frozen absolute sanity gate and paired promotion gate both pass. The deterministic promotion result is accepted:

`V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`

## Important diagnostic warning

Top-decile lift is not uniformly improved:

- F1 `+0.013907`;
- F2 `+0.002826`;
- F3 `-0.014472`;
- F4 `-0.010072`;
- median change `-0.0036228765`.

This does not retroactively change the frozen V3-B gate because top-decile lift was preregistered as a diagnostic rather than a rescue/kill criterion. It does, however, mean the evidence currently supports improved broad ranking separation and Q5-Q1 geometry more strongly than improved extreme top-decile concentration.

Do not change the V3-B feature bundle, thresholds, event definitions, or promotion gate in response to this diagnostic. Carry the warning into any later integration/final-V3 review and report selected/incremental top-ranked-name behavior explicitly there.

## Coverage review

Structure coverage is sufficient for the frozen training-imputer path and no rows were dropped:

- support distance/touch finite `91.5546%`;
- resistance distance/touch finite `96.4236%`;
- level age `99.9279%`;
- role reversal/event/volume features about `99.9302%`.

Missingness remains explicit. No zero-fill or invented level was introduced.

## Research conclusion

The evidence supports retaining the complete frozen eight-feature Structure-Lite bundle as a **surviving V3 component** for later comparison/integration.

This does not prove that each of the eight features contributes individually. No feature-level ablation is authorized from this result. Any ablation would be a separate counted hypothesis and is not currently prioritized.

This is historical-development evidence only. It is not independent validation, probability calibration, execution evidence, or deployment authorization.

## Next V3 action

Proceed to **V3-C REGIME-SPECIALIZATION specification only** under a separately frozen spec.

The V3-C question must remain narrow:

> After V2 already includes causal market context and nonlinear HGB interactions, does one small explicit regime-specialization architecture improve worst-fold / worst-regime robustness without sacrificing broad ranking separation?

V3-C must not automatically inherit Structure-Lite into its primary hypothesis. To preserve attribution, the default V3-C experiment should compare explicit regime specialization against the exact V2 control first. Structure-Lite remains a separately surviving component for the one later preregistered integration experiment.

## Safety boundary

- V2F5/V2F6 remain sealed for one final-V3 late-development confirmation;
- reserved V2 fresh-forward outcomes remain unread;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- V3-B is closed to rescue/ablation under this hypothesis;
- no V3-C outcome run is authorized by this review;
- no V3-D/E, integration, calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live or main merge is authorized.
