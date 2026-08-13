# Handoff

from: ChatGPT / independent review + remediation
to: execution-capable reviewer
task_id: IDX-FORWARD-100-SESSION-EVALUATOR-GUARDED-REMEDIATION
source_repository: `samindriano/idx-trade`
branch: `codex/idx-forward-100-evaluator-v1`
parent_implementation: `1410febf41d653cd6baf135169d31a859e9312ef`
independent_review: `beec0bffcf72074b557994b9bac99b5dc8c32d20`

## Remediation implemented

Canonical synthetic orchestration is now:

`idx_trade.forward_100_evaluator_guarded.run_guarded_synthetic_forward_evaluation`

It closes the four blocking review findings without changing the frozen metric/decision core:

1. O2 and Reliability evaluation inputs are loaded directly from the exact hash-pinned per-session artifacts; caller-supplied score/sidecar DataFrames are no longer accepted.
2. Reliability validation uses the accepted V1 model/formula/spec/source pins and exact `PROTECTED_FLAGS` contract.
3. Missing Reliability sidecars are frozen as `RELIABILITY_FORWARD_INCONCLUSIVE_DATA` in the pre-outcome contract before marker/loader execution.
4. Frozen protocol SHA is a fixed module constant and has no caller override.

The guarded path also cross-checks row-level Reliability O2 support/eligibility/scores against the exact pinned O2 artifacts and embeds all 100 session artifact hashes explicitly in the pre-outcome contract.

The earlier `forward_100_evaluator.run_synthetic_forward_evaluation` orchestration is superseded and must not be used for the future protected adapter. Its pure scientific metric functions remain the frozen core and are reused unchanged.

## Added tests

`tests/test_forward_100_evaluator_guarded.py` covers:

- no in-memory score/sidecar injection and no protocol hash override;
- accepted Reliability V1 schema vs rejected old synthetic flags;
- row-content source binding;
- pre-loader missing-sidecar disposition;
- protocol mismatch before loader/marker;
- complete manifest → marker → loader guarded run.

## Required execution review

Run, without providers or protected data:

`python -m pytest tests/test_forward_100_evaluator.py tests/test_forward_100_evaluator_guarded.py -q`

then:

`python -m pytest -q`

Also run `git diff --check` and inspect that no protected runtime adapter or outcome access was introduced.

The ChatGPT GitHub connector cannot execute pytest, so no passing-test claim is made in this handoff.
