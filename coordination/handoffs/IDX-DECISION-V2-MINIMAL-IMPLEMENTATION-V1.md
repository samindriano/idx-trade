# IDX Decision V2 Minimal Implementation V1

Status: `REVIEW_REMEDIATED_REPLAY_RUNNER_PREP_READY`

Owner: `ChatGPT/Decision-V2-Minimal-Implementation`

Parent preregistration: `research/idx-decision-v2-minimal-prereg-v1`

Scope is exact implementation of the frozen Decision V2 Minimal preregistration only: generic rank/state engine, V4-X1 profile adapter, deterministic intents/state observations, and adversarial/unit tests.

Independent audit found one observability gap: missing explicit `UNFILLED_NO_QUALIFIED_CHALLENGER` capacity state. That gap is fixed. Additional reusable state-lineage hardening now binds plan-derived shadow state to Decision `rule_id` and rejects cross-profile bound-state reuse. Full GitHub Actions validation on remediated code HEAD `32af46172a686fdf407e1026ad4acdab12edc355`: `432 passed`, `26 warnings`, `0 failed`.

No 600-OOS replay, no returns/PnL, no H5/H10 rescue rule, no score/rank smoothing, no parameter changes, no alpha/model changes, no provider/network calls, and no protected/fresh-forward outcome access.

Next boundary: prepare the exact outcome-blind 600-OOS structural replay runner. The runner must enforce pinned source hashes, exact 600-session/172,697-row identity, adjacent `(t-1,t)` session iteration with no skip/fold reset/pre-roll, bound shadow-state chaining, and all preregistered mechanical acceptance gates before any replay execution.
