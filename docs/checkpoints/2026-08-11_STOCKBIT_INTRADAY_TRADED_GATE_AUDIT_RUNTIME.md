# Stockbit Intraday Traded-Today Gate Audit Runtime

Date: 2026-08-11 (Asia/Jakarta)  
Branch: `data/stockbit-intraday-forward-capture-v1`  
Starting remote HEAD: `6c3d06cb5ae760fd230f2268b025284267988c52`  
Decision: `STOCKBIT_INTRADAY_TRADED_TODAY_GATE_AUDIT_COMPLETE_STOP_FOR_REVIEW`

## Scope

This run executed only the frozen traded-today efficiency audit for session
`2026-08-11`. Exactly **one** broad `finance:idx/stock-summary` request was
made with `length=1000`, `start=0`, and `date=2026-08-11`. No recurring capture,
Open/TradingView work, PIT-sector work, modelling, or trading was started.

The preserved broad-census root was reused unchanged:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_broad_census_v1_20260811`

The traded-gate artifacts are in the new external root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_traded_gate_audit_v1_20260811`

## Validation and implementation fixes

- Focused traded-gate tests: **8 passed**.
- Full pytest: **283 passed**.
- `ZAPI_API_KEY` was present; its value was never printed, persisted, or
  logged.

The first network response was HTTP 200 but used the provider envelope
`{"data": {"data": [...]}}`, while the initial parser accepted only a
top-level `data` list. The audit failed closed before comparison and preserved
the raw response. The smallest implementation-only parser fix was then
validated by tests and the preserved response was parsed offline. No second
network request was made.

A second implementation-only fix made the persisted `run_summary.json` carry
the stable manifest digest by excluding the report itself from manifest inputs.
This avoids a report/manifest circular hash without changing any gate rule.

## IDX stock-summary evidence

- Raw provider records: **963**.
- Valid normalized exact-ticker rows: **962**.
- Frozen universe rows: **962**.
- IDX summary coverage of frozen universe: **962/962**.
- Duplicate ticker count: **0**.
- One raw row was rejected by the exact four-character identity rule:
  `StockCode=GOTOM MVS` (ambiguous/non-canonical identity).
- Session date validation passed for all 962 normalized rows.
- `volume`, `value`, and `frequency` were non-null for **962/962** normalized
  rows.

The actual provider envelope was preserved. Its data section contained the
records list plus `dataset`, `date`, `provider`, `recordsFiltered`,
`recordsTotal`, `start`, and `length`. Relevant row activity fields were
`Volume`, `Value`, and `Frequency`; no Open field was used.

## Confusion matrices

Frozen Stockbit outcomes were **832 SUCCESS** and **130 HTTP_404**. Every
activity rule produced the same result:

| IDX rule | TP | FP | FN | TN | precision | recall | chart calls | calls saved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `volume > 0` | 832 | 0 | 0 | 130 | 1.000 | 1.000 | 832 | 130 |
| `frequency > 0` | 832 | 0 | 0 | 130 | 1.000 | 1.000 | 832 | 130 |
| `value > 0` | 832 | 0 | 0 | 130 | 1.000 | 1.000 | 832 | 130 |
| robust OR | 832 | 0 | 0 | 130 | 1.000 | 1.000 | 832 | 130 |

- False negatives: **none** for every rule.
- False positives: **none** for every rule.
- Exact mismatch ticker lists are therefore empty for all rules.
- The robust OR rule satisfies the frozen preferred zero-false-negative gate
  and would avoid **130 Stockbit chart calls per session** in this audit.

This is an efficiency-audit result only; it does not authorize a recurring
prefilter or scheduler.

## Monthly burden estimate

Using the observed robust-OR prediction of 832 Stockbit chart calls plus one
IDX summary call per session:

| sessions/month | Stockbit chart calls | IDX gate calls | total calls |
|---:|---:|---:|---:|
| 20 | 16,640 | 20 | 16,660 |
| 21 | 17,472 | 21 | 17,493 |
| 22 | 18,304 | 22 | 18,326 |

These estimates do not authorize recurring capture.

## Quota and request accounting

The broad-census final safe baseline was remaining `minute=1946` and
`month=22482`. The first traded-gate response headers were not persisted by
the pre-fix runner because schema parsing failed before the report was written.
The after value is therefore intentionally reported as:

`UNAVAILABLE_WITHOUT_ADDITIONAL_NETWORK_CALL`

No additional quota probe or summary request was made. Network accounting is
exactly: request **1**, HTTP 200 **1**, retries **0**, HTTP 429 **0**. The raw
provider payload is retained for independent review.

## Artifact hashes

| artifact | SHA-256 |
|---|---|
| `idx_stock_summary_raw.json` | `6912496562848460bf8238e9cbe45d9a0ba4b03b240199d73c30d2b3311487eb` |
| `idx_stock_summary_normalized.csv` | `7c2f79e912c5625bf5a99b3b21f1a95be8858d3f5257987bf185f1b304c145f4` |
| `stockbit_idx_activity_comparison.csv` | `4cea777272ddbe78d575b501061822b0a4955580ed7639f34e8080b22008d0e1` |
| `run_summary.json` | `385a0f89f59ddb8848fff7f2d30f3721e64e99dfb87df464b17b198f10758ef6` |
| `artifact_manifest.json` | `e41b23e2d9d2fdb7a2ccea472d24ad70197b31ea6e4b2b3ba9b9d3c699ee77eb` |

The reused broad-census manifest remains:

`c59949645e88e71fb72c5bbec53fca43b0ef1d62dd70f3960299b3d695a9807a`

## Stop decision

The one-call traded-today audit is complete, has zero observed false negatives
against the 832 successful Stockbit charts, and is preserved for independent
ChatGPT review. Recurring capture remains **not authorized** in this run.
