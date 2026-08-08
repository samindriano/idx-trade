# Handoff

from: MAIN / DATA
to: MAIN
task_id: IDX-DATA-002
model_used: Luna xhigh (root; workers were not required)
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 3a7d7d4a47d9f69c9e285bf5c0b4292e392beed7
branch: codex/idx-trade-orchestrator
head_commit: f2b76e0b3ec0f9f3c5cada0db20cd72f9075c231
scope: Execute the IDX local DATA GATE only: official sessions, listing/delisting, official suspension discovery and parsing, Yahoo raw EOD backfill, revision guards, corporate-action/raw semantics, and adversarial QA. No modeling, scoring, paper trading, or live trading.

## Files changed

- `src/idx_trade/providers/idx_sessions.py`: use the current official IDX `DigitalStatistic/GetApiData` JSON endpoint by default; retain the HTML parser as an explicit compatibility/test path; keep month and weekend checks fail-closed.
- `src/idx_trade/session_backfill.py`: record the official session-data API URL in the source manifest.
- `tests/test_idx_sessions_provider.py`: cover official JSON parsing, API URL construction, and default JSON fetching.
- `tests/test_storage.py`: separate raw-close and vendor-adjusted-close revision fixtures and cover each conflict independently.

Runtime evidence was kept outside Git under the local `idx-trade-data-gate-20260808` evidence directory. No runtime data, parquet files, PDFs, credentials, or user-specific paths were committed.

## Findings

### Validation

- Focused provider/backfill tests: `10 passed`.
- Full project suite after the final executable change: `44 passed`.
- `git diff --check`: passed.

### Official IDX exchange sessions

- The original HTML parser was stale: the official page returned empty client-rendered tables. The official page bundle identified `primary/DigitalStatistic/GetApiData` with `LINK_TABLE_DAILY_TRADING_INVESTOR_FOREIGN`; the provider now uses that endpoint.
- June 2026: HTTP 200, 20 official sessions, `2026-06-02` through `2026-06-30`, no weekend dates. Raw API SHA-256: `4e42a45156d8a95974717ab65b98b8f65dc1686f7d495eadbeeb685c656d30f2`. Canonical session-list SHA-256: `96843407e2190e63ec037fdd35c6aa0c1cf98e28b230cea9c95a58806262a5a4`.
- July 2026: HTTP 200 but official `data=[]`; the run records an explicit month error and does not substitute Yahoo or JCI. Raw API SHA-256: `68e9e3b7c16db04d68d4bb86f22abe1212d9d0bcb85a4f33c42a1465f19c0a25`.
- The response exposed retrieval headers but no independent publication-date field or `Last-Modified`/ETag evidence; publication-date verification is therefore `UNKNOWN`.

### Listing and delisting

- Official active-listing endpoint returned `962` rows; raw response SHA-256: `60c02c654ab40463402ea9f307fbf310e306060b245fa8d538caaeca23b0eab3`.
- Official delisting endpoint was queried for `2023-01` through `2026-07` (`43` monthly requests), yielding `14` delisted rows. All 35 adversarial tickers had an identity row in the combined security master.
- The public three-year boundary remains enforced. History older than the queried window is `UNKNOWN`; no free-only completeness claim to 2009 is made.

### Official tradability

- The sample official manifest: `4` documents, `3 PARSED`, `1 MANUAL_REVIEW`, `2` compile diagnostics; `coverage_complete=false`.
- Live official `GetSuspension` discovery returned `932` SPT and `872` UPT metadata rows for the public window `2023-08-08` through `2026-08-08`. For the adversarial catalog, `82` official PDFs across `16` tickers were fetched and hashed: `66 PARSED`, `16 MANUAL_REVIEW`, `130` event rows, `64` intervals, and `12` compile diagnostics.
- Manual-review diagnostics were intentional fail-closed outcomes: `11 EFFECTIVE_DATE_NOT_FOUND` and `5 MULTI_ACTION_INTRADAY_DOCUMENT`. Compile diagnostics were `10 UNMATCHED_RESUME` and `2 REDUNDANT_SUSPEND`.
- The official snapshot PDF was fetched successfully (3 pages, HTTP 200, SHA-256 `4f8bb958af1ba462a9d503d1047d5fbe97797844917122abbceb3de2ad79eb12`). Its 5 configured rows all reconciled to `UNKNOWN` rather than `SUSPENDED` because the event/coverage evidence is incomplete; reconciliation result: `0/5` matched.
- `config/tradability_coverage_windows.csv` remains empty/unknown. No complete ACTIVE complement was inferred from missing announcements.

### Yahoo price backfill and revision audit

- June raw EOD request: `35` tickers, `30 UPDATED`, `5 NO_PROVIDER_ROWS` (`ARMY`, `HDTX`, `KPAS`, `SRIL`, `TRIL`), `0` first-pass revision conflicts.
- A second fetch against the stored parquet history produced `0` revision conflicts. Existing history was not silently overwritten.
- The adapter uses `auto_adjust=False`, stores raw OHLC separately from vendor adjusted close, and does not forward-fill. Raw schema audit: `30/30` stored files verified; `5` dividend event rows and `0` split event rows were observed from the provider fields. Independent corporate-action verification remains `UNKNOWN`; split-adjusted OHLC was not created.
- Twelve provider rows for `ALMI`, `ALTO`, `ARTI`, `DEAL`, `MKNT`, and `SBAT` fell outside the official June session list (`2026-06-01` and `2026-06-16`). They were retained as provider evidence and excluded from expected-session completion.

### Adversarial DATA GATE

- Catalog: `35` cases across all seven configured families. Result: `0 passed`, `35 failed`.
- Family summaries: `NORMAL_LIQUID 0/8`, `RECENT_IPO 0/8`, `SUSPEND_RESUME 0/8`, `LONG_SUSPENSION 0/5`, `COMPLEX_MARKET_SCOPE 0/1`, `DELISTED_HISTORY 0/1`, `DATA_QUALITY_STRESS 0/4`.
- Exact blocker distribution: `30` tickers had `SESSION_COVERAGE_INCOMPLETE` + `CORPORATE_ACTIONS_UNVERIFIED`; `5` additionally had `PRICE_SEMANTICS_UNVERIFIED` (`ARMY`, `HDTX`, `KPAS`, `SRIL`, `TRIL`).

## Decisions made

- Treat June 2026 as a raw-evidence slice only; do not promote it to a model-ready historical period.
- Keep July 2026 explicitly failed because the official calendar endpoint returned no rows.
- Keep tradability coverage `UNKNOWN` until source discovery, PDF parsing/manual review, interval compilation, and independent snapshot reconciliation support a complete coverage window.
- Treat missing Yahoo rows as unresolved provider absence, never as suspension, no-trade, or data-missing proof.
- Keep corporate-action verification `UNKNOWN` and do not introduce split-adjusted OHLC.

## Decisions needed

- Obtain or authorize an authoritative corporate-action history and resolve the 16 manual-review/12 compile-diagnostic tradability outcomes.
- Decide whether to add a separately audited source path for the missing July 2026 official session publication or use a later complete month.
- Only after those inputs are complete may MAIN decide whether to rerun the gate and authorize `IDX-VAL-002`.

## Blocking risks

- `BLOCKED_EXTERNAL_DATA`: official July session data is empty.
- `SOURCE_DISCOVERY_INCOMPLETE`: the public announcement source is bounded to three years and the target manifest is not a complete parsed event history.
- `TRADABILITY_RECONCILIATION_FAILED`: 5 official snapshot rows currently reconstruct as `UNKNOWN`.
- `CORPORATE_ACTIONS_UNVERIFIED`: no independent authoritative split/dividend history was supplied.
- `PROVIDER_ROWS_MISSING`: five adversarial tickers have no Yahoo rows for the June slice.
- `PROVIDER_NONSESSION_ROWS`: 12 Yahoo rows fall outside the official session list and require explicit policy before any downstream use.

## Validation run

- `python -m pytest -c pyproject.toml`: `44 passed`.
- Runtime evidence includes session API raw JSON/source reports, active/delisted listing outputs and fetch manifests, official suspension metadata and PDF hashes, parsed event/interval/diagnostic reports, raw Yahoo parquet/report/recheck outputs, reconciliation output, and adversarial gate reports.

## Recommended next action

`BLOCKED external data`. Do not begin `IDX-VAL-002`, model development, support/resistance, opportunity scoring, Kelly, Monte Carlo, paper trading, or live trading. Resolve the listed external evidence blockers, then rerun `IDX-DATA-002` from a fresh evidence directory.
