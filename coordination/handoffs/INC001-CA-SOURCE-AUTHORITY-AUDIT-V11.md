# Handoff: INC-001 CA Source Authority Audit V1.1

from: MAIN / Codex
to: ChatGPT review
task_id: INC001-CA-SOURCE-AUTHORITY-AUDIT-V11
branch: `data/ca-aware-feature-basis-remediation-v1`
reviewed implementation baseline: `0626b653e273067612631fd3414b579ca93c3763`

## Decision

`NO-GO`: retained evidence is insufficient for full source-authority
admission, so Phase-E remains blocked. This handoff records only local raw
reconstruction and provenance audit. No provider/network, Phase-E,
outcome/target, model fit/refit/scoring, counter, canonical rewrite,
production execution, backfill, or merge occurred. PR #108/#103 remain
unmerged.

## Controlling immutable roots

```text
controlling: D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8
comparison:  D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-final-rerun-v7
```

The two roots have identical hashes for all 11 non-manifest outputs. V8 is the
controlling immutable result; V7 is an immutable comparison intermediate. V8
manifest SHA-256 is
`556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71` and V8
summary SHA-256 is
`e0475e06ec35c513dc383a3b58262954cf8d93245341a6e26ad30034df136fbc`.

## Required results

- Populations: fit `629`, application `716`, closure `716`; closure rows
  `365,968`, `2021-04-29..2026-07-17`.
- Ledger: `553` rows, including `412` primary raw source rows, `101` targeted
  schedule evidence rows, and `40` announcement-byte rows.
- Primary closure event census: `412` physical rows; `136` common with prior
  136, `276` raw-additional, old-only `0`. Forensic/taxonomy findings remain
  separate and do not inflate the physical census.
- Raw transition reconstruction: `121 RESOLVED`, `291 UNRESOLVED`;
  prior exact `42/42` re-proven; `79` newly resolved.
- Strict-26 scope: before had `5 OUTSIDE_DEPENDENCY_AFTER_CLOSURE`; after the
  candidate-date rule those five are
  `UNKNOWN_UNRESOLVED_AFTER_CLOSURE`. Final outside-after count is `0`; all
  other counts are `OUTSIDE_DEPENDENCY_TICKER=10`,
  `UNRESOLVED_CANDIDATE_BEFORE_CLOSURE=3`, and
  `UNRESOLVED_CANDIDATE_IN_CLOSURE=8`.
- KSEI bounded interval authority: `567/716` parsed-page-only for
  `RIGHTS_HMETD` and `567/716` parsed-page-only for `STOCK_DIVIDEND`; zero are
  source-certified complete intervals. Retained page bytes/row counts do not
  prove pagination, provider completeness, observed-through/as-of, or
  source-family no-event semantics. Other frozen families remain
  `UNKNOWN_INTERVAL`; bounds are per ticker rather than the global closure
  minimum.
- Acquisition plan: `25` explicit units. The event-specific transition unit
  contains `291` exact unresolved physical event identities across `193`
  tickers, reconciled as prior `94 SCHEDULE_REQUIRED` plus `197` additional
  unresolved rows. Capability-verification units are distinct from later bulk
  units; endpoint-wide IDX capability checks use `ticker_count=0` only where
  no ticker request dimension is proven.
- IDX negative coverage: all nine categories `UNKNOWN`; empty responses are
  not source-defined no-event authority.
- Global certification design: identity containment plus evidence-rich,
  source-contract/ref/hash-bound full-family coverage and hash-bound temporal
  attestation. Naked booleans cannot pass; the valid 629/716/716 architecture
  can pass only with full expanded evidence.

## ADRO -> AADI forensic result

Both ADRO and AADI are in final fit, application, and closure. Retained
per-ticker dependency bounds and population geometry are recorded in the
forensic rows; the named ADRO rights and AADI listing dates are retained for
the in-scope check. Retained evidence contains:

- ADRO KSEI `Right Distribution`, record `2024-11-29`, distribution
  `2024-12-02`, ratio `(4389 ADRO : 1000 ADRO-H )`, no cum date, page SHA
  `94cf7d898146b7366a1efd776cd3bb3b76dd3c3ae6937c318dd7604ceec39113`.
- Separate ADRO KSEI `Cash Dividend`, cum `2024-11-26`, record `2024-11-29`,
  distribution `2024-12-06`, ratio `(1 ADRO : 1 IDR)`.
- KSEI schedule refs `KSEI-27597/JKU/1124` and `KSEI-28171/JKU/1224`, with
  hashes `4c51477093cdb6b93f568781ac3d21f834a26154e18f2ac09576f1eed3867aca`
  and `177618678e05cb18f68022a2e89f33c76e05e5ad0a501ace2c4cff2fb8527b8e`;
  neither supplies an accepted exact transition semantic.
- IDX AADI `ipo`, id `45577`, date `2024-12-05`, is listing-only; IDX ADRO
  `kurangModal` is a separate 2026 row, not authority for the 2024 case.
- No retained announcement-linkage row for ADRO/AADI and no structural AADI
  KSEI history row tying AADI to the ADRO entitlement.

Conclusion: the retained ratio proves a source-native right to acquire ADRO-H,
not an AADI distribution-in-specie. The separation aspect is
`REQUIRES_POLICY_DECISION` / taxonomy `UNKNOWN`; it is not mapped to
`CAPITAL_RESTRUCTURING`, `SPIN_OFF`, `DEMERGER`, `PUPS_ENTITLEMENT`, or
`DISTRIBUTION_IN_SPECIE`. The red-team label search also found two exact
`Pemisahan Unit Usaha` TPIA schedule titles, linked to the same underlying
event/document group, and seven `gabungUsaha` IDX rows. Five are retained as
population-scoped physical events; BDMN/GDST remain forensic-only outside the
accepted global geometry. All findings are preserved with raw refs/hashes and
left unmapped.

## Artifact files

- `v11_raw_source_event_ledger.csv`
- `v11_transition_reconstruction.csv`
- `v11_dependency_closure_event_census.csv`
- `v11_structural_separation_forensics.csv`
- `v11_source_interval_authority.csv`
- `v11_idx_negative_coverage_contract.csv`
- `v11_source_family_authority_matrix.csv`
- `v11_population_authority.csv`
- `v11_remaining_gap_matrix.csv`
- `acquisition_requirements_v11.json`
- `summary.json`
- `MANIFEST.json`

The exact artifact hashes and the source-versus-historical distinction are in
the checkpoint
`docs/checkpoints/2026-08-29_INC001_CA_SOURCE_AUTHORITY_AUDIT_V11.md`.

## Scientific verdict (unchanged)

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Validation

- Focused V1.1 tests: 11 passed.
- All CA/integrity tests: 121 passed, exit 0.
- Full pytest: 360 passed, exit 0.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Deterministic artifact rerun: PASS, zero output mismatches.
- Implementation/content validation run `33199155485` on commit
  `a9b1ef45057efc7902e71bef4d1b567026552d1b`: SUCCESS, `360 passed, 5
  warnings` ([run](https://github.com/samindriano/idx-trade/actions/runs/33199155485)).
- Latest reviewed-head validation run `33199443043` on commit
  `0626b653e273067612631fd3414b579ca93c3763`: SUCCESS, `360 passed, 5
  warnings` ([run](https://github.com/samindriano/idx-trade/actions/runs/33199443043)).
  The five warnings are non-blocking Node.js action-runtime and NumPy
  timedelta deprecations, not failed tests. Final branch CI for this correction
  is run once after the handoff commit and reported with final HEAD; no
  docs-only CI loop is required.

Review this handoff and the immutable V1.1 roots. Do not merge PR #108/#103 or
run further scientific/production work as part of this handoff.
