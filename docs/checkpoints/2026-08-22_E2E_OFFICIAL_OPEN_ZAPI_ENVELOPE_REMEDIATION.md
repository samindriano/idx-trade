# E2E Baseline Paper V1 — Zapi Raw Envelope Remediation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`

## Root cause

The first dual-transport local validation proved the fallback chain itself worked:

- direct IDX attempted first and returned HTTP 403;
- Zapi raw fallback was invoked and returned HTTP 200;
- capture then failed closed with `OFFICIAL_OPEN_ZAPI_RAW_PROVIDER_MISMATCH`.

A bounded response-shape probe showed the mismatch was caused by an incorrect assumption in the validator, not by bad Zapi data.

Actual Zapi response envelope for both relevant endpoints is:

```text
{
  "data": {
    ... provider/dataset/path/counts/rows ...
  },
  "project": ...,
  "timestamp": ...
}
```

For raw IDX passthrough on session `2026-06-12`, the nested object contained:

- `provider = idx`;
- `path = TradingSummary/GetStockSummary`;
- `recordsTotal = 959`;
- `recordsFiltered = 959`;
- nested `data` list length = 959;
- duplicate `StockCode` count = 0.

Witnesses remained exact:

| Ticker | OpenPrice | FirstTrade |
|---|---:|---:|
| AADI | 8100 | 8075 |
| BBCA | 6000 | 5975 |
| BBRI | 2880 | 2890 |

The normalized full-session `finance:idx/stock-summary` endpoint without a code filter was also coherent at 959/959/959, but the canonical secondary path remains **raw IDX passthrough** because it is closer to the upstream source semantics already frozen for execution evidence.

## Remediation

`src/idx_trade/official_open_evidence_v1.py` now:

1. preserves the exact full Zapi HTTP response bytes as the raw evidence artifact;
2. reads Zapi provenance from the nested `payload["data"]` envelope;
3. requires nested `provider = idx`;
4. requires nested `path = TradingSummary/GetStockSummary`;
5. unwraps only the nested Stock Summary object for normalization/count validation;
6. applies the same `rows == recordsTotal == recordsFiltered` completeness contract;
7. leaves direct IDX payload parsing unchanged;
8. rejects Zapi envelope bytes if relabelled as `DIRECT_IDX_HTTPS`;
9. rejects direct IDX bytes if relabelled as `ZAPI_IDX_RAW_PASSTHROUGH`;
10. records `response_envelope = data` as non-secret transport metadata.

Source semantics remain unchanged:

- authority = `IDX`;
- field = `OpenPrice` only;
- `FirstTrade` is audit witness only;
- price fallback policy = `NONE`;
- zero/non-positive OpenPrice remains unavailable;
- no Stockbit/IEP/IEV substitution;
- no prior-session automatic backfill.

Tests were updated to model the actual nested Zapi response shape instead of the previously assumed top-level provider/path shape.

## Validation state

This remediation still requires fresh local focused regression and real fallback smoke on the exact new HEAD.

The scheduler remains uninstalled until that validation passes.

Pending verdict:

`OFFICIAL_IDX_OPENPRICE_ZAPI_ENVELOPE_REMEDIATED_PENDING_LOCAL_REVALIDATION`
