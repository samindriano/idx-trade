# Full-market 504-session historical expansion — FAIL / STOP

Date: 2026-08-08

Branch at runtime: `data/idx-data-002c`

Runtime source commit: `ed13ee0812e8db21d580e922f4e346873aa7b3cd`

## Window and calendar

- official calendar built: **516 sessions**;
- calendar source range: `2024-06-01` through `2026-07-31`;
- parsed months: **26/26**;
- calendar errors: **0**;
- available calendar first/last: `2024-06-03` / `2026-07-31`;
- exact target first/last: `2024-06-21` / `2026-07-31`;
- target count: **504**.

The calendar uses official IDX Digital Statistics and official IDX Daily
Statistics publication evidence. For early months the Daily Statistics listing
was empty while the official Digital Statistics table contained valid dates, so
the recovery used the latter and recorded the source fallback. No weekday
estimation, Yahoo calendar, or JCI dates were used.

The previously certified 43- and 126-session artifacts were not modified.

## Runtime validation

- pytest: **134 passed**, exit 0;
- non-blocking warnings: 2.

## Official Stock Summary execution evidence

- target sessions complete: **504/504**;
- cached sessions reused: **126**;
- newly fetched sessions: **378**;
- ACTIVE anchors: **425,340**;
- NO_TRADE anchors: **54,131**;
- unresolved metric rows: **0**.

## PIT universe and scope

- discovered before scope: **977**;
- CNTX: retained as authoritative `NON_COMMON_SHARE / Saham Preference`
  exclusion;
- required common-stock candidates: **976**;
- newly discovered historical identity: `FREN`;
- generic KSEI reconciliation: attempted, unresolved;
- hardcoded ticker identity/exclusion: **none**.

## Price extension and corporate actions

For the additional 378 official sessions, 881 common candidates required
extension:

- UPDATED: **878**;
- NO_PROVIDER_ROWS: **3** — FREN, MASA, MFIN;
- DOWNLOAD_ERROR: **0**;
- REVISION_CONFLICT: **0**.

The existing official IDX Stock Split / Reverse Stock query was reused and
filtered to the exact 504-session window. A successful authoritative query
continues to verify the no-event case as well as event-bearing tickers.

## Certification ladder

Regression horizon, 126 sessions:

- window: `2026-01-15` through `2026-07-31`;
- discovered before scope: 964;
- required common stocks: 963;
- passed/failed: **963/0**;
- UNKNOWN sessions: 0;
- missing ACTIVE prices: 0;
- quarantined non-ACTIVE bars: 2,672;
- blocker histogram: `{}`;
- status: **PASS**.

Expanded horizon, 504 sessions:

- window: `2024-06-21` through `2026-07-31`;
- discovered before scope: 977;
- required common stocks: 976;
- passed/failed: **973/3**;
- unresolved identities: FREN;
- UNKNOWN sessions: 2;
- missing ACTIVE prices: 271;
- quarantined non-ACTIVE bars: 22,400;
- blocker histogram:
  `PRICE_SEMANTICS_UNVERIFIED: 2`,
  `SECURITY_IDENTITY_UNRESOLVED: 1`,
  `SESSION_COVERAGE_INCOMPLETE: 2`;
- status: **FAIL**.

Exact failed tickers and blockers:

| ticker | blockers | evidence |
|---|---|---|
| FREN | `SECURITY_IDENTITY_UNRESOLVED` | Generic KSEI reconciliation returned an undefined security/type/listing record. |
| MASA | `SESSION_COVERAGE_INCOMPLETE`, `PRICE_SEMANTICS_UNVERIFIED` | 22 expected ACTIVE prices missing; Yahoo `NO_PROVIDER_ROWS`. |
| MFIN | `SESSION_COVERAGE_INCOMPLETE`, `PRICE_SEMANTICS_UNVERIFIED` | 249 expected ACTIVE prices missing; Yahoo `NO_PROVIDER_ROWS`. |

## Phase decision

**STOP.** The 504 gate is not certified. The first failure is already
localized to three historical securities, so no 252 diagnostic was started.
The failure artifacts are preserved in the new runtime workspace, including
the initial insufficient-price attempt and the final 504 gate outputs.

No 504 model-safe panel or certified manifest was created. Do not begin 1260,
modelling, `IDX-VAL-002`, or merge to `main` until the blockers are resolved
without weakening the gate.
