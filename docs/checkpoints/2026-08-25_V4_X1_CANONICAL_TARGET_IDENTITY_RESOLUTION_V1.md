# V4-X1 Canonical Target Identity Resolution V1

Date: 2026-08-25 (Asia/Jakarta)
Branch: `research/idx-v4-x1-prospective-evaluation-protocol-v1`
Status: `PROSPECTIVE_EVAL_GATE_V1_AUDITED_TARGET_IDENTITY_RESOLVED_REAL_ACCESS_BLOCKED`

## Scope and boundary

This checkpoint resolves the semantic identity of the frozen V4-X1
prospective target from retained pre-outcome lineage. It does not open
protected prospective outcomes, call the real protected loader, write the
real access marker, change the forward counter, or modify the model,
Decision, Sizing, or Execution contracts.

The machine-readable provenance graph is:

`docs/checkpoints/2026-08-25_V4_X1_CANONICAL_TARGET_PROVENANCE_GRAPH_V1.json`

## Resolved target

The canonical identity is:

`CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`

It is defined by the retained V4-1 contract, V4-3 target materializer, X1
preregistration, accepted clean OOS lineage, and the frozen prospective
protocol. The exact semantics are:

- prediction: `alpha_consensus`, ranked descending with ticker ascending as
  deterministic tie-break;
- `realized_h5 = Close_(t+5) / Open_(t+1) - 1`;
- `realized_h10 = Close_(t+10) / Open_(t+1) - 1`;
- each raw return is ranked within decision-session cross-section using
  average ties, ascending direction, and normalized `(rank - 1)/(n - 1)`;
- `realized_consensus = 0.5 * target_rank_h5 + 0.5 * target_rank_h10`;
- both H5 and H10 ranks are required; no missing-to-zero conversion;
- the final target is `realized_consensus` without a second target rank
  transform; the evaluator computes session-level Spearman.

The gate now binds this semantic identity to the target-spec SHA, construction
source commit/blob/SHA, model fingerprint, and the exact authoritative source
list. The gate does not resolve identity by matching a historical IC number.

## Historical metric reconciliation

The four numbers remain separate reference statistics:

| Value | Proven interpretation | Target-identity consequence |
|---:|---|---|
| `0.097554036` | Clean common-support Spearman over 600 admitted dates | Same target semantics; alternate common-support presentation |
| `0.09805414600339561` | Frozen evaluator headline `CHALLENGER_CONSENSUS_MEDIAN_FOLD_MEAN_DAILY_IC` | Same target semantics; different frozen evaluator statistic |
| `0.099248615` | Mean frozen-formula IC over 600 admitted clean dates | Same target semantics; alternate aggregation |
| `0.0980538834688018` | Value retained in the prospective contract | Exact support/derivation not proven; context-only, not target identity |

The exact provenance of `0.0980538834688018` is therefore **not resolved**.
The frozen protocol treats the historical approximately-0.098 statistic as
prior context rather than a forward pass/fail cutoff, so this does not keep
the semantic target unresolved. It remains truthfully represented as
`UNRESOLVED_CONTEXT_ONLY` in the contract.

## Adversarial coverage

The target identity tests fail closed for mutation of:

- denominator and H5/H10 horizons;
- consensus weights;
- rank direction and tie method;
- final target-rank behavior;
- prediction field;
- target source path/blob and target-spec SHA/path;
- authoritative provenance list;
- support semantics;
- model fingerprint and canonical target ID.

They also prove that changing only historical reference values does not create
a different target identity when the semantic target specification and
construction provenance remain identical.

## Validation

The following completed successfully after the code-pin refresh:

- target identity tests: `18 passed`;
- preflight tests: `7 passed`;
- gate tests: `56 passed`;
- prospective evaluator tests: `19 passed`;
- `py_compile` for canonical target, gate, and evaluator CLI: PASS;
- evaluator `--status-only`: `PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT`;
- `git diff --check`: PASS.

No real provider or protected outcome access occurred.

## Next state

Package A is ready to push for independent review. Real 100-session access
remains blocked by the existing explicit human-authorization and pre-access
artifact gates. Package B must remain a separate operational branch from the
current `origin/main` lineage.
