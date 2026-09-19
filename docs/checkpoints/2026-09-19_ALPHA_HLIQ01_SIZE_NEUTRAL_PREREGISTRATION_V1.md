# H-LIQ-01 Size-Neutral Representation — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PREREGISTERED / OUTCOME-BLIND / NO NEW CANDIDATE ID`

## Decision question

Is H-LIQ-01's exposure to low `regular_market_value` names intrinsic to the
temporal variability mechanism, or is it mainly caused by the raw scale of
`log(close * volume)`?

This is a representation question, not target-based tuning. The result may
retain, narrow, or close the H-LIQ representation family, but cannot create C5
or change any candidate's predictive status.

## Fixed representations

1. Baseline: H-LIQ-01 h20, the 20-session rolling standard deviation of
   `log(close * volume)`, higher score first.
2. Size-neutral diagnostic: on each official session, regress the cross-
   sectional rank of the baseline H-LIQ score on the cross-sectional rank of
   `regular_market_value` using an intercept and one slope; use the residual as
   the size-neutral score, higher residual first.

There is exactly one neutralization rule and no horizon, bucket-count,
winsorization, or threshold sweep. The market-value rank is a same-session
structural diagnostic only; it is not historical ADV or executable capacity.

## Required read-only outputs

For baseline and size-neutral scores, report:

- finite rows/dates/tickers;
- Top-30 date coverage, turnover, overlap, and persistence;
- selected bottom-value and bottom-volume quartile shares;
- daily Spearman and Top-30 overlap against baseline H-LIQ, C1, C2, and C4;
- score/key/source/code hashes and explicit access limitations.

## Interpretation rules

- A lower bottom-value share is only a structural exposure change, not an
  economic or predictive improvement.
- If size neutralization materially changes selection, record the baseline and
  neutralized forms as distinct representations; do not select between them
  using outcomes.
- If neutralization changes little or damages coverage/turnover materially,
  retain the original H-LIQ conclusion and close this representation.
- In all cases retain `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`
  unless a later, separately admitted decision changes it.

## Prohibited actions

No H5/H10, forward return, label, incumbent score, provider/network, cloud,
capture, scheduler, canonical-data, or production-artifact access. No refit,
target optimization, candidate promotion, or C5 creation.

