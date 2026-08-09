# Handoff

from: ChatGPT / MAIN external research-audit thread
to: Codex WORKTREE agent
task_id: IDX-OPEN-BACKFILL-TIER2-AUDIT
model_used: Luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 5c85cc2e2d62e5ab35c178425e689a00e60117f4
branch: data/idx-open-backfill-tier2-audit-v1
head_commit: 7d6e0cd
scope: bounded 50-row historical Open source audit only
files_changed: src/idx_trade/tier2_open_audit.py; tests/test_tier2_open_audit.py; docs/checkpoints/2026-08-10_OPEN_BACKFILL_TIER2_SOURCE_AUDIT_RUNTIME.md; this handoff

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

## Runtime result

status: OPEN_BACKFILL_TIER2_SOURCE_AUDIT_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW
runtime_output:
  D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_tier2_source_audit_v1_20260810
panel_sha256_before: 67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76
panel_sha256_after: 67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76
sample_sha256: e1dbeb40969508108ec480a32c4a22a07d194d850986883fd4ee4b5ae1b79385
sample_rows: 50
sample_roles: 20 known-existing; 25 missing with Wildan row; 5 missing without Wildan row
zapi: BLOCKED_CREDENTIAL_ABSENT; requests=0; admissible_missing_open=0
yahoo: requests=8; raw_rows=1035; exact_sample_rows=8; HLC=7/8; known_open=4/5; admissible_missing_open=3
yahoo_request_errors: FREN/MASA/MFIN yfinance timezone/404 diagnostics retained
admissible_yahoo_rows: AADI 2024-12-05; ALDO 2024-07-08; BREN 2024-05-06
known_answer_hlc_rejection: BBCA 2021-08-03 split-scale mismatch; existing panel Open preserved
execution_grade_promoted: false
pytest: 226 passed, 3 pre-existing warnings
audit_summary_sha256: 5aab0e1f4ca03918f12d393c79b936326621f709b7ea956cf5541e2e8f936e33
artifact_manifest_sha256: eeca6e2d0bcb126e1bf61092018e3aa893279e90b55aeda58fb1b96f722e1513

findings:
- Tier-2 sample construction is deterministic and outcome-independent.
- Zapi could not be empirically plan-tested because ZAPI_API_KEY was absent.
- Yahoo supplied 3 rows passing the unchanged H/L/C/raw-Open/range contract,
  but the pilot also exposed one known-answer H/L/C incompatibility and
  provider gaps/errors for FREN, MASA, and MFIN.

decisions_made:
- Existing panel Open values remain immutable.
- No candidate was written into the immutable panel or a derivative panel.
- No bulk backfill, direct IDX scrape, TradingView/Investing ingestion,
  Stage-5 rerun, Ranking V2 change, execution-PnL claim, modelling, or main
  merge was performed.

decisions_needed:
- Independent ChatGPT review must decide whether either source merits a new,
  separately authorized bounded follow-up. This pilot alone does not authorize
  bulk Tier-2 ingestion.

blocking_risks:
- Zapi credential/Free-plan access remains untested.
- Yahoo raw semantics are not uniformly compatible with the certified panel;
  the BBCA known-answer mismatch is a concrete rejection.
- The 3 admissible Yahoo rows are source-audit candidates only, not certified
  execution-grade fills.

validation_run:
- baseline full pytest: 217 passed, 3 warnings
- implementation full pytest: 225 passed, 3 warnings
- final full pytest: 226 passed, 3 warnings
- immutable panel hash verified before and after runtime

recommended_next_action:
STOP for independent ChatGPT review. Do not bulk-fetch the 446,843-row gap,
do not promote execution grade, and do not start modelling or Stage 5.
