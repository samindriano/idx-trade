# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-HISTORICAL-E2E-REPLAY-BLOCKER-REMEDIATION-V1
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: `5fab5a9a56ce21989ed27474566c5817db6cc1df`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: pending documentation commit
scope: outcome-blind Open, CA, dividend, Close/RMV and replay feasibility audit
files_changed:
  - `docs/checkpoints/2026-08-24_HISTORICAL_E2E_REPLAY_BLOCKER_REMEDIATION_V1.md`
  - `coordination/handoffs/IDX-HISTORICAL-E2E-REPLAY-BLOCKER-REMEDIATION-V1-RESULT.md`
  - `docs/checkpoints/2026-08-24_HISTORICAL_E2E_CLOSE_RMV_TRADABILITY_AUDIT_V1.md`
  - `coordination/handoffs/IDX-HISTORICAL-E2E-CLOSE-RMV-TRADABILITY-AUDIT-V1-RESULT.md`

## Result

`TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`

Open acquisition is fully certified at the session-manifest level but only
supports 905/1,297 BUY and 895/1,287 SELL intents with positive OpenPrice.
The current certified root is immutable and no FirstTrade/derivative price
was substituted.

Close/H/L/Volume and RMV are complete for current exposure inputs, but
tradability is not independently certified. Corporate-action attachment
evidence covers 35/94 event IDs with 16 exact candidates; the frozen CA ledger
remains untouched. Dividend transport covers 347 tickers, but metadata-only
replay passes 0/844 cash candidates and no-event status is not provable.

The scope remains `STRICT_SCOPE_EMPTY_BLOCKED`; the replay engine is not
authorized to run historical performance or NAV. The replay engine audit also
identified that a future scope-bound 6×100 runner must validate its scope and
transitive input pins before invoking one-session transitions.

## Decisions

- Do not materialize the proposed Open derivative overlay yet.
- Do not modify frozen CA or dividend artifacts.
- Do not run scoring, labels, returns, NAV, or Monte Carlo.
- The next action requires independent review/authorization of any targeted
  source acquisition or an explicit downgrade of the replay scope.

## Validation

Focused tests before this documentation pass: 15 passed. Full suite:
719 collected, all passed, 3 FutureWarnings. `git diff --check` passes after
documentation changes. No operational checkout, runtime, scheduler, counter,
model, outcome, or `coordination/TEAM_STATUS.md` was modified.
