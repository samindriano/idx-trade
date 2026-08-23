# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: IDX-HISTORICAL-E2E-REPLAY-V1
model_used: GPT-5 Codex
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: `18cd5c72376742d287de1e5a7c30073c700c58c7`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: branch HEAD produced by the commit containing this handoff

## Scope

Outcome-blind historical E2E replay preparation and strict-scope freeze for the
frozen 600-session Decision V2 structural trajectory. No performance replay was
run because the frozen strict scope was empty.

## Files changed

- `src/idx_trade/official_open_evidence_v1.py`;
- `tests/test_official_open_evidence_v1.py`;
- `tests/test_official_open_capture_runtime_v1.py`;
- `tests/test_v4_x1_execution_v1_official_open_verify.py`;
- `src/idx_trade/historical_e2e_replay_v1.py`;
- `scripts/acquire_historical_official_open_v1.py`;
- `scripts/freeze_historical_e2e_scope_v1.py`;
- `tests/test_historical_e2e_replay_v1.py`;
- this checkpoint and handoff.

## External evidence

Official-Open acquisition root:
`D:\Documents\Project\idx-historical-open-acquisition-20260824-v1`

Acquisition manifest SHA:
`dc74485c6d4ade01e125b08871105c8daea9c64f9daa2af6cc00d26592a8fcbf`

Scope freeze root:
`D:\Documents\Project\idx-historical-e2e-scope-freeze-20260824-v1`

Scope file SHA:
`8946a9b7ad4b35de32eca186f19e3297c9cf05d4771e553db8d6d8297e0a4827`

Scope payload SHA:
`40d538417b8c48dd95455ab425d4af20939f28a44f4c1cceeea876e26c5dcba3`

## Result

Final verdict:
`TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`

The 600-session official-Open archive is complete at the session-manifest
level and all 600 sessions are certified through the existing verifier. Direct
IDX was attempted first and returned HTTP 403; Zapi raw IDX passthrough was the
selected transport for all sessions. Aggregate counts are 568,555 rows,
226,323 positive OpenPrice rows, 342,232 unavailable rows, 905/1,297 BUY Opens,
392 missing BUY Opens, and 376/600 buy-ready sessions.

The strict scope is `STRICT_SCOPE_EMPTY_BLOCKED` with zero strict sessions. Its
blockers are `BUY_OPEN_SUPPORT_INCOMPLETE`,
`CA_EVENT_WINDOW_CONTINUITY_BLOCKED`, and
`DIVIDEND_MARKET_WIDE_NO_EVENT_PROOF_MISSING`.

## Synthetic controls

Synthetic production-path acceptance summary:
`D:\Documents\Project\idx-historical-e2e-synthetic-production-replay-20260824-v1\acceptance_summary.json`

SHA:
`2a14bb131054bee4454af1b822ca524d84c4c2a724980c8137d0c90d2a7a476a`

Cold-restart acceptance summary:
`D:\Documents\Project\idx-historical-e2e-cold-restart-20260824-v1\acceptance_summary.json`

SHA:
`892cb72359927478a3bbeae61155d62a554edf7e0f2603d05b7f63fa5fa1ffac`

The cold restart preserved the execution, runtime snapshot, and runtime state
hashes on the `ALREADY_COMPLETE` duplicate rerun. Synthetic controls are not
historical performance evidence.

## Decisions and boundaries

- No labels, protected outcomes, R5/R10, returns, P&L, NAV, performance metrics,
  model fit, or model scoring were accessed.
- No provider/network access occurred during scope freezing or replay
  verification beyond the separately authorized 600-session official-Open
  acquisition.
- No operational scheduler, runtime root, forward counter, or model artifact
  was changed.
- `coordination/TEAM_STATUS.md` was intentionally not edited; MAIN owns it.
- External raw and normalized artifacts remain outside Git.

## Validation

- `py_compile`: PASS;
- focused tests: `81 passed`;
- full pytest: `716 passed` with 3 existing pandas `FutureWarning`s;
- `git diff --check`: PASS.

## Blocking risks

The strict scope must remain empty until official Open support for every
required BUY intent, PIT CA event-window continuity, and market-wide dividend
no-event/entitlement evidence are separately resolved and accepted. Do not
infer missing Open, no corporate action, or no dividend event.

## Recommended next action

MAIN/ChatGPT review the checkpoint and, if desired, authorize a separate
outcome-blind remediation lane for the strict-scope blockers. Do not run the
historical performance replay or Monte Carlo on the current data.
