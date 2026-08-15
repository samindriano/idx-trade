# Handoff — Price / Trend Runtime Bridge Adapter V1

from: ChatGPT
to: Codex Windows local runtime / ChatGPT independent review
task_id: IDX-PRICE-TREND-RUNTIME-BRIDGE-ADAPTER-V1
repository: samindriano/idx-trade
branch: integration/price-trend-runtime-bridge-adapter-v1
status: REVIEW

## Current verdict

`PRICE_TREND_RUNTIME_BRIDGE_ADAPTER_V1_ENGINEERING_READY_LOCAL_SMOKE_REQUIRED`

Validated code HEAD: `2df8134aac531ec1214f560a8393cda607b9da7a`.

Later commits on the same branch are documentation/handoff only.

## Scientific parents

- accepted Price State V1 implementation: `research/idx-price-trend-confirmation-state-v1@a33863953b4521dd4549a3089f0da2cfdfb6dcd3`
- independent Price State acceptance: `review/idx-price-trend-confirmation-state-v1-acceptance@0c3b221fcecf035add4d0c7ce388ff4b9d6d27da`
- accepted Forward Sidecar engineering: `integration/price-trend-state-forward-sidecar-v1@a4d19fd1615c4a9f9988ed16540c34f5efbe1b1a`
- sidecar acceptance: `review/idx-price-trend-forward-sidecar-v1-acceptance@ae3eea14e526c27e18c035e047db524a4b566be6`
- runtime context identity pin: `integration/price-trend-runtime-context-pin-v1@417e306cf9e30dbb4a9a1ab1ea8855b7dbd7bd51`

No state formula/threshold was changed in the runtime adapter lane.

## Exact approved context

Runtime root:

`D:\Documents\Project\idx-trade-data-gate-20260808v`

Historical Clean-V2 market panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Historical official calendar:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`

SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

Bridge extension calendar:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge\calendar\ranges\2026-07-31_2026-08-13\exchange_sessions.csv`

SHA-256:

`51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`

Combined in-memory session-set SHA-256:

`dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`

Accepted Foreign Flow context anchor for the controlled smoke:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\foreign_flow_representation_v2\2026-08-13\foreign_flow_representation_v2.manifest.json`

Manifest SHA-256:

`4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d`

## Frozen bridge policy

- bridge-only market context may supply official sessions through `2026-08-10`;
- `2026-08-11` onward requires valid canonical DATA_READY `model_input.parquet`;
- canonical + bridge both valid on a bridge-eligible date fails as ambiguity;
- missing extension session fails closed;
- canonical parent calendars are verified against their own capture-time pins and are not required to equal the bridge extension calendar;
- no provider fallback, recapture, canonical repair, session compression, weekday inference, forward fill, or synthetic HLCV.

## Implemented runtime modules

- `src/idx_trade/forward_price_trend_context_bridge.py`
- `src/idx_trade/forward_price_trend_context_anchor.py`
- `src/idx_trade/forward_price_trend_controlled_smoke.py`

Required runtime verifier:

`verify_price_trend_state_context_bridge_strict`

Optional first-smoke context attestation verifier:

`verify_price_trend_context_anchor_attestation`

The context attestation is sibling evidence only and explicitly not a generic future runtime dependency.

## GitHub validation

PR `#28` validation at code HEAD `2df8134aac531ec1214f560a8393cda607b9da7a`:

- focused tests: **39 passed**;
- `git diff --check`: PASS;
- Price State workflow: PASS;
- Forward Sidecar workflow: PASS;
- Runtime Bridge Adapter workflow: PASS;
- full pytest: **78 passed, 1 failed, 4 warnings**;
- sole failure is the known unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` (`raw_close` + `vendor_adj_close` conflicts vs old expected count 1).

## Mandatory local sequence

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md` **before doing anything else**.
2. Check active lanes and safely add/update the Price / Trend Runtime Bridge Adapter lane in canonical TEAM_STATUS. Preserve every other agent's row/change; do not force-push.
3. Fetch/checkout latest `integration/price-trend-runtime-bridge-adapter-v1`. Confirm the validated code lineage includes `2df8134aac531ec1214f560a8393cda607b9da7a`.
4. Verify working tree is clean before the smoke.
5. Recheck existence and SHA-256 of every exact pinned Windows artifact above, including the accepted Foreign Flow context-anchor manifest.
6. Run focused tests for all Price State files and `git diff --check`.
7. Run full pytest and record the exact result separately from the known storage failure.
8. Execute **exactly one** controlled smoke command:

```powershell
python -m idx_trade.forward_price_trend_controlled_smoke --runtime-root "D:\Documents\Project\idx-trade-data-gate-20260808v"
```

9. Require final status exactly `PRICE_TREND_CONTROLLED_SMOKE_VERIFIED`.
10. Record:
    - source/feature session;
    - row/ticker count;
    - Price State artifact path + SHA;
    - Price State manifest path + SHA;
    - context-attestation path + SHA;
    - state distributions for all axes;
    - runtime source kinds/order;
    - combined-session-set SHA/count;
    - `bridge_strict_verified=true`;
    - `accepted_context_attested=true`;
    - `idempotent_replay_verified=true`;
    - provider_calls=0;
    - all outcome/model/trade flags remain false.
11. Do not inspect any future return, TP/SL, protected O2 vault, or historical performance.
12. Add a runtime-smoke checkpoint + handoff to this branch; commit/push.
13. Refetch latest canonical TEAM_STATUS and set this lane to `REVIEW` with exact HEAD/result while preserving other rows.
14. STOP for ChatGPT independent review.

## Explicit prohibitions

Do not:

- wire this into canonical EOD scheduler/post-capture yet;
- create/change any scheduler or forward counter;
- call a provider or recapture bridge/canonical sessions;
- access outcomes/labels/TP/SL or compute performance;
- tune Price State thresholds;
- combine Foreign Flow + Price State;
- define WATCH / READY / ENTRY_ELIGIBLE;
- change O2;
- integrate HSC/free-float/effective supply.

## Expected output location

For feature session `2026-08-13`:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\price_trend_confirmation_state_v1\2026-08-13\`

Expected files after a successful controlled smoke:

- `price_trend_confirmation_state_v1.parquet`
- `price_trend_confirmation_state_v1.manifest.json`
- `price_trend_context_anchor.attestation.json`

Existing complete identical artifacts are acceptable and must be handled idempotently. Partial or conflicting artifacts must fail closed; do not delete or overwrite them to make the smoke pass.