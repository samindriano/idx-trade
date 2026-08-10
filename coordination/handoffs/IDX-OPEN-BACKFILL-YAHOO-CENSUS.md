# Handoff

from: ChatGPT independent reviewer
to: Codex local runtime worker
task_id: IDX-OPEN-BACKFILL-YAHOO-CENSUS
model_used: GPT-5.6 Sol
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: fb6f952e7f0b9b7a39ca9baa102afb85a33c2d11
branch: data/idx-open-backfill-yahoo-census-v1
head_commit: c64668f2e72286f48d5e846bd960626dff8611ff
scope: full-universe Yahoo historical Open recovery census; derivative candidate only
files_changed: implementation/tests/docs required for census only

## Read first

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/OPEN_BACKFILL_POLICY_V1.md`
4. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_SEMANTICS_RUNTIME.md`
5. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_SEMANTICS_INDEPENDENT_REVIEW.md`
6. `docs/OPEN_BACKFILL_YAHOO_CENSUS_V1.md`
7. this handoff

## Immutable input

Panel:
`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Baseline unresolved Open: `446,843`.

## Authorization

Implement and run the smallest robust, resumable full-universe Yahoo census consistent with `docs/OPEN_BACKFILL_YAHOO_CENSUS_V1.md`.

Use raw Yahoo OHLC only with `auto_adjust=False`. Existing non-null Open is immutable.

Direct missing-Open admission requires exact ticker/date and exact certified H/L/C equality plus positive/in-range raw Open.

A split-scale path is allowed only with independently verified pre-existing official split/reverse-split factor evidence. Never infer a factor from Yahoo/panel price ratios. Transformed H/L/C must still match certified H/L/C exactly.

## Runtime engineering requirements

- full panel ticker universe only;
- full 2021-04-29 -> 2026-07-31 window;
- resumable external raw cache;
- deterministic cache/manifest naming;
- bounded concurrency or serial requests with retry/backoff;
- preserve and report provider failures explicitly;
- do not retry forever;
- do not silently change providers;
- do not use Adj Close/dividends as execution-price reconstruction;
- do not scrape IDX;
- do not use TradingView/Investing/Zapi in this task;
- preserve source and cache hashes;
- no credentials committed.

Implement focused tests for at least:

- immutable existing Open;
- direct H/L/C exact gate;
- direct accepted missing Open;
- direct mismatch rejection;
- verified split-scale acceptance;
- unverified/inferred factor rejection;
- raw/adjusted separation;
- cache idempotence/resume;
- provider error preservation;
- derivative provenance;
- deterministic summary/manifest behavior where applicable.

Run full pytest before and after implementation.

## External output root

Use:
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

Keep raw provider cache, derivative data, diagnostics, summaries and manifests outside Git.

## Required output

Report at minimum:

- branch + exact runtime code HEAD;
- pytest before/final;
- immutable panel SHA before/after;
- tickers attempted / returned / unsupported;
- provider requests / retries / errors;
- raw-cache count + manifest hash;
- provider rows returned;
- full exact ticker/date coverage;
- known-existing-Open H/L/C exact count/rate;
- known-existing-Open exact Open count/rate;
- direct missing-Open accepted;
- verified split-scale missing-Open accepted;
- total accepted fills;
- initial null `446,843` and final null;
- actual gap closed count/percentage;
- result by year;
- rejection histogram;
- provider gap/error ticker summary including FREN/MASA/MFIN/PURE if applicable;
- temporal degradation summary;
- derivative panel SHA;
- provenance/manifest SHA;
- `execution_grade_promoted=false`.

The derivative panel may contain accepted fills, but the immutable input panel must never change.

## Prohibited

- no Stage-5 rerun;
- no Ranking V1/V2 changes;
- no Probability work;
- no execution-PnL analysis;
- no paper/live trading;
- no broker integration;
- no main merge;
- no force push/rebase;
- no execution-grade promotion;
- no post-result relaxation of admission rules.

After runtime, write a factual dated checkpoint and update this handoff. Push fast-forward only if the remote branch has not advanced. Then STOP for independent ChatGPT review.
