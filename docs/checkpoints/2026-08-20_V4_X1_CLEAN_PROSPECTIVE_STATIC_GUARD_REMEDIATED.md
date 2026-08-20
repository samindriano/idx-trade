# V4-X1 Clean Prospective Score — Static Guard Remediated

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `integration/v4-x1-clean-prospective-score-v1`

## Decision

`V4_X1_CLEAN_PROSPECTIVE_STATIC_GUARD_REMEDIATED_READONLY_PREFLIGHT_RETRY_AUTHORIZED`

The first authorized local readiness preflight stopped fail-closed before any runtime inspection because `tests/test_v4_x1_clean_forward_score.py` used a raw substring ban for `historical_performance_computed`.

Independent source inspection confirms that the clean score adapter contains that text only as an accepted Phase-B manifest guard key and requires the value to be exactly `false`. It does not import, reference, or call a historical-performance evaluator through that name.

Therefore the failure is a **test false positive**, not a scientific, model, data, scoring, or runtime failure.

## Bounded remediation

Only the static test was changed:

- old test blob: `c89bfab7173cd0355739cb3ec7960d5d3ea58f8a`
- remediated test blob: `53f2d6648dcde43c765ac754b10c09eeb2f1643d`

The remediated guard parses the clean adapter with Python AST and fails if any forbidden executable symbol is imported, referenced as a code name/attribute, or called:

- `fit_v4_head`
- `materialize_v4_target_ledger`
- `evaluate_head_by_date`
- `historical_performance_computed`

A string literal named `historical_performance_computed` is explicitly allowed because it is the safety flag read from the already accepted clean refit manifest; the test additionally requires that literal to remain present.

No clean scorer source was changed. In particular:

- `src/idx_trade/v4_x1_clean_forward_score.py` remains blob `f00528422a42835e5a969bfe503e29f91e0bf957`;
- model id/fingerprint unchanged;
- accepted four model SHA-256 values unchanged;
- clean panel/security-master identities unchanged;
- freeze boundary unchanged at `2026-08-20T12:08:44+00:00`;
- feature definitions, consensus, observed-bar semantics, and same-day anti-backfill unchanged;
- no provider/network/model/outcome/runtime/counter operation occurred.

## Machine contract repin

`config/ranking_v4_x1_clean_prospective_score_v1.json`

New config blob:

`fbdbed664259cf685a71dbbfebcc38ba7e558c92`

The only pinned implementation identity changed inside the contract is:

`tests/test_v4_x1_clean_forward_score.py -> 53f2d6648dcde43c765ac754b10c09eeb2f1643d`

The contract remains:

- `deployment_authorized=false`
- `score_capture_authorized=false`
- expected clean counter `0/100`

## Authorization boundary

Authorized next action is exactly one fresh **preflight + read-only readiness** attempt under the existing handoff after it is updated to reference this checkpoint/config.

Still prohibited:

- scheduled-task mutation;
- clean EOD pipeline execution that could score;
- direct score capture;
- registry/counter mutation;
- provider/network calls from score layer;
- model fit/retune;
- historical/backfill scoring;
- realized/protected outcome access.

If focused validation fails again for any reason, stop fail-closed and report without patch/retry in that local handoff.
