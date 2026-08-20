# IDX Alternative Alpha Data Feasibility V1

Date: 2026-08-21 (Asia/Jakarta)
Branch: `research/idx-alternative-alpha-data-feasibility-v1`
Scope: one-shot source discovery only; no model, target, outcome, score, or counter access

## Executive verdict

`CONDITIONAL_SOURCE_READY_NO_HISTORICAL_ALPHA_YET`

The audit found genuinely new information sets, but none is ready to be added
to V4-X1 or to justify a performance experiment. The most realistic sources
are:

1. **Stockbit Stream**: technically accessible now through Zapi and
   prospective-only. It is the strongest actually demonstrated new source for
   behavioral/attention state, but it has no defensible historical backfill.
2. **Stockbit per-ticker broker flow**: potentially the highest-value
   orthogonal source, but the endpoint is private/undocumented, requires a
   Stockbit bearer session, is not in the Zapi catalog, and was not called with
   a user token in this audit. It remains a bounded-pilot candidate only.
3. **Official IDX disclosure/event corpus**: a defensible bounded/prospective
   event source when official publication timestamps, attachment URLs, and
   immutable bytes/SHA are retained. It must be scoped outside existing
   Financial PIT, Corporate Actions, Foreign Flow, and tradability lanes.

IDX SBL/lendable snapshots and Bank Indonesia JISDOR/policy/inflation are
credible prospective/bounded pilots. Yahoo `.JK` analysts, earnings, holders,
and summary are accessible but sparse or current-state-heavy; they are not
PIT-ready new alpha sources in this run. Generic OHLCV/intraday alternatives
are redundant with existing work and are rejected.

## Governance and boundaries

Before material work I fetched/read `origin/main:coordination/TEAM_STATUS.md`
and root `AGENTS.md`, checked the active lanes, and claimed the new row at
main commit `f8628fe544345d5fd6c2fc3ab2adfdde87944aae` with claim commit
`f8686af8e0d1f89c2288d77fc9ec47f0c2db360a`.

Existing Stockbit intraday forward capture remains the owner of its runtime;
no second capture hierarchy was created. Existing Financial PIT, Foreign Flow,
Ownership/KSEI, Corporate Actions, Market/Index/Breadth, TradingView,
Investing, V4-X1, O2, counters, models, labels, scores, protected outcomes,
and fresh-forward data were untouched.

## Method and empirical evidence

The local `ZAPI_API_KEY` was read only from the environment. It was never
printed, stored, or committed. Two read-only workers independently performed
small source probes; no bulk job or bulk download was used. Account/quota
observations were:

- Pro tier, active plan;
- pre-probe snapshot: 3,888 of 25,000 used, 21,112 remaining;
- worker live headers: 2,000/minute and 25,000/month; remaining moved from
  21,087 to 21,070 during 20 bounded GETs;
- no HTTP 429 or retry condition observed.

The exact sanitized evidence is in:

- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/source_inventory.csv`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/github_repo_inventory.csv`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/bounded_probe_results.csv`

Raw provider responses, user content, cookies, bearer tokens, and keys were
not committed.

Public source references used:

- [Zapi MCP transport, account, schema, and quota documentation](https://zpi.web.id/mcp)
- [Zapi Stockbit catalog](https://zpi.web.id/api/finance/stockbit)
- [Zapi IDX catalog and raw passthrough](https://zpi.web.id/api/finance/idx)
- [Zapi Yahoo Finance catalog](https://zpi.web.id/api/finance/yahoo-finance)
- [Zapi Bank Indonesia catalog](https://zpi.web.id/api/finance/bi-kurs)
- [Zapi TradingView catalog](https://zpi.web.id/api/finance/tradingview)
- [Stockbit reverse-engineered read-only API reference](https://github.com/INo-xious/stockbit-mcp/blob/main/STOCKBIT-API.md)

## Source findings

### Stockbit Stream — `GO_PROSPECTIVE_CAPTURE_ONLY`

Zapi `finance:stockbit/stream` takes a symbol and count. The published schema
does not expose a page, offset, cursor, before/after, last-id, or date range.
In bounded probes, AADI/CUAN/SMBR returned 30/30/29 rows when count=50; the
source dates were 2026-08-20/21. A separate BBCA probe returned 3 unique posts
with IDs, content, `createdAt` 2026-08-21 00:24:38–02:03:26 WIB, engagement and
flags. The first BBCA count=50 response in the other probe was HTTP 200 with a
schema-empty `data` shape and is recorded as an anomaly, not zero activity.

Posts can contain multiple ticker mentions and `$IHSG`. The feed is useful for
an aggregate behavioral/attention state, not user profiling. A prospective
archive would need post-ID deduplication, source `createdAt`, local observed
time, ticker/market mentions, and a deletion/edit policy. It cannot claim
historical backfill because the endpoint only exposes the latest page and
retention/ranking semantics are not proven.

### Stockbit per-ticker broker flow — `GO_BOUNDED_PILOT`

The reviewed [INo-xious/stockbit-mcp reference](https://github.com/INo-xious/stockbit-mcp)
documents Stockbit's private `https://exodus.stockbit.com` backend and
`GET /marketdetectors/{SYMBOL}`. It claims stock-specific broker rows with
net/gross lots or shares, net/gross IDR value, average prices, frequency and
`Asing`/`Lokal`/`Pemerintah` classification, plus `from`/`to` ranges.

This is materially different from the existing market-wide IDX broker summary
and Foreign Flow lanes. It is the highest orthogonality candidate if the
historical contract is confirmed. But the evidence is not yet sufficient to
admit it:

- no Stockbit bearer session was requested or automated here;
- Zapi's current Stockbit catalog has symbol/chart/stream/profile/glossary/
  user/post/trending/quote/user-stream, not `marketdetectors`;
- broker identity stability, board semantics, listing/delisting coverage,
  response revisions, exact daily-vs-range meaning, and completeness remain
  unverified for this project;
- it is private undocumented infrastructure with auth/WAF/ToS risk.

Next step, if separately authorized: a small read-only account-bound pilot,
not bulk historical acquisition, with exact dates, regular-market semantics,
response hashes, and source-time/revision tests.

### Official IDX disclosure/event corpus — `GO_BOUNDED_PILOT`

Zapi's IDX catalog exposes named endpoints and a raw passthrough to official
`/primary/...` routes. The repo's existing PIT lanes demonstrate that official
announcement references, attachment URLs, publication timestamps, and bytes
can be retained and hashed when available.

This is a promising new family only when restricted to event classes not already
covered by Financial PIT, Corporate Actions, Foreign Flow, or tradability. A
future corpus should store issuer/ticker, announcement ID, form/type, subject,
official announced-at, attachment path, attachment SHA, observed capture time,
and a deterministic ticker mapping. The public history boundary is finite;
older exchange announcements may be unavailable. Therefore the claim is
bounded archive plus prospective capture, never a fabricated 2018-complete
history.

### IDX SBL/lendable — `GO_PROSPECTIVE_CAPTURE_ONLY`

The Zapi IDX catalog exposes `lendable-stock`. A bounded BBCA call returned
HTTP 200, `total=293`, and one filtered row with lendable volume and fee fields.
This proves access to a potentially new short-supply/borrow-friction state, not
historical completeness. Capture it prospectively after a stable official
cutoff, preserve raw bytes and retrieval time, and verify the row set against
the official universe before using it anywhere.

### IDX derivatives/open interest — `WAIT_FOR_MORE_EVIDENCE`

A BBCA-underlying probe returned three contracts dated 2026-08-20, but many
high/low/settle/value/volume/open-interest fields were zero. That could mean no
trade, an unavailable field, or an after-hours limitation. It is not safe to
interpret or model until a live-session completeness and zero-field contract is
frozen.

### Yahoo `.JK` — access is broad, PIT value is weak in this sample

The exact Zapi slug is `finance:yahoo-finance`.

- **Analysts:** CUAN.JK and SMBR.JK returned explicit `404 No analyst
  coverage`; BBCA.JK returned analystCount=25, four trend periods, and empty
  upgrade/downgrade items in the independent probe. This is sparse and
  issuer-skewed, not broad coverage.
- **Earnings:** BBCA.JK returned four quarterly items, four annual rows and
  four estimates in the independent probe. The other bounded CUAN/SMBR probes
  were annual-heavy and had zero quarterly items. This is provider-dependent,
  not a proven publication/version chain.
- **Holders:** BBCA returned one holder item and five funds, with zero insider
  trades in the independent probe. Another bounded probe saw BBCA institutional
  aggregates while AADI/CUAN item lists were empty.
- **Summary:** current valuation, margins, quote, dividend, target and
  ownership fields were returned; no `as_of`, `knowledge_at`, or revision field
  was observed.
- **Historical:** BBCA.JK `range=10y, interval=1d` returned 2,463 candles from
  2016-08-22 to 2026-08-19, with OHLCV and `adjClose`. That is price history,
  not a new PIT information set, and adjusted/raw semantics require the same
  care already used by this repo.

Yahoo earnings/analysts/holders remain `WAIT_FOR_MORE_EVIDENCE`; summary and
generic price history are descriptive or redundant.

### Official IDX catalog findings

The independent worker found useful actual endpoint behavior:

- `stock-summary?date=20260731&length=3` reported `recordsTotal=963`; page 0
  began AADI/AALI/ABBA and page 1 began ABDA/ABMM/ACES;
- `stock-summary?...&code=BBCA&length=1` ignored both filter and length and
  returned all 963 rows beginning with AADI. This is a material acquisition
  blocker: never use that filter without an explicit row-identity check;
- `stock-history?code=BBCA&from=2026-07-01&to=2026-08-08` returned 28 rows for
  2026-07-01 through 2026-08-07;
- `/companies` returned 962 current records and `/securities` 962 current
  records;
- `/broker-summary` returned 3 of 88 brokers for 2026-07-31 and is market-wide,
  not stock-specific;
- `/market-activity?type=uma` returned 7 rows but nested `ResultCount=0`, an
  internal count inconsistency;
- `/foreign-flow` returned a BBCA row with unit `shares` for 2026-07-31.

These are useful source-quality observations, not authorization to modify any
existing IDX lane.

### Bank Indonesia macro — `GO_BOUNDED_PILOT`

Zapi's BI catalog exposes JISDOR date ranges plus transaction rate, banknote,
policy-rate and inflation series. JISDOR responses contain date, rate, currency
and `source=bank-indonesia`. This is a credible public external driver for
market/sector context, but release time, revision rules and cross-sectional
mapping must be frozen before a model use. It is a fourth-priority lane, not a
current V4-X1 challenger.

## PIT / source risk matrix

| Risk question | Conclusion |
|---|---|
| Economic date | Stockbit stream has `createdAt`; official IDX/BI have session/series dates; broker ranges are aggregated and must not be mistaken for daily rows. |
| Public availability time | Official sources can support a contract when metadata/bytes are captured. Zapi observed retrieval is not retroactive publication time. Yahoo/current Stockbit availability is not proven. |
| Revisions | Official bytes can be versioned by SHA. Yahoo/current private responses may be replaced; unresolved. |
| Listing/survivorship | No candidate in this run proved complete historical extinct-security coverage; join to the existing identity lineage. |
| Historical backfill | Social: no. Broker flow: technically plausible but account-unverified. Official disclosures: bounded only. SBL: unproven. BI: likely bounded date-range but release audit pending. |
| Security/privacy | Never commit keys/tokens/cookies. Treat Stockbit users as aggregate source metadata only, not prediction targets. |

## Ranked table and recommendation

The complete machine-readable ranking is in `source_inventory.csv`.

| Rank | Family | Orthogonality | Availability | PIT confidence | Role | Verdict |
|---:|---|---|---|---|---|---|
| 1 | Stockbit Stream | medium/high behavioral | demonstrated now | prospective only | aggregate attention state | `GO_PROSPECTIVE_CAPTURE_ONLY` |
| 2 | Stockbit broker flow | high participant flow | private/unverified | unproven | crowding/participant alpha | `GO_BOUNDED_PILOT` |
| 3 | Official IDX disclosure/events | high event state | public bounded | strong if bytes/time retained | event/regime alpha | `GO_BOUNDED_PILOT` |
| 4 | IDX SBL/lendable | medium/high short supply | snapshot demonstrated | prospective only | borrow/crowding context | `GO_PROSPECTIVE_CAPTURE_ONLY` |
| 5 | BI macro | medium market driver | public catalog | promising, release audit pending | regime/context | `GO_BOUNDED_PILOT` |
| 6 | IDX derivatives/OI | medium | incomplete snapshot | unresolved | positioning context | `WAIT_FOR_MORE_EVIDENCE` |
| 7 | Yahoo earnings/analysts/holders | low/medium | sparse/current | weak | descriptive cross-check | `WAIT_FOR_MORE_EVIDENCE` |
| 8 | generic OHLCV/intraday | low/redundant | existing/rejected | no new value | none | `DROP_REDUNDANT` |

If only three lanes can be funded after V4-X1, choose:

1. **Stockbit Stream prospective archive**, because it is accessible now and
   provides an information set not reconstructable from prices. Start small,
   aggregate at ticker/time, dedupe by post ID, and do not claim history.
2. **Stockbit broker-flow bounded pilot**, because it has the highest potential
   incremental cross-sectional information, but only after explicit account and
   source-contract authorization.
3. **Official IDX disclosure/event bounded archive**, because it has the best
   provenance and can encode information arrivals unavailable in OHLCV.

IDX SBL can replace the stream only if the user prioritizes a smaller,
non-personal, prospective state; BI macro is the next fallback if SBL coverage
or history fails.

## Direct answers

- Historical Stockbit social backfill: **No, not on current evidence.** It is a
  latest-page feed with no historical cursor/date contract.
- Per-ticker Stockbit historical broker flow: **Possible but not yet proven.**
  The private reference claims date-range behavior, but it is absent from Zapi
  and was not called with a user bearer session.
- Yahoo `.JK` analyst/earnings coverage: **uneven and sparse.** CUAN/SMBR had
  no analyst coverage; BBCA showed analysts and four quarters, while CUAN/SMBR
  probes were annual-heavy. No broad PIT claim is allowed.
- Any source strong enough to challenge/add to V4-X1 now: **No.** Broker flow
  is the strongest future challenger candidate, not an admitted feature or
  model input.

## Stop condition

Stop for independent ChatGPT review. A future task must freeze one source
contract before backfill/capture, including endpoint/params, date and board
semantics, completeness, timestamp/PIT rule, revision policy, identity join,
raw external artifact root, hashes, quota/rate limits, and privacy/ToS rules.
