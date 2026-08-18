# Ranking V4-3 — Corporate Action Training-Domain Gate Prep

Date: 2026-08-18
Branch: `research/idx-ranking-v4-3-ca-training-domain-v1`
Status: `PRE_TARGET_CORRECTION_READY_FOR_LOCAL_OUTCOME_BLIND_RUN`

## Why this correction exists

The accepted V4-3 CA admission bridge proved that the final Corporate Action
replay passes the frozen 600 validation-date CA-only gate.  A subsequent
pre-target audit found that this is not sufficient for the preregistered
walk-forward experiment:

1. each fold trains on all earlier H5/H10 target-eligible dates before its
   official-session purge boundary;
2. the final CA continuity ledger was materialized only for the frozen 600
   validation dates, not the earlier training domain;
3. target availability requires the row-level intersection of market/Open/Close
   observability and CA continuity.  Two independent >=90% gates do not imply
   that their row-level intersection is >=90%.

No historical V4 return, target rank, prediction, model fit, or performance
metric has been accessed yet, so this correction is still pre-target and does
not contaminate the frozen experiment.

## Frozen scientific behavior retained

- H5 = `Close(t+5) / Open(t+1) - 1` and H10 = `Close(t+10) / Open(t+1) - 1` remain unchanged, but this runner does **not** compute either return.
- Primary-liquid universe construction is unchanged.
- Exact official-session offsets and 10-session fold purge remain unchanged.
- Date target-support gate remains exactly `>= 0.90`.
- Missing CA coverage is fail-closed.
- Final CA event semantics are reused unchanged, including exact FREN 2024-04-17 PMHMETD V and 2025-04-16 merger boundaries, ADRO exact entitlement evidence, MEGA official event evidence, and the accepted KSEI schedule semantics.
- No price inference, record-date inference, EXCL stitching, provider call, network call, target materialization, model fitting, prediction, performance access, or protected-forward access is authorized by this prep step.

## New outcome-blind outputs

The local runner `scripts/run_v4_3_ca_training_domain_gate.py` writes only:

- `v4_3_ca_training_domain_continuity.csv` — CA status/reason per ticker, signal date, horizon;
- `v4_3_full_target_support_rows.csv` — boolean Open/Close/CA support only;
- `v4_3_full_target_support_per_date.csv` — H5/H10/consensus support counts/rates and >=90% eligibility;
- `v4_3_training_date_sets.csv` — exact H5/H10 training-date identities per fold under the frozen purge boundary;
- `v4_3_ca_training_event_semantics.csv` — event-semantics audit;
- `summary.json` and `MANIFEST.json` with immutable hashes and guardrails.

The runner explicitly fail-closes historical-only primary-liquid tickers absent
from the accepted 611-ticker CA census rather than silently dropping them.

## Pass conditions

The correction returns
`V4_3_CA_TRAINING_DOMAIN_PASS_READY_FOR_HISTORICAL_EXECUTION_PIN` only if:

1. all frozen 600 validation dates remain H5/H10/consensus eligible after the
   **combined** support intersection;
2. the final 600 consensus-eligible identities remain byte-for-byte the frozen
   tail-600 sequence;
3. there are no newly eligible sessions after the frozen validation end;
4. every fold has a non-empty exact H5 and H10 training-date set before its
   preregistered purge boundary.

A failure does not trigger retuning or a waiver.  The emitted diagnostics must
be reviewed outcome-blind to determine whether the blocker is historical-only
CA census coverage, unresolved exact event schedules, cross-source conflict, or
combined price-support/CA intersection.

## Local inputs

The runner reuses the already pinned V4-3 support inputs and final CA parents.
Expected roots from the accepted local lineage are:

- canonical artifact root: `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`
- Open derivative root: `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_derivative_v1_20260811`
- accepted Open recovery overlay: `D:\Documents\Project\idx-open-ca-scale-reconstruction-20260817-v1`
- security master: `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260\20260809\security_master_1260.csv`
- PIT support root: `D:\Documents\Project\idx-v4-3-pit-support-refresh-20260817-v1`
- final FREN/CA root: `D:\Documents\Project\idx-v4-ca-fren-ksei-exact-20260818-v1`
- CA admission root: `D:\Documents\Project\idx-v4-3-ca-admission-20260818-v1`

The material-six and ADRO parent roots remain the same immutable roots used by
the accepted FREN final replay.

## Boundary after local run

Do not materialize R5/R10 or fit V4-3 until this new manifest is reviewed and,
if PASS, pinned into the final historical execution runner.  This is a
correction to pre-target admission completeness, not a new hypothesis or model
variant.
