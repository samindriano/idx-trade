# Historical E2E Replay Engine Scope Guardrails V1

Date: 2026-08-24
Branch: `research/idx-historical-e2e-replay-v1`
Parent milestone: `b71fa802b5e051fce8d7a195dea4ec2c4911d083`
Scope: outcome-blind replay-engine hardening only

## Verdict

`TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`

The research replay path now has a fail-closed, hash-verified scope contract,
a six-block sequential runner, stronger execution-state idempotency checks,
and a missing-RMV guard. The canonical historical replay remains **not run**:
the pinned data scope is still empty and therefore cannot authorize scoring,
NAV, economic metrics, or Monte Carlo.

## Scope validation

The current outcome-blind recomputation was written to:

`D:\Documents\Project\idx-historical-e2e-scope-recompute-20260824-v3\REPLAY_SCOPE.json`

Scope file SHA-256:
`8946a9b7ad4b35de32eca186f19e3297c9cf05d4771e553db8d6d8297e0a4827`

Observed payload:

- status: `STRICT_SCOPE_EMPTY_BLOCKED`
- candidate sessions: `600`
- strict sessions: `0`
- payload SHA-256:
  `40d538417b8c48dd95455ab425d4af20939f28a44f4c1cceeea876e26c5dcba3`
- blockers: `BUY_OPEN_SUPPORT_INCOMPLETE`,
  `CA_EVENT_WINDOW_CONTINUITY_BLOCKED`,
  `DIVIDEND_MARKET_WIDE_NO_EVENT_PROOF_MISSING`

The recomputed payload matches the pinned scope result and was produced without
provider calls, outcome access, model fitting, or protected-label reads.

## Engine changes

### Fail-closed scope contract

`src/idx_trade/historical_e2e_scope_validator_v1.py` validates the exact
outcome-blind scope schema, required false safety flags, SHA-256 source pins,
600 ordered unique decision/execution pairs, payload hash, and (when frozen)
six contiguous blocks of 100 sessions. `STRICT_SCOPE_EMPTY_BLOCKED` is valid
for audit reporting but is rejected before any replay artifact is opened or
runtime callback is invoked.

### Sequential runner

`src/idx_trade/historical_e2e_replay_runner_v1.py` validates all 600 artifact
identities and order before the first runtime mutation, performs one T0
bootstrap, invokes transitions strictly in scope order, and emits deterministic
hash-only transition/run summaries. It exposes no outcome, P&L, NAV, or model
fit fields and does not itself call a provider.

### Production-boundary hardening

`historical_e2e_replay_v1.py` now requires the frozen scope manifest and checks
the exact decision-session/next-official-session pair after production EOD
verification. `e2e_paper_orchestration_v1.py` rejects staged or existing
execution artifacts with a non-complete status or mismatched session date.
`v4_x1_execution_v1_verify.py` now fails closed for missing, non-finite, or
negative regular-market value; genuine finite zero remains distinct and valid.

## Validation

- focused scope/replay/runner/orchestration/RMV suite: **57 passed**
- runner-specific suite: **6 passed**
- full repository suite: **745 passed, 3 FutureWarnings, 52.08s**
- changed-module `py_compile`: PASS
- `git diff --check`: PASS
- no provider/outcome/protected-label access
- operational checkout, scheduler, counter, live runtime, model artifacts,
  and `coordination/TEAM_STATUS.md` were not modified

No historical performance or Monte Carlo run is permitted while the scope
status remains `STRICT_SCOPE_EMPTY_BLOCKED`.

## Required next gate

Only a separately reviewed, non-empty, hash-pinned strict scope may invoke the
runner. That scope must include complete certified Open support, CA continuity,
market-wide dividend semantics or defensible no-event evidence, and any
remaining tradability/PIT requirements. A diagnostic or partial scope must not
be promoted to canonical performance.
