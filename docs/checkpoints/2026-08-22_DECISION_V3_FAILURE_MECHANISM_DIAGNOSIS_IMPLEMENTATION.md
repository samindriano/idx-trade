# Decision V3 Failure-Mechanism Diagnosis V1 — Implementation

Date: 2026-08-22 Asia/Jakarta

Status: `IMPLEMENTED_NOT_EXECUTED_INDEPENDENT_AUDIT_REQUIRED`

Branch: `research/idx-decision-v3-failure-mechanism-diagnosis-v1`

Frozen contract: `docs/specs/decision_v3_failure_mechanism_diagnosis_v1.json`

Canonical contract SHA-256: `3a72bf9de9edd7181f15d9cd6bf50d590828407704ded426cb13586f3a89fd03`.

Parent result is frozen as `DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT`, plan digest `1759d1b21849197257c638f6ac23ae0d3cdd320e34da820b4cc188d533931579`, with every parent artifact SHA pinned in the contract and runtime loader.

## Implemented

- fail-closed loader for the immutable V3 structural replay artifacts;
- no access to the historical alpha parquet or any provider/network path;
- per-session severe-exit clustering and mandatory-exit/vacancy-fill overlap diagnostics;
- entrant lifecycle table for Tier A, Tier B, Tier C, and Tier-A soft replacement entrants;
- next-session severe-exit and eventual exit-reason attribution from emitted state/intent ledgers;
- six fixed 100-session block summaries plus Block 3/6 versus 1/2/4/5 descriptive comparison;
- fail-closed output staging + artifact hashing;
- guarded CLI with authorization checked before contract or structural-root access;
- self-contained `src/` path bootstrap in the CLI;
- synthetic tests for severe/refill overlap, Tier-C next-session severe attribution, block accounting, output no-overwrite, exact contract hash, and bad-token ordering.

## Scientific boundary

This tool does not rerun Decision V3, simulate any alternative threshold/rule/policy, run a counterfactual, access historical alpha scores, returns/PnL, protected/fresh-forward outcomes, refit/retune a model, call a provider/network, implement a successor Decision, or activate paper/live behavior.

All reported overlaps are descriptive incidence, not causal estimates. The existing `>=3 replacements` label is inherited from the already-frozen V3 churn gate and is not a new threshold.

## Required independent audit before execution

The audit must verify:

1. exact contract canonical hash and all parent artifact pins;
2. no policy replay or historical alpha source path is reachable;
3. severe-exit/refill reporting does not silently compute a counterfactual;
4. Tier A/B/C lifecycle attribution uses emitted entry reasons and next-session incumbent state exactly;
5. Block 3/6 comparison is descriptive and cannot create a regime rule;
6. output is fail-closed and deterministic for identical immutable inputs;
7. authorization is checked before structural source access;
8. tests/CI pass on the exact reviewed implementation head.

Only an accepted audit may authorize one local diagnosis execution using the frozen V3 structural artifact root. The diagnosis result itself does not automatically authorize Decision V4 or any policy change.
