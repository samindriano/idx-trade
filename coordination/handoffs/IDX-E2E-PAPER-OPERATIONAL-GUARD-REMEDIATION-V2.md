# Handoff

from: Codex root coordinator  
to: ChatGPT independent review / MAIN integration  
task_id: IDX-E2E-PAPER-OPERATIONAL-GUARD-REMEDIATION-V2  
model_used: Codex root + Orchestra read-only audits + Sagan independent review  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `3dd7055b7669c9c7999420a81a670d906690597c`  
branch: `integration/idx-e2e-baseline-paper-v1`  
head_commit: `3dd7055b7669c9c7999420a81a670d906690597c`

## Scope

Engineering-only follow-up to the first operational guard milestone. No
provider call, outcome access, model fit/rescore/refit, T0 bootstrap, broker,
or scheduler mutation was performed.

## Review input

Sagan's independent review returned `REWORK`: no P0, with P1 findings that
the controller was still only an arm/preflight boundary, phase scripts could
be invoked independently, calendar and pointer evidence needed stronger
validation, and controller branches needed direct tests.

## Files changed

- `src/idx_trade/e2e_operational_guard_v1.py`
- `src/idx_trade/e2e_paper_operational_controller_v1.py`
- `scripts/run_e2e_paper_preopen_v1.py`
- `scripts/run_e2e_paper_post_eod_v1.py`
- `tests/test_e2e_operational_guard_v1.py`
- `tests/test_e2e_paper_operational_controller_v1.py`
- `docs/checkpoints/2026-08-23_E2E_OPERATIONAL_GUARD_REMEDIATION_V2.md`

## Findings / decisions

Calendar duplication/weekend acceptance, upstream score-manifest drift, and
prepared-parent drift are now fail-closed. The controller's Sunday path was
rerun against the exact pushed HEAD and persisted a no-op without provider or
outcome access. The existing Stockbit intraday task, ForwardEOD task, legacy
ForwardOpenArchive task, official Open task, and `TEAM_STATUS.md` were not
modified.

The implementation intentionally remains `REWORK`/review-pending rather than
claiming weekday live operation. The next implementation must bind the
existing V1.2 CA journal/attestation, invoke the existing guarded phase
consumers through one controller path, prove no direct script bypass, and add
fresh fault-injection/cold-restart/retry/idempotency acceptance.

## Validation

- Focused tests: PASS.
- Full pytest: PASS; 3 existing pandas `FutureWarning`s.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Sunday smoke: `WEEKEND_OR_HOLIDAY_NOOP`, no provider/model/outcome access.

## Recommended next action

ChatGPT review of this pushed remediation milestone. After approval, continue
only with the bounded V1.2 CA/controller integration and fresh acceptance; do
not install a new scheduler or claim a weekday proof before those gates pass.

