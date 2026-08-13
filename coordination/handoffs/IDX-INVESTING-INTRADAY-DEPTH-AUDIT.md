# Handoff

from: Codex/Investing-Intraday-Depth-Audit
to: ChatGPT independent review
task_id: IDX-INVESTING-INTRADAY-DEPTH-AUDIT
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 3704955e17a471b7a63b4da9f75fe1223fd79bbd
branch: data/investing-intraday-depth-audit-v1
head_commit: pending final documentation commit
scope: Bounded Investing.com 1-hour historical depth census across 737 V2/V3-B training-universe tickers for sparse July probes in 2018, 2020, 2022, 2024, and 2026, plus a deterministic 20-ticker daily fidelity check.
files_changed:
  - docs/checkpoints/2026-08-13_INVESTING_INTRADAY_DEPTH_AUDIT.md
  - coordination/handoffs/IDX-INVESTING-INTRADAY-DEPTH-AUDIT.md
  - coordination/TEAM_STATUS.md
findings:
  - 3,685/3,685 1-hour requests completed.
  - Final provider errors: 0; bounded retries: 58 HTTP 403 to 200; HTTP 429 events: 0.
  - Available / 737: 2018 326 (44.23%), 2020 369 (50.07%), 2022 519 (70.42%), 2024 650 (88.20%), 2026 671 (91.05%).
  - Available / 726 resolved identities: 44.90%, 50.83%, 71.49%, 89.53%, 92.42% respectively.
  - 256 resolved tickers were available in all five years; 11 identities remained unresolved.
  - 20-ticker fidelity: HLC exact 190/256; OHLC exact 136/224 comparable Open rows; volume exact 203/256; median volume ratio 1.0.
  - Ten CA-like scale anomalies were observed: BMRI 2022 near 0.5 and DSSA 2024 near 0.1; no factor was inferred or applied.
decisions_made:
  - Investing.com is a promising redundant secondary source.
  - Historical 1-hour depth justifies a separately preregistered secondary acquisition pilot, not bulk acquisition or canonical promotion.
  - `NO_DATA` inside a listed interval remains ambiguous and is not interpreted as no trading.
  - Corporate-action scale mismatches remain fail-closed.
decisions_needed:
  - ChatGPT review of whether to authorize a separate preregistered secondary intraday acquisition pilot.
  - If authorized, freeze exact identity/date/timezone, corporate-action, parity, and admission rules before any wider retrieval.
blocking_risks:
  - Fidelity is not source-parity clean enough for replacement: HLC exact 74.22%, OHLC exact 60.71% on comparable Opens.
  - Provider bar boundaries appear as 08:00–16:00 Asia/Jakarta and require explicit normalization.
  - Corporate-action discrepancies require authoritative evidence; no ratio-based repair is allowed.
validation_run:
  - Full 1-hour depth census completed at the external artifact root.
  - Local fidelity aggregation completed without network calls after the depth census.
  - Repository diff validation pending final docs commit; no executable code changed.
recommended_next_action: Stop for independent ChatGPT review. Do not start bulk historical intraday acquisition, panel writes, model work, or Path Risk.
