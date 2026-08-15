# Price / Trend Runtime Bridge Adapter V1 — Local Smoke Result

Date: 2026-08-15
Branch: `integration/price-trend-runtime-bridge-adapter-v1`
Validated implementation lineage: `2df8134aac531ec1214f560a8393cda607b9da7a`
Latest branch HEAD before this checkpoint: `d5055e29e34802ae789789107ffe71e41c0c3c89`

## Scope

This was the one authorized zero-provider local smoke only. No source code was
changed, no provider or recapture was attempted, and no scheduler/counter,
Foreign Flow + Price State integration, O2, HSC/free-float, model, trade-state,
performance, or outcome work occurred.

## Preflight

The pinned external inputs were present and hash-verified:

- historical panel: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- historical calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- bridge calendar: `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`;
- accepted Foreign Flow context manifest:
  `4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d`.

The code lineage check passed: `2df8134...` is an ancestor of the latest
branch HEAD.

## Tests

- focused Price/Trend suite: `39 passed`;
- full pytest: `78 passed, 1 failed, 4 warnings`;
- collected full-suite tests: `79`;
- unrelated failure:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict, while current shared storage reports independent
  `raw_close` and `vendor_adj_close` conflicts;
- `git diff --check`: PASS.

## Exactly-one smoke result

Command executed once:

```powershell
python -m idx_trade.forward_price_trend_controlled_smoke --runtime-root "D:\\Documents\\Project\\idx-trade-data-gate-20260808v"
```

The runner failed closed while resolving canonical EOD context for
`2026-08-11`:

`POST_MONITOR_SESSION_REQUIRES_VALID_CANONICAL_EOD 2026-08-11: RuntimeError: canonical parent calendar missing or hash-mismatched`

Evidence:

- canonical manifest:
  `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\forward_monitoring\\sessions\\2026-08-11\\manifest.json`;
- its declared parent calendar SHA:
  `e61a3b7e01215f43c7fea094afc2c001710e53734eb940c3de57324e841ce9`;
- current bytes at the declared path have SHA:
  `bd33e977ac0dd690e4527f308080f63ebb5a8696d2022448d90d83771c4dfdc3`;
- no file with the declared `e61a3b7e...` SHA was found in the runtime
  calendar files;
- the accepted bridge calendar remains independently present at its pinned
  `51d36148...b91b7e` SHA.

The expected Price State output directory did not exist before the smoke and
remains without a newly produced artifact. Therefore there is no valid
Price State artifact/manifest/attestation path or SHA, state distribution,
runtime source order, combined-session result, or final status
`PRICE_TREND_CONTROLLED_SMOKE_VERIFIED` to report.

## Decision

`PRICE_TREND_CONTROLLED_SMOKE_BLOCKED_CANONICAL_PARENT_CALENDAR_REVISION_CONFLICT`.

The runner's fail-closed behavior is working. Independent review is required
before any remediation of the external canonical calendar/manifest identity.
Do not retry, recapture, rewrite the canonical session, or alter the adapter
in this lane without a new authorization.
