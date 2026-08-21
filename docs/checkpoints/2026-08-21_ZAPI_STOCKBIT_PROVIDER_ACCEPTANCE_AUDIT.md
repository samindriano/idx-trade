# Zapi / Stockbit Provider Acceptance Audit

Date: 2026-08-21  
Scope: prospective Stockbit Stream acquisition dependency only  
Owner: ChatGPT / independent provider acceptance audit  
Status: `PASS_WITH_OBSERVED_LIMITATIONS`

## Verdict

**Zapi is technically accepted for the prospective sampled Stockbit research lane.**

This verdict does not claim a complete Stockbit firehose or historical archive. It means the live provider contracts required by this project were exercised successfully and the observed limitations are compatible with a prospective sampling design.

No local Codex execution was required for this audit. All live acceptance work ran in GitHub Actions using repository secrets scoped to the provider-probe step.

## Purpose and scientific boundary

This audit is not a model experiment. It tests whether the Zapi dependency can support the prospective Stockbit research lane without discovering a basic provider limitation only after significant data accumulation.

The audit remained outcome-blind. It inspected provider responses, schema, timestamps, quota telemetry, cache/repeat behavior, and referential integrity. It did not access returns, targets, model scores, O2, protected outcomes, or forward counters.

## Accepted live evidence

GitHub Actions run: `32457407006`  
Provider-acceptance job: `96697252992`  
Result: **SUCCESS**  
Probe verdict: `PASS_WITH_OBSERVED_LIMITATIONS`

The companion adversarial job in the same run also passed.

### Account and quota

Live `get_account` / `get_usage` authority:

- tier: `pro`
- plan status: `active`
- plan expiry observed: `2026-09-10T14:05:18.594Z`
- monthly limit: **25,000**
- quota before accepted probe: used `4,138`, remaining `20,862`
- quota after: used `4,159`, remaining `20,841`
- authenticated REST attempts made by the probe: **21**
- billed quota delta: **21**
- `billing_matches_authenticated_attempts=true`

Therefore the project must assume **every authenticated REST attempt consumes monthly quota**, including cached requests and error/diagnostic attempts. Published marketing numbers are not authoritative for this account; live usage telemetry is.

### IDX stock-summary contract

Historical session `2026-08-20`:

- HTTP 200
- provider `idx`
- dataset `stock-summary`
- 963 complete rows
- all returned `Date` values match the requested session
- unique `StockCode` rows
- immediate repeat byte-equivalent after envelope normalization
- inner canonical SHA-256: `d85887af2150ae30e98f4b6de20858a690c7b080da2ee6fb594bb51d17154d97`

Historical session `2026-06-12`:

- 959 complete rows
- repeated response equivalent
- inner canonical SHA-256: `281a29dd8f8e16de217e9315a56f99fe4c69bcc7a9071b76911a97653b6931e7`

Both `20260820` and `2026-08-20` date forms resolved to the same 963-row panel in the accepted run.

Weekend diagnostic `2026-08-16` returned HTTP 200 with provider/dataset intact and `recordsTotal=recordsFiltered=0`; therefore weekend dates are explicitly empty rather than silently mapped to a previous session.

Current REST traffic retains the observed outer `project/timestamp/data` envelope. Exact raw bytes remain provenance evidence while the nested finance payload is validated.

### Stockbit Stream contract

Live symbols tested:

- `BBCA`
- `GOTO`
- `DADA`

All three returned:

- HTTP 200
- provider `stockbit`
- exact requested symbol
- unique nonblank post IDs
- declared count equal to returned item count
- valid minimum post schema

A request with `count=50` returned **30 posts** for each of the three symbols. The accepted probe established:

- `count=1` -> 1 row
- `count=5` -> 5 rows
- `count=10` -> 10 rows
- `count=30` -> 30 rows
- `count=50` -> 30 rows
- `count=51` -> HTTP 400
- `count=100` -> HTTP 400

Thus 50 is the maximum accepted request parameter observed, while the current backing Stream page carries at most **30 posts**. The production request may remain at 50 to request the largest valid page, but completeness beyond the current page is never assumed.

Immediate repeated `BBCA,count=10` requests returned the same IDs in the accepted probe.

### Observed Stream page depth

Using the provider `createdAt` strings only for **relative within-page span**, not authoritative PIT time:

- BBCA: 30 posts covered `11,538 s` ≈ **3 h 12 m**
- GOTO: 30 posts covered `5,688 s` ≈ **1 h 35 m**
- DADA: 30 posts covered `12,696 s` ≈ **3 h 32 m**

For GOTO specifically:

- latest 5 posts spanned ≈ 19 m
- latest 10 posts spanned ≈ 44.5 m
- latest 30 posts spanned ≈ 94.8 m

This confirms that the endpoint is suitable for **sampled prospective behavioral observations**, not an exhaustive post archive. At the observed activity level the page is not so shallow that sub-minute polling is required, but high-activity periods can still overflow between scheduled observations.

### Post dereference integrity

One newest BBCA Stream post was dereferenced through `finance:stockbit/post?id=...`:

- returned ID matched the Stream post ID
- content SHA-256 matched exactly

The post endpoint therefore provides usable referential integrity for bounded diagnostics. It should not be called routinely because each authenticated request consumes quota.

### Failure behavior

- invalid API key -> HTTP **401**
- intentionally unknown ticker -> HTTP **404**, not provider 5xx
- Stream count above 50 -> HTTP **400**
- no accidental success was observed on invalid inputs

## Provider limitations accepted by design

1. `finance:stockbit/stream` is a latest-page endpoint, not a documented historical firehose. All downstream work must describe the archive as observed prospective samples.
2. Stream `createdAt` lacks an explicit timezone in all BBCA/GOTO/DADA rows tested. Collector HTTP receipt time remains the authoritative PIT availability timestamp.
3. Current Stream page capacity is 30 posts even with a valid `count=50` request.
4. Stream cache headers were observed around `private, max-age=120`, while stock-summary was around 60 seconds. Cache hits still consumed monthly quota in the live audit.
5. Provider response envelopes and cache values can drift; strict schema validation and exact raw-response provenance remain mandatory.
6. Zapi remains an adapter dependency, not a requirement for the core alpha runtime. The social lane can stop independently without invalidating V4-X1.

## Transient timeout found and remediated

The first strict live probe encountered one 30-second historical stock-summary `ReadTimeout`. A second accepted probe returned both historical panels successfully and repeatably, showing this was a transient transport/provider event rather than missing historical semantics.

Production hardening added `BoundedRetrySession`:

- maximum **3 attempts** per logical HTTP request;
- retries only transport timeout/connection failures and provider HTTP 5xx;
- 401/403/429 and other non-5xx responses are never multiplied by the retry layer;
- deterministic short backoff;
- total HTTP attempts and retry events are recorded in universe selection diagnostics;
- exhausted transport retries fail the run closed rather than silently choosing stale data.

Offline/adversarial CI after this remediation:

- Stockbit adversarial + retry suite: **33/33 PASS**
- GitHub Actions run: `32457752297`
- job: `96698228705`

Full repository CI at the same head:

- **79 passed, 1 skipped, 1 failed**
- the sole failure is the pre-existing unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` expectation mismatch (`2` conflicts emitted vs `1` expected)
- no Stockbit/Zapi test failed.

## Operational implications

With the actual 25,000-request monthly account limit, the acquisition scheduler must retain material reserve for:

- stock-summary universe requests;
- transient bounded retries;
- scheduled Stream calls;
- occasional provider errors that still consume quota.

Do not use repeated `/post` dereferences, repeated cache probes, or provider acceptance tests as recurring CI. The live acceptance job was intentionally removed from recurring PR CI after evidence was obtained.

The exact final universe/cadence remains a separate design decision. Current discussion favors a **structural majority (persistent liquidity + market capitalization) with a smaller social/discovery component**, rather than pure liquidity or meme-stock hunting. That redesign has not been promoted by this provider audit.

## Decision

`PASS_WITH_OBSERVED_LIMITATIONS` means the provider is accepted for continued implementation and prospective sampled behavioral research.

No current Zapi limitation discovered in this audit is a technical project blocker.

Cloudflare R2 bucket-lock / token-scope review is intentionally separate and remains deferred by user instruction.
