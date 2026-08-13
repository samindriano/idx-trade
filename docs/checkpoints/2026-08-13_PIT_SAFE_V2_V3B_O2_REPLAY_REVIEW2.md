# PIT-Safe Replay Review 2 — Control Equivalence and Conditional Ladder

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`  
Reviewed replay HEAD: `944d72966ad28b21eef23872762007b69294ee3d`

## Scope

This bounded remediation reads the already completed external replay artifacts
only. It does not refit models, change the corrected tables, call providers,
read protected outcomes, or modify the immutable panel. The prior replay root
remains unchanged:

`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_historical_replay_v1_20260813_001`

The derivative review root is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_historical_replay_review2_20260813_001`

## Exact V2 ↔ V3 control equivalence

The existing replay prediction artifacts were joined by fold, ticker, date,
signal-session index, and binary target. The V2 `HGB_XS_MARKET` control and
V3-B `V3B_COMMON_SUPPORT_BASELINE` have:

- rows: `144,221` vs `144,221`;
- exact identities: `true`;
- exact scores: `true`;
- maximum absolute score difference: `0.0`;
- folds: `V2F1` through `V2F6`.

Source prediction hashes:

- V2 predictions:
  `1c7f38242ef2bd78da61173f2d2855fd522c12892bd6ee1ee90e8ef63531babe`;
- V3-B predictions:
  `a1ca242d7856de6fc7eabdd6bcb1670f79008a7b705db72299721349530eaab3`.

The existing replay manifest was also re-hashed successfully before this
comparison; all `72/72` source artifact hashes remained valid.

## Conditional ladder correction

The raw O2 metric diagnostic remains:

`O2_SURVIVOR`

That raw result is not a clean-lineage survivor because its V3-B parent did not
pass the exact late paired gate:

`V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`

The corrected conditional status is therefore:

`O2_DIAGNOSTIC_ORPHANED_PARENT`

This is intentionally not `O2_NO_SURVIVOR`: the downstream diagnostic result
is preserved and not automatically converted into a failure merely because the
parent failed. It is also not eligible to create a clean O2 model identity,
forward counter, or prospective validation lineage until a valid parent is
established under a new explicit decision.

The ladder policy is persisted as:

`downstream_verdict_does_not_automatically_propagate`

## Engineering remediation

- Replay validation now accepts only actual boolean values for
  `universe_primary_liquid`; strings such as `"False"` fail closed instead of
  becoming truthy under `.astype(bool)`.
- Existing replay review can verify source manifest hashes, exact V2/V3
  control equivalence, and conditional parent status without refitting.
- The replay runner now preserves raw O2 diagnostic status separately from the
  conditional clean-lineage status.
- The stale handoff reference was corrected to reviewed HEAD `944d729`; the
  post-review commit is recorded in the final handoff.

## Validation and hashes

- focused tests: `6 passed`;
- full pytest: `494 passed, 0 failed`;
- existing warnings: four non-blocking pandas/runtime warnings;
- review summary SHA-256:
  `9c0d23d1420327794e8d6603f4cad8ee78839fc0b33d8ef17984db7296bf5a3e`;
- review artifact manifest SHA-256:
  `5029e2c58b89e5f962729dcc0703dcb9e50899de97f7674fe1bb0e57d058631a`.

No model, data, outcome, provider, forward-counter, or canonical artifact was
changed. Stop for independent ChatGPT review.
