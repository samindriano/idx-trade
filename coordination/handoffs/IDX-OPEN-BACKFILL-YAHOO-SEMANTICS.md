# Handoff

from: ChatGPT / MAIN architecture review
to: Codex Luna xhigh
task_id: IDX-OPEN-BACKFILL-YAHOO-SEMANTICS
model_used: Luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: d00c8d74f2728836ed842ba545034e07b10e5405
branch: data/idx-open-backfill-yahoo-semantics-v1
head_commit: resolve latest remote HEAD before work
scope: bounded Yahoo split-semantics + broad-coverage historical Open audit only
files_changed: implementation/tests/runtime docs required for this audit only

## Read first

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/OPEN_BACKFILL_POLICY_V1.md`
4. `docs/OPEN_BACKFILL_TIER2_SOURCE_AUDIT_V1.md`
5. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_TIER2_SOURCE_AUDIT_RUNTIME.md`
6. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_TIER2_INDEPENDENT_REVIEW.md`
7. `docs/OPEN_BACKFILL_YAHOO_SEMANTICS_V1.md`
8. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_SEMANTICS_READY.md`

## Immutable input

Use the exact 1260-session panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Initial unresolved Open rows: `446,843`.

## Task

Implement and run the smallest deterministic audit harness that satisfies `docs/OPEN_BACKFILL_YAHOO_SEMANTICS_V1.md`.

Minimum sample requirements:

- >=120 unique tickers;
- >=240 ticker/date rows;
- both known-existing-Open and missing-Open rows;
- split/reverse-split and non-split strata;
- broad date/coverage distribution;
- preserve exact sample manifest/hash before Yahoo runtime.

Use Yahoo/yfinance raw OHLC only with `auto_adjust=False`.

Direct admission remains exact certified H/L/C + finite positive in-range Open.

For split-scale diagnostics, use only independently verified corporate-action evidence already present in repository artifacts/contracts or a separately documented authoritative source. Never derive/fix a split factor solely from Yahoo-vs-panel ratios. One verified cumulative factor must transform all OHLC consistently and transformed H/L/C must match certified H/L/C exactly.

Never use `Adj Close` or dividend adjustment as execution evidence.

Do not modify immutable panel or create a bulk backfilled derivative yet.

## Tests

Add tests for at least:

- deterministic >=120-ticker sample selection;
- sample outcome independence;
- direct raw admission unchanged;
- independently verified split-factor reconstruction;
- rejection when split factor is absent/unverified;
- rejection when factor fixes only some OHLC fields;
- no dividend/Adj-Close substitution;
- existing Open preservation;
- provider error/no-row fail-closed behavior;
- artifact/sample hashing determinism.

Run full pytest before and after implementation.

## Runtime outputs

Keep artifacts outside Git under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_semantics_v1_20260810`

Report:

- sample rows/unique tickers/hash;
- split vs non-split strata counts;
- Yahoo ticker coverage and exact-date coverage;
- direct raw H/L/C exact and known Open exact;
- direct admissible missing Open;
- split-scale mismatch count;
- independently reconstructable rows/tickers;
- reconstructed H/L/C exact and known Open exact;
- reconstructed admissible missing Open;
- provider error breakdown including FREN/MASA/MFIN if selected;
- early/mid/late panel coverage;
- optional potential-recovery estimate for the 446,843 gap, with explicit assumptions only;
- panel hash before/after;
- all runtime artifact SHA-256 hashes.

## Prohibited

No direct IDX scraping/crawling. No TradingView/Investing ingestion. No Zapi expansion in this task. No source averaging. No synthetic Open. No bulk write. No Ranking V2/Stage 5 changes. No execution PnL. No paper/live trading. No main merge. No force push/rebase.

After runtime, write factual dated checkpoint/handoff update, push only fast-forward if remote has not advanced, then STOP for independent ChatGPT review.
