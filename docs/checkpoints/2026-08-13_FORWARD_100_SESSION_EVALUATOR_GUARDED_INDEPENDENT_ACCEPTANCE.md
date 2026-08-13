# Forward 100-Session Evaluator — Guarded Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Branch: `codex/idx-forward-100-evaluator-v1`
Reviewed HEAD: `12a5b99150cbb33c729343ceec3f4d4da2d66ecd`
Parent guarded remediation: `ca0b3c109cab46de2c15869a0018511e2fd366e3`
Prior changes-required review: `beec0bffcf72074b557994b9bac99b5dc8c32d20`
Frozen protocol: `6c05499d01ba644c80f0c6bd6d621aac92ab2813`
Decision: `FORWARD_100_SESSION_EVALUATOR_GUARDED_REMEDIATION_ACCEPTED`

## Independent review verdict

The four engineering blockers from the prior review are closed without changing frozen scientific semantics:

1. evaluated O2 and Reliability data are loaded from the exact hash-pinned artifacts rather than caller-supplied in-memory score/sidecar frames;
2. the guarded validator uses the accepted Reliability V1 model/formula/spec/protected-flag contract rather than the superseded synthetic surrogate schema;
3. incomplete Reliability sidecars are frozen as `RELIABILITY_FORWARD_INCONCLUSIVE_DATA` in the pre-outcome contract before marker creation and before any outcome loader can run;
4. the guarded entrypoint pins the frozen protocol SHA internally and does not expose a caller override.

The guarded path also cross-checks Reliability row support, O2 eligibility, and exact O2 scores against the pinned O2 source artifacts.

## Execution evidence

Execution review at `12a5b99150cbb33c729343ceec3f4d4da2d66ecd` reports:

- original + guarded focused tests: `17 passed, 0 failed`;
- full pytest: `295 passed, 0 failed, 3 existing warnings`;
- `git diff --check`: PASS;
- no source/scientific-semantic change after the guarded remediation;
- protected outcomes, providers, model artifacts, O2 counter, and the real outcome-access marker were not touched.

Comparison from guarded remediation `ca0b3c1` to reviewed HEAD `12a5b991` contains documentation/handoff additions only.

## Accepted boundary

The accepted canonical synthetic orchestration entrypoint is:

`idx_trade.forward_100_evaluator_guarded.run_guarded_synthetic_forward_evaluation`

The older unguarded synthetic orchestration entrypoint is superseded for future provenance/one-shot wiring.

This acceptance authorizes the guarded evaluator implementation as the pre-vault engineering implementation only. It does **not** authorize:

- protected outcome access;
- wiring or invoking the protected outcome loader;
- writing `FORWARD_OUTCOME_ACCESS_STARTED`;
- opening the vault before the canonical O2 counter reaches exactly `100/100` and all 100 sessions are H10-mature;
- changing the frozen O2/Reliability decision rules;
- evaluating O2.1 in the first one-shot verdict.

A separate final `READY_TO_OPEN_VAULT` independent review remains mandatory at the 100/100 maturity boundary.
