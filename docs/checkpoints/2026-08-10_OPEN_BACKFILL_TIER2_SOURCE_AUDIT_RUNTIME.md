# Open Backfill Tier-2 Source Audit V1 — Runtime Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tier2-audit-v1`
Runtime implementation commits: `9758586`, `7d6e0cd`

## Decision

**`OPEN_BACKFILL_TIER2_SOURCE_AUDIT_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`**

This was the authorized bounded source pilot only. It does not authorize a
bulk Tier-2 backfill, execution-grade promotion, execution-PnL analysis,
modelling, Stage 5, Ranking V2 changes, paper/live trading, or a merge to
`main`.

## Immutable panel and baseline

- input panel:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`
- SHA-256 before runtime:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- SHA-256 after runtime:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- baseline null Open rows: `446,843`
- existing non-null Open values were never overwritten
- `execution_grade_promoted=false`

## Deterministic sample

The sample was selected from the immutable panel, the preserved Tier-1
Wildan diagnostics, and pre-existing identity/action/tradability evidence
before either candidate source was queried.

- fixed seed: `20260810`
- rows: `50`
- sample SHA-256:
  `e1dbeb40969508108ec480a32c4a22a07d194d850986883fd4ee4b5ae1b79385`
- known existing Open: `20`
- missing Open with a Wildan row: `25`
- missing Open with no Wildan row: `5`
- named coverage: `FREN`, `MASA`, `MFIN`, `BBCA`, `BBRI`
- factual edge rows selected:
  - `AADI 2024-12-05` — listing/new-listing boundary;
  - `ALDO 2024-07-08` — official corporate-action-adjacent date;
  - `BREN 2024-05-06` — suspension/resumption boundary;
  - FREN rows — identity-edge tag because FREN was absent from the supplied
    canonical security-master CSV.

The sample manifest is an audit input, not a provider-outcome-selected
subset. No source result was used to alter the sample.

## Source A — Zapi IDX

- access status: `ZAPI_BLOCKED_CREDENTIAL_ABSENT`
- credential status: absent; no key was printed, persisted, or committed
- plan status: `NOT_TESTED_CREDENTIAL_ABSENT`
- requests made: `0`
- rows requested/returned: `50 / 0`
- exact ticker/date rows: `0`
- H/L/C exact agreement: `0 / 0`
- known-Open exact agreement: `0 / 0` comparisons
- missing-Open candidates: `30`
- admissible missing-Open rows: `0`
- rejection breakdown: `NO_PROVIDER_ROW=50`
- identity/date anomalies: `0`
- corporate-action fields: not available because the source was not called

Artifacts:

- `zapi_candidate_rows.csv` —
  `0ab643a79499728a6992df85fe74c9cdf182b285b8ad3b59668569033d7049a0`
- `zapi_row_audit.csv` —
  `3adbd64179068c1ae303d4aaa5b5c68a9908a56c04c1f65eaa666c0aa5d20e`
- `zapi_summary.json` —
  `3215fa87867b6b52444a307f6c349f87bf6f01c5e9d7308e2ddfba6269763d60`

## Source B — Yahoo/yfinance

Yahoo was audited independently with raw OHLC semantics (`auto_adjust=False`)
and adjusted/corporate-action fields retained separately.

- access status: `YAHOO_YFINANCE_ATTEMPTED`
- credential/plan status: `NOT_APPLICABLE / PERSONAL_RESEARCH_ONLY_UNOFFICIAL`
- requests made: `8` ticker-bounded requests (`AADI`, `ALDO`, `BBCA`, `BBRI`,
  `BREN`, `FREN`, `MASA`, `MFIN`)
- sample rows requested / raw rows returned: `50 / 1,035`
- exact ticker/date sample rows: `8 / 50`
- H/L/C exact agreement: `7 / 8 = 87.5%`
- known-Open exact agreement: `4 / 5 = 80.0%` among returned known-Open rows
- missing-Open candidates: `30`
- admissible missing-Open rows: `3`
- missing-Open result: `3` admissible, `27` no provider row
- rejection/preservation breakdown:
  - `FROZEN_CONTRACT_PASS=3`;
  - `EXISTING_OPEN_PRESERVED=4`;
  - `HLC_MISMATCH=1`;
  - `NO_PROVIDER_ROW=42`.
- provider duplicate-key rows: `0`
- identity/date anomalies: `0`
- raw adjusted separation: `true`
- provider request errors explicitly retained:
  - `FREN.JK` — `YFTzMissingError` / no timezone;
  - `MASA.JK` — HTTP 404 plus `YFTzMissingError` / no timezone;
  - `MFIN.JK` — `YFTzMissingError` / no timezone.

The three admissible missing-Open rows were:

- `AADI 2024-12-05`;
- `ALDO 2024-07-08`;
- `BREN 2024-05-06`.

The one H/L/C rejection was the known-answer row `BBCA 2021-08-03`:
Yahoo raw OHLC was `6025 / 6180 / 5985 / 6145`, while the certified panel
OHLC was `30125 / 30900 / 29925 / 30725`. It was rejected and the existing
panel Open was preserved. Known-answer Open exact rows were AADI, ALDO, BBRI,
and BREN; BBCA was not exact.

Artifacts:

- `yahoo_candidate_rows.csv` —
  `f558966789d93bb266503018cc73ead5cc2da5595bdfc29fdf800c0247747c43`
- `yahoo_row_audit.csv` —
  `87757090895b8e31de4fcf994e3b0aa0cf5da59e8d96a05740e6beaf8bfbae53`
- `yahoo_summary.json` —
  `af63fd102046e2d1694b33370e54b77ef0c6bfb9eed9b04fd99eafd3de184dc1`

## Tests and artifact manifest

- full pytest before runtime: `225 passed, 3 pre-existing warnings`
- full pytest after final implementation: `226 passed, 3 pre-existing warnings`
- no test failure
- audit summary:
  `5aab0e1f4ca03918f12d393c79b936326621f709b7ea956cf5541e2e8f936e33`
- artifact manifest:
  `eeca6e2d0bcb126e1bf61092018e3aa893279e90b55aeda58fb1b96f722e1513`

All runtime artifacts remain outside Git at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_tier2_source_audit_v1_20260810`

The prior first pilot output was preserved, unchanged, at the sibling
external backup directory ending in `_prior` before the request-error capture
repair rerun.

## Stop boundary

The pilot found potentially admissible Yahoo evidence for 3 of 30 sampled
missing-Open rows, but Yahoo also showed a known-answer H/L/C incompatibility
and provider gaps/errors for FREN/MASA/MFIN. Zapi remains unaudited because no
local credential was present. Stop for independent ChatGPT review; do not
authorize a bulk backfill from this pilot alone.
