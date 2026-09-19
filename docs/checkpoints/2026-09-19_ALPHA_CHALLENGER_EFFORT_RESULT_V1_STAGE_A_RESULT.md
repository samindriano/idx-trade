# Alpha Challenger — Effort vs Result V1 Stage A Result

Status: `STAGE_A_COMPLETE / STAGE_B_BLOCKED`

Branch: `codex/alpha-challenger-pit-safe-20260919`  
Base: `1537ba35e79c73e64fee19d499190f529122403b`

## What was checked

The new feature constructor was run against the read-only accepted clean panel
from the preregistration. No target, label, outcome, model score, prospective
artifact, provider, or forward counter was read.

Focused tests: `4 passed`.

Outcome-blind materialization:

- panel rows: `981,940`
- feature rows: `981,940`
- keys preserved exactly after ticker/date sorting: `YES`
- dates: `2021-04-29` through `2026-07-31`
- tickers: `945`
- prior-history-ready rows: `99.0376%`
- failed-breakout nonzero rows: `5.7839%`
- confirmed-breakout nonzero rows: `7.5120%`
- all non-missing candidate values finite: `YES`

Feature missingness:

| Feature | Missing |
|---|---:|
| `effort_signed_body` | 49.5719% |
| `effort_close_location` | 10.5132% |
| `range_per_effort` | 0.9624% |
| `failed_breakout_signed` | 0% |
| `confirmed_breakout_signed` | 0% |
| `effort_absorption` | 49.5719% |

The high missingness of body-based features is expected from the panel's
unavailable Open rows. The constructor leaves these values missing; it never
forward-fills or substitutes an Open.

## Findings

Three proposed effort transforms are not sufficiently orthogonal as currently
defined:

- `range_per_effort` has absolute Spearman correlation `0.999291` with its
  log-relative-volume component.
- `effort_absorption` has absolute Spearman correlation `0.904488` with the
  same component.
- `effort_signed_body` has absolute Spearman correlation `0.098344` with its
  strongest listed component, so it is less redundant but remains sparse.

The two event states are more distinct from the basic components:

- `failed_breakout_signed` strongest listed component correlation: `0.154189`
- `confirmed_breakout_signed` strongest listed component correlation: `0.306385`

There are `2` rows where `open_available=True` but `open` is missing. They are
flagged as `open_metadata_mismatch`; they are not repaired or silently treated
as usable Open data.

## Gate

`STAGE_A_PASS_FOR_CAUSAL_CONSTRUCTION_ONLY`.

`STAGE_B_NO-GO_FOR_NOW`: the frozen six-feature family should not be promoted
to a historical model test. The effort transforms fail the intended
orthogonality screen, while the event subset would be a new hypothesis and may
not be selected post hoc. In addition, the available clean panel's derived
price/trend provenance and authoritative decision-universe join must be closed
before historical target access.

The incumbent V4-X1 model, its artifacts, the prospective evaluator, runtime,
forward data, and counters were not modified or rescored.
