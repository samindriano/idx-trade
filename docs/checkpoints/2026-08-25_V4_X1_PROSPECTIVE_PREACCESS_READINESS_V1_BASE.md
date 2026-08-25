# V4-X1 Prospective Pre-Access Readiness V1 — Base Checkpoint

Date: 2026-08-25 (Asia/Jakarta)

Status: `V4_X1_PROSPECTIVE_PREACCESS_READINESS_V1_BASE_READY`

## Purpose

Provide a pure, deterministic, outcome-blind control plane that can track progress toward the already-frozen V4-X1 protected evaluation gate without duplicating the evaluator, reading protected target values, or changing the canonical forward experiment.

This base is intentionally not a production artifact-discovery adapter and not an outcome unlocker.

## Frozen identity

- model: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`
- generation: `V4-X1-CLEAN`
- fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
- ranking: `alpha_consensus DESC, ticker ASC`
- required forward sessions: `100`
- canonical target: `CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`

The existing `prospective_evaluation_v1.py`, `prospective_evaluation_gate_v1.py`, and `tools/evaluate_prospective_v4_x1.py` remain authoritative for final evaluation and protected access. This lane does not alter them.

## Base implementation

Added:

- `src/idx_trade/prospective_preaccess_readiness_v1.py`
- `tests/test_prospective_preaccess_readiness_v1.py`

The core currently provides:

1. partial first-100 inventory validation for a contiguous `1..N` prefix using the same final inventory column identity;
2. duplicate/date/index/order/path/SHA declaration checks without reading score or target values;
3. protected semantic path refusal for `outcome`, `label`, `realized`, and `vault` references;
4. recursive protected-access guard validation;
5. H5/H10 **calendar eligibility only**, with an explicit as-of cutoff so a future planned schedule cannot manufacture maturity;
6. frozen model/generation/fingerprint/ranking/canonical-target identity checks;
7. pre-access component readiness aggregation for counter, target attestation, PaperState, benchmark, prior-access audit, and code pins;
8. explicit contamination/provenance precedence;
9. deterministic human-readable operational rendering;
10. `existing_gate_preflight_eligible=true` only when the pure readiness requirements are all satisfied.

Target values remain explicitly `PROTECTED_NOT_READ` in every calendar/readiness path.

## Status vocabulary

Overall:

- `ACCUMULATING_OUTCOME_BLIND`
- `PREACCESS_REQUIREMENTS_INCOMPLETE`
- `PREACCESS_READY_FOR_EXISTING_GATE`
- `PREACCESS_PROVENANCE_INVALID`
- `PREACCESS_ACCESS_CONTAMINATED`

Component statuses:

- `READY`
- `ACCUMULATING`
- `PENDING_EXPECTED`
- `NOT_AVAILABLE`
- `PROVENANCE_INVALID`
- `ACCESS_CONTAMINATION`
- `PROTECTED_NOT_READ`

## Deliberate limitations of this base

Not implemented yet:

- production discovery of forward score manifests/artifacts;
- final-file SHA revalidation against the actual runtime filesystem;
- production adapter from Session Audit / PaperState metadata;
- canonical forward-counter attestation adapter;
- benchmark attestation adapter;
- prior-access audit adapter using the existing gate's persisted status implementation;
- code-pin adapter using existing gate validators;
- sealed prospective target-materialization / target-attestation producer;
- exact final preflight-bundle assembly.

These are intentionally left for the next production-adapter pass after repository/runtime artifact-shape discovery.

## Explicit safety boundary

This base:

- does not call providers or network sources;
- does not read a target/outcome/label/vault artifact;
- does not compute IC, return, Sharpe, PnL, drawdown, hit rate, or any prospective performance statistic;
- does not call a protected loader;
- does not write an outcome-access marker;
- does not mutate the canonical forward counter;
- does not change model, Decision, Sizing, Execution, PaperState, runtime, or scheduler;
- does not deploy or wire itself into the active E2E lane.

## Validation

Local isolated validation of the exact base source/test content before publication:

- `py_compile`: PASS
- focused synthetic pytest: `17 passed`
- whitespace/diff check: PASS
- operator rendering smoke: `ACCUMULATING_OUTCOME_BLIND`

No provider, runtime, scheduler, protected loader, target value, or prospective outcome was touched during validation.

## Next action

Perform a production-shape discovery/adaptation pass on this same lane. Reuse existing validators where possible instead of reimplementing final-gate science. In particular, determine whether a real sealed prospective target materializer/target-attestation producer already exists. If it does not, report that dependency explicitly rather than creating one inside the readiness adapter.
