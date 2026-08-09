# Official IDXData3 Opening-Price Source Lead

Date: 2026-08-09

Branch at investigation start: `data/idx-data-002c`

Latest runtime checkpoint before this source audit: `abd4ca42331c5732b2761c0c377d7d50d6d20929`

## Why this checkpoint exists

The 504-session certification remains blocked by exact historical ACTIVE-session opening-price gaps after the normal Yahoo path and official IDX Stock Summary fallback were exhausted.

Latest remaining price gaps from the validated runtime are:

- FREN: 196 ACTIVE sessions remaining; official Stock Summary parsed opening rows = 0.
- MASA: 22 ACTIVE sessions remaining; official Stock Summary parsed opening rows = 0.
- MFIN: 172 ACTIVE sessions remaining after 77 of 249 missing rows were filled from positive official Stock Summary `OpenPrice`.

The generic secondary-opening witness exists and is tested, but normal public requests to the candidate Investing.com pages returned HTTP 403. No anti-bot, CAPTCHA, authentication, or rate-limit bypass was attempted. Therefore Investing must not be treated as an available production evidence path.

## Newly identified official IDX source

Fresh public-source research found an official IDXData3 public reporting specification describing:

`SO[YYMMDD].zip` — `Daftar harga Opening Price setiap saham`.

The same official specification maps the legacy/public order-book summary fields including:

- `tradedate`
- `seccode`
- `board`
- `securityname`
- `remarks`
- `prevprice`
- `open`
- `firsttrade`
- `high`
- `low`
- `close`
- `daysvolume`
- `daysvalue`
- `numtrades`

This is potentially a materially better evidence source than a secondary vendor because it may supply the missing opening execution directly from an official IDX publication.

Official specification source:

`https://www.idxdata3.co.id/IDX%20Reporting%20PSPP/Revitalisasi/Specification%20Document-Report%20Revitalization_PUBLIK%20v1.0.pdf`

## Public-directory evidence

The official IDXData3 public download directory exposes a `Stock_First_Trx` report family with files named `SOYYMMDD.zip`. Search-index evidence confirms real historical SO files exist and use that naming convention.

However, the currently indexed visible listing inspected during this research showed SO files from 2020. That proves the report family and path semantics, but it does **not** yet prove that SO files are retained for the exact 2024-2025 dates needed by the current 504-session repair.

Separately, the official `Stock_Summary` directory clearly exposes long historical `SSYYMMDD.zip` files including the 504-window start date `SS240621.zip` and many later 2024 sessions. This reinforces that IDXData3 has public historical daily-report infrastructure, but it does not by itself establish SO retention for the same dates.

## Required next audit

Before changing any price semantics or rerunning the 504 ladder, perform a bounded live source audit against the exact remaining missing ACTIVE date sets.

For each missing FREN, MASA, and MFIN session:

1. Attempt normal public retrieval of the corresponding official `Stock_First_Trx/SOYYMMDD.zip` file.
2. Do not bypass authentication, anti-bot controls, CAPTCHAs, rate limits, or access restrictions.
3. If available, inspect the archive schema and parse the exact ticker/date/REGULAR-board row.
4. Require positive/valid official opening price and explicit provenance.
5. Cross-check ticker/date and, where available, H/L/C against the already retained official Stock Summary record; contradictions fail closed.
6. Record per-date `AVAILABLE`, `FILE_MISSING`, `TICKER_ROW_MISSING`, `INVALID_OPEN`, `CROSS_OFFICIAL_CONFLICT`, or equivalent diagnostics.
7. Do not synthesize, forward-fill, or infer an opening price from High/Low/Close.

Only after exact coverage is known should a reusable official SO provider/parser be integrated and the 504 repair rerun.

## Decision

- 504 remains **FAILED / NOT CERTIFIED**.
- 1260 remains **NOT STARTED**.
- Do not run 252 merely because this source audit is pending.
- Do not weaken the gate.
- Prefer the official SO path over secondary-vendor evidence if it can cover the exact missing sessions defensibly.
