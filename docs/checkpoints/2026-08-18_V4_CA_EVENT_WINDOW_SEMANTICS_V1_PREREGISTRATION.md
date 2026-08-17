# V4 CA Event-Window Semantics V1 — Preregistration

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-ca-event-window-semantics-v1`
Scientific code anchor before any new local/provider run: `8fa65f3bdcefd5c41d6b082e5df27a5ccd185007`
Parent KSEI census: `data/idx-v4-ksei-ca-history-census-v1@aef9037240849a3bba0b16838f3827e389ce9711`
Status: `PREREGISTERED_OUTCOME_BLIND_NO_EVENT_WINDOW_RUN_YET`

## Purpose

V4 requires price-basis continuity only across each exact target interval,
`Open_(t+1) -> Close_(t+5/t+10)`. The prior KSEI gate deliberately used a
more conservative ticker-period quarantine: one active mechanical/unknown CA
in the broad V4 period quarantined that ticker on every frozen date. That was
a valid fail-closed acquisition gate, but it is not the final pathwise test.

This generation replaces only that coarse quarantine with predeclared,
event-window-specific evidence rules. V4 target, folds, learner, evaluator,
90% coverage gate, and promotion thresholds are unchanged.

## Frozen inputs

- blocked continuity ledger SHA-256: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`;
- prior event evidence SHA-256: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`;
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- KSEI census manifest SHA-256: `7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25`;
- exact KSEI history SHA-256: `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`.

Frozen population remains 610 tickers / 600 validation dates / 344,790 H5+H10 continuity rows.

## Official semantic evidence reviewed before freeze

Official KSEI schedules explicitly separate regular/negotiated-market Cum and
Ex dates for HMETD, share dividend, mixed cash/share dividend, and bonus
shares. Official stock-split schedules separately identify the last regular
trading date on the old nominal basis and the first regular trading date on
the new nominal basis. Recording Date and C-BEST Distribution/Effective Date
can occur later, so they are not admitted as generic market-price transitions.

## Tier 1 — static exact semantics

For active KSEI rows of entitlement families (`Right Distribution`, `Stock
Dividend`, mechanically identified stock component of `Mixed Dividend`, and
bonus-share source labels), a static transition is admitted only when the
source-native Cum Date exists and is an exact official exchange session. The
transition is the first official exchange session strictly after Cum Date,
interpreted as the regular-market Ex boundary. No calendar-day inference is
used.

`Mixed Dividend` is decomposed using the source-native ratio denomination:
ratio right security equal to the ticker is a stock component; a currency is a
cash component and not a V4 price-basis blocker; anything else requires exact
schedule evidence. Cancelled/inactive events, Cash Dividend, and Proxy Voting
are non-blocking.

## Tier 2 — exact official schedule evidence

Mandatory Conversion, Voluntary Conversion, split/reverse/merger/restructuring
labels, entitlement rows without an admitted Cum Date, and unknown active
source types require an explicit official KSEI schedule.

Only `REGULAR_MARKET_EX_DATE` or
`REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` can be admitted. Exact linkage
requires exact ticker, compatible family, KSEI reference, source SHA-256, and
at least one exact Record Date or Distribution Date match between the
immutable static-history event and the schedule document. Record/Distribution
matching is identity evidence only and never the transition fallback.
Conflicting exact transition dates remain unresolved.

## Window rule

For exact transition `d`, the target interval is unresolved iff
`entry_date < d <= terminal_date`. Entry exactly on `d` is already on the
post-event basis. A relevant event still lacking exact transition evidence
fails closed. KSEI coverage failures and the existing cross-source conflict
also remain fail-closed.

The old 60-calendar-day halo is used only to select which source-history rows
need event-evidence work. It never fabricates or bounds a transition.

## Gate and staged execution

Every frozen date must have H5, H10, and exact H5∩H10 consensus continuity
coverage >= 90%. No average-date rescue.

1. Run `scripts/run_v4_ca_event_window_support.py` without schedule evidence.
   This is offline/provider-free and emits the exact schedule-evidence need set.
2. If all 600 dates pass, stop for review and make no provider call.
3. Otherwise only `scripts/run_v4_ca_schedule_acquisition.py` is authorized,
   using official public KSEI schedule index/documents for that frozen need set.
4. Rerun the same support runner with exact schedule evidence, then stop.

No source/config edits are permitted after Stage 1 exposes support results in
this generation. Bugs fail closed and require separately documented
remediation; semantics cannot be tuned to rescue coverage.

## Prepared implementation

- `config/v4_ca_event_window_semantics_v1.json`
- `src/idx_trade/v4_ca_event_windows.py`
- `src/idx_trade/v4_ca_schedule_semantics.py`
- `scripts/run_v4_ca_event_window_support.py`
- `scripts/run_v4_ca_schedule_acquisition.py`
- `tests/test_v4_ca_event_windows.py`
- `tests/test_v4_ca_schedule_semantics.py`
- `tests/test_v4_ca_schedule_dates.py`

## Hard prohibitions

No R5/R10, target ranks, model fit, predictions, IC, Top30, spread, bootstrap
performance, price-derived CA inference, alternate provider, protected/fresh
forward outcome access, V4 threshold changes, or post-result semantic tuning.
