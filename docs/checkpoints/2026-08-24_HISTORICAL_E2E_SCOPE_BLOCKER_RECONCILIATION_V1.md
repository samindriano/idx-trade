# Historical E2E Scope Blocker Reconciliation V1

Date: 2026-08-24 Asia/Jakarta  
Branch: `research/idx-historical-e2e-replay-v1`  
Mode: outcome-blind, offline diagnostics only

This checkpoint reconciles the already frozen structural/Open/CA ledgers. It
does not alter the frozen execution, target, evaluator, or protected-outcome
contracts.

## Exact support diagnostics

| Gate | Result | Longest consecutive run |
|---|---:|---:|
| All 600 execution-session manifests certified | 600/600 | 600 |
| Every Decision V2 BUY intent has positive certified Open | 376/600 sessions | 34 sessions (`306..339`) |
| CA exposure rows resolved under the accepted strict gate | 4,471/5,693 rows (78.55%) | — |
| CA per-date rate >= 90% | 164/600 dates | 15 dates (`47..61`) |
| Open-ready and CA>=90% intersection | 107/600 dates | 9 dates (`478..486`) |

Across the exact 2,584 decision intents paired to the 600 certified
execution-session artifacts, the acquired Open coverage is:

- BUY: 905/1,297 positive (69.78%); 392 true nonpositive/unavailable;
- SELL: 891/1,287 positive (69.23%); 396 true nonpositive/unavailable;
- missing ticker/session keys: 0.

The prior readiness baseline recorded BUY only (351/1,297, 27.06%) and did
not publish a separate SELL baseline. Positive coverage is therefore an
acquisition improvement, not a claim that nonpositive rows can be filled.

The CA exposure diagnostic is the accepted external ledger:

- path: `D:\Documents\Project\idx-historical-e2e-replay-readiness-20260823-v6\ca_exposure_gap.csv`
- ledger SHA-256: `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`
- policy: absence does not prove no event

The Open support result is read from the existing strict-scope output:

- path: `D:\Documents\Project\idx-historical-e2e-scope-freeze-20260824-v1\REPLAY_SCOPE.json`
- scope payload SHA-256: `40d538417b8c48dd95455ab425d4af20939f28a44f4c1cceeea876e26c5dcba3`
- status: `STRICT_SCOPE_EMPTY_BLOCKED`

## Consequence for the frozen replay contract

The required historical paper replay contract needs 6 blocks of 100
consecutive eligible signal sessions. The strongest current outcome-blind
intersection is only 9 consecutive sessions. It is therefore not defensible
to run historical performance, NAV, or Monte Carlo metrics by selecting a
shorter interval, dropping unresolved rows, or relaxing the CA/Open gates.

The dividend source lane independently remains incomplete:

- the required universe is 347 tickers;
- the bounded official IDX acquisition stopped fail-closed at HTTP 403 after
  partial progress;
- no market-wide no-event proof exists.

## Verdict

`TRUE_HISTORICAL_E2E_SCOPE_NOT_FEASIBLE_UNDER_CURRENT_FROZEN_ARTIFACTS`

This is a data-readiness conclusion, not a model-performance result. No
protected outcomes, labels, realized returns, scores, or model fits were
opened.

The only scientifically valid ways forward are to obtain new official
evidence under a separately reviewed remediation contract, or to close this
historical replay attempt as data-blocked. No metric run is authorized by
this checkpoint.
