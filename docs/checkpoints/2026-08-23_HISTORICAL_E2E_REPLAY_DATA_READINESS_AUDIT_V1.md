# Historical E2E Paper Replay — Data Readiness Audit V1

Date: 2026-08-23
Branch: `research/idx-historical-e2e-replay-data-readiness-v1`
Source commit: `d49b1540d4e6b29deddc0f47ca0cf7cacc9e3b75`

## Scope

This is an outcome-blind data-readiness audit for the frozen 600-session
Decision V2 development trajectory (`2023-12-28` through `2026-07-17`). It
does not calculate returns, P&L, NAV, performance metrics, targets, labels, or
outcomes, and it does not fit or score a model. No provider or network call was
made.

The audit uses the accepted final clean HLCV/RMV panel, the hash-verified
external Decision V2 structural ledger, the accepted CA event-window ledger,
and the bounded file-only dividend replay. It does not treat the structural
ledger as an execution replay: no 600-session sizing/fill/state artifact was
available.

## Pinned inputs

| Input | Identity | Result |
|---|---|---|
| Decision V2 structural manifest | `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba` | 600 sessions, status `DECISION_V2_MINIMAL_STRUCTURAL_REJECT` |
| Challenger score bytes | `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b` | 172,697 frozen rows; bytes hash-checked only |
| Decision intent ledger | `3ecef4d9faa9044f5d88dba3849fbb92317bf3620ce37fbca4d3b581be5f794d` | 2,584 intent rows |
| Holding-spell ledger | `8a3c649f160a418c427b201490a013ac0bebdc7c7717eb5f59c4efab06af0b6f` | 1,297 spells; 5,693 exposure rows |
| Final clean panel | `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` | 981,940 rows; 945 tickers; 1,260 dates |
| Official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` | 1,260 sessions |
| CA event-window ledger | `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f` | 344,790 rows; source status blocked |
| Bounded dividend offline result | `454213df35c3ffd741cc137c24d502f1fc45cd46e229c1c553852b2418e07aac` | 11 candidates; 7 bounded event records |

## Findings

- Decision V2 produced 2,584 intents: 1,297 buys and 1,287 sells. The
  structural artifact reconstructs 5,693 target ticker/session exposure rows
  across 347 tickers, but contains no NAV, cash, shares, lots, notional, fills,
  or execution-state lineage. It is therefore structural evidence only.
- Clean Close/RMV coverage is complete for the audited exposure rows: 5,693 /
  5,693 current Close and RMV values are present. All 981,940 clean-panel rows
  retain `corporate_action_integrity_verified=True`.
- The clean panel has 95,618 rows with explicit
  `IDX_PUBLIC_STOCK_SUMMARY_OPEN_OPTIONAL`, 439,479 Yahoo-optional rows, and
  446,843 `OPEN_UNAVAILABLE` rows. Only the explicit IDX status is admitted for
  execution-grade Open.
- Buy-order Open coverage is 351 / 1,297 = 27.0625%. The remaining 946 buy
  intents are unavailable or non-official. Across dates with buy orders, 106
  dates have all buy Opens ready; the median per-date buy-Open coverage is 0%
  and the minimum is 0%.
- Holding-input readiness is 1,350 / 5,693 = 23.7133%. Current HLC/RMV is
  complete, but next-session official Open is missing/non-official for 4,343
  holding rows. Only 69 of 600 signal dates have all holding rows ready.
- CA continuity is explicitly resolved for 4,471 / 5,693 exposure rows, with
  1,222 unresolved. The policy is fail-closed: absence of a row does not prove
  absence of a corporate action, and unresolved effective dates remain
  unresolved.
- The bounded dividend corpus has 7 admitted event records across BBCA, BBRI,
  and TLKM. Two holding spells overlap a bounded certified event (BBCA
  `2025-11-27..2025-12-08`, BBRI `2025-12-23..2026-01-02`). The other 1,295
  spells remain `NO_MARKET_WIDE_NO_EVENT_PROOF`; no market-wide PIT dividend
  ledger or position/entitlement history exists.
- No complete full-economic session passes. The longest full-economic strict
  contiguous segment is zero sessions. No 600-session Sizing V1 / Execution V1
  artifact bundle was found.

## Verdict

`HISTORICAL_E2E_REPLAY_BLOCKED_BY_DATA`

This verdict is about replay readiness, not model quality. The smallest safe
next step is to obtain a separately accepted, immutable, outcome-blind bundle
containing execution quantities/state, official Open coverage, market-wide
PIT corporate-action continuity, and market-wide PIT dividend/no-event
evidence. Do not backfill missing values, infer no-event states, or run a
historical performance replay from this audit.

## Reproducibility output

External output root:
`D:\Documents\Project\idx-historical-e2e-replay-readiness-20260823-v6`

The root contains the requested inventories, exposure/trajectory ledgers,
order/holding/RMV/Open coverage, CA/dividend gaps, per-date strict gate, and
`summary.json` / `MANIFEST.json`. Final audit manifest SHA:
`86304dac2226f40e58f18ea302f709106b67609165b4bb488bda4c5d7b4564e7`.

All output files remain external and are not committed to Git.

## Guard confirmation

`labels_loaded=false`, `target_values_accessed=false`, `returns_loaded=false`,
`r5_loaded=false`, `r10_loaded=false`, `pnl_computed=false`,
`protected_outcomes_accessed=false`, `provider_calls=false`,
`network_calls=false`, `model_fit=false`, and `model_scoring=false`.

