# V4 CA Material-Six Remediation V2 Result — 2026-08-18

Status: `COMPLETE_WITH_RESIDUAL_TICKER_LEVEL_GAPS`

Branch: `data/idx-v4-material-six-remediation-v1`

This checkpoint records the first successful 611-ticker material-six replay. It is outcome-blind and does not authorize model fitting, target/rank materialization, performance computation, or protected-forward access.

## Frozen material-six scope

- FREN
- ADRO
- MEGA
- SCMA
- AVIA
- SMAR

## Final 611-support replay

- frozen tickers: 611
- frozen dates: 600
- frozen rows: 345,394
- FREN added validation signal rows: 302
- FREN added H5/H10 horizon rows: 604
- corporate action continuity certified: `true`
- H5 gate dates: 600 / 600
- H10 gate dates: 600 / 600
- consensus gate dates: 600 / 600
- H5 minimum rate: 0.907051282051282
- H10 minimum rate: 0.9038461538461539
- consensus minimum rate: 0.9038461538461539
- cross-source conflict tickers: none
- schedule-required events: 33
- schedule-required tickers: 29
- provider calls during final continuity replay: false

Final continuity summary SHA-256:
`1364ac781599efbd1de6e370099ccc1fd55173883a0fa6981358d3bb66d6b823`

Material-six manifest SHA-256:
`866d2467babc3abc076d78d15297d2454b59251b26f3c7ce90dca8d0e28cb5a8`

## Per-ticker result

### SCMA — resolved

Frozen prior candidate `source_action_id=82840`, candidate date `2026-08-10`, is after the maximum frozen target terminal `2026-07-31`. It is acquisition-halo-only and must not poison all historical SCMA windows.

Result:
- coverage certified: true
- window rows: 1,200
- resolved window rows: 1,200
- resolved rate: 1.0
- verdict: `RESOLVED_2026-08-10_CANDIDATE_HALO_ONLY_AFTER_FROZEN_TARGET_PERIOD`

### MEGA — event semantics resolved, no frozen target rows

Issuer-official 2026 bonus-share evidence establishes:
- ratio: 1 old share : 1 bonus share
- regular-market ex-bonus date: 2026-04-10

The material-six summary reports zero frozen target-window rows for MEGA. Therefore this remediation removes a global conflict-summary issue but does not change any frozen MEGA decision windows in this replay.

Verdict:
`RESOLVED_2026_EX_BONUS_2026-04-10`

Important reporting nuance: `material_results.MEGA.coverage_certified=false` reflects that MEGA is not represented in the expanded coverage map used for per-material reporting; `expanded_support.unresolved_tickers` does not include MEGA. This is not a new continuity failure because MEGA has zero frozen target-window rows.

### FREN — support omission corrected; complete-history coverage still unresolved

FREN is no longer silently omitted:
- 302 validation signal rows added
- 604 H5/H10 rows added
- exact issuer-official merger/security-cessation boundary: 2025-04-16
- no EXCL price stitching

KSEI direct historical page lookup returned `PARSE_IDENTITY_MISMATCH`; complete FREN KSEI history therefore remains uncertified. All 604 FREN rows stay fail-closed for coverage.

Verdict:
`UNRESOLVED_COMPLETE_KSEI_HISTORY_UNAVAILABLE`

### ADRO — still unresolved by policy

The accepted KSEI row remains:
- Right Distribution
- 4389 ADRO : 1000 ADRO-H
- Record Date: 2024-11-29
- Distribution Date: 2024-12-02
- Cum Date: missing

No Record/Distribution fallback is permitted. An inferred 2024-11-28 or any other inferred ex-date is forbidden.

Verdict:
`UNRESOLVED_PRIMARY_REGULAR_MARKET_EX_DATE_NOT_PROVEN`

### AVIA — strict retry failed closed

Retry result:
- success: false
- failure class: `HTTP_NON_200_OR_EMPTY`
- no security attempt occurred because home warmup failed

Verdict:
`STRICT_KSEI_COVERAGE_RETRY_FAILED_CLOSED`

### SMAR — strict retry failed closed

Retry result:
- success: false
- failure class: `HTTP_NON_200_OR_EMPTY`
- no security attempt occurred because home warmup failed

Verdict:
`STRICT_KSEI_COVERAGE_RETRY_FAILED_CLOSED`

## Remaining expanded coverage gaps

12 unresolved names across the 611 support rows:

`AMAN, AVIA, AYAM, BCIP, FREN, PRIM, SKRN, SLIS, SMAR, SNLK, SOCI, SOFA`

Certified tickers: 599 / 611.

## Scientific interpretation

The aggregate 90% V4 CA gate remains certified after correcting the FREN omission. This materially strengthens the earlier 610-ticker pass: adding FREN does not break the frozen per-date threshold.

However, aggregate certification must not be stated as six-for-six ticker resolution. At this checkpoint:
- fully/narrowly resolved: SCMA
- official event semantics resolved but no frozen target rows: MEGA
- exact boundary found but coverage unresolved: FREN
- unresolved exact transition: ADRO
- unresolved transport coverage: AVIA, SMAR

No unresolved ticker is silently promoted to clean.

## Follow-up remediation

A V3 transport-only retry is authorized for AVIA/SMAR (and diagnostics for SCMA/ADRO): if the configured KSEI home warmup fails before any security request, attempt the exact same registered-security URL directly in a fresh session and parse with the identical strict parser. No alternate provider, URL, or parser relaxation.

For SMAR only, if strict KSEI capture proves exactly the active row `(1 SMAR : 5265 IDR)` with Distribution Date 2026-06-11, classify it narrowly as static security-to-currency nonblocking semantics, consistent with the accepted NISP treatment.

ADRO remains fail-closed unless an explicit primary official regular-market ex/first-new-basis date is proven.
