# IDX-Trade Alpha Research — ChatGPT Handoff V3

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`  
Branch: `codex/alpha-available-data-20260919`  
Latest commit: `f2b763333e8925a02dc60f313aabbfdb3b3a991c`
External staging root: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Jawaban singkat

Tidak, riset tidak berhenti total. Yang masih diblokir adalah historical
predictive evaluation karena Data QA belum mengadmit population completeness,
PIT/as-of, issuer identity, corporate-action/price basis, revision/vintage,
dan H5/H10. Pre-admission, outcome-blind structural research masih berjalan di
lane terpisah ini.

Tidak ada perubahan pada `origin/main`, canonical/incumbent model, production
data, capture/cloud/R2, scheduler, telemetry, provider/network, atau protected
target/outcome.

## Status kandidat sekarang

| Candidate | Support | Top-30 turnover | Status |
|---|---:|---:|---|
| C1 residual reversal 5 | `295,243 / 310,761` (`95.0065%`) | `42.15%` | `FUTURE_RESEARCH`; CA/PIT fragility highest |
| C2 participation confirmation 5 | `310,761 / 310,761` (`100%`) | `32.91%` | `FUTURE_RESEARCH` |
| C3 financial quality/growth | `30,994` rows; `278` usable dates | `10.93%` | `BLOCKED`; financial/PIT support sparse |
| C4 path-efficiency reversal 20 | `310,323 / 310,761` (`99.8591%`) | `23.70%` | `FUTURE_RESEARCH / ECONOMIC_CAUTION` |
| H-LIQ-01 | `155,679` finite rows; diagnostic only | `10.306%` baseline | `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 |

Base friction figures are frozen structural proxies, not realized P&L. No
candidate has a predictive, OOS, IC/ICIR, or incumbent-superiority claim.

## Apa yang sudah didapatkan

1. Corrected decision universe: `310,761` eligible rows across `711` tickers.
   C1/C2/C4 have broad structural support; C3 is blocked by sparse financial
   and PIT capability.
2. Causal/structural checks: prior-only shifts, future-row mutation isolation,
   key uniqueness, official-session masks, rank bounds, and source-hash checks
   passed. These are not proof of full historical PIT or CA authority.
3. Independent structural-lab replay recomputed the full candidate and pairwise
   maps and passed `PASS_INDEPENDENT_SOURCE_REPLAY`, `mismatch_count=0`.
4. Phase-Q red-team reviews covered causal/PIT/identity/CA, economics/
   concentration/liquidity, and combinations/H-LIQ. No new candidate was
   admitted.
5. H-LIQ-01 is structurally distinct from C2 on average, but conditional
   dependence rises in the top-value bucket. A fixed size-neutral diagnostic
   reduced selected bottom-value Q25 exposure from `39.672%` to `14.983%`, but
   raised mean Top-30 turnover from `10.306%` to `20.785%`; hence no C5.
6. C1+C4 has the lowest tested combination turnover at `34.85%`, but daily
   Spearman is about `0.8499`; this is not evidence of incremental alpha.
7. Capacity stress used only `regular_market_value` as a proxy. It sharpens
   implementation caution but does not establish ADV, spreads, fills, or
   executable capacity.
8. Corporate-action forensic work verified the retained `1,657/1,657` HLC
   overlay and replay stability. `188` unresolved non-stable scale rows and
   open-price residuals keep CA/PIT admission blocked.

9. Independent capacity-tail review found C1 median/q95/max Top-30 turnover
   `40.00%/56.67%/66.67%`, C2 `33.33%/50.00%/63.33%`, and C4
   `23.33%/36.67%/46.67%`; sessions above 50 bps were `220/599`, `60/599`,
   and `1/599`. C4's low mean turnover is offset by bottom-value Q1 exposure
   `34.46%`; this is implementation caution, not capacity proof.
10. H-LIQ-01 remains distinct from C1/C4 but shares a persistent participation
    component with C2. Its bottom-value Q1 share is `39.67%`, and its early-to-
    late Q1 share moves `51.3%` to `29.5%`; retain no-C5 status.
11. A bounded local-data inventory found `Dataset-Saham-IDX` (external commit
    `bc0ac771`, `1,014` CSVs, `1,146,324` rows, 2019-07-29–2025-02-21). It is
    `BLOCKED`: no row-level knowledge-time/vintage field, 56 duplicate ticker
    groups including 11 non-identical copies, and unclear CA/identity/source
    selection. Its static sector/listing files are `METADATA_ONLY`.

## Latest CA exposure attribution

The latest read-only counterfactual replay exactly reproduced stored baseline
scores for C1/C2/C4. It classified changed `(ticker,date)` rows against the
188-row unresolved artifact:

| Candidate | Direct score/rank changes | Spillover score/rank changes | Direct / spillover changed Top-30 slots | Mean Top-30 overlap | Minimum |
|---|---:|---:|---:|---:|---:|
| C1 | `66 / 65` | `82,291 / 31,281` | `18 / 1,172` | `98.2618%` | `36.6667%` |
| C2 | `66 / 65` | `457 / 8,929` | `38 / 96` | `99.8140%` | `83.3333%` |
| C4 | `66 / 62` | `319 / 9,877` | `12 / 52` | `99.9112%` | `86.6667%` |
| H-LIQ-01 diagnostic | `66 / 63` | `317 / 10,247` | `16 / 174` | `99.7363%` | `90.0000%` |

Meaning: C1's score sensitivity is mostly cross-sectional spillover, while
C2/C4 have smaller but visible direct-row sensitivity. “Direct” and
“spillover” are preregistered row classifications, not causal proof and not
an admitted correction. Full evidence is in
`2026-09-19_ALPHA_CA_EXPOSURE_ATTRIBUTION_RESULT_V1.md`.

## What remains blocked

- Historical PIT/as-of and population completeness admission.
- Issuer/ISIN continuity and complete corporate-action price-basis authority.
- Revision/vintage authority and real capacity fields.
- Protected H5/H10/forward outcomes, target ranking, IC/ICIR/OOS, incumbent
  comparison, refit, promotion, or model deployment.

## Safe next steps

Continue only with bounded, outcome-blind audits of local evidence: source
admission, issuer/CA/PIT provenance, capacity clarification, and documentation
integrity. The highest-value unblock is an independent Data QA admission
artifact. If no new admissible evidence appears, stopping is reasonable; there
is no justification to open target data merely to force a winner.

## Primary documents

- `2026-09-19_ALPHA_CA_EXPOSURE_ATTRIBUTION_RESULT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`
- `2026-09-19_ALPHA_STRUCTURAL_LAB_REPLAY_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_SIZE_NEUTRAL_RESULT_V1.md`
- `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
- `2026-09-19_ALPHA_CAPACITY_STRESS_RESULT_V1.md`
- `2026-09-19_ALPHA_PHASE_FRONTIER_AUDIT_RESULT_V1.md`
- `2026-09-19_ALPHA_REENTRY_PACKET_AUDIT_RESULT_V1.md`

## Hard boundary

No protected outcome was opened, no provider/network scrape was performed, no
canonical or active dataset was changed, and no telemetry/capture/cloud state
was touched. The lane remains structurally productive but predictive proof is
not yet authorized.
