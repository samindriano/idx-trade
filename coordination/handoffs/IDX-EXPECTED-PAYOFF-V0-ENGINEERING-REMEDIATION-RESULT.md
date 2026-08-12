# Handoff

from: Codex Luna xhigh
to: ChatGPT independent review
task_id: IDX-EXPECTED-PAYOFF-V0-ENGINEERING-REMEDIATION
model_used: GPT-5 Codex
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 7345e9790dd4b339a8f495e05c7804b6fde2ab38
branch: research/idx-expected-payoff-v0-feasibility
scope: engineering remediation only after accepted V0 scientific review

## Result

Scientific verdict remains unchanged:
`EXPECTED_PAYOFF_V0_FEASIBILITY_GO`.

Completed without rerunning V0:

- added explicit missing/invalid exit, cutoff, exact-score-consumption,
  readiness/feasibility boundary, protected-runtime, and diagnostic tests;
- derived fold-level D1/D10 mean/median/q25/q75 and decile monotonicity from
  the preserved resolved artifact;
- reverted the unrelated `storage.py` suppression so independent
  `vendor_adj_close` revisions remain visible;
- updated the storage test to require both independent conflicts.

Focused tests: 17 passed.  
Full pytest: 54 passed, 0 failed, 0 warnings, 5.264 seconds.

## External post-review artifacts

Root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\expected_payoff_v0_feasibility_20260812_001`

Post-review manifest SHA-256:
`c750eac0c9b0784aa38bb45142a2b2ac4c835f13ad5d30af3309424e8ce8a121`.

Original V0 artifact manifest unchanged:
`c84170d5b438ad7481aa9a7985f377fbbd701ebfee80d720cd689d3bb7a49abd`.

Post-review files:

- `post_review_fold_d1_d10_quantile_summary.csv` SHA
  `5d1b2d791f11cb972fb1298dadcc2003d40284730e93e0181f11415aaf24ee65`;
- `post_review_decile_monotonicity.csv` SHA
  `e4586d0f1cf2e0c7700d44ba60213d2ecba43e170b6e004df6df52972ae25d9d`.

## Boundaries verified

- no provider calls;
- no one-shot V0 rerun or rescore;
- no alternate target/entry/horizon/normalization;
- no fresh-forward outcomes and no `FORWARD_OUTCOME_ACCESS_STARTED`;
- no O2/O2.1/V3-B/runtime/counter/outcome-vault changes;
- no payoff model fit.

Expected Payoff V1 still requires a new frozen specification and review.
