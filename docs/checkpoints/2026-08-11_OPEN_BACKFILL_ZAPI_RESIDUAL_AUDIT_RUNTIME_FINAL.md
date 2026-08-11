# Targeted Zapi Residual Audit — Final Runtime Result

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-residual-audit-v1`
Runtime base HEAD: `574f7223bf4f98ff933d8d7c31c44007e85aa78f`

## Decision

**`ZAPI_TARGETED_RESIDUAL_AUDIT_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`**

The frozen 240-row Source-2 audit completed with empirically accessible Zapi
IDX stock-summary access. This is diagnostic evidence only. It does not
authorize bulk backfill, execution-grade promotion, corporate-action repair,
modelling, Ranking/PIT-sector work, execution PnL, or main merge.

The first credentialed invocation exposed a concrete role-alias wiring issue:
the sample uses `KNOWN_CONTROL` while the shared auditor recognized only the
legacy `KNOWN_EXISTING_OPEN` role. Its artifacts were preserved outside Git
under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811_pre_role_fix`

The final runtime below was rerun with the smallest bounded alias fix. The
sample remained deterministic and unchanged.

## Runtime and input integrity

- runtime base HEAD before local bounded fix:
  `574f7223bf4f98ff933d8d7c31c44007e85aa78f`;
- process-local `PYTHONPATH` was set to the worktree `src` directory because
  this src-layout checkout is not installed as a package; no dependency or
  source-path change was persisted;
- panel SHA-256 before:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- panel SHA-256 after:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- Yahoo census inputs were read-only;
- corporate-action residual classes remained out of scope;
- `execution_grade_promoted=false`;
- `bulk_backfill_authorized=false`;
- `corporate_action_repair_performed=false`.

## Validation and bounded fix

- focused pytest after role-alias fix: `6 passed`, `2 warnings`;
- full pytest after role-alias fix: `236 passed`, `5 warnings`;
- bounded fix: shared auditor now treats `KNOWN_CONTROL` as an existing-Open
  control alongside `KNOWN_EXISTING_OPEN`, including row admission and summary
  counters;
- regression test added for known-control existing-Open comparison;
- no sample quota, source, endpoint, admission rule, or arbitration class was
  changed.

The runtime emitted one non-blocking pandas FutureWarning from nullable-boolean
`fillna` aggregation in the shared auditor. No runtime error or rate-limit
event occurred.

## Frozen sample

- rows: `240`;
- role counts:
  - `RESIDUAL_HLC_MISMATCH`: `120`;
  - `RESIDUAL_PROVIDER_GAP`: `80`;
  - `KNOWN_CONTROL`: `40`;
- unique tickers: `206`;
- unique dates: `178`;
- sample manifest SHA-256:
  `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`;
- all five Yahoo provider-error tickers were represented:
  `FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`;
- no corporate-action residual row was selected.

## Zapi access and request result

- credential status: `PRESENT_NOT_RETAINED`;
- access status: `ACCESSIBLE`;
- plan status: `EMPIRICALLY_REACHED`;
- requests made: `178`;
- unique dates requested: `178`;
- retries: `0`;
- HTTP 429/rate-limit events: `0`;
- request errors: `[]`;
- provider rows returned: `240`;
- duplicate provider-key rows: `0`;
- exact ticker/date rows: `240 / 240`;
- identity/date anomalies: `0`.

No API key value was printed, persisted, hashed, or committed.

## Quality, admission, and arbitration

- H/L/C exact: `240 / 240` (`100%`);
- known-control H/L/C exact: `40 / 40` (`100%`);
- known-control Open comparisons: `40`;
- known-control Open exact: `20 / 40` (`50%`);
- provider-gap recovery candidates:
  `0` (`SOURCE2_RECOVERY_CANDIDATE`);
- rejection breakdown:
  - `EXISTING_OPEN_PRESERVED`: `40` controls;
  - `CANDIDATE_OPEN_INVALID`: `200` rows;
- Zapi corporate-action fields present: `false` (corporate-action track was
  not part of this audit).

Arbitration counts:

| class | rows |
|---|---:|
| `SOURCE2_SUPPORTS_CERTIFIED_PANEL` | 120 |
| `SOURCE2_SUPPORTS_YAHOO` | 0 |
| `SOURCE2_RECOVERY_CANDIDATE` | 0 |
| `SOURCE2_PANEL_HLC_MATCH_OPEN_REJECTED` | 80 |
| `SOURCE2_NO_ROW` | 0 |
| `THREE_WAY_DISAGREEMENT` | 0 |
| `CONTROL_PANEL_HLC_OPEN_EXACT` | 20 |
| `CONTROL_PANEL_HLC_ONLY` | 20 |

All 120 Yahoo H/L/C-mismatch rows had Zapi H/L/C equal to the certified
panel. All 80 provider-gap rows also had exact H/L/C, but their Open evidence
was invalid under the frozen contract; therefore none became recovery
candidates. Twenty controls had exact positive Open; twenty returned invalid
Open (zero), yielding the 50% known-control Open rate.

## Final external artifacts

Runtime root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811`

| artifact | SHA-256 |
|---|---|
| `zapi_targeted_sample_manifest.csv` | `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344` |
| `zapi_targeted_sample_manifest.json` | `3f0023eaef6fce48cb44ab4793aaaa1d330acdc199d0701eb2595fe8bd9fc85b` |
| `zapi_candidate_rows.csv` | `047d90b1ef4babf4834c28e9b74a9a9c89023e42265b982381cfd3229739343f` |
| `zapi_row_audit.csv` | `f2013e412b94543bee70d60d32853843987ae454006361d0cdfe994c01a3a7ee` |
| `zapi_arbitration.csv` | `e466ec3b18db5dd28c766d8c60b48fba847fa0716a9ad99a8974ac0b9c99a3fa` |
| `zapi_targeted_summary.json` | `5e6db621d7d0c965955480eea4624204215cba0270b29dc62e3bea78d1cdef07` |
| `artifact_manifest.json` | `899def2f280d49695a85f6fa2ddc34a4c793dcdf240ce114a02dd0055787fd1d` |

Manifest verification passed: every listed artifact hash matches; summary's
`artifact_manifest_sha256` matches the final manifest; summary and manifest
are excluded from the manifest payload.

## Stop boundary

Stop for independent ChatGPT review. Do not start bulk Zapi backfill,
corporate-action repair, another provider, Yahoo rerun, execution-grade
promotion, modelling, Ranking/PIT-sector work, execution PnL, paper/live
trading, broker integration, or main merge.
