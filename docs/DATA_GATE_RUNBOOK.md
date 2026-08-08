# DATA GATE runbook

The project remains in the **data foundation** phase. Model, support/resistance, probability and Kelly work must stay blocked until the required research period passes this gate.

## 1. Build official identity reference

Use the IDX active-listing and delisting adapters to construct the listing security master. Current active listings are identity/reference data only and must never define a historical backtest universe by themselves.

Required outputs:

- canonical security master with `listed_from` / `listed_to`;
- source references and retrieval manifest;
- unresolved ticker/schema errors reported explicitly.

## 2. Build an official Exchange-Day calendar

Coverage must be measured against official IDX Exchange Days, not against the dates returned by the price provider under audit.

Use the IDX Digital Statistics daily-trading tables as the primary free session-calendar evidence. If a monthly Digital Statistics response is empty or incomplete, cross-check and fall back to the official IDX Daily Statistics publication listing. Never use Yahoo or JCI dates as Exchange-Day truth. The session backfill writes:

- `exchange_sessions.csv`;
- `exchange_session_sources.csv`;
- `exchange_session_summary.json` including a canonical session-list hash.

A month that cannot be parsed keeps the calendar incomplete. Record the source identity and fallback reason for every month; do not silently replace missing official calendar months with Yahoo/JCI dates.

## 3. Build Regular-Market tradability history

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

### Free official announcement-history constraint

The public IDX announcement page states that only **three years** of announcement data are available there; older historical data is directed to TICMI. Therefore the project must not claim free official suspension/resumption completeness back to 2009 merely because price data exists that far back.

The initial free-only research-period candidate should be chosen inside the interval for which official announcement discovery can actually be audited. A longer period may be promoted only if an additional official/appropriately licensed source (for example TICMI) supplies the missing historical state evidence.

## 4. Separate discovery coverage from per-security state anchors

A `tradability_coverage_window` means only that the relevant event-source discovery process is independently supported as complete for a market and bounded period. It must carry explicit source, discovery basis and boundary basis. It does **not** contain or imply one market-wide initial `ACTIVE` state.

Per-security state evidence is stored separately in `tradability_anchors` with:

- `ticker`;
- `market`;
- `as_of_date`;
- `state`;
- `source` / `source_ref`;
- `evidence_type`.

Inside a complete discovery window, the ACTIVE complement may be inferred for a ticker only when that ticker has authoritative anchor evidence in the same window and the anchor is consistent with the explicit event intervals. No anchor means `UNKNOWN`. Conflicting anchor/event evidence is a hard failure.

A valid free official ACTIVE anchor may be derived from IDX Stock Summary when the same official daily record proves a strictly positive Regular-Market transaction: total `Volume - NonRegularVolume > 0` **and** total `Frequency - NonRegularFrequency > 0`. This proves that Regular-Market trading occurred for that ticker on that date. Zero activity, mere row presence, `Remarks`, or Yahoo price presence do **not** prove ACTIVE and remain `UNKNOWN` unless another authoritative state source exists.

Official status snapshots may be used as anchors, including SUSPENDED anchors for securities already suspended at the left boundary. When event discovery is complete, a SUSPENDED boundary anchor may be propagated forward only through explicit official transitions; nothing before the anchor is inferred. The same snapshot rows must not simultaneously serve as independent validation evidence. Reserve separate dates/rows as reconciliation holdouts.

Do **not** infer discovery completeness or ACTIVE state from:

- all documents in a hand-picked manifest parsing successfully;
- Yahoo prices looking continuous;
- absence of known suspensions;
- a ticker having many OHLC rows;
- listing existence alone.

Use independent official status snapshots (for example long-suspension/status lists where applicable) to reconcile reconstructed states. A mismatch is a blocker.

Outside a declared-complete discovery window, or for a ticker without a valid causal anchor inside that window, unresolved state remains `UNKNOWN`.

## 5. Collect raw EOD price history

Primary free research source: Yahoo/yfinance with `auto_adjust=False`.

Rules:

- preserve raw OHLCV for execution semantics;
- keep vendor adjusted close separate;
- do not synthesize split-adjusted technical OHLC from adjusted close;
- do not forward-fill missing price bars;
- do not infer `SUSPENDED` or `NO_TRADE` from a missing provider row;
- historical provider revisions must be surfaced rather than silently replacing prior research snapshots.

## 6. Verify corporate actions and price semantics

The official IDX Corporate Actions source is authoritative for the technical actions in V1. The provider must retain source references and focus on:

- `Stock Split`;
- `Reverse Stock`.

Yahoo split events may be cross-checked for diagnostics only; they never override IDX. The official IDX action table's action amount and total-after-action fields must be interpreted directionally before deriving a ratio.

Every required ticker needs explicit evidence flags for:

- `split_history_verified`;
- raw execution-price semantics verified.

Both flags fail closed only when active/executable observations are actually expected in the evaluated window. A ticker with zero expected active sessions must not fail solely because Yahoo returned no price rows. Dividend history is informational for V1 and must not block this gate; do not create dividend-adjusted technical OHLC. Raw OHLC and vendor-adjusted fields remain separate.

Split-adjusted technical prices may be introduced only after explicit split-event history is verified.

## 7. Run the adversarial QA universe

`config/adversarial_cases.csv` deliberately includes normal liquid names and difficult cases: recent IPOs, suspend/resume cases, long suspensions, delisted history, market-scope anomalies and illiquid/data-quality stress names.

This catalog is **not** the model universe and must not be used as evidence of alpha.

Run `run_adversarial_data_gate(...)` against the candidate research period. Review results by case family.

Expected standard:

- all required listing states explained;
- all relevant Regular-Market suspension intervals explained or deliberately `UNKNOWN`;
- authoritative per-ticker anchors exist wherever ACTIVE complements are inferred;
- no expected active session silently missing;
- no price bar exists inside a known non-active state without investigation;
- split history verified;
- price semantics verified.

A failure means fix or narrow the research period. Do not weaken the gate merely to obtain a pass.

## 8. Full-universe gate

Only after adversarial cases pass should the same session-level gate be run over the entire candidate point-in-time universe.

The model-development period can begin only when:

1. the chosen historical period has an audited Regular-Market event-discovery window;
2. required securities have authoritative tradability anchors within that window;
3. independent status reconciliation passes;
4. the official Exchange-Day calendar is complete for that period;
5. required price histories pass expected-vs-observed session coverage;
6. split-history and execution-price semantics are verified;
7. unresolved provider gaps are classified explicitly;
8. reproducibility manifests capture code, environment and data-source fingerprints.

## Decision rule

- **PASS:** freeze a versioned data snapshot and begin support/resistance/setup research.
- **FAIL:** fix data, obtain better evidence, or shorten the historical period.
- **UNKNOWN:** remains a failure for model development.

The objective is not to force a 2009–present dataset. A shorter clean point-in-time period is preferable to a long dataset whose trading states are guessed.
