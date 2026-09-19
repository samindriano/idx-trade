# Alpha Research Program — Ledger V1

Lane: `codex/alpha-available-data-20260919`
Protocol: `docs/checkpoints/2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md`
Status: `OPEN — STAGE A NOT STARTED`

This ledger is append-only within the isolated research lane. Every admitted,
rejected, failed, or blocked candidate must remain visible. No result is a
production or prospective claim.

## Source and artifact admission inventory

| Source/artifact | Classification | Permitted use | Reason / boundary |
|---|---|---|---|
| `model_safe_signal_research_panel_1260_final_clean.parquet` | `ADMISSIBLE` for outcome-blind causal feature construction | C1, C2, C4 and structural audits | 981,940 rows; 945 tickers; 2021-04-29–2026-07-31; unique `(ticker,date)`; no outcome-like columns; SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`; exact PIT/universe admission still must be bound to the authoritative decision mask before target claims. |
| `bundle_rows.parquet` from `idx-financial-representation-v2-20260816-v1-run3` | `ADMISSIBLE` for PIT feature construction on complete, provenance-valid selected rows | C3 structural and, after protocol freeze, fixed historical comparison | 277,244 rows; 729 tickers; 2021-06-02–2026-07-17; unique `(ticker,date)`; SHA-256 `c6004832e651b380161ec216efb2020dddb86419d89c4521f77aeb09335876b`; no outcome-like columns; no partial-bundle fallback. |
| Frozen historical target ledger / challenger scores | `CONTROLLED — CLOSED UNTIL PROTOCOL FREEZE` | Fixed six-fold historical development/OOS only after this protocol is committed | Forward target data is not opened for discovery/tuning before this contract; not a fresh prospective holdout. |
| Protected prospective outcome vault/counter | `BLOCKED` | None | Explicitly out of scope; no access, reset, archive, or mutation. |
| Zapi IDX/TradingView/Investing/Stockbit probes | `PARTIAL` or `UNKNOWN` by source contract | Capability assessment only | Staged probe evidence is not automatically PIT/admission evidence; Investing identity/scale is ambiguous, Stockbit historical pagination is unestablished, and no new probe is authorized here. |
| Official IDX current/monthly snapshots | `PARTIAL` | Capability/schema assessment only | Current/monthly availability and common zero-open behavior do not establish historical PIT transition authority for this lane. |
| Foreign-flow representation path not found at the prior expected location | `UNKNOWN` | None for scientific claims | Do not revive or broaden historical source discovery merely to fill this gap. |

## Prior work reconstructed

| Prior family / artifact | Recorded lesson | Effect on this lane |
|---|---|---|
| Foreign Flow V2 Core | Exact additive H10 eight-feature challenger failed; family not closed for all mechanisms/horizons. | No duplicate additive rescue; only genuinely distinct C2/C3-style information is eligible. |
| Financial Alpha V1 / exact financial-event candidate | Exact prior formulations failed or were effectively flat; family not automatically closed. | C3 is a fixed quality/growth composite, not a post-result rescue of the prior event formula. |
| Breakout event | Fixed event candidate underperformed incumbent. | C2 is not a breakout-event variant; overlap and failure remain visible. |
| Effort-vs-result Stage A | Causal construction passed, but range/effort was highly correlated with relative volume and Stage B was not admitted. | C2 must disclose overlap and cannot be tuned to rescue the family. |
| Price-trend structural audit | Structural availability/overlap evidence only, no performance claim. | C1/C4 require outcome comparison and orthogonality gates; structural rank is not alpha proof. |
| Historical source/tombstone lanes | Blocked/ambiguous sources are not canonical evidence. | No reopening of blocked TradingView/Investing/Open approximations. |

## Candidate ledger

| ID | Candidate | Stage A | Historical comparison | Robustness/economics | Verdict | Reason |
|---|---|---|---|---|---|---|
| C1 | `residual_reversal_5_v1` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Fixed formula in frozen protocol; no outcome read yet. |
| C2 | `participation_confirmation_5_v1` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Fixed formula in frozen protocol; no outcome read yet. |
| C3 | `financial_quality_growth_v1` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Fixed formula in frozen protocol; no outcome read yet. |
| C4 | `path_efficiency_reversal_20_v1` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Fixed formula in frozen protocol; no outcome read yet. |

## Audit trail

- Protocol freeze: pending commit of this file before any target/label read.
- New feature artifacts: none.
- New outcome access: none.
- New provider/network access: none.
- Protected/canonical/production mutations: none.
