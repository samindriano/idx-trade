# Handoff

from: ChatGPT / MAIN external research-audit thread
to: Codex WORKTREE agent
task_id: IDX-OPEN-BACKFILL-TIER2-AUDIT
model_used: Luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: e8a76055b267727854d33d49b5def1a661e0f86b
branch: data/idx-open-backfill-tier2-audit-v1
head_commit: e8a76055b267727854d33d49b5def1a661e0f86b
scope: bounded 50-row historical Open source audit only
files_changed: implementation/tests/docs needed for pilot audit only

## Question

Can Zapi IDX and/or Yahoo Finance supply genuinely additional raw historical Open evidence for currently-null panel rows while preserving the frozen H/L/C semantics and known-answer consistency?

## Required first reads

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/OPEN_BACKFILL_POLICY_V1.md`
4. `docs/OPEN_BACKFILL_TIER2_SOURCE_AUDIT_V1.md`
5. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_WILDAN_RUNTIME.md`
6. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_TIER2_AUDIT_READY.md`

Verify worktree root, detached/worktree HEAD, starting branch, remote branch head, and clean state before edits.

## Immutable panel

Use the exact existing local panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Expected SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Do not modify it.

## Implementation task

Implement the smallest deterministic pilot harness needed to:

1. construct and hash the frozen adversarial sample described in `docs/OPEN_BACKFILL_TIER2_SOURCE_AUDIT_V1.md`;
2. probe Zapi IDX first when `ZAPI_API_KEY` exists locally;
3. never print/store the secret key;
4. classify missing credential as `ZAPI_BLOCKED_CREDENTIAL_ABSENT` rather than silently skipping;
5. classify plan-gated access separately from data-quality failure;
6. audit Yahoo/yfinance independently even if Zapi is blocked;
7. preserve raw provider OHLC fields separately from panel values;
8. calculate exact admission/rejection diagnostics using the frozen rules;
9. write runtime outputs outside Git;
10. produce a concise machine-readable summary with artifact hashes.

Prefer reuse of existing repository provenance/storage/secondary-witness utilities. Do not create a broad new framework if a bounded module suffices.

## Deterministic sample

Use a fixed seed and deterministic sorted candidate universe. Do not choose rows after seeing provider results.

Target approximately 50 unique rows satisfying the frozen strata. If a requested edge-case stratum does not have enough factual rows in available repository/local evidence, report the shortfall instead of inventing rows.

Save the exact sample manifest outside Git and hash it.

## Zapi

Public docs indicate `finance:idx / stock-summary` supports historical `date`, optional ticker `code`, and up to 1000 rows. Free accounts exist, but endpoint `minPlan` must be empirically established.

- Read key only from `ZAPI_API_KEY`.
- Do not create or request credentials programmatically.
- Do not bypass plan gating.
- Keep requests bounded to the pilot.
- Record HTTP/status/error class without exposing auth material.

If no key exists, continue with Yahoo and report Zapi as blocked.

## Yahoo/yfinance

Treat as an unofficial personal-research provider candidate only.

- fetch raw daily OHLCV with auto-adjust disabled;
- do not substitute Adj Close into raw OHLC;
- preserve any corporate-action fields separately;
- compare exact raw H/L/C against certified panel rows;
- score known-answer Open separately from missing-Open admissibility.

## Tests

Add tests for at least:

- deterministic sample selection;
- no overwrite of existing Open;
- exact H/L/C gate;
- Open positive/in-range gate;
- Zapi missing-key blocked classification;
- plan/access failure classification distinct from source-data rejection;
- Yahoo adjusted/raw separation;
- secret redaction from summaries/logs.

Run full pytest before runtime and after any implementation changes.

## Runtime output directory

Create a new external directory under the existing runtime root, for example:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_tier2_source_audit_v1_20260810`

Do not commit runtime artifacts.

## Required report

For each source report:

- access status;
- credential/plan status;
- requests made;
- sample rows requested/returned;
- exact H/L/C match rate;
- known-existing-Open exact agreement rate;
- missing-Open candidate count;
- admissible missing-Open count;
- rejection breakdown;
- identity/date/corporate-action anomalies;
- raw/sample/summary artifact hashes.

Also report immutable panel re-hash before/after runtime.

## Prohibited

- no bulk 446,843-row backfill;
- no direct IDX scraping/crawling;
- no TradingView/Investing.com ingestion;
- no source averaging/majority vote;
- no synthetic/forward-filled Open;
- no threshold relaxation after inspecting outcomes;
- no Stage-5 rerun;
- no Ranking V2 changes;
- no execution-PnL/paper/live trading;
- no main merge;
- no force push/rebase/history rewrite.

## Completion

After runtime, document only factual results in a new dated checkpoint and update the handoff status. Push the resulting documentation/code commit as a fast-forward to `data/idx-open-backfill-tier2-audit-v1` only if the remote branch has not advanced; otherwise stop and report the detached HEAD commit for reconciliation.

Then STOP for independent ChatGPT review.