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
| `model_safe_signal_research_panel_1260_final_clean.parquet` | `PARTIAL — FROZEN_ONLY` | Capability/structural audit only; no new-alpha target claim | 981,940 rows; 945 tickers; 2021-04-29–2026-07-31; unique `(ticker,date)`; no outcome-like columns; SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`. Authoritative status permits frozen-baseline reproduction but does not certify new refit/scoring/admission. |
| `model_safe_signal_research_panel_1260.parquet` (frozen V4-X1 input) | `PARTIAL — FROZEN_ONLY` | Existing baseline reproduction only | 981,940 rows; 945 tickers; 1,260 dates; SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` (recorded source hash). The alternate frozen input does not widen new-alpha authorization. |
| `bundle_rows.parquet` from `idx-financial-representation-v2-20260816-v1-run3` | `PARTIAL` | Capability/structural audit only; no scientific alpha claim | 277,244 rows; 729 tickers; 2021-06-02–2026-07-17; unique `(ticker,date)`; parquet SHA-256 `c6004832e651b380161ec216efb2020dddb86419d89c4521f77aeb09335876b`; Financial PIT remains parked/partial and no same-science admission is certified. |
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
| C1 | `residual_reversal_5_v1` | `PENDING` | `BLOCKED — source admission` | `PENDING` | `BLOCKED` | Fixed formula; panel is frozen-only for new alpha claims. |
| C2 | `participation_confirmation_5_v1` | `PENDING` | `BLOCKED — source admission` | `PENDING` | `BLOCKED` | Fixed formula; panel is frozen-only for new alpha claims. |
| C3 | `financial_quality_growth_v1` | `PENDING` | `BLOCKED — source admission` | `PENDING` | `BLOCKED` | Financial PIT source is partial/parked; no same-science admission. |
| C4 | `path_efficiency_reversal_20_v1` | `PENDING` | `BLOCKED — source admission` | `PENDING` | `BLOCKED` | Fixed formula; panel is frozen-only for new alpha claims. |

## Audit trail

- Protocol freeze: committed before any target/label read; tightened after the independent data-admission audit.
- Admission audit: no source currently passes for new-alpha historical outcome claims.
- New feature artifacts: none.
- New outcome access: none.
- New provider/network access: none.
- Protected/canonical/production mutations: none.
