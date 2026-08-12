# Stage 3 runtime review correction

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage3-v1`
Runtime code commit: `4c484b087aff592234dbe9905213e9d83b2f2611`
Runtime documentation head before this correction: `3651d9ca989ed149988a9140a00cc170a82a57a5`

## Purpose

This checkpoint corrects one wording/arithmetic inconsistency in the original Stage-3 runtime checkpoint without changing any runtime artifact or model result.

## Correct H10 population accounting

The full-valid H10 label ledger contains 712,325 rows:

- `TP_FIRST`: 197,910
- `SL_FIRST`: 315,049
- `AMBIGUOUS_SAME_BAR`: 6,974
- `NO_BARRIER_HIT`: 107,189
- `UNRESOLVED_PATH`: 40,463
- `INVALID_BARRIER`: 44,740
- `UNRESOLVED_HORIZON_END`: 0

Therefore the resolved binary population across the **full-valid universe** is:

`197,910 + 315,049 = 512,959` rows.

The previously reported `208,375` rows are not the full-valid resolved count. They are the resolved H10 rows admitted to the **primary broad-liquid model universe**:

- primary-liquid `TP_FIRST`: 80,038
- primary-liquid `SL_FIRST`: 128,337
- total primary model rows: `208,375`

No model metric changes as a result of this correction. F1/F2/F3 and pooled OOF metrics were already computed on the intended primary-liquid model table.

## Review status

The pre-registered Stage-3 advancement rule remains met:

- `logistic_compact`: F2/F3
- `hist_gradient_boosting`: F1/F2/F3

This remains development OOF evidence only. It is not final holdout evidence and not an execution-profitability claim.

## Documentation hygiene finding

`docs/PROJECT_CONTEXT_MASTER.md` still contains stale bootstrap wording near the top that calls Stage 1 the current phase and predates `SIGNAL_RESEARCH_HLCV`, Stage 2, and Stage 3. New sessions must treat the newest checkpoint and ledger additions as newer evidence until the master bootstrap header is explicitly refreshed. This is a documentation issue, not a runtime-result issue.
