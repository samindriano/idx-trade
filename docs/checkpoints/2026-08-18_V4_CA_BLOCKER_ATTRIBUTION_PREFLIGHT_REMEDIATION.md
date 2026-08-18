# V4 CA Blocker Attribution V1 — Preflight Remediation

Status: `PREFLIGHT_BUG_CORRECTED_REVALIDATION_REQUIRED`

## Context

The first local validation of `data/idx-v4-ca-blocker-attribution-v1` stopped fail-closed before `py_compile`, input SHA verification, or attribution execution.

Observed result:

- focused pytest: `3 passed, 1 failed`
- failing test: `test_consensus_uses_h5_h10_intersection`
- failure: `SCENARIO_PER_DATE_COUNT_CHANGED`
- provider calls: `0`
- Stage-B ledger not read
- output root not created
- no attribution result exposed

## Root cause

`per_date_metrics()` incorrectly compared every helper output to the production constant `EXPECTED_DATES=600`. The failing deterministic unit fixture intentionally contains one signal date, so the helper rejected a valid one-date fixture before its consensus assertions could run.

This was a test/helper cardinality bug only. Production cardinality remains independently enforced by `normalize_ledger()`, which requires exactly:

- `344,790` rows
- `610` tickers
- `600` signal dates
- horizons `{5,10}`
- no duplicate `(ticker, signal_date, horizon)` identity

## Remediation

The helper now validates its output against the date cardinality actually present in its supplied frame. This makes deterministic small fixtures valid without weakening the real-run 600-date hard gate.

Additional pre-result hardening was added:

1. scenario mask index must exactly equal frame index, preventing silent positional misalignment;
2. a known mechanical-crossing row may not already carry the resolved status;
3. the fresh one-shot output directory is created only after all input validation and all in-memory scenario computations have completed successfully, preventing a computation error from consuming the output-root retry budget.

Regression coverage now additionally checks:

- one-date H5/H10 consensus intersection;
- mask-index mismatch fail-closed behavior;
- a synthetic 600-date all-resolved fixture produces 600/600 H5, H10, and consensus gates with `all_600_pass=true`;
- combined-only attribution verdict;
- even-combined-fails attribution verdict.

ChatGPT independently replayed the regression logic in its own Python runtime and all synthetic checks passed. This is not a substitute for the required local repository pytest/py_compile run.

## Scientific boundary

No CA semantic rule, blocker reason definition, frozen gate, universe, threshold, provider source, Stage-A/Stage-B artifact, target, model, prediction, performance metric, protected outcome, or fresh-forward outcome was changed or accessed.

The accepted immutable Stage-B ledger remains pinned at SHA-256:

`585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`

The first attribution run has still **not** occurred.

## Retry authorization

Exactly one local retry is authorized only after the updated focused tests, `py_compile`, and `git diff --check` all pass. If any validation fails, STOP again without patching locally.
