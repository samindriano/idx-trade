# IDX Decision V2 Minimal Implementation V1

Status: `CLAIMED_IMPLEMENTATION_ACTIVE`

Owner: `ChatGPT/Decision-V2-Minimal-Implementation`

Parent preregistration: `research/idx-decision-v2-minimal-prereg-v1`

Scope is exact implementation of the frozen Decision V2 Minimal preregistration only: generic rank/state engine, V4-X1 profile adapter, deterministic intents/state observations, and adversarial/unit tests. No 600-OOS replay, no returns/PnL, no H5/H10 rescue rule, no score/rank smoothing, no parameter changes, no alpha/model changes, no provider/network calls, and no protected/fresh-forward outcome access.

The implementation must not reinterpret the frozen thresholds after observing runtime behavior. Historical replay remains separately gated after code/contract review.
