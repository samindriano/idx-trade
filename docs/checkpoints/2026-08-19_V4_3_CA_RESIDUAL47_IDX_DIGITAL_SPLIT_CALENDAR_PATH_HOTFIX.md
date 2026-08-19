# V4-3 CA Residual47 IDX Digital Split — Calendar Path Hotfix

Date: 2026-08-19

## Trigger

The frozen acquisition completed successfully, but offline adjudication stopped before evidence evaluation because the config named `official_idx_session_calendar.csv`, which is not present under the canonical artifact root.

## Diagnosis

The previously successful frozen IDX schedule-59 adjudication uses `official_exchange_sessions_1260.csv` with SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

The residual47 config pinned the exact same SHA-256 but used the wrong filename `official_idx_session_calendar.csv`.

## Authorized correction

Path-only correction:

- from: `official_idx_session_calendar.csv`
- to: `official_exchange_sessions_1260.csv`
- SHA-256 remains exactly `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

No threshold, event identity, source-date rule, family compatibility, listing-date rule, official-session requirement, parser behavior, provider evidence, target access, model fit, prediction, performance, or protected outcome access changes.

The completed acquisition artifact with manifest SHA-256 `84271e7b72d36c77d958472b7bcf9214ec7f433b9bff96d27d92d97b07077538` remains immutable.

The failed adjudication invocation occurred before output-root creation and before candidate evidence evaluation.
