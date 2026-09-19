# IDX-Trade Alpha — Local Zapi Probe Admission Audit V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Scope: read-only inspection of already persisted local probe artifacts only

## Result

`BLOCKED / NOT_ADMITTED / NO_NEW_ALPHA_SURFACE`

The local Zapi archive does not provide a usable historical IDX alpha source.
No network request, provider call, scraper, panel substitution, or model work
was performed in this audit.

## Audited local artifacts

The local archive contains four Zapi probe directories:

1. `D:\Documents\Project\idx-zapi-company-profile-dividend-probe-20260821-v1`
2. `D:\Documents\Project\idx-zapi-dividends-probe-20260821-2026-03-v1`
3. `D:\Documents\Project\idx-zapi-dividends-probe-20260821-v1`
4. `D:\Documents\Project\idx-zapi-dividends-probe-20260821-v1-r2`

The persisted raw payload hashes are:

| Artifact | SHA-256 | Observation |
|---|---|---|
| `company_profile_raw.json` | `76481254403de2b283ad8b911a9a66743df10431c4a6bc823987a9e5b992c5cf` | One BBCA company-profile snapshot; one 2026 dividend row. |
| March dividends `dividends_raw.json` | `d65efaeb59ba9803e232cc04717c7bb795765f1a4b2c4db931b0c54b66aab1ab` | `year=2026, month=3, count=0, total=0`. |
| August dividends `dividends_raw.json` | `963a2bd8a0599bf63ead4c517165ade688de72144584356ce646cf9e714bf3fa` | `year=2026, month=8, count=0, total=0`. |

The shared catalog schema exposes only `year`, `month`, `page`, `length`, and
`search`. It does not expose a row-level knowledge/publication timestamp,
revision/vintage identifier, source-selection contract, or historical
available-at field.

## Findings

### Company-profile snapshot

The BBCA payload was returned at `2026-08-21T05:43:19.295Z` and contains a
single 2026 dividend row with `cumDate=2026-08-28`, `exDate=2026-08-31`,
`recordDate=2026-09-01`, and `paymentDate=2026-09-16`. The persisted review
failed the preregistered official parity event:

`OFFICIAL_BBCA_2026_Q2_PARITY_EVENT_NOT_FOUND`

The review status is `FAIL_NOT_ELIGIBLE_FOR_V1_1_COMPANY_PROFILE_HELPER`.
This is a current snapshot, not a population-wide historical event archive.

### Dividends probes

Both persisted dividends payloads contain zero rows. The March probe review
reports `NO_DIVIDEND_ROWS_FOUND` and `NO_ROW_WITH_REQUIRED_DIVIDEND_SEMANTICS`.
The remediated August review additionally reports:

- `REQUEST_DID_NOT_USE_AVAILABLE_SEARCH_FILTER`;
- `GLOBAL_FEED_ROWS_HAVE_NO_TICKER_IDENTITY`;
- `NO_ROW_WITH_REQUIRED_DIVIDEND_SEMANTICS`.

Both reviews are `FAIL_NOT_ELIGIBLE_FOR_V1_1`. The empty responses cannot prove
that the underlying source has no dividends; they only prove that these local
probe artifacts contain no usable selected rows.

## PIT, identity, and alpha-admission assessment

| Gate | Result | Reason |
|---|---|---|
| Historical population completeness | `UNKNOWN/BLOCKED` | Only one ticker snapshot and empty monthly probes are present. |
| Row-level available-at/publication time | `ABSENT` | Response timestamp is not row publication time and no row-level field exists. |
| Revision/vintage contract | `ABSENT` | No revision identity or immutable historical version selection is present. |
| Security identity continuity | `INSUFFICIENT` | Ticker/company metadata is not an issuer/ISIN transition chain. |
| Corporate-action authority | `INSUFFICIENT` | One snapshot dividend row and failed parity do not establish event authority or price basis. |
| New alpha candidate | `NONE` | No daily cross-sectional or historical PIT feature surface exists in the archive. |

## Disposition

Keep the Zapi artifacts as source-capability/probe evidence only. Do not use
them to fill the clean panel, repair corporate actions, construct a dividend
feature, or reopen a provider search. A future Zapi lane would require an
explicitly authorized acquisition contract, historical pagination/date
semantics, row-level timing, identity/CA authority, deduplication, and source
terms review before any feature construction.

This audit does not change C1-C4, C3, H-LIQ-01, H-VOL-01, H-EXC-02, the
candidate budget, or the protected evaluation packet.
