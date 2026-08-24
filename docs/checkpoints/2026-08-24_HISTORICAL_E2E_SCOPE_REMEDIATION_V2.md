# Historical E2E Scope Remediation V2

Date: 2026-08-24  
Branch: `research/idx-historical-e2e-replay-v1`  
Parent: `9c505366fa7704ec58ca976b32d9994c92d63ebb`  
Scope: outcome-blind historical E2E scope validation and replay-boundary hardening

## Verdict

`TRUE_HISTORICAL_E2E_REPLAY_SCOPE_BLOCKED_BY_CA_DIVIDEND_DATA`

The scope freezer now accepts an explicitly hash-pinned contiguous range with a
declared `start_session`, `end_session`, and `session_count`; it no longer
assumes a fixed 6x100 shape. The fresh recompute still produces no strict
range because the exposure-level corporate-action and dividend gates are not
complete. No historical replay, performance metric, NAV, label, protected
outcome, model fit, or Monte Carlo was run.

## Frozen scope contract

- Candidate source range: 600 ordered official sessions.
- Strict minimum: 20 contiguous sessions.
- Supported declared lengths: 20, 60, 120, 252, or 600, subject to the
  explicit contiguous-range and gate checks.
- The current runner only bootstraps a zero-holding state at session index 0.
  A non-zero `start_session` is therefore rejected as
  `REPLAY_SCOPE_NONZERO_START_STATE_UNSUPPORTED` until a predecessor-state
  anchor contract is separately implemented and reviewed. This is a safety
  boundary against silently replaying an arbitrary subrange with an incorrect
  initial portfolio state.
- The longest eligible range is selected by completeness only, with earliest
  start as the deterministic tie-break. No performance information is used.

## Open evidence semantics

The certified Open verifier now distinguishes:

- `OFFICIAL_POSITIVE_OPEN`: usable positive OpenPrice;
- `OFFICIAL_NONPOSITIVE_TRUE_UNAVAILABLE`: certified IDX evidence exists, but
  OpenPrice is zero/non-positive and remains unavailable to sizing;
- `EVIDENCE_MISSING` or invalid provenance: a strict identity blocker.

The latter two categories are not conflated. Certified non-positive evidence is
allowed to follow the frozen Execution V1 pending semantics; it is never
replaced with FirstTrade, H/L/C, an inferred value, or a synthetic value.

Fresh recompute results:

- 600/600 session manifests certified;
- required BUY identities: 1,297 evidence rows, 905 positive, 392
  non-positive, 0 missing;
- required SELL identities: 1,287 evidence rows, 891 positive, 396
  non-positive, 0 missing;
- BUY-ready sessions by the evidence/pending contract: 600/600;
- SELL-ready sessions by the evidence/pending contract: 600/600.

The positive Open counts are reported for diagnostics only. They do not cause
the scope to be treated as complete by substituting values for non-positive
rows.

## Exposure-level continuity gates

Fresh output:
`D:\Documents\Project\idx-historical-e2e-scope-recompute-20260824-v9\REPLAY_SCOPE.json`

- scope file SHA-256:
  `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0`
- canonical scope payload SHA-256:
  `f75cf7302f4bd27927e36e296634c7ae9adfcd32849ed8fc78555a9e27dc6fd7`
- status: `STRICT_SCOPE_EMPTY_BLOCKED`
- candidate sessions: 600
- strict sessions: 0
- blockers:
  - `NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE`
  - `DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`

The exact exposure universe contains 5,693 rows. Corporate-action evidence is
strictly resolved for 4,471/5,693 rows and 40/600 sessions have every exposure
row CA-ready. Dividend evidence is ready for only 11/5,693 rows and 0/600
sessions have every exposure row dividend-ready. The dividend policy remains
fail-closed: absence of a candidate is not proof that no dividend or other
entitlement event occurred.

## Pinned inputs

- readiness manifest:
  `D:\Documents\Project\idx-historical-e2e-replay-readiness-20260823-v6`
  SHA `86304dac2226f40e58f18ea302f709106b67609165b4bb488bda4c5d7b4564e7`
- readiness summary SHA:
  `31aea94cf6cea52b1a2dcea25676f944bd13f06731b745f0179044f2aca9a040`
- exact exposure universe SHA:
  `110d3f7543c33e90a7d2cea1352f6360e0385fd5399c4b61409ee3acba56d030`
- CA exposure gap SHA:
  `8172ef21fde01545a8d176ed1d2b40703663675c9577bc34791b820ab50e973b`
- dividend exposure gap SHA:
  `625c3dfe6986bd9f9309a9a2fad4cb0f8398dfb1edb770655784eac4187c2322`
- Open acquisition manifest SHA:
  `dc74485c6d4ade01e125b08871105c8daea9c64f9daa2af6cc00d26592a8fcbf`
- CA manifest SHA:
  `c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4`
- CA ledger SHA:
  `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`
- dividend result SHA:
  `454213df35c3ffd741cc137c24d502f1fc45cd46e229c1c553852b2418e07aac`
- calendar SHA:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## Validation and boundaries

- focused scope/replay/Open-verifier tests: 58 passed;
- full pytest: 745 passed, 0 failed, 3 existing pandas `FutureWarning`s;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- no provider call in this remediation;
- no protected outcome, label, score, return, NAV, or performance access;
- no scheduler, counter, operational runtime, or model artifact changed;
- `coordination/TEAM_STATUS.md` was not modified; MAIN owns it.

## Required next gate

Do not run the historical E2E replay or Monte Carlo on this scope. A later
lane must first provide accepted exposure-level CA continuity, dividend
semantic/no-event evidence, and any required tradability/session evidence,
then freeze a non-empty hash-pinned scope and validate its predecessor-state
semantics before replay.
