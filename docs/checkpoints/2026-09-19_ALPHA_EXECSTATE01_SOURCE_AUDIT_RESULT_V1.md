# EXECSTATE-01 Official Execution-State Surface — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `SOURCE_PARTIAL_STRUCTURAL_SIGNAL / NOT_ADMITTED / NO CANDIDATE`

## Decision

The official execution/no-trade sidecar is internally coherent and provides a
useful execution-state diagnostic. It is not admitted as alpha data. The
available artifact establishes regular-market state labels and a distinct
population with non-regular activity, but it does not establish exchange
semantics, completeness, row-level available-at time, revision/vintage
behavior, or executable capacity.

No target, outcome, IC, ICIR, OOS, predictive comparison, candidate ID, or
production/status change was created.

## Source quality profile

- Source: official IDX execution/trade-state artifacts under
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\execution_1260\`.
- Grain: `(ticker, as_of_date)`; market is regular in the retained anchor
  table.
- Anchor rows: `1,104,064`; tickers: `980`; official dates: `1,260`.
- State counts: `982,398 ACTIVE`; `121,666 NO_TRADE`.
- Required keys and source fields are non-null; anchor keys are unique; state
  values are limited to the registered state set.
- Session report covers `1,260 / 1,260` sessions, with zero unresolved
  sessions and exact active/no-trade sums.
- Raw cache rows match the retained anchor inventory exactly: `1,104,064`;
  cache-only rows: `0`.
- Anchor/panel overlap: `981,940`; panel-only rows: `0` in the audited join.

The regular-market state rules are internally consistent: every `NO_TRADE`
row has zero regular volume/frequency/value, while every `ACTIVE` row has all
three positive. This is a source consistency result, not proof that the label
means suspension, illiquidity, or inability to execute a strategy.

## Structural diagnostics

- `NO_TRADE` rows with positive non-regular activity: `4,647`, across `1,200`
  dates and `340` tickers.
- `ACTIVE` rows with non-regular activity: `146,545`.
- State transitions: `26,100`, across `583` tickers; maximum transitions for a
  ticker: `374`.
- The eligible-universe diagnostic contains `310,761` rows and zero eligible
  `NO_TRADE`/non-regular rows because the current eligible-universe contract
  requires positive regular activity. This prevents treating the diagnostic
  as a predictive signal.

The non-regular activity split is a useful audit lead, but it is not itself a
tradability, liquidity, or alpha claim. A separate suspension reconciliation
below shows that `NO_TRADE` cannot be equated to suspension from the currently
available evidence.

## Disposition and blockers

| Gate | Result |
|---|---|
| Schema/source/market/state validity | `PASS` |
| Key uniqueness and raw-cache exactness | `PASS` |
| Official-session/session-report reconciliation | `PASS` |
| Regular activity/state arithmetic | `PASS` |
| Exchange definition of `ACTIVE`/`NO_TRADE` | `UNKNOWN` |
| Population completeness and row-level available-at | `UNKNOWN` |
| Revision/vintage behavior | `UNKNOWN` |
| Security identity/issuer transition chain | `UNKNOWN` |
| Predictive admissibility | `NOT ADMITTED` |

The artifact is retained as a provenance-backed structural capability. Do not
forward-fill, reinterpret `NO_TRADE` as suspension, create a liquidity
feature, or promote it into a candidate without an explicit exchange semantic
contract and PIT/revision/identity evidence.

## Reproducibility and firewall

- Preregistration: `docs/checkpoints/2026-09-19_ALPHA_EXECSTATE01_SOURCE_PREREGISTRATION_V1.md`.
- Generator: `research/alpha_execstate01_source_audit_v1.py`; SHA-256
  `3311ded213d6a134dfe6a6d959e0f188f0795294a0d66890f18ff5cc6f8fdfe2`.
- Result JSON SHA-256:
  `c995bc572f658406c73d7150616a1492977be4f41260d657d7dba465a51b0e4f`.
- Independent verifier: `research/verify_alpha_execstate01_source_audit_v1.py`;
  SHA-256 `1f5479a951fd266c6d3afacfc02439dc455deecbee13c9041291b9bec2c473b3`.
- Independent verification: `PASS`; output SHA-256
  `ea173d9b721c6278b0f7b7f9cfe3381d4092e7e459b56aa2ee2cccc102d25f91`.
- Hash-contract output SHA-256
  `f2cf0aec82b71ec0bf2b99704d5e5f3beb47fdb0e57f22fa650b4197b878469f`;
  status `PASS`.
- Generator target/privacy firewall output SHA-256
  `efaf3c305dd4aabaaf742f2a389771267399c132395e51227cb9271c2e7023e9`;
  status `PASS`.
- Independent-verifier target/privacy firewall output SHA-256
  `774071cadb9907b2408a720fa7eb0c0ec120804766e8b349fe2d7e78342bce18`;
  status `PASS`.

The generator firewall hash above is recorded from the final staged artifact;
the displayed value contains no spaces in the actual SHA-256. No target,
provider, cloud, incumbent predictive data, canonical data, capture,
scheduler, or production artifact was accessed or modified.

## Next allowed action

The highest-value follow-up is the narrow `SUSPSTATE-01` reconciliation. If
that remains unresolved, retain EXECSTATE-01 as a structural source only and
do not retry with alternate interpretations or provider fallback.
