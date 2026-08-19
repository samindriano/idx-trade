# TradingView V2.1 Fidelity Forensic V1 — Prep

Date: 2026-08-20 (Asia/Jakarta)
Branch: `data/tradingview-v2-1-fidelity-forensic-v1`
Scientific parent: `data/tradingview-historical-price-path-v2-1-remediation@bfb3cbc`
Status: `PREPARED_OFFLINE_RUNTIME_REQUIRED`

## Purpose

Resolve the apparent 2022 TradingView HLC anomaly before authorizing a full V2.1 historical acquisition or any Path Risk V3 work.

The failed V2 runtime reported 2022 HLC exact fidelity of about 75.46%, but only about 0.83% of 2022 ACTIVE ticker-sessions were covered under the shallow ~550-bar request contract. Because each request was anchored to its ticker-specific historical `required_end`, old-year support can be compositionally enriched for historical/delisted/reorganized names. The existing 2022 aggregate therefore cannot be interpreted as a market-wide year-specific TradingView failure without a same-ticker and three-way forensic.

## Frozen hypotheses

The audit distinguishes four explanations without tuning a threshold after seeing results:

1. `SUPPORT_SELECTION`: shallow V2 pagination caused old-year fidelity to be dominated by historical-end ticker cohorts.
2. `CANONICAL_ORACLE_CONFLICT`: TradingView agrees with official IDX Stock Summary while the existing canonical daily comparator differs.
3. `TRADINGVIEW_YEAR_SPECIFIC_FIDELITY_RISK`: canonical and official IDX agree while TradingView differs materially on the same 2022 rows.
4. `MIXED_UNRESOLVED`: no single explanation dominates defensibly.

Corporate-action neighborhood differences are recomputed using ordered official-session adjacency; no price rescaling, inferred split factor, source voting, averaging, or repair is allowed.

## Exact offline evidence

### A. Same-ticker controls

Reuse only the accepted five V2.1 depth-preflight controls:

- BBCA
- BBRI
- BMRI
- TLKM
- ASII

Accepted preflight root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_depth_preflight_20260816`

The parent checkpoint records 50,986 returned 60m bars, all five controls reaching 2020-01-02 with zero structural/session violations. The forensic aggregates those exact bars to daily H/L/C and measures each calendar year on the same ticker set.

### B. Legacy V2 exact 2022 cohort

Reuse the immutable failed-V2 artifacts under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814`

The forensic retains exact ticker/date support and adds:

- request `required_end`;
- listing end when present;
- historical-end vs window-end cohort;
- canonical `price_provenance`;
- H/L/C mismatch pattern and direction;
- ticker concentration;
- corporate-action quarantine under ordered official sessions.

### C. Three-way reconciliation

For exact supported ticker/date rows compare:

`TradingView 60m daily aggregate ↔ existing canonical daily raw ↔ official IDX Stock Summary`

Each row is classified as one of:

- `ALL_AGREE`
- `TV_IDX_AGREE_CANONICAL_DIFF`
- `CANONICAL_IDX_AGREE_TV_DIFF`
- `TV_CANONICAL_AGREE_IDX_DIFF`
- `ALL_DIFFER`
- `INSUFFICIENT_THREE_WAY_SUPPORT`

The official IDX archive remains diagnostic; this audit does not silently replace the frozen canonical admission oracle.

## Conservative adjudication

The helper can emit a diagnostic interpretation only. It cannot authorize acquisition, panel mutation, Path Risk, model fitting, or outcome access.

- Long-lived 2022 controls must clear the existing 95% HLC reference level against both canonical and supported official IDX rows before a support/oracle-bias explanation can be considered strong.
- `CANONICAL_ORACLE_CONFLICT` requires at least half of resolved legacy three-way rows to be `TV_IDX_AGREE_CANONICAL_DIFF`.
- `SUPPORT_SELECTION` requires historical-end mismatch rate to exceed window-end mismatch rate by more than 10 percentage points while controls are clean.
- `TRADINGVIEW_YEAR_SPECIFIC_FIDELITY_RISK` requires weak same-ticker 2022 TV-vs-IDX fidelity plus legacy three-way support on the canonical/IDX side.
- Otherwise the verdict remains `2022_ANOMALY_MIXED_UNRESOLVED`.

These are forensic interpretation rules, not new admission gates. Frozen V2/V2.1 admission thresholds remain unchanged.

## Implementation

Prepared files:

- `src/idx_trade/tradingview_v2_1_fidelity_forensic.py`
- `scripts/run_tradingview_v2_1_fidelity_forensic_v1.py`
- `tests/test_tradingview_v2_1_fidelity_forensic.py`

Synthetic helper tests were independently exercised before publication: `6 passed`.

The runtime script has no TradingView adapter call, subprocess provider call, HTTP client, model fit, or protected-outcome path. It refuses to overwrite a non-empty output root and verifies the pinned canonical panel SHA before analysis.

## Stop boundary

A local Windows runtime is required because all decision-bearing V2/V2.1/canonical/official-archive bytes are external under `D:\Documents\Project\...` and are not available in the current ChatGPT execution environment.

Do not start full 978-ticker V2.1 acquisition after this prep. First run this exact offline forensic, preserve the generated manifest and summary, then stop for independent result review.
