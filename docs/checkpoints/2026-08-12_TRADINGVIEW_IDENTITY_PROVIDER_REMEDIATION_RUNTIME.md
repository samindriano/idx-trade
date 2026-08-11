# TradingView Identity/Provider Remediation Runtime

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tradingview-identity-remediation-v1`
Starting HEAD: `a8f4c2fb4c8be02405b5d00ce9272b91459daf9e`
Implementation commit: pending
Decision: `TRADINGVIEW_IDENTITY_REMEDIATION_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`

## Scope and controls

This run executed only the frozen 2,877-row
`TV_IDENTITY_OR_PROVIDER_ERROR` remediation target. The target was loaded
from the preserved TradingView census and was verified at source SHA
`1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd`.

No history-window, H/L/C-disagreement, or corporate-action bucket was touched.
No panel, Yahoo+TradingView derivative, or model artifact was written. No
alternate provider, Investing request, stock-history request, modelling,
Ranking/PIT work, or execution work was started.

The immutable panel SHA-256 remained unchanged before and after:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

The accepted Yahoo+TradingView derivative remained unchanged:

- `execution_open_candidate_panel_yahoo_tradingview.parquet`:
  `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`
- `execution_open_candidate_provenance_yahoo_tradingview.parquet`:
  `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687`

## Frozen target and offline identity evidence

| Ticker | Rows | Date range | Preserved prior provider evidence |
|---|---:|---|---|
| FREN | 952 | 2021-04-29 to 2025-04-14 | HTTP 404 / request error |
| MASA | 717 | 2021-06-28 to 2024-07-25 | HTTP 404 / request error |
| MFIN | 915 | 2021-04-29 to 2025-09-19 | HTTP 404 / request error |
| RMBA | 65 | 2021-04-29 to 2021-08-05 | HTTP 404 / request error |
| SMBR | 1 | 2023-03-14 | prior HTTP 520 |
| TURI | 227 | 2021-04-29 to 2022-05-25 | HTTP 404 / request error |
| **Total** | **2,877** | **2021-04-29 to 2025-09-19** | |

The filtered target artifact SHA is
`7bbcfe904f659e48d8fa726ea7b2c72d57834a89352c109795238b5dcea5e7fc`.

Offline evidence was inspected before network execution:

- FREN was resolved from the curated project identity evidence as a common
  share, listed 2006-11-29 through 2025-04-16.
- MASA, MFIN, RMBA, SMBR, and TURI were resolved from the existing PIT
  security master and official Stock Summary snapshots.
- Official snapshots showed names under the same ticker only. SMBR's two
  name forms (`Semen Baturaja (Persero) Tbk.` and `Semen Baturaja Tbk.`) are
  not an evidenced ticker alias.
- No explicit historical/current ticker alias relationship was found for any
  target ticker. `aliases_tested=[]`; no alternate symbol was guessed or
  requested.

## Authorized network execution

The only authorized network request was one unchanged canonical retry:

```text
symbol=IDX:SMBR
market=indonesia
resolution=1D
count=1000
```

Result:

- logical requests: 1;
- HTTP attempts: 1;
- HTTP status: 200;
- candles returned: 1,000;
- retries: 0;
- rate-limit events: 0;
- request errors: none;
- prior successful tickers refetched: 0;
- alternate symbols tested: 0.

The preserved raw response was re-read offline after the request. Its actual
shape is a top-level `data`/`project`/`timestamp` wrapper; the unwrapped chart
object has these keys:
`candles`, `count`, `currency`, `exchange`, `market`, `name`, `provider`,
`resolution`, `symbol`, and `timezone`. The corrected shape is recorded in the
external summary; no network call was made for that correction.

## Exact admission result

The existing exact gate was unchanged: exact ticker/date, exact certified
H/L/C, finite positive raw Open, and Open within the certified Low–High range.

| Metric | Result |
|---|---:|
| Target rows | 2,877 |
| Exact ticker/date coverage | 1 |
| Exact certified H/L/C | 1 |
| Admissible positive/in-range Open candidates | 1 |
| Resolved candidate rows | 1 |
| Unresolved rows | 2,876 |

The single candidate is `SMBR` on `2023-03-14`:

| Field | Certified panel | TradingView raw |
|---|---:|---:|
| High | 388 | 388 |
| Low | 372 | 372 |
| Close | 372 | 372 |
| Open | missing | 388 |

It passed as `TV_RECOVERY_CANDIDATE` with diagnostic
`EXACT_HLC_POSITIVE_IN_RANGE_OPEN`. No panel value was written.

Unresolved rows remained by ticker:

- FREN: 952;
- MASA: 717;
- MFIN: 915;
- RMBA: 65;
- TURI: 227.

## Validation and external artifacts

- Focused tests: **10 passed** (`test_tradingview_identity_remediation.py`
  and `test_zapi_tradingview_targeted_census.py`).
- Full pytest: **271 passed**, 6 existing `FutureWarning` locations,
  0 failures.
- External runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_identity_remediation_v1_20260812`
- Immutable artifact manifest SHA-256:
  `ace16c99a14cf805cf1b48b8407d7f8e6ab9d90116264d2267e12c39ed56d669`
- Corrected external summary SHA-256:
  `1c19787690ede5b008358196795b48d7c9bbb8a926df9e2d993a659a1f4113a0`

Manifest artifact hashes:

| Artifact | SHA-256 |
|---|---|
| `frozen_identity_provider_target_rows.csv` | `7bbcfe904f659e48d8fa726ea7b2c72d57834a89352c109795238b5dcea5e7fc` |
| `offline_identity_evidence.json` | `fe8755ae3b6e3c23f154c355083aee6703be81272f7d29daddc262fdd6521227` |
| `target_input_provenance.json` | `0d5c061324cbda24335a7424775f2789021fd09a7dfa773ff40f9990c403f332` |
| `tradingview_remediation_raw_responses.jsonl` | `9a54f709ee752f06e41f81408d12ec64b1062181bd5e00892ca9d858756d30de` |
| `tradingview_remediation_row_audit.csv` | `33b06259e663ab3ecae5be01514d495a071ef57f7628b061986cf88af9e0e7f5` |
| `tradingview_remediation_rows.csv` | `2454ce69be1ac652c1fa800cf12c11bfdc4ec5eb213744b42243e8cf12b3c3d5` |
| `tradingview_remediation_ticker_status.csv` | `13436ece49be642d9fe4b33e22ee25ee70049a453d89afe764ee05b9c9e4b20f` |

The API key was not printed, persisted, or committed. The run ends here for
independent ChatGPT review. No later bulk census or execution-grade promotion
is authorized by this checkpoint.
