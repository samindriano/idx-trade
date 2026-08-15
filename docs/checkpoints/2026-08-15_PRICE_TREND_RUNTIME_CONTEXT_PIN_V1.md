# Price / Trend Runtime Context Pin V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/price-trend-runtime-context-pin-v1`

Status: `CONTEXT_IDENTITY_PINNED_LOCAL_RUNTIME_ADAPTER_REQUIRED`

Verdict: `PRICE_TREND_RUNTIME_CONTEXT_IDENTITY_RESOLVED`

## Purpose

Resolve the only remaining blocker in the accepted Price / Trend Forward Sidecar V1: the exact scientific identity of the historical H/L/C/Volume warm-up context and the official post-2026-07-31 session bridge.

No data are recaptured and no provider is called in this lane.

## Parent contracts

Accepted Price State implementation:

`research/idx-price-trend-confirmation-state-v1@a33863953b4521dd4549a3089f0da2cfdfb6dcd3`

Independent Price State acceptance:

`review/idx-price-trend-confirmation-state-v1-acceptance@0c3b221fcecf035add4d0c7ce388ff4b9d6d27da`

Accepted forward sidecar engineering:

`integration/price-trend-state-forward-sidecar-v1@a4d19fd1615c4a9f9988ed16540c34f5efbe1b1a`

Independent sidecar acceptance:

`review/idx-price-trend-forward-sidecar-v1-acceptance@ae3eea14e526c27e18c035e047db524a4b566be6`

Sidecar verdict was `PRICE_TREND_FORWARD_SIDECAR_V1_ACCEPTED_RUNTIME_CONTEXT_PIN_REQUIRED`.

## Exact historical market parent — reuse, do not fork

Price State V1 must reuse the exact Clean-V2 causal market panel already used and accepted by Foreign Flow Representation V2. This prevents a second historical price lineage.

| Role | Path | SHA-256 | Accepted evidence |
|---|---|---|---|
| Clean-V2 causal market panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` | Foreign Flow Representation V2 offline census |
| historical official exchange calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` | 1,260 sessions, 2021-04-29..2026-07-31 |

The accepted Foreign Flow V2 runner required the market panel to expose at least:

`ticker`, `date/session_date`, `high`, `low`, `close`, `volume`, `regular_market_value`.

Price State consumes only the H/L/C/Volume subset. It must not use `regular_market_value`, Open, adjusted price, labels, outcomes, or model-support-only subsets.

The 292k Clean-V2 H10/model-support table is **not** the historical parent for Price State. The full causal panel above is the only authorized historical market parent for this V1 runtime context.

## Exact post-cutoff official calendar bridge

The accepted Foreign Flow context-bridge remediation established a separate immutable official calendar for the post-2026-07-31 seam:

| Role | Path | SHA-256 | Range |
|---|---|---|---|
| bridge extension calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge\calendar\ranges\2026-07-31_2026-08-13\exchange_sessions.csv` | `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e` | 2026-07-31..2026-08-13, 10 sessions |

Calendar seam rules already validated by the Foreign Flow bridge lane:

- historical calendar and bridge calendar overlap exactly at `2026-07-31`;
- no other overlap is permitted;
- in-memory union contains 1,269 sessions;
- combined range is `2021-04-29..2026-08-13`;
- combined session-set SHA-256 is `dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`;
- verified source-to-target transition is `2026-08-12 -> 2026-08-13`.

No new combined calendar file should be written. The combined calendar is an in-memory construction only.

## Extension market-context source policy

Price State requires market H/L/C/Volume only. It must reuse the already preserved market artifacts under the accepted Foreign Flow context bridge rather than recapturing the gap.

For official sessions after the historical cutoff and through source `t`:

1. `2026-08-03` through `2026-08-10`: use exactly one verified bridge-only market artifact from:
   `forward_monitoring/context_bridge/sessions/<YYYY-MM-DD>/market_context.parquet`.
2. `2026-08-11` onward: require valid canonical EOD `DATA_READY` `model_input.parquet`.
3. A valid canonical artifact and a valid bridge artifact for the same bridge-eligible session is ambiguous and must fail closed.
4. An invalid canonical 2026-08-10 artifact may be bypassed only by the already separately preserved and hash-verified bridge artifact; canonical bytes are never rewritten.
5. Missing official extension sessions fail closed. No calendar compression, weekday inference, forward fill, or synthetic HLCV is allowed.

The accepted bridge calendar remediation records that bridge context resolves 2026-08-03..2026-08-10 and canonical EOD resolves 2026-08-11 and 2026-08-12.

## Bridge artifact contract to reuse

Bridge sessions are valid only if their existing manifest verifies all of the following:

- `status == FOREIGN_FLOW_CONTEXT_BRIDGE_READY`;
- `schema == idx-trade/foreign-flow-forward-context-bridge-v1`;
- `bridge_only == true`;
- `canonical_session_repair == false`;
- exact session date;
- bridge calendar path and SHA equal the pinned calendar above;
- `outcome_blind == true`;
- `forward_outcomes_accessed == false`;
- exact `market_context.parquet` hash;
- raw Stock Summary and Foreign Flow hashes remain valid as bridge provenance even though Price State consumes only market HLCV;
- Stock Summary completeness remains `COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE`.

Price State must use these bridge bytes read-only. No bridge provider/capture entrypoint is authorized.

## Canonical EOD contract to reuse

Canonical sessions are valid only through their existing session manifest:

- `status == DATA_READY`;
- exact session date;
- `outcome_blind == true`;
- `forward_outcomes_accessed == false`;
- exact canonical `model_input.parquet` path and SHA;
- the parent session's own calendar path and SHA still verify;
- the session belongs to that parent calendar.

Price State must not require the canonical operator calendar to equal the bridge-extension calendar. These are intentionally different authorities. Target/source timing comes from the pinned historical + bridge in-memory session union; canonical parent calendars are verified only against their own capture-time pins.

## Controlled target

The first authorized mechanical runtime smoke target for this context is the already established transition:

- source: `2026-08-12`;
- feature session: `2026-08-13`.

The canonical target `2026-08-13` session directory/data are not required.

The smoke is **not** historical performance evaluation. It may inspect only artifact schema, row/ticker counts, state distributions, timing/provenance, hashes, and idempotency.

## Why the existing sidecar entrypoint cannot be used unchanged

`produce_session_price_trend_state()` from Forward Sidecar V1 assumes one forward calendar path must equal each canonical parent manifest's calendar path. That is intentionally too strict for this already accepted bridge architecture:

- bridge extension calendar is an immutable 2026-07-31..2026-08-13 evidence range;
- canonical EOD sessions preserve their own operator-calendar SHA observed at capture time.

Therefore the next adapter must be bridge-aware and read-only:

`historical full panel + bridge market sessions through 2026-08-10 + canonical model_input sessions after 2026-08-10 -> accepted Price State materializer`.

Do not weaken the existing producer to silently accept arbitrary calendars. Add a separate controlled runtime-context adapter with explicit source policy instead.

## Runtime root resolved

All pinned artifacts above share the existing runtime/data root:

`D:\Documents\Project\idx-trade-data-gate-20260808v`

This path is evidence from the accepted Foreign Flow bridge remediation, not a guessed local path.

## Current readiness

- historical scientific parent identity: **RESOLVED**;
- historical calendar identity: **RESOLVED**;
- bridge-extension calendar identity: **RESOLVED**;
- bridge/canonical source policy: **RESOLVED**;
- source-to-target smoke transition: **RESOLVED**;
- sidecar producer/strict verification mechanics: **ACCEPTED**;
- actual local byte existence/hash recheck at current time: **LOCAL RUNTIME REQUIRED**;
- bridge-aware Price State adapter: **NOT YET IMPLEMENTED IN THIS CHECKPOINT**;
- real smoke: **NOT RUN IN THIS CHECKPOINT**.

## Next authorized boundary

Implement and locally verify one **zero-provider bridge-aware Price State runtime adapter**. It must:

1. hard-pin or explicitly require the exact paths/hashes above;
2. use bridge market context read-only for 2026-08-03..10;
3. use canonical DATA_READY `model_input.parquet` for 2026-08-11..source;
4. reject ambiguity/missing extension sessions;
5. pass only H/L/C/Volume through source `t` to the accepted Price State materializer;
6. write the already accepted immutable prospective sidecar for `t+1`;
7. use a bridge-aware strict verifier that re-establishes the same source policy and all input hashes;
8. execute exactly one source `2026-08-12` -> target `2026-08-13` zero-provider smoke;
9. stop for independent review.

Still prohibited: provider calls, bridge/canonical recapture, scheduler/counter changes, outcome/performance access, threshold tuning, Foreign Flow + Price State combination, WATCH/READY/ENTRY_ELIGIBLE, O2 changes, and HSC/free-float integration.
