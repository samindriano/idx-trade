# Forward First-Weekday Reliability Remediation V1

Date: 2026-08-24 (Asia/Jakarta)

## Scope

This checkpoint covers a bounded reliability remediation for the existing
Stockbit prospective archive and Official Open capture. It does not change the
historical E2E replay, model contracts, counters, labels, outcomes, or the
installed Windows tasks.

Working branch: `fix/forward-first-weekday-reliability-v1`
Parent: `integration/idx-e2e-baseline-paper-v1@d49b1540d4e6b29deddc0f47ca0cf7cacc9e3b75`

The Stockbit implementation files are carried from the reviewed
`origin/main@5f1f1689240b43fe70eb2f6bb4b54dd901fa297c` lineage into this
isolated remediation branch; the official Open implementation remains from
the E2E integration lineage.

## Forensic result before remediation

All times below are Asia/Jakarta.

### Stockbit

- Pre-open scheduled run `32684333136` succeeded on the `origin/main` workflow
  code: `200/200`, `DATA_READY`, 5,941 normalized rows, manifest SHA
  `94d76d9dc3d60b81ab62f728fcf949fd4bb4f6ec77686ba88df5590bf383e952`.
- Midday scheduled run `32694723874` failed at 12:46 with a Zapi
  `requests.ReadTimeout`; it emitted no final manifest. The immutable log did
  not identify whether the timeout was during universe selection or stream
  retrieval, so no narrower claim is made.
- At 16:12 the after-close slot (16:47) had not yet run. The workflow is
  calendar-daily at 08:47, 12:07, and 16:47, not weekday-only.

### Official Open

- The installed task is enabled and Ready. Its five daily triggers are
  09:02, 09:07, 09:12, 09:17, and 09:22 plus AtLogOn, with
  `StartWhenAvailable` and `IgnoreNew`.
- Task history records one delayed launch at 15:10:52 with result `4` and five
  `NewInstanceIgnored` events. The event says a time-trigger condition but does
  not prove which trigger or AtLogOn caused the launch.
- The immutable status was `CAPTURE_FAIL_CLOSED` for 2026-08-24. No certified
  session manifest/raw/normalized folder was created.
- The prior direct/Zapi wrapper discarded the underlying request exception
  details, and the default direct path did not use the already accepted warmed
  `curl_cffi` Chrome transport.

## Remediation implemented

### Stockbit Stream V2

- `requests.RequestException` is captured for both universe and per-symbol
  requests.
- Each request has at most one bounded retry. Request errors and allowlisted
  transient HTTP 5xx responses are recorded with attempt number, safe error
  type/detail, status, and UTC observation time.
- A stream that fails twice is recorded as `REQUEST_EXCEPTION` and the run is
  `PARTIAL_FAILURE`; it cannot become `DATA_READY`.
- A partial immutable manifest is never overwritten. A deterministic resume
  namespace reuses only hash-verified prior `OK` raw/normalized objects and
  writes repaired objects and the terminal manifest under a new immutable run
  ID. A second incomplete resume namespace fails closed rather than creating
  duplicate or ambiguous writes.
- Existing quota, deterministic top-200 universe, per-symbol provenance,
  immutable storage, and outcome/model/counter boundaries are preserved.

### Official Open

- Default direct IDX capture now uses the accepted `curl_cffi` Chrome
  impersonation session, the two proven public-page warm-ups, session cookie
  continuity, and the page-specific referer. User-Agent is owned by the
  impersonation profile rather than manually fabricated.
- Direct request diagnostics retain a bounded exception type/message without
  credentials. Direct transport errors can fall back to Zapi raw passthrough.
- Zapi raw retries once only for request exceptions and allowlisted HTTP 5xx.
  Authentication errors, malformed HTTP 200 responses, incomplete counts,
  and provenance/schema errors remain non-retryable and fail closed.
- The existing `DIRECT_IDX_THEN_ZAPI_RAW_V1` policy and OpenPrice-only
  certification are unchanged. FirstTrade is never substituted.

## Bounded live probe

After focused and full tests passed, one isolated probe was run at
16:13:07 WIB using external root
`D:\Documents\Project\idx-forward-reliability-probe-20260824-v1`.
It returned `SOURCE_NOT_READY_OR_NO_SESSION` with
`OFFICIAL_OPEN_RAW_DATA_MISSING`, and produced only
`official_open/latest_capture.json`; no certified session artifact, paper
counter, or production runtime state was touched.

The probe therefore confirms fail-closed behavior, not a successful official
Open capture. The 16:47 Stockbit after-close run and the next weekday Official
Open run remain the controlled proof points.

## Validation

- Focused: `36 passed` using an isolated pytest temp root.
- Full repository: `706 passed`, `0 failed`, `3 existing FutureWarnings`.
- `python -m py_compile` passed for the changed Python modules.
- `git diff --check` passed.
- No provider/model/outcome/counter access occurred before the permitted
  isolated Official Open probe; no protected/fresh-forward outcomes were
  accessed.

## Decision

`FORWARD_RELIABILITY_REMEDIATED_NEXT_SESSION_PROOF_PENDING`

The transport/retry/idempotency defects are remediated and tested. A future
controlled weekday capture is still required before claiming an end-to-end
first-weekday PASS. Windows scheduled tasks were inspected only; they were not
mutated in this remediation.

`coordination/TEAM_STATUS.md` is owned by MAIN under the repository policy and
must be updated during integration rather than edited from this branch.
