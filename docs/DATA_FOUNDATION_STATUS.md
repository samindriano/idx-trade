# IDX-Trade — Data Foundation Status

Date: 2026-08-12 (Asia/Jakarta)

This file is the short dashboard for independent data-foundation lanes. Detailed methodology, evidence, hashes, tests, and blockers remain in each lane's spec/checkpoint/handoff and draft PR.

| Lane | PR | State | Current verdict / blocker | Next action |
|---|---:|---|---|---|
| PIT IDX-IC sector history | #17 | PARKED | `5 ready / 3 blocked`; 2022/2023 canonical archive unresolved; 2026 effective-date evidence unresolved | Reopen only if new official archive/evidence appears |
| Historical Universe V1 | #18 | PARKED / FAIL-CLOSED | `FAIL_NO_COMPLETE_WINDOW`; public relisting path cannot prove complete lifecycle census | Reopen only with stronger official historical listing/relisting evidence |
| Corporate Actions V1 | #19 | PARKED / DISCOVERY-ONLY | `SPLIT_METADATA_DISCOVERY_ONLY_CANONICAL_PROMOTION_FAIL_CLOSED`; official metadata useful, but effective-session semantics and provider price alignment are insufficient for canonical adjustment | Do not adjust prices; reopen only for document-level effective-session work |
| Financial Statements PIT V1 | #20 | PARKED / CONDITIONAL | `CONDITIONAL_PASS_SOURCE_DISCOVERY_ONLY_NO_GO_FOR_COMPLETE_FINANCIAL_PIT_ACQUISITION`; recent publication joins work, but public announcement retention is ~3 years and revision completeness is unproven | Keep recent sample methodology; do not bulk acquire 2021–2026 until archive/revision coverage is solved |
| Historical OPEN recovery | #11–#15 | ACTIVE IN SEPARATE LANE | Dedicated OPEN source/backfill work continues separately | Do not mix into these data-foundation lanes |

## Current data-priority frontier

The next independent data lane is **Foreign Flow V1**.

Goal: determine whether official IDX/Zapi data can provide a historically consistent per-ticker foreign buy/sell/net-flow series with defensible date, unit, coverage, and provenance semantics over the research window.

Do not treat this dashboard as authorization to alter the frozen V3-B model, access realized forward outcomes, modify OPEN work, or start execution/PnL/paper/live trading.
