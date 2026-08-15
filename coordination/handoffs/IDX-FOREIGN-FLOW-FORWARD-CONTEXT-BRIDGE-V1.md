# Handoff — Foreign Flow Forward Context Bridge V1

from: ChatGPT
to: Codex local runtime / ChatGPT independent review
task_id: IDX-FOREIGN-FLOW-FORWARD-CONTEXT-BRIDGE-V1
repository: samindriano/idx-trade
branch: data/foreign-flow-forward-context-bridge-v1
base: integration/foreign-flow-representation-v2-forward-v1 @ db630a80ae5cac3e25acbe149a3c1335a38c99d8
implementation_head: e128725fd856c3332abb4110cd28fe42e68c64c9
validation_pr: #25 (draft, CI-only, no merge authorization)
scope: close the bounded post-2026-07-31 rolling-context gap without changing Foreign Flow V2/Setup State semantics or O2 runtime rules

## What is implemented

- `src/idx_trade/forward_foreign_flow_context_bridge.py`
  - isolated immutable official IDX bridge calendar ranges;
  - self-contained official Stock Summary transport with strict `recordsTotal` completeness;
  - bridge-only Stock Summary + Yahoo raw-OHLCV context capture;
  - Foreign Flow normalization through the existing accepted parser;
  - validation-before-final-write behavior;
  - immutable market/flow/raw/manifest artifacts;
  - strict verification and outcome-blind flags.
- `src/idx_trade/forward_foreign_flow_context_bridge_plan.py`
  - zero-provider-call, zero-write planner;
  - classifies required dates into canonical-ready, bridge-ready, bridge-capture-required, canonical-EOD-required, or ambiguous.
- `src/idx_trade/forward_foreign_flow_context_bridge_run.py`
  - bridge-aware adapter around the accepted prospective V2 materializer;
  - bridge fallback allowed only through 2026-08-10;
  - after 2026-08-10 only verified canonical EOD is accepted;
  - immediate prospective Setup State remains downstream.
- focused tests for calendar isolation, canonical/bridge ambiguity, invalid-canonical fallback, post-monitor canonical-only policy, planner behavior, operator-counter non-mutation, accepted V2 causality, and prospective Setup State delivery.

## Validation already completed

GitHub Actions scoped focused workflow:

`24 passed, 5 warnings`

The five warnings are existing pandas `FutureWarning`s from the accepted V2 implementation.

The first bridge CI attempt exposed unavailable imports from the separate operator-EOD branch. Those cross-branch dependencies were removed. The bridge tests now collect and pass on the accepted producer base.

Repository-wide default CI still stops at collection because pre-existing `foreign_flow_alpha_v2.py` imports `joblib`/scikit-learn while this branch's `pyproject.toml` does not declare/install those historical-alpha dependencies. The bridge lane does not modify that unrelated dependency contract merely to force a green full-suite result.

No provider/runtime artifact call has been performed from ChatGPT.

## Local sequence

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md` and claim/continue this lane before provider/runtime execution. Preserve all other rows. Do not claim or modify HSC/free-float or O2 scientific scope.
2. Checkout/pull `data/foreign-flow-forward-context-bridge-v1` at or after `e128725fd856c3332abb4110cd28fe42e68c64c9`.
3. Re-run focused tests:

   `pytest -q tests/test_forward_foreign_flow_context_bridge.py tests/test_forward_foreign_flow_context_bridge_policy.py tests/test_forward_foreign_flow_context_bridge_plan.py tests/test_forward_foreign_flow_representation_v2.py tests/test_forward_foreign_flow_setup.py`

4. Run the available full `pytest` and `git diff --check`. Do not fix unrelated `joblib`/historical-alpha dependency or storage expectations from this lane; document them if encountered.
5. Identify the actual local runtime root and accepted historical panel/archive/security-master pins already used by the V2 forward producer. Do not guess paths or hashes.
6. Create an immutable bridge calendar covering 2026-07-31 through at least the desired next feature-session horizon using:

   `python -m idx_trade.forward_foreign_flow_context_bridge sync-calendar ...`

   Do not modify `forward_monitoring/calendar/exchange_sessions.csv`.
7. Run the read-only planner with historical cutoff `2026-07-31` through the chosen latest completed source session.
8. Inspect and record the planner result before provider calls.
9. For each `NEED_BRIDGE_CAPTURE`, capture only if date <= 2026-08-10. Existing preserved canonical bytes must not be overwritten. Expected pre-monitor dates are not authoritative until the official calendar confirms them.
10. For each `NEED_CANONICAL_EOD` after 2026-08-10, use the existing canonical EOD catch-up runtime. Do not substitute bridge capture.
11. Rerun the planner. Proceed only if status becomes `CONTEXT_BRIDGE_READY` with no ambiguous sessions.
12. Run exactly one `forward_foreign_flow_context_bridge_run` prospective production for the latest valid completed source session. It must create/verify Representation V2 + prospective Setup State for the next official session.
13. Verify hashes/provenance and that operator calendar/counter rules were not modified. No outcome access.
14. Update checkpoint/handoff with exact runtime results, hashes, planner classifications, and test results; commit/push; update TEAM_STATUS to `REVIEW`; STOP for ChatGPT review.

## Hard boundaries

- No overwrite or repair of preserved 2026-08-10/11/12 canonical bytes.
- A fresh bridge capture of 2026-08-10, if planner requires it and official response passes completeness, is a separate bridge-only revision, not canonical repair.
- No bridge fallback after 2026-08-10.
- No second scheduler, monitor, forward counter, model worker, or provider family.
- No HSC/free-float integration.
- No price-state / MA / higher-low / breakout research.
- No historical alpha rerun or Foreign Flow feature/threshold change.
- No protected/fresh-forward outcome access.
