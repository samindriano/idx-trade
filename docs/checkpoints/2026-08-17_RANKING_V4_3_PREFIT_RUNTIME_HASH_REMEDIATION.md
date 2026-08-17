# Ranking V4-3 — pre-fit runtime hash remediation

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`
Blocked predecessor: `9d3452528acb481dac679d3b2239decd627730e3`
Status: `V4_3_PREFIT_RUNTIME_HASH_REMEDIATED_READY_FOR_LOCAL_CAPTURE_RETRY`

## Finding

The failed pre-fit capture was caused by a checkout-byte identity mismatch, not a scientific-config mutation.

Independent Git comparison from the original preregistration anchor `8dbde070b18edf432348062e5a9218f6ef2665f9` through blocked HEAD `9d3452528acb481dac679d3b2239decd627730e3` shows no change to `config/ranking_v4_3_preregistration.json`.

The frozen protocol expected SHA-256:

`835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849`

The Windows working-tree checkout reported `3a54dcf...` while remaining Git-clean. This is consistent with checkout line-ending conversion: Git semantic/tracked identity is unchanged, while raw working-tree bytes may differ.

## Remediation

The scientific pin is **not changed**.

Required artifact pins are now verified against canonical bytes stored at the current Git HEAD using:

`git show HEAD:<path>`

The capture separately records raw working-tree SHA-256 values. A clean worktree remains mandatory, so a semantic/local edit still fails closed.

This makes the identity rule platform-robust without normalizing, rewriting, or re-pinning the preregistered configuration.

## Files changed

- `config/ranking_v4_3_prefit_runtime_protocol.json`
- `scripts/capture_v4_3_prefit_environment.py`
- `tests/test_ranking_v4_3_prefit_runtime.py`

No V4-0/V4-1/V4-2/V4-3 scientific parameter, target, fold, feature, learner hyperparameter, threshold, or support identity was changed.

## Runtime boundary

The retry remains capture-only. It may inspect package/runtime/estimator configuration but may not:

- load or materialize R5/R10;
- materialize target ranks;
- fit an estimator;
- produce predictions;
- compute IC, Top-30, raw-return or other performance metrics;
- access protected/fresh-forward outcomes;
- call a provider.

## Remaining pre-target blocker

Even after a successful runtime capture, first V4 target materialization remains unauthorized until the exact execution path is frozen and the V4-2 fail-closed corporate-action continuity rule is implemented across `Open_(t+1) -> Close_(t+5/t+10)`.

Verdict:

`V4_3_PREFIT_RUNTIME_HASH_REMEDIATED_READY_FOR_LOCAL_CAPTURE_RETRY`
