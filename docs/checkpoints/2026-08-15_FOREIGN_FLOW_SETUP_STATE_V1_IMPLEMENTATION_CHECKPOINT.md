# Foreign Flow Setup State V1 — Implementation Checkpoint

Date: 2026-08-15 (Asia/Jakarta)
Status: `REVIEW`
Branch: `research/idx-foreign-flow-setup-state-v1`
Scientific base: `b98466348e8ad16ccb7c53a5bddc22aa9f2b7910`

## Scope completed

This milestone implements the first outcome-blind Foreign Flow setup/state layer after the accepted direct-H10 V2 Core `NO_SURVIVOR` result.

Implemented files:

- `docs/checkpoints/2026-08-15_FOREIGN_FLOW_SETUP_STATE_V1_CONTRACT.md`
- `src/idx_trade/foreign_flow_setup_state.py`
- `src/idx_trade/foreign_flow_setup_sidecar.py`
- `tests/test_foreign_flow_setup_state.py`
- `tests/test_foreign_flow_setup_sidecar.py`

No historical alpha experiment, provider call, protected/fresh-forward outcome access, O2 counter change, model fitting, free-float/effective-supply inference, or price-confirmation model was performed.

## Key semantic decision

Current participation and own-history abnormality remain separate axes.

The implementation explicitly supports the economically important case where:

- ticker A has `50%` current foreign participation but routine historical pressure;
- ticker B has only `5%` current participation but an extreme own-history shock and persistent accumulation.

Ticker B can therefore be classified as a stronger accumulation setup even though its current-volume participation ratio is much smaller.

The sidecar preserves raw evidence alongside categorical state:

- current participation;
- shock 1d / mean 5d / mean 20d;
- own-history percentile;
- 5d / 20d cross-sectional shock ranks;
- 5d / 20d persistence;
- acceleration;
- 5d / 20d flow-price divergence.

It does not emit an alpha probability, expected return, trade recommendation, or fitted score.

## State outputs

Deterministic state axes:

- participation intensity and direction;
- historical abnormality;
- persistence;
- cross-sectional pressure;
- flow-price divergence;
- acceleration direction;
- descriptive setup label.

Composite labels currently include:

- `HIGH_PARTICIPATION_ROUTINE_FLOW`
- `ABNORMAL_ACCUMULATION`
- `PERSISTENT_ACCUMULATION`
- `STEALTH_ACCUMULATION_CANDIDATE`
- `DISTRIBUTION_PRESSURE`
- `NEUTRAL_OR_MIXED`
- `INDETERMINATE`

`STEALTH_ACCUMULATION_CANDIDATE` is descriptive WATCH/setup context only and does not imply BUY.

## Guardrails

- Outcome/label keys such as `binary_target`, `TP_FIRST`, `SL_FIRST`, `outcome`, and `realized` are rejected even if they would not otherwise be consumed.
- Missing/non-finite required state inputs fail closed to `INDETERMINATE` with explicit missing fields.
- Invalid cross-sectional rank domains fail closed.
- Duplicate `(ticker, feature_session)` sidecar keys fail closed.
- No forward fill.
- No inferred free-float denominator.
- No new forward counter.

## Validation

Focused semantic tests corresponding to the two new test modules were executed in an isolated local harness using the exact branch implementation semantics:

`12 passed`

The focused checks cover:

- 50% participation / routine-flow versus 5% participation / extreme-abnormality separation;
- low-participation stealth accumulation;
- distribution symmetry;
- missingness fail-closed behavior;
- invalid rank fail-closed behavior;
- forbidden outcome-column rejection;
- threshold-contract validation;
- sidecar evidence preservation;
- duplicate-key rejection;
- required-evidence enforcement.

Full repository pytest has **not** yet been executed on the actual branch checkout. GitHub Actions did not provide a run for this branch during this milestone.

## Diff boundary

Compared with scientific base `b98466348e8ad16ccb7c53a5bddc22aa9f2b7910`, the lane contains only the contract, classifier, sidecar builder, and their tests. No model/provider/outcome implementation path is changed.

## Next authorized action

Before deployment/prospective runtime wiring:

1. run exact focused tests plus full repo pytest and `git diff --check` from a real checkout of this branch;
2. inspect and reuse the existing accepted Foreign Flow prospective capture/sidecar infrastructure rather than creating another capture system or counter;
3. wire the setup-state sidecar only after that review;
4. keep the future price-state / confirmation layer separate and prospective-only.

No historical performance evaluation of this post-V2 state architecture is authorized.

Final milestone status:

`FOREIGN_FLOW_SETUP_STATE_V1_IMPLEMENTED_REVIEW_REQUIRED`
