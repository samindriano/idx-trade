# IDX CA-Aware Feature-Basis Remediation V1

Status: `ACTIVE`
Date: 2026-08-27 Asia/Jakarta

Implementation branch: `data/ca-aware-feature-basis-remediation-v1`
Draft stacked PR: `#108`
Implementation HEAD: `faa42315b8efe41dea21da9d19fa7fd15db0a8bb`
Base / controlling QA lane: `audit/research-integrity-data-qa-gate-v1` / PR `#103`
Incident: `INC-001 — Historical CA / backward feature price-basis integrity`

## Scope

Outcome-blind implementation/application of the frozen `CA_AWARE_FEATURE_BASIS_POLICY_V1` only.

Current implementation checkpoint:
`docs/checkpoints/2026-08-27_CA_AWARE_FEATURE_BASIS_REMEDIATION_V1_IMPLEMENTATION.md`

Validated implementation primitives include exact backward dependency geometry, resolved basis epochs, bounded/unbounded transition fail-closed handling, explicit CA no-event coverage admission, event semantic certification, and safe strict-census / coverage adapters.

PR #108 exact-head CI for `faa42315...`: **282 passed, 0 failed**, run `32996260760`. Four warnings are pre-existing tradability NumPy timedelta deprecation warnings.

An earlier pre-fix run exposed a faulty synthetic test fixture for rolling-60 recovery: the transition was placed before a complete 60-observation pre-event warmup. The fixture was corrected without weakening admission logic.

## Current boundary

Historical application remains blocked on source-backed event-family semantics, transition sessions/bounds, and market-wide structural-CA no-event coverage.

Do not duplicate this remediation lane or silently infer transition dates from listing/record dates or price jumps.

## Explicit non-authorizations

- no protected target/outcome access;
- no V4-X1 fit/refit/tuning/scoring;
- no prospective counter reset/mutation;
- no generic historical H/L/C adjustment;
- no generic split-style rights/bonus/conversion handling;
- no provider writes/calls for remediation;
- no production capture/runtime changes;
- no canonical historical artifact overwrite.
