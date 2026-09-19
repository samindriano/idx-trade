# Alpha Data Inventory Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Scope: read-only inventory of locally available research assets and schemas;
protected outcome/counter contents excluded

## Inventory scope

The census covered the alpha staging root, the frozen research-panel roots,
financial representation bundle, official-session/tradability roots, retained
historical ranking/O2/source-probe directory names, the local IDX external
snapshot root, and committed historical checkpoints/ref mappings. Protected
forward-monitoring/outcome/counter payloads were not opened or copied. A source
being listed below does not make it admissible.

## Primary data assets

| Asset | Observed capability | Classification | Permitted use |
|---|---|---|---|
| Clean OHLCV panel `model_safe_signal_research_panel_1260_final_clean.parquet` | 981,940 rows; 945 tickers; 2021-04-29–2026-07-31; unique ticker/date | `PARTIAL / FROZEN_ONLY` | structural features and implementation diagnostics |
| Frozen official sessions | 1,260 dates | `PARTIAL / FROZEN_ONLY` | calendar ordering and masks |
| Tradability anchors | 1,104,064 anchors; 1,260 dates | `PARTIAL / FROZEN_ONLY` | same-session eligibility mask |
| `config/tradability_snapshot.sample.csv` | 5 rows, all dated 2025-07-30 | `PARTIAL / CHECKPOINT-SAMPLE / NON-ADMISSIBLE` | no historical event-log use |
| `config/idx_tradability_manifest.sample.csv` | 4 announcement references; one `MANUAL_REVIEW` | `PARTIAL / CHECKPOINT-SAMPLE / NON-ADMISSIBLE` | discovery/reference only |
| `config/tradability_coverage_windows.csv` | header-only; zero declared windows | `EMPTY / UNKNOWN` | no coverage claim |
| Financial PIT `bundle_rows.parquet` | 277,244 rows; 729 tickers; 2021-06-02–2026-07-17; unique keys | `PARTIAL / PARKED` | C3 capability/provenance audit only |
| Corrected Stage A feature artifacts | C1–C4 values/ranks and eligibility; guarded versions in external staging | `DERIVED / ISOLATED` | target-free diagnostics only |
| External Stage-A generations | multiple 981,940-row derived feature generations; some byte-identical with different manifests | `DERIVED / STRUCTURAL-ONLY / HISTORICAL-STAGING` | lineage/duplicate/superseded status must be explicit; not new raw data |
| `config/stockbit_stream_universe_v1.csv` activity metadata | 963 tickers; `activity_median_regular_value_60` populated for 105; `capture_high=1` for 100; five populated ranks are 101–105 with `capture_high=0` | `PARTIAL / METADATA_ONLY / NON-ADMISSIBLE` | inventory/future-source clue only; no ticker-date history or available-at/PIT timestamps |
| Historical Ranking V2/V3/V4 caches | retained historical development artifacts and manifests | `HISTORICAL / CLOSED OR FROZEN` | archaeology only; no new refit/rescore |
| O2/O2.1/path-risk/reliability artifacts | retained auxiliary historical runs | `HISTORICAL / DIAGNOSTIC` | failure/mechanism archaeology only |
| Zapi/IDX/TradingView/Investing/Stockbit probes | directory-level and staged probe evidence | `PARTIAL / BLOCKED / UNKNOWN` | source capability review; no panel substitution |
| Sector/listing/ownership/corporate-action roots | source leads, snapshots, audits, or partial archives | `PARTIAL / BLOCKED` | provenance and admission research only |
| Protected prospective target/counter/forward roots | deliberately not opened | `BLOCKED / PROTECTED` | none |

## Frozen-panel fields

The inspected clean panel exposes:

`ticker`, `date`, `high`, `low`, `close`, `volume`,
`regular_market_value`, `price_provenance`, `open`, `open_available`,
`open_evidence_status`, `corporate_action_integrity_verified`, and
`signal_contract`.

Current use/disposition:

- `high`, `low`, `close`, `volume`, and `regular_market_value` support the
  causal structural candidates and implementation-economics diagnostics.
- `price_provenance`, `corporate_action_integrity_verified`, and
  `signal_contract` are governance/audit fields, not independent alpha
  candidates in this lane.
- `open`, `open_available`, and `open_evidence_status` remain source-sensitive;
  they are not used to silently repair or widen the C1–C4 panel. Historical
  executable-Open recovery remains blocked under the source-admission contract.
- No sector/industry history, spread, order-book, queue-position, or broker-side
  flow fields are present in the clean panel schema.

## Derived Stage A fields

The guarded feature artifact exposes:

- `eligible_decision_universe`;
- C1 `residual_reversal_5_v1` and rank;
- C2 `participation_confirmation_5_v1` and rank;
- C3 `financial_quality_growth_v1` and rank;
- C4 `path_efficiency_reversal_20_v1` and rank;
- `financial_pit_valid` and `source_panel_row_present`.

The output contains no target, forward-return, realized-consensus, PnL, NAV,
Sharpe, or incumbent-score fields. The target firewall independently checks
this schema and the producing code.

The current guarded Stage-A generation is the documented structural artifact,
but older `stage-a`, `stage-a-v2`, and `stage-a-v3` generations remain in the
external staging area. Some feature files are byte-identical while their
manifest heads and audit metadata differ. They are retained for provenance and
must not be treated as independent data sources or silently substituted for the
guarded generation.

## Financial bundle fields

The financial bundle contains five candidate values:

- liabilities/assets;
- cash/assets;
- net-income/revenue margin;
- YoY revenue;
- YoY total assets.

It also contains status/available/missing-class fields, fiscal period/stratum,
decision timestamp, reporting knowledge timestamp, reporting version and
attachment identity, filing age, candidate state counts, bundle provenance
flags, and same-bundle/knowledge-time violation flags. The capability audit
found that the metadata exists in schema but is missing or unresolved for a
large subset; field existence is not equivalent to PIT admission.

## Research-root census interpretation

The local research store contains retained directories for:

- V2/V3/V4 ranking preparation, runs, audits, and manifests;
- O1/O2/O2.1 geometry, minimality, robustness, and common-support work;
- financial representation and PIT remediation;
- foreign-flow capture, representation, behavioral forensics, and acquisition;
- open-price/Yahoo/Zapi/TradingView/Investing historical probes;
- listing/history, corporate actions, sector, ownership/free-float/HSC;
- expected-payoff, reliability/uncertainty, and path-risk auxiliary models;
- clean V4-X data consolidation, sessions, tradability, and integrity audits.

Most historical directories are evidence for archaeology or source-admission
failure, not reusable scientific inputs. Reusing them requires rechecking the
specific source hash, PIT contract, and current lane authorization. Retry
directories do not constitute independent evidence by themselves.

Tradability sample files are not a historical event log: the snapshot has only
five rows on one date, the manifest is a four-reference sample, and the
coverage-window file is empty. The reconciliation implementation explicitly
requires event-log/discovery evidence before completeness can be claimed.

The activity metadata is intentionally not promoted into the structural panel:
it is a current-universe 60-session median snapshot as of 2026-07-31, has no
per-date observation history, no available-at timestamp, and no explicit
revision/vintage contract. The five populated rows outside the `capture_high`
flag also make the flag semantics an unresolved governance issue.

## Missing capability versus inadmissible capability

| Question | Current answer |
|---|---|
| Does OHLCV exist for structural work? | Yes, frozen-only panel |
| Does same-day volume/value liquidity exist? | Yes, structural proxy only |
| Does PIT financial data exist? | Partially; C3 capability island only |
| Does historical sector history exist? | Leads/snapshots exist; no complete PIT-admissible history |
| Does historical foreign flow exist? | Partial/blocked representations; no current admitted population-wide source |
| Does historical ownership/free-float exist? | Source work exists; no complete admitted time series |
| Does corporate-action metadata exist? | Partial/event-level and forward foundations; historical transition authority remains bounded |
| Does spread/order-book/broker-side flow exist? | Not in the inspected clean alpha panel; future source opportunity |
| Does protected target/forward evidence exist? | Protected/blocked for this lane; not opened |

## Future data capability opportunities

Highest-value gaps are population-wide historical-as-of financial vintages,
sector membership intervals with availability timestamps, corporate-action
transition authority, broker/foreign flow with PIT publication semantics,
ownership/free-float history, and spread/order-book or defensible liquidity
microstructure history. Each requires a separate source contract, identity
mapping, revision policy, cost/licensing review, and admission artifact.

## Boundary and reproducibility

- No canonical dataset was modified or backfilled.
- No provider/network acquisition was performed.
- No protected target, forward return, incumbent prediction, counter, or
  production artifact was accessed.
- Source hashes and field-level observations are recorded in the master
  checkpoint and data-capability matrix.
