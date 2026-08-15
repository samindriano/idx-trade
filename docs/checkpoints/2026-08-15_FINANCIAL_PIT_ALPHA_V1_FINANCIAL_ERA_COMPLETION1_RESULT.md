# Financial PIT Alpha V1 — financial-era completion run

Status: `FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR`

This is the one explicitly authorized exact-contract completion run after the
previous wrapper timeout. No scientific code, feature, fold, support, cutoff,
preprocessing, hyperparameter, evaluator, or gate was changed.

## Identity and preflight

- Branch: `research/idx-financial-pit-alpha-v1`
- Documentation HEAD after this checkpoint: recorded in the handoff
- Executable scientific code identity: `507aaf8bca3286996eb30f3f8e7ea161d8892cc1`
- Documentation parent before this result: `a677cda58c2e963015aecf9bc9b4bb7809bede51`
- Frozen contract SHA-256:
  `cabeb0db3db44996bda91472576855cb549965d19791f640717502cdd321993c`
- Common support: 70,520 rows / 321 tickers
- Common support SHA-256:
  `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`
- Selected 52-slot Financial matrix SHA-256:
  `464c2a18bd7b238f98c786365026466bfd52c514022b3ced09798b2654665471`
- Historical H10 label source SHA-256:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`
- Exact eligible folds: `V2F4`, `V2F5`, `V2F6`

Both previous partial output roots were preserved read-only. The completion
run used a new root:

`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-completion1`

## Run result

- Nine fits completed: three candidates × three folds
- Runtime: `16.12591` seconds
- Prediction rows: `142,017`
- Artifact count in manifest: `16`
- Summary SHA-256:
  `3594934c846bacfd67eb7a775512be9a1a75b33af2c290f06d678a8100fc4b3f`
- Artifact manifest SHA-256:
  `07241cc863315a354e241f4f60e9bb7554a5ad8c927fc0bf3472a1024f5ef70a`
- Predictions SHA-256:
  `20a77ba50c3319f9cf8fdb676fe15b557b7903e7fe91bc0452469a104bc70e20`
- Fold metrics SHA-256:
  `094819ada64ec56de40f8a1d29426a65affba93b85ffe9a6a5c6891a4462cbc2`
- Aggregate metrics SHA-256:
  `7c8d46ad667da193648ee918367869a340363fd11ae2173a586670a4d854c395`
- Primary paired artifact SHA-256:
  `0fe94ec0c9448368bd87fdc53e7fd37a61cd3592a214cfd1489640694f29d19e`

Historical labels were accessed as authorized. `provider_calls=0`,
`o2_accessed=false`, `protected_forward_outcomes_accessed=false`, and
`fresh_forward_accessed=false`.

## Primary comparison

Primary comparison is frozen as `V2_PLUS_FINANCIAL` versus
`CONTROL_FINANCIAL_ERA`. `FINANCIAL_ONLY` remains diagnostic-only.

| Fold | Control PR-AUC | V2+Financial PR-AUC | PR delta | Control ROC | V2+Financial ROC | ROC delta | Control Q5-Q1 | V2+Financial Q5-Q1 | Q5-Q1 delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F4 | 0.377167 | 0.378445 | +0.001278 | 0.476185 | 0.473839 | -0.002346 | 0.046510 | 0.004055 | -0.042456 |
| V2F5 | 0.515827 | 0.518837 | +0.003010 | 0.542281 | 0.537586 | -0.004695 | 0.050051 | 0.038682 | -0.011369 |
| V2F6 | 0.363148 | 0.332443 | -0.030705 | 0.508725 | 0.490331 | -0.018395 | 0.022574 | 0.039394 | +0.016820 |

Aggregate primary gate values:

- median paired PR-AUC delta: `+0.0012781203`
- q25 paired PR-AUC delta: `-0.0147136528`
- positive paired folds: `2/3`
- candidate median ROC-AUC: `0.4903306189`
- control median ROC-AUC: `0.5087252608`
- candidate median Q5-Q1: `0.0386820315`
- control median Q5-Q1: `0.0465104028`
- guardrail reversal: `true`
- survivor gate: `FAIL`

The median PR and minimum positive-fold requirements pass, but q25 PR is
negative and both candidate median ROC-AUC and median Q5-Q1 are below control,
which triggers the frozen guardrail. Therefore the deterministic verdict is
`FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR`.

The diagnostic `FINANCIAL_ONLY` candidate does not rescue the primary failure.
No alternate candidate, fold, support population, or gate was tried.

## Feature identities

- CONTROL 25-feature order SHA-256:
  `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72`
- FINANCIAL_ONLY 52-feature order SHA-256:
  `c64b5fddf12e86b4d21d39d13eace81d44fac1bda4a4f9497c577e1deb489188`
- V2_PLUS_FINANCIAL 77-feature order SHA-256:
  `7704275d3ec85ecc09f6e20b5abac27d9ea6e70cc274bd24949f133d7faee0ec`

## Boundaries and validation

The two earlier partial output roots remain untouched. No canonical refit or
promotion was performed. O2, fresh-forward, protected-forward outcomes,
provider calls, and unrelated research lanes were not accessed.

The latest branch validation before the completion run remains:

- focused Financial Alpha tests: `10 passed`;
- full pytest: `61 passed, 1 failed`, unrelated existing
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflict`;
- `git diff --check`: passed.

