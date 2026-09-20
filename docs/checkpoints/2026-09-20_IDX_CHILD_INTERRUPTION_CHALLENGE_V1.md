# IDX-Trade Child Interruption Challenge V1

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Scope

This is an outcome-blind, provider-free subprocess challenge. It does not run
the scheduler, access canonical/provider data, or mutate external runtime,
capture, telemetry, cloud, alpha, or protected-outcome state.

## Challenge

`tests/test_e2e_paper_operational_controller_v1.py::test_real_child_timeout_preserves_boundary_and_requires_recovery`
starts a real Python child that is forcibly timed out while the controller has
already persisted the `PREOPEN / CHILD_EXECUTION` boundary. The next controller
pass is then run against the same synthetic runtime root with deployment and
lock surfaces locally stubbed.

Required result:

- child timeout is surfaced as `E2E_OPERATIONAL_CHILD_PROCESS_FAILED:interrupt`;
- no child completion is inferred;
- the persisted boundary is recovered as `RECOVERY_REQUIRED`;
- interrupted phase remains `PREOPEN`;
- interrupted side effect remains `CHILD_EXECUTION`;
- `provider_calls` and `outcome_access` remain false.

## Result

PASS. The focused test and the neighboring redacted-child-failure test both
passed. This proves the local subprocess/recovery contract only; an authorized
live provider/scheduler challenge remains outside this lane.
