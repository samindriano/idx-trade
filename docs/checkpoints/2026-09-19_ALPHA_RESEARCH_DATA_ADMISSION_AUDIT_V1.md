# Alpha Research Program — Data Admission Audit V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Scope: read-only, outcome-blind, no provider access, no canonical writes

## Result

`NO-GO` for new-alpha historical outcome claims in the current lane.

Local artifacts are sufficient for capability and structural feature audits,
but the authoritative data-QA boundary does not certify a same-science,
population-wide, historical-as-of subset for a new alpha comparison. The
incumbent and its frozen baseline artifacts remain untouched.

## Evidence

- The clean OHLCV panel used by prior challenger construction is
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_final_20260820_v2\model_safe_signal_research_panel_1260_final_clean.parquet`.
  It has 981,940 rows, 945 tickers, dates 2021-04-29–2026-07-31, unique
  `(ticker,date)` keys, no outcome-like columns, and SHA-256
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`.
  Its permitted status is frozen-only baseline reproduction/capability
  assessment, not authorization to refit, score, or admit new alpha.
- The separately recorded frozen V4-X1 input has 981,940 rows, 945 tickers,
  1,260 dates, and source hash
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` as
  recorded in the independent inventory. This does not widen authorization.
- The Financial PIT bundle
  `D:\Documents\Project\idx-financial-representation-v2-20260816-v1-run3\bundle_rows.parquet`
  has 277,244 rows, 729 tickers, dates 2021-06-02–2026-07-17, unique keys,
  and parquet SHA-256
  `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`.
  It is structurally useful but remains `PARTIAL`/parked for new alpha claims;
  complete rows do not by themselves establish population completeness or
  source admission.
- Official IDX and Zapi staging artifacts are snapshots or sample/probe
  evidence. They are `PARTIAL`, `BLOCKED`, or `UNKNOWN` for this scientific
  purpose and are not substituted into the candidate panel.
- The historical foreign-flow archive remains blocked for scientific alpha
  claims, and the prior expected representation path was not found as an
  admitted source.

## Consequence

The four frozen candidates may be materialized and audited for causal
construction, missingness, coverage, deterministic provenance, and internal
overlap. They must not be compared to forward targets, assigned IC/ICIR,
called OOS winners, or marked `RESEARCH_SURVIVOR` until a separate admission
decision certifies the input and target population. No target/forward-label
artifact has been opened in this lane.
