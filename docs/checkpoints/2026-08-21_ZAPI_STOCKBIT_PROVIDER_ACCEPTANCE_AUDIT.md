# Zapi / Stockbit Provider Acceptance Audit

Date: 2026-08-21  
Scope: prospective Stockbit Stream acquisition dependency only  
Owner: ChatGPT / independent provider acceptance audit  
Status: `LIVE_ACCEPTANCE_PROBE_PENDING`

## Purpose

This audit is not a model experiment. It tests whether the Zapi dependency can support the prospective Stockbit research lane without discovering a basic provider limitation only after significant data accumulation.

The audit must remain outcome-blind. It may inspect provider responses, schema, timestamps, quota telemetry, cache/repeat behavior, and referential integrity. It must not access returns, targets, model scores, O2, protected outcomes, or forward counters.

## Known concerns recorded before the live probe

1. `finance:stockbit/stream` is a latest-page endpoint, not a documented historical firehose. Completeness of all Stockbit posts is therefore not assumed.
2. Stream `createdAt` examples do not carry an explicit timezone. Collector receipt time remains the authoritative prospective availability timestamp unless source-time semantics are separately proven.
3. Stream depth and `count` behavior have not yet been live-tested beyond the bounded smoke.
4. Stable post IDs are useful only if the documented `/post?id=...` endpoint dereferences the same post content in practice.
5. Zapi adds an outer `project/timestamp/data` response envelope in current REST traffic; the provider adapter must tolerate this while preserving exact raw bytes.
6. Historical IDX stock-summary must honor the exact requested date and return a complete one-page market panel before it can drive runtime universe selection.
7. Published pricing/quota documentation is not the operational authority. The account's live `get_account` and `get_usage` telemetry is authoritative.
8. Cache behavior must not be treated as a guarantee of exhaustive observation. Immediate-repeat stability is diagnostic only.
9. Unknown-symbol and invalid-auth paths must fail without provider 5xx or accidental success.
10. Zapi/Stockbit remains an optional prospective behavioral-data dependency; core alpha/runtime architecture must not require this provider to function.

## Live acceptance gates

Hard PASS requirements:

- invalid API key returns 401;
- historical stock-summary returns HTTP 200, provider `idx`, dataset `stock-summary`, exact requested row dates, unique StockCode rows, and internally complete row-count metadata;
- both supported date formats resolve to the requested session;
- BBCA, GOTO, and DADA Stream probes return HTTP 200 with provider `stockbit`, exact requested symbol, unique post IDs, declared count equal to returned item count, and valid minimum item schema;
- Stream `count` probes never return more rows than requested;
- one Stream post ID dereferences through `/post` to the same ID and content bytes;
- an intentionally unknown symbol does not cause a provider HTTP 5xx;
- live quota telemetry can be read before and after the probe.

Soft diagnostics, not hard gates:

- exact number of Stream rows returned at count 50/100;
- whether smaller-count result IDs are exact prefixes of larger-count results;
- whether immediate repeats return identical IDs under cache;
- weekend stock-summary behavior;
- whether source `createdAt` includes an explicit timezone;
- observed billable quota delta versus raw HTTP request count.

## Decision rule

`PASS_WITH_OBSERVED_LIMITATIONS` means the provider is accepted for prospective sampled behavioral research under the documented limitations above. It does not imply complete Stockbit-history coverage.

`FAIL_PROVIDER_ACCEPTANCE` means the Stockbit acquisition lane stays blocked until the failing provider contract is remediated or replaced.

Cloudflare R2 bucket-lock / token-scope review is intentionally separate and remains deferred by user instruction.
