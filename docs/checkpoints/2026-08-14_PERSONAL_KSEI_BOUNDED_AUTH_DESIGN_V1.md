# Personal AKSes KSEI — Bounded Real-Auth Test Design V1

Date: 2026-08-14

Branch: `integration/personal-ksei-bounded-auth-design-v1`

Parent accepted schema HEAD:
`dd323be798b6d2fa1631e65b3dc3f2693be07ef8`

Authorization entering this lane:
`ACCEPTED_FOR_BOUNDED_REAL_AUTH_TEST_DESIGN`

## Scope

This lane implements the **design and offline safety harness only** for a future
single private AKSes KSEI authentication check.

Not authorized in this lane:

- real AKSes login;
- real username/password/token use;
- provider/KSEI network calls;
- raw portfolio persistence;
- bearer-token persistence;
- browser/frontend transport;
- public API exposure;
- `global-identity`;
- scheduler/history/backfill;
- public Ownership/KSEI changes;
- model/outcome/Financial PIT/Corporate Action/Foreign Flow changes;
- automatic BUY/SELL or portfolio action.

## Frozen call plan

The future reviewed run is constrained to:

1. one activation request;
2. one login request;
3. at most one request to each of the six audited portfolio endpoints, in order:
   - `PORTFOLIO_SUMMARY`
   - `CASH`
   - `EQUITY`
   - `MUTUAL_FUND`
   - `BOND`
   - `OTHER`

There are no retries. The transport receives a fixed 15-second timeout and no
caller-supplied endpoint path. `global-identity` is not in the allowlist.

## Secret handling

`EphemeralCredentials`, `EphemeralSecret`, `ProviderResponse`,
`ActivationResult`, and `LoginResult` are deliberately plain `__slots__`
classes rather than dataclasses. This reduces accidental generic introspection
and prevents `dataclasses.asdict()` from copying secret/raw-response fields.

The sensitive containers:

- redact `repr`/`str` where applicable;
- reject pickle/reduce/getstate serialization;
- are cleared after the one-shot runner exits where applicable;
- are never included directly in the report.

`prompt_ephemeral_credentials()` uses non-echoing `getpass` for both username
and password, so credentials are not accepted as command-line arguments.

Python cannot guarantee physical memory zeroization for immutable strings or
bytes. The V1 guarantee is therefore **no persistence, no generic
serialization, no logging, and best-effort reference clearing**, not
cryptographic RAM erasure.

## Observation boundary

Provider bodies are processed only in memory. The retained/reportable evidence
contains only:

- stage / endpoint class / allowlisted path;
- HTTP status or sanitized failure code;
- response byte count;
- SHA-256 of raw response bytes;
- JSON container/key/type/cardinality shape;
- bounded structural truncation markers;
- for summary only: row count and whether zero-valued summary rows were
  observed, without asset-class labels or numeric values.

No provider values are copied into the report. Dynamic object keys that look
like account identifiers are replaced by `<redacted-key>`.

The summary probe is deliberately non-committal:
`zero_value_rows_present=False` means only that none were observed in that
single response; it does not prove zero-value categories are omitted.

## Failure behavior

- activation/login failure stops immediately;
- 401/403 from a portfolio endpoint stops remaining calls;
- a non-auth endpoint failure is recorded once and the remaining exact
  endpoints may still be attempted;
- unexpected transport exceptions are collapsed to `TRANSPORT_ERROR` without
  propagating the original exception text into the sanitized report;
- oversized or non-JSON response bodies fail closed for structural parsing.

`completed_call_plan=True` means all six portfolio endpoint slots were
attempted once; it does **not** mean all six succeeded.

## Provider boundary

`BoundedKseiTransport` is a protocol only. No `requests`/HTTP implementation,
login parser, JWT handling, token store, or provider execution is added here.

A future concrete transport must be separately reviewed to prove that each
protocol method performs only the intended single network request, honors the
timeout, disables retries, keeps the bearer token in memory only, and does not
log raw request/response material.

## Validation performed by this agent

Because this runtime cannot checkout the private GitHub repository, exact
branch pytest is not claimed here.

A standalone synthetic package surrogate using the new module and a fake
transport passed:

`11 passed`

The surrogate covered the frozen policy, exact six-endpoint order, one-shot
budget, secret/reference clearing, report redaction, summary zero-state probe,
auth-stop behavior, non-auth continuation without retry, raw exception
sanitization, dynamic-key redaction, non-dataclass/non-serializable sensitive
containers, invalid JSON fail-closed behavior, and oversized-body fail-closed
behavior.

Exact repository tests and full pytest remain mandatory in independent review.

## Coordination note

Before implementation the latest `origin/main` was read and no other active
lane owned this private AKSes bounded-auth scope. The canonical AKSes row was
still stale relative to the accepted schema HEAD.

This ChatGPT connector cannot safely patch a single line of the shared
`TEAM_STATUS.md` without replacing the entire concurrently changing file.
Therefore the canonical row must be synchronized by a local/Codex reviewer
before any real-auth execution is considered. This is a coordination debt, not
authorization to bypass the ledger.

## Next gate

Independent review may return only:

- `ACCEPTED_FOR_ONE_BOUNDED_PRIVATE_REAL_AUTH_RUN`
- `REWORK`

Acceptance authorizes at most implementation/review of the concrete
server/local transport and one explicitly bounded run. It does not authorize
scheduler/history/UI/public API integration or repeated account access.
