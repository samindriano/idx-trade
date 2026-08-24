# V4-X1 Prospective Evaluator V1 — Implementation Checkpoint

Date: 2026-08-24 (Asia/Jakarta)

Status: `V4_X1_PROSPECTIVE_EVALUATOR_V1_SYNTHETIC_VALIDATED_PROTECTED_RUNNER_NOT_AUTHORIZED`

## Controlling parent

- Protocol: `V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND`
- Protocol commit: `ed719dd67ae93b6b20f02579df80fd67eec331dd`
- Model: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`
- Generation: `V4-X1-CLEAN`
- Fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`

## Implementation

Added:

- `src/idx_trade/prospective_evaluation_v1.py`
- `tests/test_prospective_evaluation_v1.py`

The evaluator is deliberately a pure development-safe metric layer. It performs no network or file access, writes no outcome-access marker, and accepts only `SYNTHETIC` or `AUTHORIZED_NON_PROSPECTIVE` data classifications. `PROTECTED_PROSPECTIVE` input fails closed. A future protected-outcome runner must be separately committed and must satisfy the preregistered final-access/provenance gates before feeding sealed artifacts into this unchanged metric layer.

Implemented frozen behavior includes:

- exact V4-X1 model/generation/fingerprint guard;
- canonical-target resolved/nonblank guard;
- exact session-date/session-index alignment;
- cross-sectional Spearman using average ranks for ties without adding SciPy;
- deterministic ranking `alpha_consensus DESC`, ticker ASC;
- session-level mean/median/std IC, positive-IC rate and ICIR;
- fixed rank buckets `1-10`, `11-20`, `21-50`, `>50`, aggregated by session;
- fixed top-10/top-20 session summaries;
- frozen moving-block bootstrap: session unit, block 5, 10,000 replicates, seed 20260824, percentile 95% CI;
- NAV daily returns, net total return, annualized volatility, zero-RF Sharpe, zero-MAR Sortino, max drawdown, CAGR-equivalent and Calmar;
- turnover `(gross buys + gross sells) / prior NAV`;
- pending-Open denominator semantics preserving legitimate unavailable Open legs;
- exact strategy start/end benchmark alignment;
- exact exclusion-ledger coverage and preregistered state vocabulary;
- frozen Alpha/Economic/Execution/Overall verdict boundaries;
- separation of alpha verdict from portfolio/execution operational validity.

## Validation

The exact Git blobs committed to the branch were verified against the locally tested files:

- evaluator Git blob: `ce7a6d356b0b1ab52277c50411fdfb86ac59ad4c`
- tests Git blob: `24c78fb55032a1e04c8d9296124868741909a816`

Local validation against those exact bytes:

```text
python -m py_compile src/idx_trade/prospective_evaluation_v1.py tests/test_prospective_evaluation_v1.py
PASS

PYTHONPATH=src pytest -q tests/test_prospective_evaluation_v1.py
..................                                                       [100%]
18 passed in 3.73s
```

The repository workflow is configured to run on `main` pushes and pull requests, not ordinary research-branch pushes; therefore no branch-push GitHub Actions run was expected at this checkpoint.

## Scientific boundary

At this checkpoint:

- `PROSPECTIVE_OUTCOMES_ACCESSED = FALSE`
- `PROTECTED_PROSPECTIVE_INPUT_USED_FOR_TESTING = FALSE`
- `MODEL_RETUNED = FALSE`
- `DECISION_CHANGED = FALSE`
- `SIZING_CHANGED = FALSE`
- `EXECUTION_CHANGED = FALSE`
- `OUTCOME_ACCESS_MARKER_WRITTEN = FALSE`

The implementation does **not** authorize opening the prospective vault. The final protected runner/access gate remains a later, separately reviewed step and must not be added after inspecting protected performance.
