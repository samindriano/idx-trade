# Targeted Zapi Residual Audit — Runtime Result

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-residual-audit-v1`
Remote base verified before changes: `cf896b2b3677f807a39fb6050291eda7dcf60875`

## Decision

**`ZAPI_BLOCKED_CREDENTIAL_ABSENT`**

The bounded Zapi runtime did not start because `ZAPI_API_KEY` was absent from
the local environment. No Zapi endpoint was called, no Zapi network request
was made, no alternate source was substituted, and the external runtime output
directory was not created.

This is a fail-closed access result, not a provider data-quality result. Stop
for independent ChatGPT review and a separately authorized credential/access
decision.

## Pre-runtime verification

- worktree started at remote HEAD:
  `cf896b2b3677f807a39fb6050291eda7dcf60875`;
- target branch matched remote before local changes;
- immutable panel exists and required SHA remains:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- accepted Yahoo census audit and provider-status inputs exist;
- required output directory was absent/empty before the blocked runtime;
- `ZAPI_API_KEY` presence check: `false`;
- secret value was not read, printed, hashed, persisted, or committed.

## Allowed implementation verification and bounded fixes

The two explicitly documented invariants were checked. Both required the
smallest bounded implementation correction:

1. Known-control exact-Open arbitration now evaluates nullable/numpy boolean
   values by truth value (`pd.notna(...)` plus `bool(...)`), instead of Python
   object identity (`is True`).
2. Artifact finalization now excludes both `zapi_targeted_summary.json` and
   `artifact_manifest.json` from the manifest payload. The manifest hash is
   written into the finalized summary afterward, avoiding stale/circular
   hashes.

No sample quota, sample role, methodology, provider, admission rule,
arbitration class, endpoint, or access policy was changed.

Changed files:

- `src/idx_trade/zapi_residual_audit.py`
- `tests/test_zapi_residual_audit.py`

## Validation

- focused pytest before fix: `3 passed`;
- full pytest before fix: `236 passed`, `5 warnings`;
- focused pytest after fix: `5 passed`, `2 warnings`;
- full pytest after fix: `236 passed`, `5 warnings`;
- new focused coverage verifies numpy boolean known-control exactness;
- new focused coverage verifies manifest exclusion of summary and manifest;
- no Zapi runtime artifacts were generated because credential access was
  blocked before runtime.

The warnings are existing pandas FutureWarnings, including the pre-existing
nullable-boolean fill warning in the audit module; they are non-blocking for
this handoff.

## Scope boundary preserved

- `execution_grade_promoted=false`;
- `bulk_backfill_authorized=false`;
- no panel or Yahoo census artifact was modified;
- no corporate-action repair, alternate provider, Yahoo rerun, modelling,
  Ranking/PIT-sector work, execution PnL, paper/live trading, or main merge was
  performed.

Stop here. A future run may proceed only after the credential/access posture is
separately authorized and the local environment supplies `ZAPI_API_KEY`.
