# DATA GATE runbook

The project remains in the **data foundation** phase. Model, support/resistance, probability and Kelly work must stay blocked until the required research period passes this gate.

## 1. Build official identity reference

Use the IDX active-listing and delisting adapters to construct the listing security master. Current active listings are identity/reference data only and must never define a historical backtest universe by themselves.

Required outputs:

- canonical security master with `listed_from` / `listed_to`;
- source references and retrieval manifest;
- unresolved ticker/schema errors reported explicitly.

## 2. Build Regular-Market tradability history

Maintain an auditable manifest of official IDX suspension/resumption announcements. Run the tradability ingestion pipeline against that manifest.

The ingestion pipeline produces:

- `tradability_events.csv`;
- `tradability_parse_diagnostics.csv`;
- `tradability_intervals.csv`;
- `tradability_compile_diagnostics.csv`;
- `tradability_ingestion_report.json`.

Parser/compiler integrity **does not** prove historical announcement discovery is complete. `coverage_complete` intentionally remains `false` until a separate source-discovery audit justifies a coverage window.

Automatic parsing is fail-closed. At minimum the following require explicit review instead of automatic flattening:

- intraday open/resuspend sequences;
- negotiated-market-only temporary openings;
- later-session resumptions;
- Periodic Call Auction resumptions;
- scanned/image-only documents;
- unknown market/ticker/effective-date wording.

## 3. Declare tradability coverage only after discovery audit

A `tradability_coverage_window` may be marked complete only when we have reasonable evidence that official suspension/resumption source discovery is complete for that market and period.

Do **not** infer completeness from:

- all documents in a hand-picked manifest parsing successfully;
- Yahoo prices looking continuous;
- absence of known suspensions;
- a ticker having many OHLC rows.

Outside a declared-complete coverage window, missing suspension records resolve to `UNKNOWN`, not `ACTIVE`.

## 4. Collect raw EOD price history

Primary free research source: Yahoo/yfinance with `auto_adjust=False`.

Rules:

- preserve raw OHLCV for execution semantics;
- keep vendor adjusted close separate;
- do not synthesize split-adjusted technical OHLC from adjusted close;
- do not forward-fill missing price bars;
- do not infer `SUSPENDED` or `NO_TRADE` from a missing provider row;
- historical provider revisions must be surfaced rather than silently replacing prior research snapshots.

## 5. Verify corporate actions and price semantics

Every required ticker needs explicit evidence flags for:

- corporate-action history verified;
- raw execution-price semantics verified.

Both flags fail closed. An absent verification flag is a blocker.

Split-adjusted technical prices may be introduced only after explicit split-event history is verified.

## 6. Run the adversarial QA universe

`config/adversarial_cases.csv` deliberately includes normal liquid names and difficult cases: recent IPOs, suspend/resume cases, long suspensions, delisted history, market-scope anomalies and illiquid/data-quality stress names.

This catalog is **not** the model universe and must not be used as evidence of alpha.

Run `run_adversarial_data_gate(...)` against the candidate research period. Review results by case family.

Expected standard:

- all required listing states explained;
- all relevant Regular-Market suspension intervals explained or deliberately `UNKNOWN`;
- no expected active session silently missing;
- no price bar exists inside a known non-active state without investigation;
- corporate actions verified;
- price semantics verified.

A failure means fix or narrow the research period. Do not weaken the gate merely to obtain a pass.

## 7. Full-universe gate

Only after adversarial cases pass should the same session-level gate be run over the entire candidate point-in-time universe.

The model-development period can begin only when:

1. the chosen historical period has an audited Regular-Market tradability coverage window;
2. required price histories pass expected-vs-observed session coverage;
3. corporate-action and execution-price semantics are verified;
4. unresolved provider gaps are classified explicitly;
5. reproducibility manifests capture code, environment and data-source fingerprints.

## Decision rule

- **PASS:** freeze a versioned data snapshot and begin support/resistance/setup research.
- **FAIL:** fix data, obtain better evidence, or shorten the historical period.
- **UNKNOWN:** remains a failure for model development.

The objective is not to force a 2009–present dataset. A shorter clean point-in-time period is preferable to a long dataset whose trading states are guessed.
