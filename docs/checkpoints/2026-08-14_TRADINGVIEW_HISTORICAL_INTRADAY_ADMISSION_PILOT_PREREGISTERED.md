# TradingView Historical Intraday Admission Pilot V1 - Preregistered

Status: `PREREGISTERED_BEFORE_NETWORK`

This is a bounded admission pilot for the question whether anonymous
TradingView `prodata` can serve as a secondary raw 1-hour IDX source for
2021-2026. It is not a bulk-acquisition authorization and does not modify the
canonical panel, models, O2, Path Risk, or protected outcomes.

## Lineage and immutable inputs

- Branch: `data/tradingview-historical-intraday-admission-pilot-v1`
- Initial audit: `data/tradingview-historical-intraday-audit-v1` at
  `fb5a6384a49ce2a3c80c07ae2b79134de2f584bb`
- Remediation: `data/tradingview-historical-intraday-remediation-v1` at
  `fcfa5084c172c21d21d4e00489808b6bb20f6333`
- Independent remediation review: `6b12d689d06d7e71a5c642f948e590858764fcca`
- Prior remediation artifact manifest SHA-256:
  `aa57118d2def02e87fd6b9664203fcc0caa8228df01e0d14205782952d8cba24`
- New external artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814`
- New sample manifest SHA-256:
  `3de36746942bbf6e7dc201ce14d1aa94c75ab1dc6ebd59989e828f41114971bd`
- Config SHA-256:
  `7feafca01885486e958b03f1894b7636e63391a1297eaf3059fbd91c33524d5b`
- Security master SHA-256:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- Official calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Canonical panel SHA-256 before network:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

The sample manifest was created with `created_before_network=true` and the
preparation artifact records `network_started=false`. The prior audit and
remediation artifact roots are read-only.

## Frozen source contract

- Primary client: `Mathieu2301/TradingView-API`
- Exact commit: `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`
- Package: `3.5.2`
- Server: `prodata`
- Access: anonymous only; no credentials, cookies, or session tokens
- Symbol: `IDX:<ticker>`
- Timeframe: `60`
- Session: `regular`
- Adjustment: `none`
- Raw epochs and OHLCV are preserved; no rescaling, timestamp shifting,
  substitution, interpolation, or forward fill is allowed.

The exact pinned `endenwer/tradingview-ws` commit
`97c743c8230f732e5a49646dd8f0f44c5981a458` may provide bounded completion and
depth corroboration. Its numeric bars remain quarantined because the pinned
resolver hard-codes split adjustment.

## Frozen sample

Deterministic seed: `20260814`.

- 50 unique tickers total;
- 40 core common stocks listed by `2021-07-01`, selected from the frozen
  security master plus canonical 2024 liquidity strata;
- 10 edge controls: five post-cutoff listings and five lower-liquidity or
  identity-edge candidates;
- mandatory controls: `BBCA BBRI BMRI TLKM ASII INDF UNTR ANTM PTBA DSSA`.

Frozen ticker ordering:

`ADRO AMRT ANTM ASII BBCA BBNI BBRI BCIC BIPP BMHS BMRI BOGA BOSS BRIS BRPT
BUKA CANI CLAY DSSA FAPA FLMC GLOB INDF KOIN LMSH MDKA MLPT MOLI MYTX NICL
PCAR PPRO PTBA ROCK SCCO SDRA SMGR SQMI TCPI TFCO TIFA TLKM TOTO TOYS TPIA
TRJA UNTR UVCR WICO YPAS`.

No ticker was selected using TradingView results.

## Frozen yearly windows

Every year uses `July 1` through `July 7`; only dates present in the preserved
official calendar are admitted as certified sessions:

| year | requested window | certified dates |
|---|---|---|
| 2021 | 2021-07-01 to 2021-07-07 | Jul 1, 2, 5, 6, 7 |
| 2022 | 2022-07-01 to 2022-07-07 | Jul 1, 4, 5, 6, 7 |
| 2023 | 2023-07-01 to 2023-07-07 | Jul 3, 4, 5, 6, 7 |
| 2024 | 2024-07-01 to 2024-07-07 | Jul 1, 2, 3, 4, 5 |
| 2025 | 2025-07-01 to 2025-07-07 | Jul 1, 2, 3, 4, 7 |
| 2026 | 2026-07-01 to 2026-07-07 | Jul 1, 2, 3, 6, 7 |

No official dates are fabricated. The calendar covers all six requested
windows.

## Frozen request matrix

- Fixed 60-minute requests: `50 x 6 = 300` prodata requests, initial range
  500, no pagination.
- TV1D reconciliation: 10 mandatory/liquid controls x 6 = `60` prodata
  requests, `1D`, adjustment none.
- Deep pagination: `BBCA BBRI BMRI TLKM ASII INDF UNTR PTBA`, `8` prodata
  requests, `2021-01-01` through `2026-07-31`, initial range 500, three
  bounded `request_more_data` steps of 5,000, 15-second page waits, 30-second
  request timeout.
- endenwer corroboration: the same eight tickers, `8` bounded depth/completion
  requests, up to 13,000 candles / three pages, numeric data quarantined.

The expected primary request count is `368`; expected corroborator count is
`8`. The pilot is not a full-universe history download.

## Frozen gates and verdict logic

Preferred admission range: `2021-2026`.

- symbol resolution >= 95%;
- exact target-window availability >= 90% overall and >= 85% in every year;
- deep pagination reaches at least 2021 for >= 90% of the eight long-lived
  controls;
- certified-session coverage >= 90% wherever official calendar evidence exists;
- H/L/C exact >= 95% overall and >= 90% in every evaluated year;
- non-corporate volume within +/-5% of canonical daily volume >= 90% overall
  and >= 80% in every year with at least 10 matched rows;
- TV1D reference exact gate >= 90% overall and >= 80% per year;
- structural validity is mandatory: duplicate timestamps, malformed OHLCV,
  invalid geometry, off-session bars, and unapproved substitutions are
  quarantined and fail the structural gate.

The fallback range is exactly `2022-2026`, and is allowed only when all
preferred gate failures are 2021-specific. No other cutoff may be chosen after
observing results.

Open is evaluated separately. Full OHLCV admission requires TV60 aggregated
Open exact >= 90%, or a deterministic provider/session convention explained
without modifying raw bars. If coverage/HLC/volume gates pass but Open does
not, the verdict is price-path-only; no Open-dependent feature is admitted.

Verdict is computed by `evaluate_frozen_verdict(...)`, not manually selected:

`TRADINGVIEW_INTRADAY_ADMIT_2021_2026_FULL_OHLCV`

`TRADINGVIEW_INTRADAY_ADMIT_2021_2026_PRICE_PATH_ONLY`

`TRADINGVIEW_INTRADAY_ADMIT_2022_2026_FULL_OHLCV_2021_BLOCKED`

`TRADINGVIEW_INTRADAY_ADMIT_2022_2026_PRICE_PATH_ONLY_2021_BLOCKED`

`TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`

## Explicit boundaries

No bulk historical acquisition, canonical panel write, model/feature fitting,
Path Risk restart, O2/protected-outcome access, authenticated experiment,
execution-PnL claim, silent price/volume repair, or automatic downstream
admission is authorized. If authentication appears necessary, stop with
`AUTHENTICATED_ACCESS_EXPERIMENT_WARRANTED`.

## Pre-network validation

- Focused tests: `14 passed` (remediation + pilot gate tests).
- Python compilation: passed.
- Mathieu adapter JavaScript syntax: passed.
- Mathieu dependency install: passed, 0 npm vulnerabilities.
- `git diff --check`: passed.

Network execution may begin only after this checkpoint, the frozen sample, and
the claim/status update are committed and pushed.
