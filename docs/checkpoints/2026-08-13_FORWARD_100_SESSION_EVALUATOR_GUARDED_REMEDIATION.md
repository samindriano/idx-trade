# Forward 100-Session Evaluator — Guarded Remediation

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `codex/idx-forward-100-evaluator-v1`  
Parent implementation: `1410febf41d653cd6baf135169d31a859e9312ef`  
Independent review: `beec0bffcf72074b557994b9bac99b5dc8c32d20`  
Decision: `FORWARD_100_SESSION_EVALUATOR_GUARDED_REMEDIATION_IMPLEMENTED_PENDING_EXECUTION_REVIEW`

## Scope

This remediation addresses only the four engineering blockers from the independent review. Frozen scientific semantics were not changed: O2 metrics and PASS/MIXED/FAIL boundaries, Reliability metric family and PASS/INCONCLUSIVE/FAIL/readiness boundaries, the fixed 100-session and 50/50 split, anti-rescue rules, and O2.1 exclusion remain delegated to the already-reviewed metric core in `forward_100_evaluator.py`.

The canonical synthetic orchestration entrypoint after this remediation is:

`idx_trade.forward_100_evaluator_guarded.run_guarded_synthetic_forward_evaluation`

The earlier `forward_100_evaluator.run_synthetic_forward_evaluation` entrypoint from `1410feb` is **superseded for provenance/one-shot orchestration** and must not be used as the basis for the eventual protected-runtime adapter.

## Remediation 1 — evaluated data are the hash-pinned artifacts

The guarded runner no longer accepts caller-supplied `o2_scores` or `reliability` DataFrames.

It validates the exact 100-session inventory and then loads the O2 score and Reliability sidecar parquet files directly from the inventory paths after verifying their SHA-256 values and manifests. O2 artifact model/feature identity is checked again at row-artifact level. Reliability artifacts are checked against the exact O2 support, row-level O2 eligibility, and exact O2 score values before any outcome loader can be called.

This removes the prior gap where a valid hash inventory could coexist with a different in-memory frame used for the verdict.

## Remediation 2 — accepted Reliability V1 schema is authoritative

The guarded inventory validator imports and requires the accepted Reliability V1 identity:

- model ID `RELIABILITY-V1-SCORE-MARGIN-SHADOW`;
- formula `score_margin_reliability_v1`;
- frozen spec commit `3239a319fbd4ff492b16a74d899a20edc9affa7f`;
- exact accepted `PROTECTED_FLAGS` dictionary from `reliability_v1_forward_shadow.py`;
- exact O2 score/session-manifest source pins;
- O2 model and feature-order pins;
- `outcome_access=LOCKED`.

The earlier synthetic six-key runtime-flag surrogate is no longer accepted by the guarded path.

## Remediation 3 — missing sidecars are declared before outcome access

Before writing the synthetic marker or calling the outcome loader, the guarded runner determines whether all 100 Reliability sidecars are present and valid.

The pre-outcome contract records one of exactly two dispositions:

- `READY_FOR_FROZEN_RELIABILITY_EVALUATION`, or
- `RELIABILITY_FORWARD_INCONCLUSIVE_DATA`.

If any sidecar is absent, `RELIABILITY_FORWARD_INCONCLUSIVE_DATA` is therefore frozen in `pre_outcome_contract.json` before the loader can execute. The post-loader evaluation is additionally required to preserve that decision; otherwise the guarded runner fails closed.

No missing sidecar is rebuilt from outcome data.

## Remediation 4 — protocol identity cannot be overridden by caller

The guarded runner has no `expected_protocol_sha256` parameter.

It accepts the protocol only when the supplied file bytes hash exactly to the module-level frozen `PROTOCOL_SHA256` tied to commit `6c05499d01ba644c80f0c6bd6d621aac92ab2813`. A changed protocol fails before marker creation or loader execution.

The guarded runner also requires a full 40-hex evaluator commit pin for the synthetic pre-outcome contract.

## Additional pre-outcome provenance hardening

The pre-outcome contract now embeds the 100 session dates/indices plus each session's exact O2 score SHA, O2 manifest SHA, and available Reliability artifact/manifest SHA, rather than relying only on an aggregate inventory-file hash. Shared model/model-manifest/feature-order/calendar/security/tradability/corporate-action/source-snapshot artifacts remain independently hash-verified.

## Added adversarial tests

`tests/test_forward_100_evaluator_guarded.py` adds coverage for:

1. no caller-injected O2 score / Reliability frames and no protocol-hash override parameter;
2. acceptance of the real Reliability V1 manifest schema and rejection of the superseded synthetic flag schema;
3. rejection when a hash-consistent Reliability artifact contains O2 row scores inconsistent with its hash-pinned O2 source;
4. pre-loader `RELIABILITY_FORWARD_INCONCLUSIVE_DATA` declaration when any sidecar is absent;
5. fixed frozen protocol SHA mismatch blocking before loader/marker;
6. complete guarded synthetic manifest → marker → loader execution path.

## Protected boundary

This remediation did not wire or discover the real protected outcome loader. It did not inspect protected forward outcomes, write the real `FORWARD_OUTCOME_ACCESS_STARTED` marker, alter the O2 counter, refit/rescore models, evaluate O2.1, call providers, or change any frozen scientific decision rule.

## Validation status

The code and tests are committed for execution review. The ChatGPT GitHub connector environment cannot execute the repository pytest suite, so focused/full pytest claims are intentionally **not** fabricated here. The next execution-capable review should run:

- `python -m pytest tests/test_forward_100_evaluator.py tests/test_forward_100_evaluator_guarded.py -q`
- `python -m pytest -q`

No protected data or provider access is needed for those tests.
