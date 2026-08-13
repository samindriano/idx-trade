# AKSes Adapter Schema Hardening V2

Status: `REVIEW_ROUND_2`

Branch: `integration/schema-hardening-v2`

## Purpose

This checkpoint records remediation of the first independent review of the Personal AKSes KSEI Portfolio Integration V1 preparation lane. The scope remains preparation and safe integration skeleton only.

No real AKSes login, credential use, bearer/token acquisition, provider request, authenticated response capture, public API, or portfolio UI is authorized by this checkpoint.

The target trust boundary remains:

`Personal Web -> authenticated first-party private IDX-Trade backend -> server-side personal portfolio adapter -> AKSes KSEI`

The browser must never communicate with AKSes directly.

## Non-overlap boundary

This lane remains separate from the existing public Ownership/KSEI V1 work (including PR #23). It does not change public market ownership providers, public ownership facts, Corporate Action PIT, Financial PIT, Foreign Flow, model ranking, forward outcomes, or O2 research.

## Independent review round 1

Round 1 returned `REWORK` before any real-auth test. The findings were:

1. `COMPLETE` did not prove all required endpoint classes succeeded.
2. Append-only/dedup was only an interface and lacked a concrete atomic uniqueness/immutability reference implementation.
3. `source_commit_pins` was mutable despite frozen dataclasses.
4. Data minimization was key-name focused and did not sufficiently constrain sensitive values/raw account identifiers.
5. Runtime Python contract and checked-in JSON Schema were not a single enforced validation path.
6. Decimal scale differences changed hashes/dedup keys.
7. Duplicate holdings/cash rows were not rejected.

## Remediation

### 1. Evidence-backed completeness

The canonical snapshot now requires endpoint evidence for the complete fixed endpoint-class set:

- `PORTFOLIO_SUMMARY`
- `CASH`
- `EQUITY`
- `MUTUAL_FUND`
- `BOND`
- `OTHER`

Each endpoint evidence row records success, observed rows, accepted rows, rejected rows, and an optional bounded failure code.

`COMPLETE` is valid only when every required endpoint is present exactly once, every endpoint succeeded, and every endpoint has zero rejected rows. `PARTIAL` requires explicit failure or rejection evidence. Accepted detail-row counts are reconciled against the canonical positions/cash rows. An empty `COMPLETE` snapshot therefore requires explicit zero-row success evidence for every required endpoint; it cannot arise from a default flag.

### 2. Append-only storage semantics

`PortfolioSnapshotStore` now separates:

- `append_if_new()`
- `latest_observation()`
- `latest_complete()`

A reference `SqlitePortfolioSnapshotStore` implements the required semantics for tests/design validation:

- primary uniqueness on `(scope_ref, history_dedup_key)`;
- atomic `BEGIN IMMEDIATE` + insert-if-absent behavior;
- unique `snapshot_id`;
- database triggers reject UPDATE and DELETE;
- `latest_complete()` only reads last-good complete state, so a newer partial observation cannot replace it.

This SQLite class is explicitly a reference/test implementation. It is not authorization to store real KSEI holdings in an unencrypted local SQLite file. Production storage must preserve equivalent uniqueness/immutability while remaining private and encrypted at rest.

### 3. Immutable provenance pins

Reviewed source references remain pinned to:

- `nichsedge/ksei-mcp@a3dfd3260889d704b75001387b646c25b4b69aa3`
- `chickenzord/goksei@5e51319feb3d373e463c21dfca5c31f971335653`

Both exact pins are mandatory. The mapping is defensively copied and exposed through `MappingProxyType`; caller mutation cannot alter a constructed snapshot's provenance/hash semantics.

### 4. Fail-closed data minimization

The canonical contract now uses structural allowlists and bounded string lengths, in addition to forbidden identity/secret field names.

`subaccount_ref` cannot be a raw provider account value. `derive_subaccount_ref()` requires a backend-held HMAC key of at least 32 bytes and emits only `ksa_<sha256>`. The raw identifier and HMAC key are never canonical fields.

The minimization validator rejects common authorization/secret forms, JWT-like values, email-like identity values, phone-like identity values, and long raw account/identity-number-like strings in free-text fields. Institution/security text is bounded and control characters are rejected. Programmatic synthetic negative tests cover these cases without using real personal data.

Still excluded from canonical persistence by design: AKSes username/password or transformed password, bearer/session token, raw securities account number, SID/investor identifiers, NIK/NPWP/passport/card IDs, full profile identity, email/phone, global-identity response, and raw authenticated provider payload.

### 5. Runtime JSON Schema parity

`src/idx_trade/personal_portfolio/schema.py` is the runtime Draft 2020-12 schema definition. Canonical snapshot generation invokes schema validation with `FormatChecker`, so timezone-naive JSON timestamps fail the same canonical path rather than relying only on the `format` annotation.

The checked-in artifact is `schemas/personal_portfolio_snapshot_v1.schema.json`. Tests require structural equality between that file and the runtime schema and exercise dataclass -> canonical JSON -> schema -> dataclass round-trip parity.

The reviewed upstream commit pins and fixed endpoint set are also encoded in the schema rather than allowing arbitrary/empty provenance pins.

### 6. Decimal canonicalization

Decimal serialization now strips representation-only scale differences and canonicalizes signed zero to `0`. Therefore economically identical values such as `1200.0` and `1200.00` produce the same canonical holdings representation and history dedup key.

`fetched_at` remains deliberately excluded from `history_dedup_key`, while `snapshot_at`, holdings/cash, endpoint evidence, raw-response hash, and source provenance remain included. A transport retry can deduplicate; a later provider observation remains appendable.

### 7. Duplicate-row rejection

Positions are unique by the canonical identity tuple of security symbol/code, asset class, currency, institution, and opaque subaccount reference. Cash rows are unique by currency, institution, and opaque subaccount reference. Duplicate identities fail before persistence rather than silently double-counting a portfolio.

## Source/client audit retained

### nichsedge/ksei-mcp

Reviewed pin: `a3dfd3260889d704b75001387b646c25b4b69aa3`.

Behavioral reference only. The reviewed implementation shows the AKSes web login/activation and portfolio endpoint pattern but also includes local JSON token persistence and unverified JWT-expiry parsing. Its async aggregate can represent category failure as `None` and print errors. The README says MIT, but the reviewed pinned tree did not contain a LICENSE file, so licensing remains inconsistent and no code was copied.

### chickenzord/goksei

Reviewed pin: `5e51319feb3d373e463c21dfca5c31f971335653`.

Behavioral/type-shape reference only. The pinned repository contains an MIT license and useful typed portfolio structures, but its default file-backed auth store is not encrypted, JWT expiry is parsed unverified, generic GET status handling is not consistently fail-closed, and `RemoveInvalidData()` can silently remove malformed share rows. None of those behaviors is adopted as the production adapter contract.

## Security decisions unchanged

- Credentials/backend secrets remain server-side only and must never enter browser bundles, local/session storage, repository files, fixtures, logs, CLI arguments, or artifacts.
- Bearer/session material should be in-memory by default. Any future persistence requires a protected OS/cloud secret store or equivalently encrypted restricted server storage.
- Unverified JWT expiry may at most be a cache hint, never authenticity or authorization proof.
- Logs must be allowlisted metadata only; no auth headers, credentials, provider bodies, identity profile, or raw account values.
- No raw provider/debug endpoint may be exposed through the web application.
- First-party web auth must use secure session controls; state-changing endpoints need CSRF defenses and all rendered/provider text must remain XSS-safe.
- Normalized stored financial data requires encryption at rest and service-level access restrictions; raw authenticated provider responses are not retained by default.
- Login/session refresh must be rate-limited/singleflight with bounded retry/backoff and no retry storm.
- Provider outage serves only explicitly stale last-good normalized state; failures never overwrite a good complete state.
- Unknown response shapes fail closed rather than being guessed/coerced.

## Validation boundary

No live provider validation is included. Review-round-2 validation is limited to focused offline tests, import/compile checks, schema parsing, and repository diff review.

The branch must not be promoted to a real-auth test solely because these remediation changes exist. It requires a second independent review verdict.

## Next gate

Exact sequence remains:

`independent review round 2 -> bounded real-auth test design -> one bounded private/no-persist real-auth test -> sanitized response-shape capture -> normalizer against actual observed shape -> authenticated private backend API -> small portfolio UI`

Optional historical scheduling remains later and requires a separate privacy/retention decision.

Until review round 2 accepts the remediation, stop here.
