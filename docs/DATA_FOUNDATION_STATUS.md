# IDX-Trade — Data Foundation Status

Date: 2026-08-12 (Asia/Jakarta)

This file is the short dashboard for independent data-foundation lanes. Detailed methodology, evidence, hashes, tests, and blockers remain in each lane's spec/checkpoint/handoff and draft PR.

| Lane | PR | State | Current verdict / blocker | Next action |
|---|---:|---|---|---|
| PIT IDX-IC sector history | #17 | PARKED | `5 ready / 3 blocked`; 2022/2023 canonical archive unresolved; 2026 effective-date evidence unresolved | Reopen only if new official archive/evidence appears |
| Historical Universe V1 | #18 | PARKED / FAIL-CLOSED | `FAIL_NO_COMPLETE_WINDOW`; public relisting path cannot prove complete lifecycle census | Reopen only with stronger official historical listing/relisting evidence |
| Corporate Actions V1 | #19 | PARKED / DISCOVERY-ONLY | `SPLIT_METADATA_DISCOVERY_ONLY_CANONICAL_PROMOTION_FAIL_CLOSED`; official metadata useful, but effective-session semantics and provider price alignment are insufficient for canonical adjustment | Do not adjust prices; reopen only for document-level effective-session work |
| Financial Statements PIT V1 | #20 | PARKED / CONDITIONAL | `CONDITIONAL_PASS_SOURCE_DISCOVERY_ONLY_NO_GO_FOR_COMPLETE_FINANCIAL_PIT_ACQUISITION`; recent publication joins work, but public announcement retention is ~3 years and revision completeness is unproven | Keep recent sample methodology; do not bulk acquire 2021–2026 until archive/revision coverage is solved |
| Foreign Flow V1 | #22 | PARKED / SOURCE-USABLE | `SOURCE_AND_UNIT_USABLE_BUT_PIT_TIMING_UNRESOLVED_COVERAGE_INCOMPLETE`; shares/buy/sell/net semantics and sampled IDX parity pass, but source exposes only session date with no first-publication timestamp and no certified complete historical window | Preserve contract; no historical PIT bulk acquisition. A future forward EOD capture may establish actual availability timing prospectively |
| Ownership / KSEI V1 | #23 | PARKED / SOURCE-USABLE | `CONDITIONAL_SOURCE_READY_PIT_BLOCKED`; per-security local/foreign ownership and investor categories cross-check exactly against direct KSEI, with sampled archive availability from 2021-12 through 2026-07, but no timezone-aware publication timestamp or immutable revision lineage | Preserve source contract and archive evidence; no PIT materialization or bulk acquisition until timing/version policy is solved |
| Historical OPEN recovery | #11–#15 | ACTIVE IN SEPARATE LANE | Dedicated OPEN source/backfill work continues separately | Do not mix into these data-foundation lanes |

## Current data-priority frontier

The next independent data lane should be **Market / Index / Breadth History V1**.

Goal: determine whether official IDX/Zapi sources can provide stable historical market-level context over the research window, including IHSG/index state, market breadth/participation, turnover/value/frequency and other session-level aggregates that can later support market-regime context without relying on current-survivor reconstruction.

Priority source families to inspect first:

- IDX index summary/history and Trading Summary raw endpoints;
- market-wide advancing/declining/unchanged or equivalent breadth fields if officially exposed;
- total value/volume/frequency and other exchange-session aggregates;
- representative Zapi/direct-IDX parity and historical revision behavior.

Do not treat this dashboard as authorization to alter the frozen V3-B model, access realized forward outcomes, modify OPEN work, or start execution/PnL/paper/live trading.
