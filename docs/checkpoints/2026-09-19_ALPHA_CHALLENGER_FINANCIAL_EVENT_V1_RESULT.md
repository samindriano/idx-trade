# Alpha Challenger — Financial Reporting Event V1 Result

Status: `NO-GO / EXACT FIXED CHALLENGER`

Preregisration: `2026-09-19_ALPHA_CHALLENGER_FINANCIAL_EVENT_V1_PREREGISTRATION.md`  
Branch: `codex/alpha-challenger-pit-safe-20260919`

## PIT and materialization

The accepted Financial Representation V2 bundle passed the constructor's
invariants:

- selected CORE3 rows: `70,520`
- selected tickers: `321`
- selected dates: `525`
- distinct transition events: `1,211`
- event tickers: `286`
- event rate among CORE3 rows: `1.7172%`
- event rate on accepted V4-X1 historical score support: `0.7124%`
- same-bundle violations: `0`
- knowledge-time violations: `0`
- selected provenance-incomplete rows: `0`
- all non-missing feature values finite: `YES`

The builder was corrected before this run so a reporting event appears only on
the first decision row of a new state, not on every subsequent day. Focused
challenger tests: `8 passed`.

## Historical comparison

The diagnostic used the accepted V4-X1 historical validation scores and target
ledger through `2026-07-17`, on `152,171` exact common-support rows and `600`
valid dates. No fresh/protected/O2 outcomes, provider calls, model fitting, or
runtime mutation occurred.

| Score | Mean daily IC | Q25 daily IC |
|---|---:|---:|
| Accepted incumbent | `0.09755404` | `-0.01019388` |
| Financial event overlay | `-0.00157506` | `-0.06265427` |
| Fixed 90/10 blend | `0.09755339` | `-0.01021893` |

Fixed-blend paired evidence:

- mean delta: `-0.00000064`
- q25 delta: `0.0`
- positive daily deltas: `113/600`
- non-negative daily deltas: `475/600`
- non-negative 20-session blocks: `18/30` (`60%`)
- exact common-support coverage: `100%`

Economic diagnostic:

- mean top-30 overlap with incumbent: `99.7722%`
- mean top-30 churn: `0.2278%`
- top-30 churn q95: `3.3333%`

## Verdict

`FINANCIAL_EVENT_V1_NO_SURVIVOR`.

The candidate was PIT-safe, genuinely orthogonal at the score level, and cheap
in turnover, but it did not improve IC or stability. The exact event
specification is closed. No alternate weights, ratio subsets, windows,
horizons, model fits, or rescue searches were run.

V4-X1, Decision V2, prospective evaluation, runtime, counters, and forward
financial data remain unchanged.
