# Targeted Zapi Residual Audit — Independent Review

Date: 2026-08-11 (Asia/Jakarta)
Reviewed branch: `data/idx-open-backfill-zapi-residual-audit-v1`
Reviewed runtime/fix commit: `9dc99710fd27254dea1b5f3b9f2475acc96802d9`

## Decision

**`ZAPI_ACCESS_BLOCKER_ACCEPTED_WAIT_FOR_CREDENTIAL`**

The bounded Zapi residual-audit implementation remains methodologically valid and the runtime correctly failed closed because `ZAPI_API_KEY` was absent.

This is an access blocker only. It is not evidence that Zapi is unavailable, plan-gated, or low quality. No substitute source is authorized from this review.

## Review findings

- zero Zapi network requests were made;
- no runtime output directory was created;
- no alternate provider was substituted;
- immutable panel SHA remained `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- the two implementation changes were exactly the previously authorized bounded invariants:
  1. nullable/NumPy boolean known-control exactness is evaluated by value rather than Python identity;
  2. artifact manifest generation excludes the final summary and the manifest itself, then records the manifest hash into the finalized summary;
- sample quotas, source, endpoint, admission rule, arbitration semantics, and methodology were unchanged;
- focused tests improved from `3 passed` to `5 passed` after the bounded fixes;
- full pytest remained `236 passed` with `5 warnings`.

The fixes are accepted. No additional implementation work is required before credentialed runtime unless a concrete runtime issue is observed.

## Current external access posture

Zapi currently documents the IDX `finance:idx / stock-summary` endpoint with historical `date` support and OHLC fields including `OpenPrice`, `High`, `Low`, and `Close`. Zapi also documents free API-key creation without a credit card. However, endpoint plan eligibility must still be determined empirically with the user's credential because endpoint-level plan gating can exist.

## Authorized next action

The next action is only:

1. user creates or supplies a local Zapi API key;
2. store it locally as environment variable `ZAPI_API_KEY` and never commit or print the secret;
3. rerun the already-frozen targeted Zapi residual audit from this branch;
4. if access is denied or plan-gated, record that fact and STOP;
5. if access succeeds, run only the bounded targeted sample and STOP for independent review.

No new design, sample expansion, provider substitution, corporate-action repair, bulk backfill, execution-grade promotion, modelling, Ranking/PIT-sector work, execution-PnL, paper/live trading, or main merge is authorized.

## Stop boundary

Until `ZAPI_API_KEY` is present, pause this branch. Other independent project tracks may continue on their own branches, but this data-recovery branch should not be redesigned merely to avoid the credential step.
