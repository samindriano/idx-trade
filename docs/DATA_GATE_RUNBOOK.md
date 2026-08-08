# DATA GATE runbook

The project remains in the **data foundation** phase. Model, support/resistance, probability and Kelly work must stay blocked until the required research period passes this gate.

## 1. Build official identity reference

Use the IDX active-listing and delisting adapters as the primary listing-security-master sources. Current active listings are identity/reference data only and must never define a historical backtest universe by themselves.

The IDX `GetSecuritiesStock` current-list endpoint must **not** be assumed exhaustive for long-suspended or otherwise non-trading securities. If a required ticker is absent from that primary response, reconcile its identity against KSEI Registered Securities before declaring the identity unresolved. The KSEI fallback is accepted only when the page explicitly proves all of the following for the requested short code:

- security type is a common share (`Saham Biasa` / common share);
- `Stock Exchange = IDX`;
- KSEI registration `Status = Active`;
- a valid listing date is present.

KSEI is a supplemental identity/reference source, not the authority for current exchange-listing state or tradability. `Status = Active` on KSEI means the registered security remains active in KSEI's registry; it must not override an official IDX delisting date. When IDX delisting evidence exists, that `listed_to` boundary remains authoritative and closes the listing interval. KSEI may supply missing identity/listing-date evidence, but it must never turn a delisted or suspended security into an exchange-listed or `ACTIVE` trading state.

A required ticker whose identity and complete listing interval are known may legitimately have zero listed sessions in the evaluated research window, for example because it was delisted before the window or listed only after it. That is resolved non-eligibility, not missing coverage. A ticker absent from the security master entirely remains a hard `SECURITY_IDENTITY_UNRESOLVED` failure.

Required outputs:

- canonical security master with `listed_from` / `listed_to`;
- source references and retrieval manifest;
- explicit diagnostics for primary-list omissions and KSEI fallback results;
- unresolved ticker/schema conflicts reported explicitly.

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

A longer legal-state reconstruction period may be promoted only if an additional official/appropriately licensed source supplies the missing historical state evidence.

## 4. Separate legal-state discovery from direct session execution evidence

A `tradability_coverage_window` means only that the suspension/resumption event-discovery process is independently supported as complete for a bounded market period. It does **not** imply one market-wide initial `ACTIVE` state.

Per-security point evidence is stored in `tradability_anchors` with:

- `ticker`;
- `market`;
- `as_of_date`;
- `state`;
- `source` / `source_ref`;
- `evidence_type`.

An authoritative anchor is valid on its exact `as_of_date` even when surrounding event discovery is incomplete. Using that anchor to infer state on a different date still requires a complete causal event-discovery path. Conflicting anchor/event evidence is a hard failure.

### Direct official execution evidence

IDX Stock Summary can provide direct Regular-Market execution truth for a session. In the legacy Stock Summary schema, `Volume` and `Frequency` are the regular/order-book daily metrics. `NonRegularVolume` and `NonRegularFrequency` are separate non-regular-market metrics and must **not** be subtracted from the regular metrics.

- `Volume > 0` **and** `Frequency > 0` => `ACTIVE` point evidence;
- `Volume == 0` **and** `Frequency == 0` => `NO_TRADE` point evidence;
- missing, negative, or internally inconsistent regular metrics => unresolved;
- row absence => unresolved.

`NO_TRADE` means **no Regular-Market transaction was observed on that official IDX session**. It is not a claim that the security was legally suspended. Explicit suspension evidence remains more descriptive and is retained separately.

This direct evidence may satisfy session-level model-data coverage without proving that the entire announcement archive is complete, provided every listed session required by the research period has authoritative point evidence or another explicit state explanation. This is not a relaxation: unresolved sessions remain `UNKNOWN` and still fail the gate.

Do **not** infer state from:

- Yahoo price presence or absence;
- listing existence alone;
- `Remarks` text without an audited mapping;
- a hand-picked set of announcements;
- row counts alone.

Official status snapshots may be used as point anchors. Separate rows/dates must be reserved as independent reconciliation holdouts rather than reused as both anchor and validation evidence.

## 5. Collect raw EOD price history

Primary free research source: Yahoo/yfinance with `auto_adjust=False`.

Rules:

- preserve raw OHLCV for source auditability and execution semantics;
- keep vendor adjusted close separate;
- do not synthesize split-adjusted technical OHLC from adjusted close;
- do not forward-fill missing price bars;
- do not infer `SUSPENDED` or `NO_TRADE` from a missing provider row;
- historical provider revisions must be surfaced rather than silently replacing prior research snapshots.

### Raw provider history vs model-safe price view

Official IDX point evidence is authoritative for Regular-Market session state. Yahoo is the price provider, not the tradability authority.

Therefore a Yahoo row on a session classified by official evidence as `NO_TRADE`, `SUSPENDED`, `FCA_WATCHLIST`, `DELISTED`, or otherwise non-ACTIVE must be retained in the raw provider artifact for audit but **quarantined from the model-safe research price view**. Its presence does not override IDX exchange truth and does not by itself fail session coverage.

The model-safe price view contains only provider rows whose point-in-time official state resolves to `ACTIVE`. The DATA GATE still fails when:

- an expected `ACTIVE` session has no provider price row;
- a required listed session remains `UNKNOWN`;
- split history or raw-price semantics are unverified when price evidence is required.

Provider rows on non-ACTIVE sessions remain explicit contamination diagnostics (`quarantined_nonactive_bars`) and must never enter feature, support/resistance, liquidity, label, or backtest calculations.

## 6. Verify corporate actions and price semantics

The official IDX Corporate Actions source is authoritative for the technical actions in V1. The provider must retain source references and focus on:

- `Stock Split`;
- `Reverse Stock`.

Yahoo split events may be cross-checked for diagnostics only; they never override IDX.

Every required ticker needs explicit evidence flags for:

- `split_history_verified`;
- raw execution-price semantics verified.

Both flags fail closed only when active/executable observations are actually expected in the evaluated window. A ticker with zero expected active sessions must not fail solely because Yahoo returned no price rows. Dividend history is informational for V1 and must not block this gate.

Split-adjusted technical prices may be introduced only after explicit split-event history is verified.

## 7. Run the adversarial QA universe

`config/adversarial_cases.csv` deliberately includes normal liquid names and difficult cases: recent IPOs, suspend/resume cases, long suspensions, delisted history, market-scope anomalies and illiquid/data-quality stress names.

This catalog is **not** the model universe and must not be used as evidence of alpha.

Run `run_adversarial_data_gate(...)` against the candidate research period.

Expected standard:

- all required identities and listing intervals are explained;
- a known security with zero listed sessions in the window is treated as resolved non-eligibility, not missing data;
- every listed research session resolves through direct official execution evidence or explicit tradability evidence;
- unresolved sessions remain `UNKNOWN`;
- no expected ACTIVE session silently misses its raw price bar;
- provider rows on explicitly non-ACTIVE sessions are counted and quarantined, never promoted into execution evidence;
- split history verified;
- price semantics verified.

A failure means fix or narrow the research period. Do not weaken the gate merely to obtain a pass.

## 8. Full-universe gate

Only after adversarial cases pass should the same session-level gate be run over the entire candidate point-in-time universe.

The model-development period can begin only when:

1. required security identities and point-in-time listing intervals are resolved;
2. the official Exchange-Day calendar is complete for the period;
3. every required listed security/session has authoritative direct execution evidence or explicit tradability-state evidence;
4. unresolved point evidence is zero for the required universe/period;
5. independent reconciliation checks pass on reserved evidence;
6. required ACTIVE-session price histories pass expected-vs-observed session coverage;
7. non-ACTIVE provider contamination is quarantined from all research/model views;
8. split-history and execution-price semantics are verified;
9. unresolved provider gaps are classified explicitly;
10. reproducibility manifests capture code, environment and data-source fingerprints.

A complete suspension-announcement reconstruction is still valuable for legal-state explanation and stress analysis, but it is no longer required to manufacture an `ACTIVE` complement when direct official per-session execution evidence already exists.

## Decision rule

- **PASS:** freeze a versioned data snapshot and begin support/resistance/setup research.
- **FAIL:** fix data, obtain better evidence, or shorten the historical period.
- **UNKNOWN:** remains a failure for model development.

The objective is not to force a 2009-present dataset. A shorter directly evidenced point-in-time period is preferable to a long dataset whose trading states are guessed.
