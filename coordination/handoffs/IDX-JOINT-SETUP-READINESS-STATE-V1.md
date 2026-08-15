# Handoff

from: Codex/Joint-Setup-Readiness
to: ChatGPT independent review
task_id: IDX-JOINT-SETUP-READINESS-STATE-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 5c98d8a674ddf6f2da24e7d52e9a308af4c88079
branch: research/idx-joint-setup-readiness-state-v1
head_commit: implementation and contract checkpoint commit pending final push
scope: Deterministic outcome-blind joint state contract over accepted Foreign Flow Setup State V1 and Price / Trend Confirmation State V1 parents; no runtime wiring.

## Parent lineage

- Foreign Flow Setup State / Representation V2 prospective parent:
  `integration/foreign-flow-representation-v2-forward-v1`
- Price / Trend runtime parent implementation lineage:
  `integration/price-trend-runtime-bridge-adapter-v1`, validated code lineage
  `2df8134aac531ec1214f560a8393cda607b9da7a`
- Independent acceptance context:
  `review/idx-price-trend-runtime-smoke-blocker-v1@5aa81aaf00533f3930cecdf302c0bf7de52acb4c`

## Files changed

- `src/idx_trade/joint_setup_readiness_state.py`
- accepted parent contract modules copied without semantic changes:
  `src/idx_trade/foreign_flow_setup_state.py`,
  `src/idx_trade/foreign_flow_setup_sidecar.py`,
  `src/idx_trade/price_trend_state.py`
- `tests/test_joint_setup_readiness_state.py`
- `docs/checkpoints/2026-08-15_JOINT_SETUP_READINESS_STATE_V1_CONTRACT.md`

## Decisions

- Exact join key: `(ticker, feature_session)`.
- Foreign Flow `flow_through_session` must equal Price State `source_session`.
- Both parent sessions must map to the next official session.
- Missing, duplicate, partial, state-invalid, provenance-invalid, or protected
  parent input fails closed and does not produce a partial joint row.
- Valid rows classify only to `IGNORE`, `WATCH`, `READY`, or
  `ENTRY_ELIGIBLE`; the last state is descriptive context, never a trade
  recommendation.
- Frozen matrix and reason codes are recorded in the checkpoint and exported
  by the implementation.

## Validation

- Focused tests: 7 passed.
- Full pytest: 46 passed, 1 known unrelated storage expectation failure, 47
  collected.
- `git diff --check`: pending final validation before push.
- No provider calls, outcome access, model fitting/scoring, O2/counter changes,
  scheduler changes, HSC/free-float work, or prospective runtime wiring.

## Decisions needed

Independent review should decide whether this contract is accepted. Runtime
wiring is intentionally not started in this lane.

recommended_next_action: review contract/matrix and tests; authorize any runtime wiring separately only after acceptance.
