# Zapi TradingView Targeted Non-CA Census Runtime

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-tradingview-targeted-census-v1`
Starting HEAD: `1510585f6a11c52411edb47f08127b9ee3525685`
Decision: `TRADINGVIEW_NON_CA_RESIDUAL_CENSUS_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`

## Scope and controls

The frozen target was the exact 38,819 non-corporate-action rows from the
49,476-row Yahoo residual detail. The 10,657 corporate-action rows were
excluded and not reclassified. The TradingView contract was unchanged:
`symbol=IDX:<ticker>`, `market=indonesia`, `resolution=1D`, `count=1000`.

No panel write, panel backfill, execution-grade promotion, alternate symbol
resolution, Investing call, stock-history call, corporate-action repair,
modelling, Ranking work, or execution work was performed.

The immutable panel SHA-256 was unchanged:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

## Inputs and reuse

| Item | Result |
|---|---:|
| Residual detail rows | 49,476 |
| Authorized non-CA rows | 38,819 |
| Excluded corporate-action rows | 10,657 |
| Authorized residual tickers | 652 |
| Residual input SHA-256 | `26cd2319991aa5dc2fcce78d7f256f31fb1762b4510c0623fcd16fb87b66fd02` |
| Preserved combined TradingView manifest SHA-256 | `68adea6bd6cf2b251b43e010133d8a3899c7d3ff8af8566f4bd9b88f0f9f3134` |
| Tickers fully covered by preserved cache before network | 112 |
| Tickers partially covered by preserved cache before network | 66 |
| Preserved successful tickers in authorized scope | 188 |
| Tickers uncovered before network | 474 |
| Prior successful tickers refetched | 0 |

The five preserved TradingView provider/symbol failures were not retried:
`FREN`, `MASA`, `MFIN`, `RMBA`, and `TURI`. The deterministic new network set
contained 459 unique tickers; its SHA-256 was
`55ff305ddc076b8237266f95ba79ccdc2b4ff574965534e0bbee03c21e7d2dc8`.

## Network result

| Metric | Result |
|---|---:|
| Logical ticker requests | 459 |
| HTTP attempts | 459 |
| Retries | 0 |
| HTTP 429 events | 0 |
| Targeted SUCCESS tickers | 458 |
| Targeted request-error tickers | 1 (`SMBR`, HTTP 520) |
| New provider rows | 429,282 |
| Combined deduplicated provider rows | 623,241 |

Quota preflight confirmed Pro headers without persisting the API key:

- `plan_status=PRO`, `pro_limits_confirmed=true`;
- minute limit/remaining: `2000` / `2000`;
- month limit/remaining: `25000` / `24060`;
- preflight response status was HTTP 400 from the safe MCP initialize call,
  while the quota headers still confirmed the Pro limits;
- post-run safe quota probe ended with a transport `ConnectionResetError(10054)`
  and no response body was persisted. Post-run remaining quota is therefore
  unavailable; this is not treated as a quota number.

## Final 38,819-row census

| Metric | Count | Rate |
|---|---:|---:|
| Exact ticker/date provider coverage | 23,240 | 59.8676% |
| Exact certified H/L/C | 5,675 | 14.6191% |
| Admissible positive/in-range Open candidates | 5,675 | 14.6191% |
| `TV_HISTORY_WINDOW_UNAVAILABLE` | 12,702 | 32.7185% |
| `TV_HLC_DISAGREEMENT` | 17,565 | 45.2485% |
| `TV_IDENTITY_OR_PROVIDER_ERROR` | 2,877 | 7.4119% |

All 5,675 exact-H/L/C rows passed the unchanged positive/in-range Open gate.
Recovery by original residual class:

- `NO_PROVIDER_ROW`: 3,664;
- `PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR`: 2,011;
- corporate-action rows: 0 by design.

Recovery by calendar year:

| Year | Candidates |
|---:|---:|
| 2021 | 1,529 |
| 2022 | 2,160 |
| 2023 | 1,120 |
| 2024 | 860 |
| 2025 | 6 |

Top-20 recovery ticker concentration:

`TECH=515`, `HKMU=511`, `CBMF=420`, `GAMA=333`, `ARGO=304`, `JSKY=304`,
`PURE=304`, `LMAS=261`, `HOTL=260`, `WSKT=241`, `CPRI=216`, `MAGP=177`,
`BNBA=126`, `DUCK=79`, `BATA=36`, `MPMX=36`, `GIAA=32`, `FIMP=17`,
`SMMA=17`, `PGJO=14`.

Cumulative candidate concentration: top 10 = 3,453; top 50 = 4,438; top
100 = 4,689.

Yahoo arbitration over the final census rows:

- supports certified panel: 5,675;
- supports Yahoo only: 0;
- disagreement: 17,565;
- no provider row: 15,579.

Final provider/symbol error tickers were `FREN`, `MASA`, `MFIN`, `RMBA`,
`SMBR`, and `TURI`. The detailed unresolved breakdown is stored in
`final_census.unresolved_by_reason_class_year` in the external summary; it
contains 21 deterministic reason/class/year groups. The aggregate unresolved
count is 33,144 (= 38,819 - 5,675), with 12,702 history-window rows, 17,565
H/L/C disagreements, and 2,877 identity/provider-error rows.

The hypothetical remaining non-CA residual count if—and only if—all 5,675
admissible candidates were later approved is **33,144**. This is
counterfactual only; no panel values were written.

## Validation and artifacts

- Focused census tests: **5 passed**.
- Full pytest after implementation/finalization: **263 passed**, 3 existing
  FutureWarning locations.
- Panel SHA before/after: unchanged at
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
- External runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_targeted_census_v1_20260811`
- Artifact manifest SHA-256:
  `d0f5899310f9bf37d9f2f726be440fa11a8dcbf7de6703dde068a18009290bf1`

Manifest file hashes:

| Artifact | SHA-256 |
|---|---|
| `authorized_non_ca_residual_detail.csv` | `c6dd6fbe8df37fb13a999d9b2bf7c666565a0df682f0d8ce6dedc004077be9a1` |
| `quota_after.json` | `af0647da0fe9c3ba29ccca9395e2d0be8da2d76f299d605e3aad138d42a2f825` |
| `quota_before.json` | `2d99edab2098e1bda20e53fe283bf81136f4e2680f06721ed1d814f937c2802f` |
| `residual_input_provenance.json` | `b9335bf6cf56701b058b61abc70495bbf8a598cec2c52610db1e6158e3d354da` |
| `tradingview_combined_row_audit.csv` | `1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd` |
| `tradingview_combined_rows_with_provenance.csv` | `0453776a87995cb32a2a1da9b662bc4eb33e7318f6c53181d33a47130d2da87f` |
| `tradingview_combined_ticker_status.csv` | `40a9acda3eae3cbb2068ce8240c11f9679c6620c68b6d357c9d1ca33fc0f1620` |
| `tradingview_targeted_raw_responses.jsonl` | `91431367321eba72cbfd879458bd7938ab38099e328dac01d1d2ec9d77570a76` |
| `tradingview_targeted_row_audit.csv` | `b1171b1c9f5d3201ce7af3627a5435b0ea8c4ad5456f7cd161ca2b97c42280c6` |
| `tradingview_targeted_rows.csv` | `33b8e26ad2fb8f982fbbc3e0db80739d95f47b22236466c8ed6abe1837b1c9bf` |
| `tradingview_targeted_ticker_status.csv` | `a02221048543dfecf935fd8b339a3c0b6ce9e0699831fd14c1a328b18bce837a` |

The API key was never printed, persisted, or committed. Stop condition:
preserve artifacts and wait for independent ChatGPT review; do not authorize
panel approval or the 49,476-row residual census from this result.
