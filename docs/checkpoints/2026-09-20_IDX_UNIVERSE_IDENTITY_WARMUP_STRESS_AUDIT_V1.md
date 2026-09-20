# IDX-Trade Universe Identity / IPO Warmup Stress Audit — V1

Date: 2026-09-20  
Status: `STRUCTURAL FAILURES FOUND / NO DATA OR OUTCOME ACCESS`  
Lane: isolated `codex/alpha-available-data-20260919`

This is a read-only adversarial audit of the listing identity, historical
warmup, and dynamic liquidity-universe boundary. It uses only synthetic
fixtures and current branch source. It does not access providers, canonical
datasets, cloud/capture state, telemetry, protected outcomes, or the incumbent
portfolio. No source or configuration change was applied.

## 1. Baseline checks

The existing focused suites passed before the probes:

`tests/test_universe.py`, `test_security_coverage.py`, `test_data_gate.py`,
`test_adversarial_data_gate.py`, `test_tradability_reconciliation.py`, and
`test_tradability_pipeline.py`: **19 passed**.

Those tests cover delisting, ordinary IPO warmup, unknown tradability,
suspension/resumption, missing coverage, and parser integrity. They do not
cover normalized-key collisions, pre-listing observations, or overlapping
listing eras.

## 2. Adversarial probe results

### A. Pre-listing observations count toward IPO warmup — FAIL

Synthetic setup:

- one ticker listed on 2025-04-24;
- 100 observed price dates beginning 2025-01-01;
- as-of date 2025-05-20;
- only 19 observations fall on/after the listing date;
- `minimum_warmup_sessions=60`.

Observed result:

| Field | Result |
|---|---:|
| Post-listing observations | 19 |
| Reported `observed_sessions_since_listing` | 100 |
| Eligibility | `True` |
| Selection | `True` |
| Reason | `ELIGIBLE` |

`universe.py:56-78` counts all deduplicated observations at or before the
as-of date and passes that count into `model_eligibility`; it does not filter
the count, recent observation share, or liquidity median by the applicable
listing interval. The function therefore violates the semantic name
`observed_sessions_since_listing` when the input contains pre-listing bars.

This is a structural warmup and liquidity-contamination path. It does not
prove that any current production input contains such rows.

### B. Normalized ticker aliases create duplicate universe rows — FAIL

Synthetic setup passed both `ALIS` and `ALIS.JK` as separate `price_frames`
keys. `normalise_ticker` maps both to `ALIS`.

Observed result:

| Field | Result |
|---|---:|
| Input keys | `ALIS`, `ALIS.JK` |
| Output rows | 2 |
| Output tickers | `ALIS`, `ALIS` |
| Selected tickers | `ALIS`, `ALIS` |
| Duplicate ticker rows | 2 |

`universe.py:56` iterates raw mapping keys and normalizes each one, but does
not reject or merge normalized-key collisions. A downstream fixed-seat
selection can therefore spend two seats on one ticker, and any consumer that
assumes unique ticker rows receives an ambiguous universe.

### C. Overlapping listing eras are accepted while downstream remains ticker-only — FAIL

Synthetic setup supplied two `REUS` listing rows:

- `IDX:REUS:20200101`, ending 2022-12-31;
- `IDX:REUS:20220601`, open-ended.

At 2022-08-01 both intervals are active.

Observed result:

| Field | Result |
|---|---:|
| Security-master rows | 2 |
| Active security IDs during overlap | 2 |
| `existence_state("REUS", 2022-08-01)` | `LISTED` |
| Input rejected | No |

`security_master.py:33-64` creates distinct `security_id` values but only
deduplicates equal `(ticker, listed_from)` keys; it does not reject overlapping
eras. `existence_state` then collapses the overlap to a ticker-level
`LISTED` state. `universe.py` and `coverage.py` also consume ticker-level
inputs, so the security ID is not sufficient to prevent issuer-era mixing.

This is an identity-integrity gap, not evidence that the synthetic overlap is
an actual IDX event.

## 3. What still works

- Unknown tradability remains fail-closed outside a declared complete window.
- Explicit suspension intervals override a complete-window ACTIVE complement.
- Expected-vs-observed coverage rejects missing active-session bars and
  unexpected non-active bars.
- Corporate-action and price-semantics flags remain hard data-gate blockers.

These PASS surfaces do not repair the three cross-component identity/warmup
failures above.

## 4. System impact

The three paths can interact:

`listing identity -> observed warmup/liquidity -> selected ticker rows ->
fixed-seat portfolio / downstream score universe`

The result is a risk of admitting a name with insufficient post-listing
history, duplicating one issuer into multiple selection seats, or using one
ticker's data across overlapping issuer eras. The downstream Decision and
Sizing layers cannot be expected to correct this because they receive the
already-materialized universe/identity boundary.

No predictive metric, protected target, PnL, or incumbent decision was opened;
the impact statement is structural only.

## 5. Recommended hardening, not applied

These are proposed fail-closed changes for a separately authorized lane:

1. In `build_security_master`, reject overlapping listing intervals for one
   normalized ticker, including same-day boundary overlap, unless an explicit
   issuer-identity/era contract is introduced downstream.
2. In `build_dynamic_liquidity_universe`, reject duplicate normalized
   `price_frames` keys rather than silently producing duplicate rows.
3. Resolve the active listing era before counting observations; filter
   warmup, recent active share, and liquidity statistics to that era's
   listing interval.
4. Carry `security_id`/era identity into the universe artifact, or prove a
   single-era invariant before allowing ticker-only consumers.
5. Add these three probes as regression tests only after the intended policy
   is accepted; do not silently change a frozen scientific population.

## 6. Evidence hashes

Source hashes at audit time:

- `src/idx_trade/security_master.py` —
  `C777600F459D69CB2B52C6C4C8EEB61FD22D7AFB1A85645FB63E1D4EBD180B69`
- `src/idx_trade/universe.py` —
  `FCB2A793608826D5EA3BD8D4401A30F743157F8D24ACF20CFD1209CD8C730FC5`
- `src/idx_trade/coverage.py` —
  `0A85F62B5D0379722F82C298C065E05758E0C853F499BE6243FDA6C43F5C8F5A`
- `src/idx_trade/data_gate.py` —
  `E6CCE2F81E3502449DFC804B4881BC3D754FC4814BD436DADCAB8162B4492921`

## 7. Verdict and no-retry boundary

Verdict: `FAIL — UNIVERSE_IDENTITY_AND_WARMUP_BOUNDARY_NOT_PROVEN`.

Do not retry with external data, populate canonical data, rerun alpha or
Decision evaluation, or infer production contamination from these synthetic
counterexamples. The highest-value next step is a policy-authorized,
outcome-blind hardening/test lane for the identity and listing-era contract.

