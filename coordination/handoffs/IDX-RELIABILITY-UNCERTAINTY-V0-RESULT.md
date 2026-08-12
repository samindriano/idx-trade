# Handoff

from: Codex
to: ChatGPT review
task_id: IDX-RELIABILITY-UNCERTAINTY-V0
model_used: Luna xhigh / Orchestra DIRECT
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `37259c68e22d5703f6fae6738785dee87886e63c`
branch: `research/idx-reliability-uncertainty-v0`
head_commit_before_handoff: `74858eb`

## Scope

Executed the frozen Reliability / Uncertainty V0 historical diagnostic exactly
once against the accepted historical O2 OOF predictions, V3-B training table,
and pinned Open coverage/readiness artifact. No provider call, O2 refit/rescore,
reliability model fit, fresh-forward access, or proxy/gate change occurred.

## Result

- verdict: `RELIABILITY_V0_FEASIBILITY_GO`;
- qualified primary proxy: `score_margin_reliability`;
- non-qualified primary proxy: `joint_marginal_support_reliability`;
- O2 OOF rows: `140,679`;
- Open coverage rows: `292,633`;
- Open-ready/common-support rows: `278,168`;
- session metric rows: `2,400`.

`score_margin_reliability` six-fold metrics are persisted in the dated result
checkpoint. Its gate aggregates were Spearman median/q25 `0.055202`/`0.047736`,
Q4−Q1 median `0.026501`, selective-lift median `0.011495`, conditional-lift
median `0.007326`, with `6/6` positive folds for every gate family.

## External artifact

Output directory:
`D:\Documents\Project\idx-trade-data-gate-20260808v\reliability_uncertainty_v0_20260813_001`

Artifact manifest SHA-256:
`09b0f927821c3f594d74d07f2bd6d2b03fd2bcce13366f0cc9231d3912db7eb1`

All child hashes match the manifest; the full list is in
`docs/checkpoints/2026-08-13_RELIABILITY_UNCERTAINTY_V0_RESULT.md`.

## Validation

- Reliability-focused tests: `8 passed`;
- full pytest: `48 passed, 0 failed, 0 warnings, 1.53s`;
- small unrelated storage fixture correction was included so the existing
  independent raw/vendor revision-conflict contract is represented accurately.

## Decisions / boundaries

The result is a feasibility diagnostic only. It does not authorize a
reliability model, composite score, trade filter, O2 change, forward scoring,
or fresh-forward inspection. Stop for independent ChatGPT review.
