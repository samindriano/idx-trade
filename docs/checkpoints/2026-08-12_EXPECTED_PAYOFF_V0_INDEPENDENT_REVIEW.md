# Expected Payoff V0 — Independent ChatGPT Review

Date: 2026-08-12 (Asia/Jakarta)
Branch reviewed: `research/idx-expected-payoff-v0-feasibility`
Reviewed HEAD: `a9586429a0c07ebbcdaab1a854f060743384bb25`
Frozen spec anchor: `024c91fcd9c105744b575d5584160b077c848e3e`

Decision: `EXPECTED_PAYOFF_V0_FEASIBILITY_GO_ACCEPTED_WITH_ENGINEERING_REMEDIATION_BEFORE_V1`

## Independent scientific verdict

The frozen feasibility verdict is accepted.

The reported fold values satisfy the preregistered gate without changing any threshold after the result:

- fold-median ATR ICs are positive in 6/6 folds;
- median of fold-median ATR ICs is approximately `0.04247`;
- q25 of fold-median ATR ICs is approximately `0.03332`;
- median of the six fold-mean D10-D1 ATR-payoff spreads is approximately `0.17868`;
- 4/6 folds have positive fold-mean D10-D1 ATR-payoff spread.

The runtime implementation uses the accepted O2 OOF score artifact directly, maps signal session `t` to next-session Open `t+1` and fixed Close `t+10` through the verified calendar, uses signal-time ATR normalization, applies accepted Open provenance, and excludes known price-scale corporate-action crossings fail-closed. The result is therefore valid historical-development evidence that O2 score contains information about payoff magnitude under this frozen gross-price contract.

This remains a feasibility result only. It is not fresh-forward validation, a payoff model, a net-PnL model, or a production trading rule.

## Engineering / specification compliance findings

The scientific gate can be accepted, but the branch should be remediated before authorizing Expected Payoff V1.

### 1. Frozen test checklist is under-covered

The spec required explicit fail-closed tests for missing/invalid exit Close, behavioral cutoff rejection, exact consumption of accepted O2 scores without recomputation, coverage/feasibility gate boundary cases, and no fresh-forward marker/runtime access. The committed suite contains only six tests and does not explicitly cover all of those required cases.

Remediation: add the missing contract tests only. Do not change V0 target, entry, exit, normalization, metrics, thresholds, or historical verdict, and do not rerun the one-shot diagnostic merely to add tests.

### 2. Some required non-gating summaries are not persisted exactly as specified

The frozen spec asked fold-level D1/D10 payoff mean, median, q25, and q75 plus an explicit decile-index versus realized-payoff monotonicity diagnostic. The implementation persists per-session decile summaries and fold-level D1/D10 means, but does not persist the complete fold-level D1/D10 quantile summary or a separately named monotonicity diagnostic.

This does not affect the frozen gate because these fields were explicitly non-gating, but the implementation should be brought into contract compliance before V1.

Remediation: derive and persist these non-gating summaries from the already-produced V0 artifacts or add code/tests for future reproducibility. Do not reinterpret them as new gate evidence and do not change the accepted V0 verdict.

### 3. `storage.py` change is out of scope and should not ride with the payoff result without a separate justification

The branch changes `revision_conflicts()` so that any `vendor_adj_close` conflict is suppressed whenever `raw_close` changed. Repository data semantics explicitly keep vendor adjusted close separate from raw execution Close. The current suppression can hide an independent adjusted-close revision in an audit conflict list.

This storage change did not create the Expected Payoff V0 result and is not needed to accept the scientific verdict.

Remediation: preferably revert the storage behavior change on this payoff branch, or handle it in a separate data-foundation fix with an explicit contract and test proving when de-duplication is safe. Do not weaken historical revision surfacing merely to make an unrelated test pass.

## Interpretation of the evidence

The signal is real enough to justify designing V1, but it is not uniformly strong:

- fold-median ATR IC ranges from about `0.0043` to `0.0571`;
- V2F4 and V2F5 have negative fold-mean D10-D1 ATR spread even though all six fold-median ICs are positive;
- percentage-payoff spread is also unstable in those folds.

Therefore V1 should not assume a simple high-score = stable linear expected-return relationship. A later V1 preregistration should prefer robust/distribution-aware targets and baselines and must preserve fold/session structure.

## Authorization boundary

`EXPECTED_PAYOFF_V0_FEASIBILITY_GO` is scientifically accepted.

Expected Payoff V1 is **not yet authorized to run** from this review. Before V1 implementation/model fitting:

1. remediate the engineering/spec-compliance items above without rerunning or retuning V0;
2. checkpoint the remediation;
3. then create a new preregistered Expected Payoff V1 specification covering target(s), model family, baselines, loss/metrics, folds, robustness gate, and fresh-forward boundary.

No change is authorized to O2, O2.1, V3-B, Probability, Path Risk, active forward counters, or outcome vaults.
