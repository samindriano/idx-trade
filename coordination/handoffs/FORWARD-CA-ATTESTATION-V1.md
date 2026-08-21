# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `DIVIDEND_AUTHORITY_ADMITTED_ACCOUNTING_CORE_IMPLEMENTED_LOCAL_VALIDATION_PENDING_EVENT_ADMISSION_BLOCKED`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope and hard boundary

Prospective, outcome-blind corporate-action protection for paper Execution V1. This lane protects execution/portfolio-accounting continuity and does not modify historical training data or frozen V4-X1 alpha/model/Decision V1.

Legacy `PaperPortfolioState`, `paper_state_hash()` and `V4_X1_EXECUTION_V1` remain unchanged. Dividend V1.1 is additive.

## Primary provider

- repository: `nichsedge/idx-bei`
- pinned commit: `75d6c0f74fa360d225794c70c383348977de6798`
- upstream: direct `https://www.idx.co.id/primary`
- transport: `curl_cffi`, chrome impersonation
- isolated provider environment: `uv` / Python 3.13

Do not fork `idx-bei` for dividend business logic. It remains transport/session infrastructure. Dividend normalization, evidence, state transitions, hashing and accounting live in `idx-trade`.

## Frozen live calendar schema

Accepted 2026-08-21 evidence:

- raw SHA-256 `7ad2aeab850ea23a4df9f6aee91f1523b2a4110a30f48d6ecf51e8376be88c1c`
- structural fingerprint `09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`
- review `PASS_ELIGIBLE_FOR_SCHEMA_FREEZE`
- 260 results, no warnings/failures.

## Existing Forward CA V1

Required generic legs remain:

1. `/ListingActivity/GetIssuedHistory`
2. `/NewsAnnouncement/GetAllAnnouncement`
3. `/Home/GetCalendar`

Both POST_EOD and PREOPEN are required with immutable raw/source-chain verification.

Current legacy execution admission is intentionally still `NO_RELEVANT_EVENTS` only. A relevant event cannot pass blindly.

## Cash dividend contract

Preregistered at:
`docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ACCOUNTING_CONTRACT_V1.md`

Frozen semantics:

- entitlement = paper shares held EOD regular-market cum date, after same-session execution;
- buy Open cum-date and still hold EOD => entitled;
- sell Open cum-date => no entitlement;
- sell ex-date => keeps prior entitlement/receivable;
- first buy ex-date => no prior entitlement;
- ex-date creates gross receivable;
- receivable contributes to total-return NAV but is not spendable before payment;
- payment moves receivable to cash exactly once;
- tax/withholding remains unresolved and explicit; no silent haircut.

## Forward dividend authority — ADMITTED

The source gate is resolved.

Current/forward authority:

`/ListedCompany/GetAnnouncement` + hash-pinned official IDX announcement attachments.

Admission review:
`PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1`

Authority recommendation:
`DIRECT_IDX_ANNOUNCEMENT_PLUS_HASHED_ATTACHMENT`

Admitted BBCA event:

- announcement ID `20260819183103-005/CSG-IVR/2026_id-id`
- number `005/CSG-IVR/2026`
- title `Jadwal Dividen Tunai Interim`
- timestamp `2026-08-19T18:31:03`
- form ID `11000`
- Rp25/share
- cum regular/negotiated 2026-08-28
- ex regular/negotiated 2026-08-31
- record 2026-09-01
- payment 2026-09-16.

Announcement raw SHA:
`6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473`

Attachment SHAs:

- `4ee38c989b3ff09c5d721e6d56340d873e8183822eadd3c87cd8dbfa576e092c`
- `1d8b37031c4a0c23baeb6d511e8270c3f2be160c9c40c3102c7faaffdf54b94b`
- `93ff2e663af91ac6d87ed29c6a192725f2b4b86b0fc0432610ff7bdaad0c1949`

The PDF semantic review observed all required fields and passed after remediation of the parser for `Rp25,00 per lembar saham`.

## LINK_DIVIDEND role

`/DigitalStatistic/GetApiDataPaginated?urlName=LINK_DIVIDEND` is live and structured but is **not forward authority**.

Observed:

- historical March query: HTTP 200 / structured rows but the expected BBCA event was not in that monthly bucket;
- active August BBCA query: HTTP 200 / zero BBCA rows while the official announcement already existed.

Frozen role:
`LAGGING_CORROBORATION_AND_HISTORICAL_HELPER_NOT_FORWARD_AUTHORITY`.

## Zapi status

- dedicated `/dividends`: final NO-GO for V1.1 after known-positive BBCA March 2026 targeted request still returned zero rows;
- `company-profile`: did contain the current BBCA Rp25 event, but remains optional parity only;
- neither Zapi source may override direct official IDX evidence.

## Dividend Engine V1.1 core — IMPLEMENTED, LOCAL TEST EVIDENCE PENDING

Checkpoint:
`docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ENGINE_V1_1_CORE_IMPLEMENTATION.md`

Module:
`src/idx_trade/forward_dividend_v1.py`

Additive state types:

- `CertifiedCashDividend`
- `PaperDividendEntitlement`
- `PaperDividendReceivable`
- `PaperDividendSettlement`
- `DividendLedger`
- `DividendAwarePaperState`

Capabilities implemented:

- offline certification from admitted attachment review with actual file SHA re-verification;
- deterministic evidence/event IDs;
- deterministic dividend ledger and dividend-aware state hashes;
- cum-date EOD entitlement snapshot;
- ex-date receivable creation;
- payment settlement to gross cash;
- replay/idempotency checks;
- fail-closed event conflicts;
- total-return NAV including receivables;
- additive `prepare_execution_v1_1()` that corrects NAV while leaving spendable cash unchanged;
- additive `execute_open_v1_1()` that preserves the dividend ledger while delegating base execution to frozen V1.

Tests added:
`tests/test_forward_dividend_v1.py`

They must be run locally before claiming PASS.

## Why V1.1 is still NOT authorized

`forward_ca_v1_1_authorized=false` remains correct.

The old CA verifier and `execute_open_v1()` still admit only `NO_RELEVANT_EVENTS`. The accounting core by itself does not authorize a cash-dividend event to pass the Forward CA gate.

Remaining blockers:

1. run focused local `forward_dividend_v1` tests;
2. implement event-specific CA attestation/reconciliation status for a certified cash dividend;
3. bind that status into execution verification without weakening other relevant-event fail-closed behavior;
4. integrate official announcement/attachment capture into POST_EOD/PREOPEN orchestration;
5. validate restart/replay end-to-end;
6. only then promote Forward Paper V1.1.

## Alpha/research boundary

Dividend announcements are prospectively valuable research data: amount/yield surprise, sessions to cum/ex, pre-cum run-up, ex-date behavior, and post-ex mean reversion.

Archive publication timestamps + immutable source hashes, but do not alter frozen V4-X1 features/ranks. Any dividend-aware alpha/entry overlay belongs to a separately preregistered V4-X2/successor experiment.
