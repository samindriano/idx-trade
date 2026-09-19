# Alpha Phase-Frontier Audit — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Commit at audit: `dfab1b238235f36562d0e6689bb7d24164c58e0c`  
Scope: independent read-only pre-admission audits; no derived output was written
by the workers.

## Executive result

The frontier is still scientifically productive, but no result admits a new
candidate or unlocks protected evaluation.

- Capacity/friction: `NO-GO` for scalability or promotion claims.
- H-LIQ-01: remains `NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5.
- Newly surfaced `Dataset-Saham-IDX`: `BLOCKED` pending a dedicated source
  admission audit.

## A. Capacity and friction adversarial result

Independent read-only recomputation used the fixed 600-session window
`2024-01-12`–`2026-07-31`, Top-30, and existing structural inputs.

| Candidate | Turnover median / q95 / max | Stress friction q95 / max | Sessions above 50 bps |
|---|---:|---:|---:|
| C1 | `40.00% / 56.67% / 66.67%` | `62.33 / 73.33 bps` | `220/599 = 36.73%` |
| C2 | `33.33% / 50.00% / 63.33%` | `55.00 / 69.67 bps` | `60/599 = 10.02%` |
| C4 | `23.33% / 36.67% / 46.67%` | `40.33 / 51.33 bps` | `1/599 = 0.17%` |

Decision-changing counterexamples:

- C4's low mean turnover does not establish scalable capacity: selected value
  buckets Q1/Q2/Q3/Q4 were `34.46% / 24.91% / 22.28% / 18.36%`, indicating a
  strong bottom-value tilt.
- C2 had the highest Q4 value exposure at `34.99%`, but recent-listing names
  (age <=365 days) were `8.84%` of selected slots versus `5.51%` in the
  eligible baseline.
- Names selected at least 20 times contributed `89.33%` of C1 slots, `88.83%`
  of C2 slots, and `90.68%` of C4 slots. Maximum selection counts were `126`,
  `139`, and `202` respectively.
- Entry/exit events were broad rather than dominated by a few names: the top
  ten names accounted for only `5.3%`, `6.4%`, and `6.2%` of C1/C2/C4 events;
  half of events required `119`, `128`, and `118` names respectively.

Sector/industry conditioning is `UNKNOWN`: no sector field exists in the
admitted panel, guarded features, or identity header. ADV, spread, queue depth,
fill probability, executable capacity, PIT survivorship, CA basis, and
predictive outcomes remain unknown.

Disposition: preserve all candidate statuses. C1 receives stronger friction-tail
caution; C4 receives stronger bottom-value/capacity caution; C2 remains
structurally preferable on value exposure but is not admission-ready.

## B. H-LIQ-01 novelty adversarial result

H-LIQ-01 remains structurally distinct enough not to reject, but the
“liquidity variability” interpretation is weakened by dynamic size composition.

- Full-window Top-30 overlap with C1/C4 is `8.97% / 12.48%`; across six
  100-session eras the ranges remain low at `3.5%–17.6%` and `3.9%–17.6%`.
- H-LIQ/C2 Spearman is positive in every era (`0.0763–0.1312`), with era
  Top-30 overlap `24.77%–37.13%`; value-bucket dependence reaches `0.1958` in
  Q4.
- H-LIQ selects bottom-value Q1 names in `39.67%` of slots, versus C1
  `26.63%`, C2 `21.26%`, and C4 `34.46%`.
- H-LIQ's Q1 share moves from `51.3%` early to `29.5%` in the last era, so
  apparent novelty is partly dynamic size composition. Volume Q1 is `27.58%`,
  so H-LIQ is not simply a low-volume selector.

Conclusion: retain `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; do
not create C5. Further adjudication requires an authoritative turnover-unit,
price-basis, and executable-capacity contract, not target access.

## C. Newly surfaced Dataset-Saham-IDX audit

### Inventory and integrity

- External repository: `D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX`.
- Git commit: `bc0ac7712ce5e46f1067349e13ab9f338883c6c4`.
- Git tree: `b85e5df6bd941ee1798d78ef1110efd25c66a547`.
- `Saham` subtree: `1,014` CSV files, `1,146,324` rows, `958` distinct
  filename tickers.
- Date range: `2019-07-29` through `2025-02-21`; all parsed dates were valid
  after accepting `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS` forms; no duplicate
  dates within a file and no descending adjacent dates were observed.
- Duplicate filename groups: `56`; `45` groups were byte-identical across
  folders and `11` groups were non-identical. This creates a source-selection
  ambiguity for tickers present in both `LQ45` and `Semua` folders.
- All 1,014 files shared one 25-field schema. Fields include OHLCV, value,
  bid/offer, listed/tradable shares, foreign buy/sell, and delisting date.
  There is no row-level `available_at`, publication, update, vintage, or
  knowledge-time field.
- `List Emiten` contains 13 CSVs: `all.csv`, `LQ45.csv`, and 11 sector-named
  files. These are static listing/sector metadata, not historical PIT sector
  intervals.

### Source authority and classification

| Surface | Classification | Reason |
|---|---|---|
| Daily OHLCV/foreign/bid-offer/share CSVs | `BLOCKED` | Manual update process, no row-level vintage/PIT contract, duplicate non-identical folder copies, unresolved CA/identity semantics. |
| Sector/listing files | `METADATA_ONLY` | Static `code,name,listingDate,shares,listingBoard`; no historical interval/knowledge-time authority. |
| Foreign-flow representation v2 | `PARTIAL` | Already audited; shadow-only and not admitted. |
| Financial PIT bundle | `PARTIAL` | Capability/C3 evidence only; not candidate-admitted. |
| Stockbit activity metadata | `METADATA_ONLY` | Snapshot metadata without ticker-date available-at history. |
| Guarded Stage-A artifact | `ADMISSIBLE` for target-free structural diagnostics only | Bound to manifest and source hashes; not target-admissible. |

`info.json` says `last_update = 2024-07-19`, while repository HEAD is dated
`2025-02-23`; the README describes manual updates and explicitly provides no
row-level timing contract. This mismatch is additional provenance risk, not
proof that any particular row is stale.

Relevant source hashes:

- `info.json`: `6c7c6481b69b4a7958a5a76619e4dad668eeed9e4f480ad2d67028ed91b5a30f`
- `README.md`: `a680b6f567c306bcf569df5bc96b930d8599cd831ceb9fc844d5394280589858`
- `Keterangan Nama Kolom.md`: `e0d84cefc2d13097ba9d35e24bf5d3c4a136704bbf3d4eee0031f2a31ac7c0a5`

### Safe next action

Run one separate read-only source-admission audit of this external repository:
coverage against official sessions, identity continuity, row-level timing and
vintage, CA/scale semantics, and foreign/sector definitions. Do not construct
features or open protected outcomes unless that audit first passes an explicit
admission decision. The first bounded admission audit has now been completed and
is `BLOCKED / NOT_ADMITTED`; detail is in
`2026-09-19_ALPHA_DATASET_SAHAM_IDX_ADMISSION_AUDIT_V1.md`.

## Boundary and provenance

All three worker tasks were read-only and pinned to the isolated research lane.
No worker modified files or configuration. No target, forward return, label,
incumbent target-derived score, provider, network, cloud/R2, capture,
telemetry, scheduler, or canonical dataset was accessed or modified.
