# INC-001 CA-Aware Feature-Basis Remediation V1 — R3 A-D Audit

Date: 2026-08-27 Asia/Jakarta  
Branch: `data/ca-aware-feature-basis-remediation-v1`  
Source parent: `5f95831949b475bee881be6969838196763375d3`

## Scope

This R3 pass closes the R2 population-scope gap without opening Phase-E. It
reconciles the exact final-fit population, the full primary-liquid
cross-sectional application population on fit dates, the observed-row
backward dependency closure, the old/current support lineage, and KSEI
coverage against all three populations. It also adds fail-closed checks for
strict CA-census completeness, identity uniqueness, and population-scope
attestation.

All work is outcome-blind and offline. Existing immutable local artifacts were
reused; no provider call, historical feature recomputation, model operation,
counter mutation, canonical artifact mutation, or Phase-E run was performed.

## Exact populations

| Population | Rows | Tickers | Dates / interval | Result |
|---|---:|---:|---|---|
| H5 exact final-fit | 239,648 | 629 | 978 dates; 2022-02-11—2026-07-17 | `PASS_IDENTITY_RECONCILED` |
| H10 exact final-fit | 237,976 | 629 | 974 dates; 2022-02-11—2026-07-17 | `PASS_IDENTITY_RECONCILED` |
| Final-fit union | 240,344 | 629 | 980 dates; 2022-02-11—2026-07-17 | `PASS_IDENTITY_RECONCILED` |
| Primary-liquid cross-section application | 276,153 | 716 | 980 fit dates | `PASS_FULL_PRIMARY_LIQUID_ON_FIT_DATES` |
| Cross-section-only beyond final fit | 35,809 | 274 | subset of application | retained, not discarded |
| Observed-row dependency closure | 365,968 | 716 | 2021-04-29—2026-07-17 | `PASS_OBSERVED_ROW_CLOSURE_COMPUTED` |
| Primary-membership dependency closure | 364,189 | 716 | 2021-11-18—2026-07-17 | official-session 60-row window |

The observed-row closure uses actual rows per ticker and frozen feature
offsets; it does not subtract calendar days. The primary-membership closure
uses the frozen official-session window and is retained as a separate audit
dimension.

Observed dependency-family rows are: `atr14=311,480`,
`close_return_20=303,471`, `close_return_5=287,713`,
`relative_volume_20=319,525`, `rolling20=319,525`, and `rolling60=365,968`.
Missing offset counts are `atr14=0`, `close_return_20=184`,
`close_return_5=0`, `relative_volume_20=0`, `rolling20=0`, and
`rolling60=141,257`; missing target counts are `close_return_20=184` and
`rolling60=6,766` (other families zero).

## KSEI reconciliation

The pinned KSEI census is ticker-level only and has no per-session as-of,
date-level no-event, or historical coverage attestation. It therefore cannot
certify any of the three populations as a historical CA source.

| Scope | Population | Present | Certified | Unresolved | Absent | Coverage verdict |
|---|---|---:|---:|---:|---:|---|
| Fit | 629 tickers | 562 | 530 | 32 | 67 | `UNKNOWN_TICKER_ONLY_NO_DATE_ATTESTATION` |
| Cross-section application | 716 tickers | 610 | 567 | 43 | 106 | `UNKNOWN_TICKER_ONLY_NO_DATE_ATTESTATION` |
| Backward dependency closure | 716 tickers | 610 | 567 | 43 | 106 | `UNKNOWN_TICKER_ONLY_NO_DATE_ATTESTATION` |

The KSEI snapshot was retrieved on 2026-08-17. That retrieval timestamp is
not a historical publication/knowledge timestamp and is not promoted to one.

## Structural CA scope

The strict attested census contains 26 rows and is complete for the pinned
input, but no row has certified transition semantics. Family counts are:

```text
STOCK_SPLIT=7
STOCK_DIVIDEND=3
BONUS_SHARES=1
RIGHTS_HMETD=10
MANDATORY_CONVERSION=4
CAPITAL_RESTRUCTURING=1
```

Scope classifications are `OUTSIDE_DEPENDENCY_AFTER_CLOSURE=5`,
`OUTSIDE_DEPENDENCY_TICKER=10`,
`UNRESOLVED_CANDIDATE_BEFORE_CLOSURE=3`, and
`UNRESOLVED_CANDIDATE_IN_CLOSURE=8`. All candidate transition semantics
remain unresolved. The R3 result does not treat a source candidate date as a
generic effective transition date.

The frozen evidence still exposes taxonomy/coverage blockers, including
voluntary-versus-mandatory conversion inconsistency, capital-reduction versus
capital-restructuring mapping, and incomplete merger coverage. The BBCA trace
has exact IDX H/L/C equality for 61 rows, but Open basis continuity remains
unknown and does not certify the backward feature windows.

## Support lineage reconciliation

| Support | Old population | Current Phase-B population | Common | Old-only | Current-only |
|---|---:|---:|---:|---:|---:|
| H5 | 241,487 | 239,648 | 239,648 | 1,839 | 0 |
| H10 | 239,836 | 237,976 | 237,976 | 1,860 | 0 |
| Union | 241,724 | 240,344 | 240,344 | 1,380 | 0 |

The current populations are strict subsets of the old support identities. The
old accepted 56,602-row overlay was measured on the superseded Stage-C
population; its applicability to current Phase-B support is
`NOT_APPLICABLE_UNPROVEN_ON_CURRENT_SUPPORT` and no recomputation was done.

## External R3 artifacts

Root: `D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v3-final`

| Artifact | SHA-256 |
|---|---|
| `MANIFEST.json` | `198b619e7e465597de935837346a6369b0395162bc140fef1eb7ae5f8d0f690e` |
| `r3_summary.json` | `60ad6ad2c04482b09d8384966929d25be68915dfe00c983502d9149178cc41a9` |
| `r3_cross_section_population_reconciliation.csv` | `1048b8efdab7aec7fc623f7d5b45503cf23b42e690fc5add94cfc1bafa3e51e9` |
| `r3_cross_section_ticker_summary.csv` | `67a10103456d158668e2e994c0b89b358c227b357deb491fcd9c914809ebff7d` |
| `r3_backward_dependency_closure.csv` | `5c04428dd3c82d0941310763a770516021b98e05b9ba1d323adc1370af79dc05` |
| `r3_structural_ca_event_scope.csv` | `b44931e3a562db57eed8caa88cad23e357362c2b4ab0b6ff6570b727fd65de4d` |
| `r3_support_lineage_reconciliation.csv` | `58581c431d923e950b892c9d64086795f03064d63952d913ca37d8745b385765` |
| `r3_support_lineage_summary.json` | `462f4162739785810c3b71f18cc022973955e3cf5640fe457b769f296cc4bccf` |
| `r3_ksei_population_scope_reconciliation.csv` | `25668572965acd93864e9b0e4afc83abc18f2f40e8dcfbf0908947dcf9a3beb1` |

The final fresh rerun in
`D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v3-final-rerun`
matched all 9 output hashes: `HASH_MISMATCHES=0`. The rerun manifest and
summary hashes are identical to the final root.

## Frozen verdict

```text
EXACT_FINAL_FIT_POPULATION = PASS_IDENTITY_RECONCILED
CROSS_SECTION_APPLICATION_POPULATION = PASS_FULL_PRIMARY_LIQUID_ON_FIT_DATES
BACKWARD_DEPENDENCY_CLOSURE = PASS_OBSERVED_ROW_CLOSURE_COMPUTED
KSEI_FIT_POPULATION_COVERAGE = FAIL_629_VS_610_NO_DATE_ATTESTATION
KSEI_CROSS_SECTION_COVERAGE = FAIL_716_VS_610_NO_DATE_ATTESTATION
KSEI_DEPENDENCY_CLOSURE_COVERAGE = FAIL_716_VS_610_NO_DATE_ATTESTATION
TEMPORAL_COVERAGE = UNKNOWN_NO_KSEI_PER_SESSION_AS_OF_ATTESTATION
STRUCTURAL_CA_EVENT_SCOPE = FAIL_OR_UNKNOWN_UNRESOLVED_TRANSITION_SEMANTICS
OLD_241724_POPULATION = PRESENT_HASH_PINNED_LEGACY_STAGE_C_SUPPORT
CURRENT_240344_POPULATION = PRESENT_HASH_PINNED_ACCEPTED_PHASE_B_SUPPORT
POPULATION_EQUIVALENCE = FAIL_DIFFERENT_POPULATION
OLD_56602_APPLICABILITY_TO_CURRENT_PHASE_B = NOT_APPLICABLE_UNPROVEN_ON_CURRENT_SUPPORT
STRUCTURAL_CA_FAMILY_COVERAGE = FAIL_PARTIAL_OR_CONFLICTING_FAMILY_EVIDENCE
TRANSITION_SEMANTICS = FAIL_OR_UNKNOWN_ALL_STRICT_EVENTS_UNRESOLVED
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

## Guardrails and validation

```text
outcome_blind = true
target_values_accessed = false
outcomes_accessed = false
provider_calls = false
model_fit = false
model_scoring = false
historical_feature_recompute = false
phase_e_run = false
counter_mutated = false
canonical_artifacts_mutated = false
```

Validation on the final branch worktree:

```text
Focused CA/integrity regression: 95 passed, 0 failed, 0 skipped, 0 warnings
Full pytest: 334 passed, 0 failed, 0 skipped, 0 warnings
py_compile: PASS
git diff --check: PASS
Deterministic fresh rerun: 9/9 output hashes match
```

No Phase-E application, historical CA repair, model refit/score, provider
call, outcome access, counter mutation, or canonical data overwrite is
authorized by this checkpoint. INC-001 remains open audit and the historical
CA-aware admission remains blocked pending family-specific effective-date,
basis, and temporal evidence.
