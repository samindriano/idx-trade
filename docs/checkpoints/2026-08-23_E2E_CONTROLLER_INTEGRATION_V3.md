# Controlled E2E Paper Controller Integration V3

Date: 2026-08-23 Asia/Jakarta  
Branch: `integration/idx-e2e-baseline-paper-v1`

## Scope

This milestone binds the existing dividend/CA batch runtime and the existing
guarded POST_EOD/PREOPEN consumers behind the single operational controller.
It does not create a provider, scoring, model, outcome, broker, or scheduler
hierarchy. `coordination/TEAM_STATUS.md` was not changed because MAIN owns it.

## Changes

- The controller now validates the exact EOD session manifest, score manifest,
  score artifact, previous score parent, provider checkout commit, and the
  configured legacy CA attestation before operational work.
- Existing `run_forward_dividend_acquisition_batch_v1.py` is invoked only by
  the controller for deterministic POST_EOD/PREOPEN CA phases. Batch outputs
  are immutable and recorded in compact, hash-bound phase sidecars.
- Existing guarded POST_EOD and PREOPEN consumers are invoked through the
  controller with exact artifact arguments. They require a short-lived,
  controller-issued phase attestation, preventing an unbound phase script from
  being treated as an operational run.
- Child stdout/stderr are never persisted; only command arguments, exit code,
  and stdout/stderr hashes are recorded in the operational process log.
- Missing CA configuration remains a normal fail-closed status. No provider
  call, T0 bootstrap, model score, or execution is attempted when prerequisites
  are absent.

## Validation

- Focused operational/controller/orchestration/dividend suite: PASS.
- Full repository pytest: PASS, 3 existing pandas `FutureWarning`s.
- `py_compile`: PASS for changed Python modules/scripts/tests.
- `git diff --check`: PASS.
- No provider, protected outcome, broker, or scheduler operation was run by
  this milestone. A weekday live-cycle proof remains pending.

## Remaining gates

The runtime still requires an explicitly configured and hash-pinned legacy CA
attestation before it can perform a real POST_EOD/PREOPEN cycle. The user-level
E2E scheduler remains uninstalled until independent review accepts this
controller integration and a weekday fault-injection/cold-restart acceptance
passes.
