# Open Research-Grade Coverage Gate — Frozen Spec

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-open-research-coverage-gate-v1`
Base: `969367bcbc0f5ee28a403c8d7f01a6aaab9cfeb3`
Decision: `OPEN_RESEARCH_COVERAGE_GATE_AUTHORIZED_NO_MODELLING`

## Purpose

Determine whether the remaining Open missingness is material to the exact frozen V3-B Structure-Lite alpha research universe. This is a research-data adequacy gate, not an execution-grade promotion and not a new model experiment.

## Accepted Open sources before this gate

- immutable/certified panel Open rows;
- accepted Yahoo fills: 397,367;
- accepted TradingView fills already applied: 5,675;
- one additional accepted SMBR TradingView candidate on 2023-03-14.

If the SMBR row is applied as a read-only overlay or new derivative, expected global accounting is:

- total rows: 981,940;
- null Open: 43,800;
- known Open: 938,140;
- global Open coverage: 95.5394423%.

The immutable certified panel must remain unchanged.

## Exact universe requirement

Do not approximate the relevant model universe from all active rows.

Reproduce the exact V3-B Structure-Lite historical research eligibility logic from repository code and frozen artifacts. The current final historical-development ranker is `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`.

Where an exact frozen final-refit population is available, verify its identity/counts/hashes before reporting coverage. If exact train/validation/test or walk-forward partitions are reproducible from frozen artifacts, use those exact partitions. If some partition cannot be reconstructed faithfully, mark it unavailable rather than inventing one.

## Required analysis

Report at minimum:

1. global Open coverage after the accepted SMBR overlay/application;
2. exact V3-B model-eligible row count and Open-known/Open-missing counts;
3. Open coverage rate on exact V3-B eligible rows;
4. exact final historical-refit population Open coverage if separately identifiable;
5. coverage by calendar year;
6. coverage by ticker, including concentration of missing rows in top 10/20/50 tickers;
7. coverage by official session and worst sessions;
8. coverage by any frozen historical train/validation/test or walk-forward partitions that can be reproduced exactly;
9. number and percentage of V3-B eligible rows lost if future OHLCV experiments require non-null Open;
10. overlap of remaining missing Open with liquidity/universe eligibility, listing status, corporate-action residuals, history-window residuals, H/L/C disagreements, and identity/provider errors where provenance permits;
11. causal feature-readiness diagnostics for a minimal Open feature family without fitting a model:
    - overnight gap using current Open and prior Close;
    - intraday return using current Close/Open;
    - Open position in current High-Low range;
    - Open-to-High and Open-to-Low excursions;
    - any one-day lag needed to make a feature available strictly before the model decision time must be explicit;
12. after all required lags/warm-up, count rows that remain usable for a fair OHLCV challenger dataset;
13. define a future fairness intersection: any HLCV baseline-vs-OHLCV challenger comparison must use the exact same Open-eligible evaluation rows when measuring incremental Open value.

## Decision rubric

Return one factual recommendation:

### PASS_FOR_OHLCV_ALPHA_RESEARCH
Use if Open missingness is small and not pathologically concentrated in a way that invalidates the frozen research universe; causal Open-derived feature rows remain sufficiently broad across time/tickers/sessions for controlled challenger experiments.

### CONDITIONAL_PASS_FOR_OHLCV_ALPHA_RESEARCH
Use if coverage is generally sufficient but one or more periods/tickers/partitions require explicit exclusions or a restricted common-support universe.

### FAIL_FOR_OHLCV_ALPHA_RESEARCH
Use if missingness materially damages the exact V3-B research population, creates severe temporal/cross-sectional selection, or leaves inadequate common-support rows.

Do not use an arbitrary global coverage threshold alone; justify the verdict from concentration and common-support diagnostics.

## Hard boundaries

- No OHLCV model training or hyperparameter search.
- No V3-B retuning.
- No protected fresh-forward outcome access or interim evaluation.
- No corporate-action repair.
- No new provider/network calls are needed for this gate.
- No execution-grade promotion.
- No immutable-panel mutation.
- No Ranking/PIT-sector changes.

Run focused tests and full pytest for any implementation added. Persist factual analysis artifacts/hashes, write a dated runtime checkpoint, push fast-forward, and STOP for independent ChatGPT review.
