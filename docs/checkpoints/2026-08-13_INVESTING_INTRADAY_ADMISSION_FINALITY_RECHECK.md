# Investing Intraday Admission — Finality Recheck

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT independent recheck
Branch: `data/investing-intraday-admission-pilot-v1`

## Decision

`CURRENT_INVESTING_INTRADAY_ADMISSION_PATH_FINAL_REJECTED_NOT_SOURCE_GLOBALLY_USELESS`

The exact Investing.com `tvc6` + persisted pair-ID + 60-minute-history path tested in the frozen admission pilot remains rejected and should not be rerun, bulk-backfilled, or admitted as a secondary historical intraday dataset. This recheck does **not** claim that every Investing.com product, endpoint, or future acquisition method is unusable. Investing may remain useful for bounded discovery/corroboration, or may be reconsidered only if a materially different source/acquisition hypothesis is preregistered.

## Why the rejection is now high-confidence

The current admission pilot failed multiple independent gates: 58/138 final provider errors; old/mid/recent listed-session coverage 44.30%/69.65%/52.17%; overall H/L/C exact 79.22%; Open exact 70.50%; and old volume-near 59.36%. Structural parsing itself was clean.

The key finality check is the prior depth audit. In that earlier run, all 3,685 sparse 1-hour requests completed with zero final provider errors, yet daily reconciliation was still only 74.22% H/L/C exact, 60.71% OHLC exact where Open was comparable, 79.30% volume exact, and 83.20% volume near-parity. Therefore the fidelity weakness exists even in a run where transport succeeded; fixing current 403 behavior alone does not solve the source-quality/admission problem.

The current upstream `investiny` implementation also documents interval-60 request handling with a 1,030-day per-chunk limit and a 1,927-day historical-lookback limitation. The pilot's roughly three-month windows are far inside the per-request span limit, so there is no evidence that the admission failure was caused by accidentally asking for an unsupported request window.

Upstream PR #84 (`Use curl-cffi to prevent 403 error`) changes the request client from `httpx` to `curl_cffi.requests` and adds `impersonate="chrome"` while retaining the same `tvc6` endpoint and headers. The pilot already aligned its transport to this pattern. Thus the obvious currently known anti-403 transport remediation was already incorporated before the final runtime.

## What remains possible

Do not spend further effort rescuing this exact path via more retries, longer backoff, chunk-size tuning, or gate relaxation. Such changes might improve transport but do not address the independently reproduced daily-fidelity weakness.

Reopen Investing only if there is materially new evidence, for example:

- a different official/paid Investing data product or endpoint with reproducible historical intraday semantics;
- a demonstrated deterministic explanation for the daily-fidelity mismatches that can be validated without outcome/model access;
- or a separately frozen limited role such as corroboration-only evidence rather than dataset admission.

Historical intraday source research itself remains open in principle; this checkpoint closes only the current Investing admission route.

## No scientific state change

No provider call, artifact regeneration, canonical-panel write, model work, O2/Path Risk work, or protected-outcome access occurred in this recheck. The accepted pilot runtime artifacts and prior rejection remain immutable.
