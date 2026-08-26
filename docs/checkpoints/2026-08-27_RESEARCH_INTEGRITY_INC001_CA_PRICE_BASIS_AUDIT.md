# Research Integrity / Data QA Gate V1 — INC-001 Audit

Date: 2026-08-27 Asia/Jakarta
Branch: `audit/research-integrity-data-qa-gate-v1`
Audit PR: `#103`
Audit HEAD: `4a2cfbe3f4332aad4431b65931bfaf01bbb4979b` before this checkpoint
Current `origin/main` observed during finalization: `30d725ffba1175b64b62617ec0265c6c5792b800`
Latest `origin/main` observed before final handoff publication: `8769949caa59b340aa8c4c0abfa49c8ab5c0b7be`.

## Scope and safety

This is a Research Integrity / Data QA audit only. It used the existing local
frozen artifacts and historical repository lineage. No provider or network
data acquisition, protected outcome/holdout access, target-value access,
model fit/score/refit, V4-X1 refit/tuning, counter mutation, runtime change,
canonical artifact overwrite, or retroactive fill was performed.

The audit source bundle is time-pinned. Its input manifest records
`source_main_sha=abef0d47b0f728adcffbb7c4e6353b09739fa66f`, which differs from
the current `origin/main` observed above. The bundle is therefore reproducible
for its pinned source state, but it is not a certification of all later main
changes.

## Phase 1 — framework validation and hardening

The initial adversarial review found real framework false-pass paths. The
following bounded fixes were made only in the integrity-gate framework:

- required-check profiles now reject empty requirements and validate the
  fail-closed profile flags;
- missing required checks and required PASS checks without evidence become
  blocking `UNKNOWN`;
- serialized reports are recomputed and consistency-checked instead of
  trusting serialized `passed`/blocker fields;
- empty data, null keys, non-finite values, impossible OHLC, empty hash
  expectations, and naive PIT timestamps fail closed;
- direct CLI invocation bootstraps the repository `src` path and refuses to
  overwrite an existing report.

Validation:

- Focused integrity tests: **21 passed**.
- Full repository pytest: **260 passed, 0 failed** (pytest collection also
  reported 260 tests).
- `py_compile` for the framework module and CLI: **PASS**.
- CLI `--help`: **PASS**.
- CLI synthetic PASS smoke: **exit 0**, `passed=true`, no blockers.
- CLI synthetic UNKNOWN smoke: **exit 2**, `passed=false`, missing required
  `pit.knowledge_time` was materialized as a blocker.
- `git diff --check`: **PASS**.

No model or outcome evidence was used for these checks.

## Phase 2 — HEAVY QA execution

The audit followed the repository HEAVY QA shape with separate read-only
lanes for source/coverage, PIT/provenance, economic/event semantics,
independent recomputation/blast radius, and adversarial falsification. The
results reconcile on the critical quantities below.

### Pinned inputs and outputs

Existing audit root:
`D:\Documents\Project\idx-ca-feature-basis-integrity-audit-20260826-v4`

- `audit_manifest.json`: SHA-256
  `b9a37511fd92a8f4bfc9e7e7e16597a720523523c2ae87f9ae135e872dab89d3`
- `audit_summary.json`: SHA-256
  `3f6de321e673775dfe9b39150aded7ff54295b0d9b68828d14ff77943f50494c`
- `input_manifest.json`: SHA-256
  `41e12116637f1cd1df190a4f8ea53c1048d6ab0eff8d263a05db470f893d5b40`
- `ca_event_census.csv`: SHA-256
  `10540f8f73e6a0cec3975ac189dc2ab2034a81c6610f81381009966848f95ed3`
- `bbca_2021_trace.csv`: SHA-256
  `17c79b31d63d1a0c4f7da277b233ed78f0330076efc0bce80e292131fba48a5a`
- `backward_feature_window_exposure.csv`: SHA-256
  `ef0db297653a935165946d08464ad55e4d1d3d6c3379dfe7c23448c88dda051f`
- `cross_sectional_spillover_summary.csv`: SHA-256
  `12a40777f26d01eab439c23312b179f09f1c6baac1eb8cf196ab12ffe2e1cb68`
- `final_fit_identity_impact.csv`: SHA-256
  `a84a9948e2ee56f7bff394035f6500b879def2b29fdfc74809abc64cbe787b93`

The prior input manifest's 11 consumed inputs and generated outputs matched
their declared sizes/hashes. The accepted combined manifest declares two
overlay hashes whose files are absent from that root; those entries remain
`UNKNOWN` and were not silently treated as verified.

The gate check input/report artifacts generated for this run are external and
immutable-by-convention:

- `data_admission_checks.json` SHA-256
  `0925b8322afc0f522c44ec029eebba632543999ae18dff806fa42660adc5f93e`
- `data_admission_report.json` SHA-256
  `6d2429438e62196df327464a51f7be1763e435e353849e0c2894b5bca502630e`
- `research_admission_checks_v2.json` SHA-256
  `962d9e60ba4d369cfee31ba0fd277a7d60da8bd0d245c687a0bffcf23e63928e`
- `research_admission_report_v2.json` SHA-256
  `09e7dc95304e04bcf3688ca0c5af86464e130897dcf3d4588abc86f09642619c`

## Evidence summary

### Structural and coverage

- Frozen panel: 981,940 rows, 945 tickers, 1,260 dates.
- Panel `(ticker,date)` identity: unique; no non-official-session rows;
  H/L/C complete and OHLC-valid.
- Open unavailable rows: 446,843; no zero-fill or synthetic Open was used.
- Final training dates: 986 unique dates; all map to official sessions.

### Corporate-action event semantics

The strict census contains 26 rows: STOCK_SPLIT 7, STOCK_DIVIDEND 3,
BONUS_SHARES 1, RIGHTS_HMETD 10, MANDATORY_CONVERSION 4, and
CAPITAL_RESTRUCTURING 1. All are
`PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE`.

The evidence distinguishes event labels, but that is not enough to certify
price-basis continuity:

- IDX `TanggalPencatatan` is not treated as a generic market-effective date.
- Reverse split and merger absence in the strict sample is `UNKNOWN`, not
  proof of no historical events.
- SINI 2023-03-08 is a source `Voluntary Conversion` but was classified as
  `MANDATORY_CONVERSION`; broader source evidence indicates a systematic
  taxonomy inconsistency (99 voluntary rows mapped into mandatory in the
  cited active census).
- SCMA `kurangModal` mapping is inconsistent across evidence (`CAPITAL_RESTRUCTURING`
  versus `CAPITAL_REDUCTION`).
- Cash dividends are distinct and non-blocking under the existing policy, but
  their omission from the continuity census is not proof of no price effect.

The accepted continuity evidence also reports 344,740 rows without
market-wide no-event coverage and 50 candidate events crossing a window
without a proven effective date; 600/600 validation dates have zero certified
H5/H10/consensus continuity under that gate.

### Backward feature-window integrity

The frozen feature lineage computes ATR14, close-return lags, and rolling
features directly from H/L/C. No CA-aware backward reset/quarantine is
present in the cited feature builder.

BBCA 2021 has a source-corroborated 1:5 split recorded on 2021-10-13. The
61-row trace independently matches H/L/C to the IDX public Stock Summary
source. It shows pre-event rows exposed in the 5, 14, 20, and 60-session
backward windows. Exact BBCA final-fit identities are H5=0 and H10=0, so this
case proves feature-layer exposure but not BBCA exact-fit membership.

The broader accepted support-only reconstruction is material:

| head | exact-fit rows | changed rows | direct rows | spillover rows | tickers | dates |
|---|---:|---:|---:|---:|---:|---:|
| H5 | 241,487 | 56,514 | 680 | 55,834 | 486 | 290 |
| H10 | 239,836 | 56,221 | 666 | 55,555 | 486 | 290 |
| UNION | 241,724 | 56,602 | 681 | 55,921 | 486 | 290 |

Direct impact covers 3 tickers (`CLEO`, `CUAN`, `RAJA`); the remaining
changed rows are cross-sectional spillover across 483 tickers and 245 dates.
Independent identity recomputation found zero changed rows outside the
corresponding exact-fit support.

The 1,657 stable scale rows across 12 tickers are all `YAHOO_RAW`, with
observed factors 2/5/10/25 plus 1.480000055. This is not treated as an
automatically safe adjustment formula.

## Gate verdict

The Research Integrity CLI was executed against the explicit check matrix.
Required `UNKNOWN` blocks exactly like `FAIL`.

### DATA_ADMISSION

`FAIL`

Blocking checks:

`source.semantics`, `units.contract`, `missingness.policy`,
`pit.knowledge_time`, `ca.price_basis`, `golden_cases.data`,
`anomaly.reconciliation`.

Passing checks retained in the report:

`schema.required_columns`, `schema.unique_key`,
`calendar.session_membership`, `provenance.hashes`.

### RESEARCH_ADMISSION

`FAIL`

Blocking checks:

`data_admission.pass`, `feature.backward_window_integrity`,
`research.visual_sanity`, `golden_cases.feature`.

Passing checks retained in the report:

`feature.independent_recompute`, `universe.pit`,
`research.outcome_blindness`, `research.reproducibility`.

### MODEL_PROMOTION

`NOT_EVALUATED`. No model fit, score, promotion review, target, or protected
outcome access was authorized or performed.

### Overall

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
MATERIALITY = MATERIAL
REMEDIATION_REQUIRED = YES
CA_PRICE_BASIS_INTEGRITY = FAIL
BACKWARD_WINDOW_INTEGRITY = FAIL
EXACT_FINAL_FIT_IMPACT = MATERIAL
INC-001 = CONFIRMED / NOT_CLOSED
```

This is a targeted/quarantine blocker, not a claim that every historical row
is defective and not authorization for a blanket price repair. No scientific
rescue, model refit, or protected evaluation should proceed under this
unresolved admission state.
