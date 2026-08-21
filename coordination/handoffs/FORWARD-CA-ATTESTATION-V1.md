# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `ZAPI_DIVIDENDS_AUDIT_HARNESS_FIXED_EXISTING_ARTIFACT_INCONCLUSIVE_V1_1_BLOCKED`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope

Prospective, outcome-blind corporate-action attestation for paper Execution V1. This protects execution/portfolio accounting continuity; it is not the historical CA training-data lane and does not modify V4-X1 alpha.

## Primary provider

- repository: `nichsedge/idx-bei`
- pinned commit: `75d6c0f74fa360d225794c70c383348977de6798`
- upstream: direct `https://www.idx.co.id/primary`
- isolated provider environment managed by `uv` / Python 3.13

## Frozen live calendar schema

Accepted 2026-08-21 direct-IDX probe evidence:

- HTTP 200
- 260 `Results`
- raw SHA-256 `7ad2aeab850ea23a4df9f6aee91f1523b2a4110a30f48d6ecf51e8376be88c1c`
- structural fingerprint `09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`
- review status `PASS_ELIGIBLE_FOR_SCHEMA_FREEZE`
- no warnings or failures

Production `EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` is pinned to that value. Future raw calendar payload schema drift fails closed.

## Required Forward CA V1 legs

1. `/ListingActivity/GetIssuedHistory`
2. `/NewsAnnouncement/GetAllAnnouncement`
3. `/Home/GetCalendar`

Both `POST_EOD` and `PREOPEN` captures are required with identical ticker/date scope. Raw response bytes and source-chain hashes are verified before the final attestation.

Current Execution admission remains only:
`NO_RELEVANT_EVENTS`

Any relevant event, source incompleteness, hash mismatch, provider-pin mismatch or schema drift blocks normal execution and requires reconciliation.

## Cash dividend accounting — explicit requirement

Preregistered contract:
`docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ACCOUNTING_CONTRACT_V1.md`

Required future state semantics:

- entitlement snapshot = paper shares at EOD cum date after same-session execution;
- on ex date create a gross dividend receivable asset;
- receivable contributes to total-return NAV but is not spendable cash;
- selling on ex date does not erase already-earned receivable;
- buying first on ex date does not receive that dividend;
- on payment date transfer receivable to cash without recognizing PnL a second time;
- dividend tax/withholding remains explicit/unresolved.

Automatic dividend reconciliation is still `NOT_IMPLEMENTED_FAIL_CLOSED`.

## Alpha boundary around dividend traps

Do not adjust V4-X1 price inputs or ranks for dividends through this lane. V4-X1 is frozen. Any ex-date normalization, dividend-yield feature, days-to-cum/ex feature or event-aware entry rule requires a separately preregistered alpha/overlay challenger.

## Zapi `/dividends` audit — current gate

The user explicitly requested that `/dividends` be audited before Forward CA V1.1 is created.

Audit preregistration:
`docs/checkpoints/2026-08-21_ZAPI_IDX_DIVIDENDS_BOUNDED_AUDIT_PREP.md`

Prepared audit-only entry points:

- live bounded probe: `scripts/probe_zapi_idx_dividends_v1.py`
- offline reviewer: `scripts/review_zapi_idx_dividends_probe_v1.py`
- one-command Windows runner: `scripts/run_zapi_idx_dividends_audit_v1.ps1`

The runner uses the public Zapi catalog schema first and performs at most one authenticated request, with zero retries. `ZAPI_API_KEY` is never persisted.

Hard PASS status:
`PASS_ELIGIBLE_FOR_V1_1_STRUCTURED_HELPER`

It requires a ticker-scoped row with positive cash dividend/share plus parseable cum, ex, recording and payment dates with coherent ordering.

Forward CA V1.1 is currently:
`NOT_AUTHORIZED`

If the audit fails, do not create V1.1 from this endpoint. If it passes, V1.1 may be prepared with direct IDX remaining authority and Zapi acting only as a structured helper/parity source; disagreement remains fail-closed.

## Prepared Forward CA V1 entry points

- provider setup: `scripts/setup_idx_bei_forward_ca_provider.ps1`
- direct capture: `scripts/capture_forward_ca_idx_bei.py`
- offline merge/attestation: `scripts/build_forward_ca_attestation_v1.py`
- source verifier/classifier: `src/idx_trade/forward_ca_attestation_v1.py`
- Execution CA verifier: `src/idx_trade/v4_x1_execution_v1_verify.py`
- config: `config/forward_ca_attestation_v1.json`
- schema freeze checkpoint: `docs/checkpoints/2026-08-21_FORWARD_CA_ATTESTATION_V1_SCHEMA_FREEZE.md`

## Audit result — 2026-08-21

The existing external probe was reviewed offline. Its raw response is a valid
nested `data` envelope with `provider=idx`, `dataset=dividends`, and explicit
empty pagination (`page=1`, `nextPage=null`, `count=0`, `total=0`,
`hasMore=false`, `items=[]`). However, the catalog exposes `search` as an
upstream code/company filter and the existing request used only
`page=1&length=20`. The request therefore does not establish the endpoint's
ticker-scoped semantics for BBCA.

The minimal harness remediation and offline result are recorded in:
`docs/checkpoints/2026-08-21_ZAPI_IDX_DIVIDENDS_BOUNDED_AUDIT_RESULT.md`.
Result handoff:
`coordination/handoffs/FORWARD-CA-ATTESTATION-V1-ZAPI-DIVIDENDS-AUDIT-RESULT.md`.

Final procedural verdict:
`AUDIT_HARNESS_BUG_FIXED_REVIEW_EXISTING_ARTIFACT_AGAIN`.
The endpoint remains unadmitted; Forward CA V1.1 remains blocked. No second
authenticated request was made.

## Next lane action

1. run exactly one bounded Zapi `/dividends` audit using the repository runner;
2. review result against the preregistered PASS gate;
3. only on PASS, create Forward CA V1.1 and implement cash-dividend event certification/receivables;
4. then implement split/reverse-split quantity transform and Forward Paper orchestration.

Until an event-specific transformation is implemented, detected CA continues to block blind execution.
