# Handoff

from: Codex root coordinator  
to: ChatGPT independent review / MAIN integration  
task_id: IDX-E2E-PAPER-CONTROLLER-INTEGRATION-V3  
model_used: Codex root + prior Orchestra audits + Sagan review remediation  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: pending final commit  
branch: `integration/idx-e2e-baseline-paper-v1`  
head_commit: pending final commit

## Scope

Engineering-only controller integration. No provider call, protected outcome
access, model refit/rescore, broker operation, scheduler mutation, or change to
existing EOD/Open/Stockbit tasks.

## Implemented

- Single controller path now owns CA phase acquisition and invokes the existing
  guarded POST_EOD/PREOPEN consumers.
- Phase scripts require a hash-verified, short-lived controller phase
  attestation bound to branch, commit, phase, and session.
- Calendar, score manifest/artifact, EOD files, prior score, CA attestation,
  provider checkout commit, and all phase outputs are fail-closed and
  provenance checked.
- CA phase sidecars and redacted process logs are immutable; child output is
  represented only by hashes.

## Decisions and boundaries

- Missing required operational configuration yields
  `WAITING_OPERATIONAL_CONFIGURATION`; it does not silently acquire data or
  create T0 state.
- No retroactive PREOPEN CA capture is permitted after 09:02 Asia/Jakarta.
- No paper execution is permitted after the PREOPEN window closes.
- Existing runtime roots and provider/batch consumers remain the source of
  truth; no second provider or scheduler hierarchy was introduced.
- `coordination/TEAM_STATUS.md` was intentionally not edited on this branch.

## Validation

- Focused suite: PASS.
- Full repository pytest: PASS; 3 pre-existing pandas `FutureWarning`s.
- `py_compile`: PASS.
- `git diff --check`: PASS.

## Remaining decisions / blockers

- Independent review must verify the child attestation boundary, exact phase
  invocation, fault handling, and cold-restart/idempotency behavior.
- A hash-pinned legacy CA attestation is not currently configured in the local
  E2E runtime, so a real weekday cycle has not been claimed.
- Do not install/enable the E2E scheduler or claim armed weekday operation until
  the independent review and weekday acceptance gates pass.

## Recommended next action

Review this pushed remediation, then run only the synthetic/fault-injection and
cold-restart acceptance. If accepted, configure the already-authorized CA
attestation and schedule one controlled weekday cycle; leave all existing
IDX-Trade automation unchanged.
