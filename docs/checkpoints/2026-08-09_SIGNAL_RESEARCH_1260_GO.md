# SIGNAL_RESEARCH_1260 GO — final bounded data-foundation diagnostic

Date: 2026-08-09 (Asia/Jakarta)
Branch: `data/idx-data-002c`
Implementation commit: `524fbfa8b794597a1959aa0e25392df242991d09`

## Decision

`STRICT EXECUTION-GRADE 1260: FAIL`
`SIGNAL-RESEARCH 1260: GO`

This is a separate research-layer decision. It does not change, weaken, or
relabel the strict 1260 gate. Strict 126 remains PASS; strict 504 and strict
1260 remain FAIL.

## Controls and validation

- Exact window: `2021-04-29 -> 2026-07-31`, 1,260 official IDX sessions.
- Runtime reused without market redownload:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`.
- Full pytest: **157 passed, 0 failed**; three existing pandas warnings only.
- Four bounded local read-only workers processed date-partitioned cache data.
- No paid data, market-wide Yahoo rerun, Open synthesis, strict contract
  change, modelling, `IDX-VAL-002`, or main merge.

## Exact UNKNOWN audit

The exact input was `research_metrics_1260/unknown_sessions.csv`: 572 rows,
381 dates, and 8 tickers.

| classification | rows | share |
|---|---:|---:|
| `UNKNOWN_WITH_OFFICIAL_EXECUTION` | 0 | 0.000% |
| `UNKNOWN_WITH_PROVIDER_PRICE_ROW` | 0 | 0.000% |
| `UNKNOWN_NO_EXECUTION_EVIDENCE` | 572 | 100.000% |
| `UNKNOWN_LEGAL_STATE_BOUNDARY` | 0 | 0.000% |
| `OTHER` | 0 | 0.000% |

All rows were `LISTED`, `COMMON_SHARE`, and `IN_SCOPE_COMMON_STOCK`. All had:

- no exact official Stock Summary row;
- no positive official Volume/Frequency;
- no valid official H/L/C;
- no Yahoo/provider row;
- no valid H/L/C from any approved source;
- no explicit legal suspension interval.

Ticker-level rows:

| ticker | UNKNOWN rows | date range | class |
|---|---:|---|---|
| ADCP | 190 | 2021-05-21 -> 2022-02-22 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| FINN | 1 | 2021-05-05 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| GRPH | 1 | 2024-01-17 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| KETR | 376 | 2021-04-29 -> 2022-11-09 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| MASA | 1 | 2025-10-30 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| MFIN | 1 | 2025-10-02 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| RMBA | 1 | 2024-01-16 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |
| TURI | 1 | 2023-04-06 | `UNKNOWN_NO_EXECUTION_EVIDENCE` |

Reason boundary counts: 2 listing left-boundary rows, 565 rows before the
first authoritative anchor, and 5 listed-to-boundary rows. The nearest-state
summary is 567 rows with no prior anchor and next `ACTIVE`, and 5 rows with
prior `NO_TRADE` and no next anchor. These remain UNKNOWN and are not promoted
to any other state.

## Critical consistency check

The exact set intersection was computed from the preserved official regular-
trade anchors and the UNKNOWN input:

`UNKNOWN ticker/date pairs ∩ required signal-research ACTIVE pairs = 0 rows`.

There is no critical contradiction.

## Signal-research HLCV result

Included rows require point-in-time common-share scope, `LISTED` existence,
official `ACTIVE` execution evidence, valid positive High/Low/Close/Volume,
explicit provenance, and verified split/reverse-split integrity. Open is
nullable and never synthesized. UNKNOWN rows are excluded.

| metric | result |
|---|---:|
| required common stocks | 979 |
| eligible common stocks | 979 |
| expected ACTIVE rows | 981,940 |
| eligible ACTIVE rows | 981,940 |
| ACTIVE-row coverage | 100.000% |
| total known Regular-Market Value | 15,620,249,523,853,300 |
| eligible known Regular-Market Value | 15,620,249,523,853,300 |
| trading-value coverage | 100.000% |
| remaining unsupported securities | 0 |
| corporate-action integrity | 979/979 verified |
| UNKNOWN rows excluded | 572 |

## Dual contract implementation

The explicit layer is implemented in `src/idx_trade/signal_research.py` and
tested in `tests/test_signal_research.py`. The permanent contract definition
is `docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md`.

- `EXECUTION_GRADE_OHLCV`: strict path, Open required, unchanged and FAIL at
  1260.
- `SIGNAL_RESEARCH_HLCV`: ACTIVE-only HLCV path, Open nullable, no synthetic
  values, explicit Open status and provenance.

## Materialized research panel

- path:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`;
- rows: 981,940;
- tickers with rows: 945;
- required tickers represented by the contract: 979, including 34 with zero
  expected ACTIVE sessions;
- null Open rows: 446,843;
- null Open percentage: 45.5061409047%;
- valid H/L/C/Volume rows: 981,940/981,940;
- provenance: 751,958 IDX Stock Summary rows and 229,982 Yahoo raw HLCV rows;
- duplicate ticker/session rows: 0;
- panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Separate signal-research manifest

- path:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\signal_research_1260_manifest.json`;
- SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- artifact count: 15;
- immediate verification: `valid=true`, 15/15 hashes verified;
- verification output:
  `signal_research_1260_manifest_verification.json`.

## Next phase and prohibitions

Recommended next phase: **STAGE 2 — RESEARCH SPECIFICATION AND VALIDATION
DESIGN**.

Do not begin modelling, run `IDX-VAL-002`, modify strict OHLCV certification,
synthesize Open, expand the historical window, or merge to `main` from this
checkpoint.
