# Price / Trend Runtime Bridge Adapter V1 — Final GitHub Validation

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/price-trend-runtime-bridge-adapter-v1`

Validated code HEAD: `2df8134aac531ec1214f560a8393cda607b9da7a`

Status: `REVIEW`

Verdict: `PRICE_TREND_RUNTIME_BRIDGE_ADAPTER_V1_ENGINEERING_READY_LOCAL_SMOKE_REQUIRED`

## Final additions after the main checkpoint

Two controlled-smoke hardening pieces were added without changing the accepted Price State formulas or the bridge source policy:

1. `src/idx_trade/forward_price_trend_context_anchor.py`
   - optional sibling context-attestation only;
   - binds the Price State manifest SHA to the independently accepted Foreign Flow Representation V2 2026-08-13 manifest SHA `4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d`;
   - verifies exact agreement on historical panel/calendar, bridge calendar, combined session set, source/feature sessions, and bridge/canonical market-source identities;
   - does not modify the immutable Price State sidecar;
   - explicitly records `future_runtime_dependency=false`.

2. `src/idx_trade/forward_price_trend_controlled_smoke.py`
   - one-shot zero-provider orchestration only;
   - produce -> bridge-aware strict verify -> optional accepted-context attest -> attestation verify -> idempotent replay;
   - CLI is intentionally locked to `2026-08-12 -> 2026-08-13` when using the accepted default pins;
   - does not install/change a scheduler, counter, provider, model, outcome path, or Foreign Flow state.

## Final validation

Validation PR: `#28`.

At code HEAD `2df8134aac531ec1214f560a8393cda607b9da7a`:

- focused Price State + sidecar + bridge adapter + context anchor + controlled smoke tests: **39 passed**;
- `git diff --check`: **PASS**;
- Price State validation workflow: PASS;
- Forward Sidecar validation workflow: PASS;
- Runtime Bridge Adapter validation workflow: PASS;
- full repository pytest: **78 passed, 1 failed, 4 warnings**.

The sole full-suite failure remains the pre-existing unrelated storage assertion:

`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`

Storage emits two independent conflicts (`raw_close`, `vendor_adj_close`) while the old test expects one. No Price State / sidecar / bridge / anchor / controlled-smoke test failed.

## Local command after mandatory TEAM_STATUS coordination

From a Windows checkout of this branch:

```powershell
python -m idx_trade.forward_price_trend_controlled_smoke --runtime-root "D:\Documents\Project\idx-trade-data-gate-20260808v"
```

The command is authorized for exactly one mechanical `2026-08-12 -> 2026-08-13` smoke. It is expected to print `PRICE_TREND_CONTROLLED_SMOKE_VERIFIED` only after bridge-aware strict verification, accepted-context attestation verification, and idempotent replay all pass.

## Stop boundary

The local smoke is the only next authorized runtime action. Do not wire the adapter into canonical EOD automation/scheduler yet. Do not combine Price State with Foreign Flow and do not define WATCH / READY / ENTRY_ELIGIBLE before independent review of the local smoke.