# Expected Payoff V0 Engineering Remediation

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `research/idx-expected-payoff-v0-feasibility`  
Review anchor: `7345e9790dd4b339a8f495e05c7804b6fde2ab38`  
Scientific verdict: `EXPECTED_PAYOFF_V0_FEASIBILITY_GO` (unchanged)

## Boundary

This checkpoint records engineering/spec-compliance remediation only. The
accepted V0 experiment was not rerun, retuned, rescored, or reinterpreted. No
provider, outcome, fresh-forward, O2 runtime/counter, or payoff-model path was
accessed. `EXPECTED_PAYOFF_V0_FEASIBILITY_GO` remains the result of the original
one-shot run.

## Remediation completed

### Frozen-contract tests

The test suite now explicitly covers:

- missing exit Close and invalid/non-positive exit Close: both exclude without
  fill;
- behavioral rejection of parent signal dates after `2026-07-31`;
- exact consumption of stored O2 scores through the verified parent artifact,
  with no recomputation path;
- readiness boundary at exactly 90% global, 85% per fold, and 80 eligible
  sessions;
- strict feasibility behavior when the IC gate is zero or only 3/6 spread
  folds are positive;
- explicit protected runtime flags, all false;
- deterministic post-review diagnostic generation from preserved resolved rows.

Focused tests: **17 passed** (`test_expected_payoff_v0.py` + `test_storage.py`).

### Non-gating post-review diagnostics

The following were derived only from the existing external
`resolved_payoff_rows.parquet`; the original V0 artifacts and verdict were not
modified:

- `post_review_fold_d1_d10_quantile_summary.csv`: fold-level D1/D10 pooled
  mean, median, q25, and q75 for ATR and percentage payoff;
- `post_review_decile_monotonicity.csv`: decile-index versus realized-payoff
  means, Spearman diagnostic, adjacent non-decreasing pair count, and strict
  monotonicity flag;
- `post_review_diagnostic_manifest.json`.

Post-review manifest SHA-256:
`c750eac0c9b0784aa38bb45142a2b2ac4c835f13ad5d30af3309424e8ce8a121`.

Source original V0 artifact manifest SHA-256 remains:
`c84170d5b438ad7481aa9a7985f377fbbd701ebfee80d720cd689d3bb7a49abd`.

Post-review artifact hashes:

- D1/D10 quantile summary:
  `5d1b2d791f11cb972fb1298dadcc2003d40284730e93e0181f11415aaf24ee65`;
- decile monotonicity:
  `e4586d0f1cf2e0c7700d44ba60213d2ecba43e170b6e004df6df52972ae25d9d`.

The diagnostic confirms that payoff ordering is not uniformly monotone. For
example, ATR decile-mean Spearman is `-0.515152` in V2F4 and percentage-payoff
Spearman is `0.927273` in V2F6. These are descriptive, non-gating diagnostics.

### Revision-conflict scope correction

The unrelated `storage.py` semantic change was reverted. `vendor_adj_close`
remains independently auditable from `raw_close`; when both fields revise, both
conflicts are surfaced. `tests/test_storage.py` now asserts this transparent
contract rather than suppressing the adjusted-close conflict.

## Validation

- focused remediation suite: **17 passed**;
- full repository pytest: **54 passed, 0 failed, 0 warnings** in **5.264
  seconds**;
- original V0 one-shot was not rerun;
- no fresh-forward marker was written.

## Next boundary

Expected Payoff V1 remains unauthorized. A new preregistered V1 specification
must be reviewed and frozen before any payoff model fit or fresh-forward
validation.
