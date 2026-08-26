# Corporate-Action Feature-Basis Integrity Audit V1

Date: 2026-08-26
Repository: `samindriano/idx-trade`
Branch: `audit/ca-feature-basis-integrity-v1`
Audit base / current origin/main at bootstrap: `abef0d47b0f728adcffbb7c4e6353b09739fa66f`
Frozen parent model-safe panel SHA: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

## Verdict

`AUDIT_COMPLETE_REVIEW_REQUIRED`

Required explicit outputs:

- `BACKWARD_CA_FEATURE_WINDOW_RISK=PRESENT_NO_CA_AWARE_BACKWARD_RESET_FOUND`
- `EXACT_FINAL_FIT_IMPACT=MATERIAL_FOR_ACCEPTED_12_TICKER_BASIS_OVERLAY`
- `BBCA_2021_VERDICT=EXCLUDED_BEFORE_FIT`
- `MARKET_WIDE_SEVERITY=MATERIAL_LOCALIZED_AND_UNRESOLVED_MARKET_WIDE_COVERAGE`
- `EXISTING_GUARD_COVERAGE=TARGET_WINDOW_CONTINUITY_ONLY_NOT_BACKWARD_FEATURE_WINDOWS`
- `REMEDIATION_REQUIRED=YES_REVIEW_CA_AWARE_FEATURE_WINDOW_POLICY_AND_REVALIDATE_INPUTS`

This is an outcome-blind forensic audit, not an authorization to alter the
canonical panel, refit a model, or create a production price adjustment.

## Scope and hard guards

The audit traced the accepted historical price-basis and V4-X1 feature lineage,
replayed only existing immutable local artifacts, and measured feature-layer and
exact final-fit identity impact. It did not call providers, access protected
outcomes/returns/PnL, read target values, fit/score/refit/tune a model, change a
feature definition, change a V4-X1 contract, or overwrite canonical artifacts.

`audit_manifest.json` records all guard flags as false, except
`outcome_blind=true`, and `no_canonical_artifact_overwrite=true`.

## Lineage inspected

- Historical panel and price evidence: `scripts/run_v4_3r_historical_one_shot.py@08233877eb1f94e0ddefcd4f35409923f1c7dda5`.
- H/L/C pre-record-date repair: `src/idx_trade/price_basis_remediation.py@c088710037257bcfd63670349be08bc15a52eae8`.
- Open recovery: `src/idx_trade/price_basis_open_remediation.py@efd3e7bfb37951f1f60b0ae8d995bba6e44b38be`.
- Clean panel consolidation: `src/idx_trade/v4_x_clean_data_consolidation.py@eee928c5e2c81ef1aad755191d50f780b2ad1da4`.
- V4 feature construction: `src/idx_trade/ranking_v4_3_features.py@c3c3d97bd09b5d97665b12fc9063eb3baf518a55`.
- CA training-domain gate: `src/idx_trade/ranking_v4_3_ca_training_domain.py@c51ca2a502df0d115417cf67dfc978d59ef30dab`.
- Target/continuity gate: `src/idx_trade/ranking_v4_3_target_execution.py@e659a7362fce8fcf047b612edba27018183c7762`.
- Final-refit identity filtering: `scripts/run_v4_x1_final_refit_freeze.py@56bd210bf776e413b988825646861008fa46c1a5`.

The price-basis remediations replace H/L/C or Open only under their accepted
factor and date rules. The feature builder then computes lagged returns, ATR14,
20/60-session extrema, liquidity, cross-sectional ranks, and market-relative
context. No explicit CA-aware reset/quarantine for those backward windows was
found. The target builder separately requires exact future-window continuity;
that is not a backward-feature-window guard.

## BBCA FY 2021 forensic trace

Local official evidence identifies BBCA stock split ratio `1:5` with
`ListingDate=2021-10-13` and `AdditionalListedShares=98,620,040,000` in:

- `D:\Documents\Project\idx-v4-3-ca-residual47-idx-digital-split-20260819-v1\raw\2021_10_p01_attempt_01.bin`, SHA-256 `1c0e51a043edfa9534cebaa0c87be369e344e2135374c2c8b3a68c0fca94cb17`;
- direct IDX issued-stock-split evidence, SHA-256 `da9a82a5295e6ec039cdb51a23960aa53d0b3ee4c4455571fc3d054272a46979b`.

The accepted panel witness is exact to IDX public H/L/C on both sides of the
recorded date:

| date | high | low | close | provenance |
|---|---:|---:|---:|---|
| 2021-10-12 | 36,600 | 36,225 | 36,600 | `IDX_PUBLIC_STOCK_SUMMARY` |
| 2021-10-13 | 8,250 | 7,400 | 7,525 | `IDX_PUBLIC_STOCK_SUMMARY` |
| 2021-10-14 | 7,900 | 7,600 | 7,750 | `IDX_PUBLIC_STOCK_SUMMARY` |

This is a mechanically material price-basis discontinuity consistent with the
recorded split, but the available evidence does not prove that
`TanggalPencatatan` is the generic market-effective transition for every
continuity use. The audit therefore does not manufacture an effective date or
price correction.

The trace covers 61 post-record-date rows beginning at session index 111. The
backward windows still expose pre-event rows for:

- 5 rows: `close_return_5` / five-session lag;
- 14 rows: ATR14, whose true range uses prior close;
- 20 rows: `close_return_20` and rolling-20 high/low;
- 60 rows: rolling-60 high/low/history.

All 1,231 BBCA combined-support rows have H5/H10 support flags false, and exact
final-fit membership is H5 `0`, H10 `0`. Therefore the final verdict for BBCA
is `EXCLUDED_BEFORE_FIT`: feature-layer exposure is demonstrated, but no BBCA
row entered the exact accepted H5/H10 final-fit identities.

## Market-wide CA evidence and semantics

The strict promoted event-family evidence inventory contains 26 rows:

| event family | evidence rows |
|---|---:|
| `STOCK_SPLIT` | 7 |
| `STOCK_DIVIDEND` | 3 |
| `BONUS_SHARES` | 1 |
| `RIGHTS_HMETD` | 10 |
| `MANDATORY_CONVERSION` | 4 |
| `CAPITAL_RESTRUCTURING` | 1 |
| reverse split observed | 0 |
| merger observed | 0 |

The zero counts are absence from this strict inventory, not evidence that the
event families never occur. All 26 strict event rows remain unresolved for a
generic market-effective date; no generic `TanggalPencatatan` inference was
accepted. The broader local KSEI inventory had 610 tickers, 567 certified and
43 unresolved, with 14,723 history rows; 464 tickers had resolved continuity
and 146 remained unresolved in that prior gate. This audit does not promote
that broader inventory to a new continuity authority.

Rights/HMETD cannot be treated as a simple split without offer price, TERP, and
effective-date evidence. Bonus shares and mandatory conversion likewise require
event-specific semantics; no generic multiplicative H/L/C assumption is made.

## Exact accepted final-fit identity impact

The accepted v1.2 price-basis impact artifact was read support-only and its
feature-change identities were reconstructed without target/outcome values.

| head | exact fit rows | changed rows | changed dates | changed tickers | direct | spillover |
|---|---:|---:|---:|---:|---:|---:|
| H5 | 241,487 | 56,514 | 290 | 486 | 680 | 55,834 |
| H10 | 239,836 | 56,221 | 290 | 486 | 666 | 55,555 |
| UNION | 241,724 | 56,602 | 290 | 486 | 681 | 55,921 |

The overlay basis contains 1,657 stable scale rows across 56 runs and 12
tickers. The changed rows are not floating-point noise: prior accepted
diagnostics showed a V2 median absolute rank delta of about `0.003205`, p95
`0.018072`, and max `35.075630`; one affected rank feature had median absolute
delta about `0.005168` and max `0.969697`. These are descriptive identity and
feature-change diagnostics only, not performance evidence.

Direct changes are localized to three tickers, while most changes are
cross-sectional spillover through ranks and market context. This is why a
local CA event can change a broad set of exact model-input rows without proving
that every changed ticker had its own corporate action.

## Ten audit questions answered

1. **Can the current price basis be treated as CA-integrity safe?** No. The
   accepted factor overlay is bounded and auditable, but the feature layer has
   no general backward-window reset policy.
2. **Does the CA/price-basis lineage reach feature construction?** Yes. H/L/C
   and Open remediation feed the consolidated panel consumed by V4 features.
3. **Can a post-event row use a pre-event observation in a backward feature?**
   Yes, for the demonstrated five-, 14-, 20-, and 60-session windows.
4. **Is the future target continuity gate sufficient?** No. It protects the
   forward target window, not backward feature geometry.
5. **Is BBCA 2021 in the accepted final fit?** No; exact H5/H10 membership is
   zero, so it is `EXCLUDED_BEFORE_FIT` despite feature-layer exposure.
6. **Is the issue only a BBCA anomaly?** No. Exact v1.2 support-only impact is
   486 tickers and 290 dates, with large spillover through ranks/context.
7. **Is there enough evidence for a market-wide correction now?** No. The
   strict event inventory has 26 rows and unresolved effective dates; it is
   insufficient for a blanket correction.
8. **Are rights, bonus, mandatory conversion, and split events interchangeable?**
   No. They require separate event semantics; rights especially need TERP/
   offer-price evidence.
9. **Are existing guards sufficient?** Only for listing/tradability and exact
   future target continuity. They do not establish backward CA-window safety.
10. **What is the safe next step?** Review and freeze a CA-aware backward
    feature-window policy, then revalidate/recompute affected inputs before any
    model or performance decision. No remediation is authorized by this audit.

## External artifacts

External root (not committed to Git):
`D:\Documents\Project\idx-ca-feature-basis-integrity-audit-20260826-v4`

The output is immutable for this audit and is pinned by:

| artifact | SHA-256 |
|---|---|
| `audit_manifest.json` | `b9a37511fd92a8f4bfc9e7e7e16597a720523523c2ae87f9ae135e872dab89d3` |
| `audit_summary.json` | `3f6de321e673775dfe9b39150aded7ff54295b0d9b68828d14ff77943f50494c` |
| `input_manifest.json` | `41e12116637f1cd1df190a4f8ea53c1048d6ab0eff8d263a05db470f893d5b40` |
| `ca_event_census.csv` (26 rows) | `10540f8f73e6a0cec3975ac189dc2ab2034a81c6610f81381009966848f95ed3` |
| `bbca_2021_trace.csv` (61 rows) | `17c79b31d63d1a0c4f7da277b233ed78f0330076efc0bce80e292131fba48a5a` |
| `backward_feature_window_exposure.csv` (4 rows) | `ef0db297653a935165946d08464ad55e4d1d3d6c3379dfe7c23448c88dda051f` |
| `final_fit_identity_impact.csv` (112,735 rows) | `a84a9948e2ee56f7bff394035f6500b879def2b29fdfc74809abc64cbe787b93` |
| `cross_sectional_spillover_summary.csv` (6 rows) | `12a40777f26d01eab439c23312b179f09f1c6baac1eb8cf196ab12ffe2e1cb68` |

Key pinned input manifests:

- v1.1 basis impact manifest: `62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6`;
- v1.2 basis impact manifest: `620fbd1f98924365e623919d3339f005abd7960f66631213631b845dcd7061f5`;
- combined CA training-domain manifest: `12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`;
- final-refit manifest: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`.

## Validation

- `python -m pytest -q tests/test_ca_feature_basis_integrity_audit.py`: PASS,
  2 passed.
- `python -m pytest -q`: PASS, all collected tests passed with clean basetemp
  and exit code 0. The first run also completed all test cases but exited with
  a Windows pytest temp-cleanup `WinError 5`; the clean-basetemp rerun was the
  final result.
- `python -m py_compile scripts/run_ca_feature_basis_integrity_audit_v1.py`:
  PASS.
- `git diff --check`: PASS before documentation finalization; it will be
  rerun after this checkpoint/handoff/status update.

## Decision boundary

This checkpoint does not authorize a CA-aware feature reset, a market-wide
reacquisition, a model refit, a score rerun, or any outcome/performance review.
The next decision is independent ChatGPT review of the forensic evidence and
whether to freeze a narrowly scoped remediation contract.
