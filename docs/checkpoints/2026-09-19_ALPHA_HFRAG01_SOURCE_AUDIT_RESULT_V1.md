# H-FRAG-01 Official Stock-Summary Source Audit — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `SOURCE_BLOCKED / PARTIAL / NO C5`

## Decision

`SOURCE_BLOCKED` under the preregistered fail-closed rules. The official
stock-summary cache is a real, internally coherent source surface, and its
non-regular fields are not exact duplicates of the frozen panel. However,
`nonregular_volume / volume` leaves `[0,1]` on 8,750 eligible rows and
`nonregular_frequency / frequency` leaves `[0,1]` on 7 eligible rows. The
preregistration defines this as a validity failure; no clipping, winsorization,
reinterpretation, candidate creation, packet expansion, or status upgrade was
performed.

This is a source-capability/structural diagnostic only. It is not a target,
IC, ICIR, OOS, P&L, superiority, or C5 result.

## Source inventory and integrity

- Source: `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\stock_summary_cache_1260\`
- Parquet files: `1,260`; matching sidecars: `1,260`.
- Cache rows: `1,104,064`; tickers: `980`; official dates: `1,260`, from
  `2021-04-29` through `2026-07-31`.
- Duplicate `(ticker,date)` rows: `0`.
- Source identity: exactly `IDX_PUBLIC_STOCK_SUMMARY`.
- Sidecar rows: `1,104,064`; sidecar `records_total`: `1,106,490`; source-ref
  count: `1,260`; row/date sidecar checks passed.
- Numeric required fields were non-negative and required fields were non-null.
- Deterministic cache inventory SHA-256:
  `b3502bc09064fb8183f787b1389141b263880c17fd96c8cc26347e8c49168c3f`.

## Reconciliation to the frozen panel

- Frozen panel rows: `981,940`.
- Exact `(ticker,date)` overlap: `981,940`.
- Cache-only rows: `122,124`; cache-only tickers: `35`.
- Panel-only rows: `0`.
- `volume` exact on overlap: `981,940 / 981,940`.
- `regular_value` versus panel `regular_market_value` exact on overlap:
  `981,940 / 981,940`.

The exact overlap is reconciliation evidence only. It does not establish the
publication/available-at semantics or PIT admissibility of the non-regular
fields.

## Target-free structural diagnostic

The existing eligible decision universe contains `310,761` rows and `711`
tickers. On the latest `600` common official sessions (`2024-01-12` through
`2026-07-31`), the two source-composition ratios were compared structurally
with C1/C2/C4 and H-LIQ only. No target or predictive outcome was read.

Summary of eligible ratio coverage:

- Both ratios had `100%` finite eligible coverage.
- Non-regular volume ratio: median `0.0`, q90 `0.0944143`, q99 `5.0265502`,
  boundedness violations `8,750`.
- Non-regular frequency ratio: median `0.0`, q90 `0.0013319`, q99
  `0.0096618`, boundedness violations `7`.
- Positive rows: `100,226` for each non-regular field.
- Bottom-value Q1 share among selected Top-30 slots: volume ratio `13.5389%`;
  frequency ratio `19.6556%`.

Mean daily Spearman on the 600-session structural window:

| Surface | C1 | C2 | C4 | H-LIQ |
|---|---:|---:|---:|---:|
| Non-regular volume ratio | -0.0148 | -0.0244 | -0.0312 | -0.1494 |
| Non-regular frequency ratio | -0.0086 | -0.0316 | -0.0193 | -0.1535 |

Mean Top-30 overlap with the existing surfaces was low (approximately
`6.97%`–`12.48%` across the two ratios and four references), but this is only
structural non-redundancy evidence. It cannot establish economic value or
predictive usefulness.

## Independent verification and firewalls

- Generator: `research/alpha_hfrag01_source_audit_v1.py`; SHA-256
  `2c4f3288e043aa1027c949c169476849c382c6309f4892bca8508705a1cad599`.
- Artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hfrag01_source_audit_v1.json`; SHA-256
  `aa37a326a2449926625bf8a0be37efa285cdd9595a813e96c996f9eeeb247277`.
- Artifact hash-contract: `PASS`; output SHA-256
  `7c048ecc8f41db795316e1af4a221a6b2c372108d1166fe581bf88b0d9ac95a3`.
- Independent verifier:
  `research/verify_alpha_hfrag01_source_audit_v1.py`; SHA-256
  `5a5dab9d0617cd96c5260097fd47ebc2d484ba245b1e788e138b1f3040e3f4b4`.
- Independent verification: `PASS`; output SHA-256
  `c1c079eb4280769efdd4cf8d9adb533c8ed1e9a62b1b98b7d1da63ef019ad732`.
  It independently reproduced the inventory hash, counts, exact panel
  reconciliation, and `8,750`/`7` boundedness violations.
- Generator target/privacy firewall: `PASS`; output SHA-256
  `9a638a16cdfa81549a9328108e14fa299282a600c86d732b08c294b695b38b4d`.
- Independent-verifier target/privacy firewall: `PASS`; output SHA-256
  `a008eafd3a2cda7e76979ca2566569926e844d3ffb12c5ba073139b7c0a1e06c`.

All recorded access flags are false for outcome, provider, cloud, incumbent
predictive data, and candidate creation.

## Next allowed action

Do not admit H-FRAG-01, assign a candidate ID, expand the one-shot packet, or
run a live/OOS smoke. The next research action requires independent field
semantics, regular/non-regular classification definition, row-level
available-at/knowledge-time, revision/vintage behavior, and identity coverage.
Until those are supplied and separately admitted, retain this as a blocked
future hypothesis only.
