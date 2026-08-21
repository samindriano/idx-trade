# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `DIRECT_IDX_DIVIDEND_PROBE_PREPARED_V1_1_BLOCKED_PENDING_LIVE_PARITY`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope

Prospective, outcome-blind corporate-action attestation for paper Execution V1. This protects execution/portfolio accounting continuity; it is not the historical CA training-data lane and does not modify V4-X1 alpha.

## Primary provider

- repository: `nichsedge/idx-bei`
- pinned commit: `75d6c0f74fa360d225794c70c383348977de6798`
- upstream: direct `https://www.idx.co.id/primary`
- isolated provider environment managed by `uv` / Python 3.13

Do not fork or modify `idx-bei` for dividend business logic. It remains a pinned transport/Cloudflare layer. Dividend normalization, state, reconciliation, hashing and accounting belong in `idx-trade`.

## Frozen live calendar schema

Accepted 2026-08-21 direct-IDX probe evidence:

- HTTP 200
- 260 `Results`
- raw SHA-256 `7ad2aeab850ea23a4df9f6aee91f1523b2a4110a30f48d6ecf51e8376be88c1c`
- structural fingerprint `09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`
- review status `PASS_ELIGIBLE_FOR_SCHEMA_FREEZE`
- no warnings or failures

Production `EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` is pinned to that value. Future raw calendar schema drift fails closed.

## Required Forward CA V1 legs

1. `/ListingActivity/GetIssuedHistory`
2. `/NewsAnnouncement/GetAllAnnouncement`
3. `/Home/GetCalendar`

Both `POST_EOD` and `PREOPEN` captures are required with identical ticker/date scope. Raw bytes and source-chain hashes are verified before final attestation.

Execution admission remains only `NO_RELEVANT_EVENTS`. Any relevant event, incomplete source, hash/provider mismatch or schema drift blocks blind execution until reconciled.

## Cash dividend accounting

Preregistered contract:
`docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ACCOUNTING_CONTRACT_V1.md`

Required semantics:

- entitlement snapshot = paper shares at EOD cum date after same-session execution;
- on ex date create gross dividend receivable;
- receivable contributes to total-return NAV but is not spendable cash;
- sell on ex date preserves already-earned receivable;
- buy first on ex date gets no prior entitlement;
- payment date moves receivable to cash without double-counting PnL;
- dividend tax/withholding remains explicit/unresolved.

Automatic dividend reconciliation remains `NOT_IMPLEMENTED_FAIL_CLOSED`.

## Dividend terms source — direct IDX pivot

A first-party structured IDX dividend feed was identified:

`GET /DigitalStatistic/GetApiDataPaginated?urlName=LINK_DIVIDEND`

with monthly parameters `periodYear`, `periodMonth`, `periodType=monthly`, bounded `pageSize/pageNumber`, and structured rows containing at minimum:

- `code`
- `cashDividend`
- `cumDividend`
- `exDividend`
- `recordDate`
- `paymentDate`

Independent implementations reviewed before admission:

- `NeaByteLab/IDX-API` commit `910b8db70893b93920a1bba331d00a1a245907c6`;
- `rakasatriaefendi/Si-Cuan-Apps` commit `0b78bcaf04705f8eeea34cde05a7a394478c20c8`.

The second implementation additionally demonstrates currency/type normalization, source fingerprinting, duplicate handling and validation warnings.

Prepared direct-IDX admission probe:

- `scripts/probe_forward_ca_idx_dividend_v1.py`
- `scripts/review_forward_ca_idx_dividend_probe_v1.py`
- `scripts/run_forward_ca_idx_dividend_probe_v1.ps1`
- checkpoint: `docs/checkpoints/2026-08-21_FORWARD_CA_DIRECT_IDX_DIVIDEND_ENGINE_PREP.md`

Known-positive preregistered parity event:

- BBCA
- period 2026-03
- Rp281/share
- cum 2026-03-27
- ex 2026-03-30
- record 2026-03-31
- payment 2026-04-08

Hard PASS:
`PASS_DIRECT_IDX_DIVIDEND_SOURCE_ELIGIBLE_FOR_V1_1`

The probe performs exactly one direct official IDX request through the pinned provider, zero retries, immutable raw capture + SHA, then offline exact parity review. It does not mutate paper state or promote V1.1 itself.

## Announcement/publication evidence remains mandatory

`LINK_DIVIDEND` certifies structured terms but does not replace disclosure-time evidence. Existing direct IDX announcement capture remains the source for publication timestamp, early announcement detection, attachments, revisions and cancellation evidence.

Target dividend state machine after source admission:

1. `ANNOUNCED_PENDING_TERMS`
2. `TERMS_CERTIFIED`
3. `ENTITLED`
4. `RECEIVABLE`
5. `PAID`
6. `REVISED_OR_CONFLICTED`

Any missing/conflicting official evidence fails closed.

## Alpha boundary and prospective research archive

Dividend announcement information may be valuable alpha data: amount/yield surprise, sessions to cum/ex, pre-cum run-up and post-ex behavior. Archive it prospectively with publication timestamps and immutable source hashes, but **do not modify frozen V4-X1**.

Any dividend-aware entry rule, price normalization, indicated-yield feature or event overlay must be a separately preregistered V4-X2/successor experiment.

## Zapi status

Dedicated Zapi `/dividends` is final `NO_GO` for V1.1 after a corrected known-positive BBCA March 2026 request returned HTTP 200 but `total=0/items=[]`.

Do not spend further requests trying to rescue that endpoint absent a material Zapi version change.

Zapi `company-profile` audit tooling remains available but is now **optional parity only** and is not required to unblock Direct IDX Dividend V1.1.

## Forward CA V1.1 promotion sequence

Current status: `NOT_AUTHORIZED`.

1. run the direct IDX `LINK_DIVIDEND` known-positive probe;
2. only on PASS, add `dividend_terms` as an official Forward CA capture/evidence leg;
3. normalize deterministic dividend event IDs/source fingerprints and reconcile announcement + calendar evidence;
4. implement/test entitlement → receivable → payment lifecycle, restart/idempotency and revisions;
5. include receivables in NAV/state hash but exclude from spendable cash before payment;
6. then implement split/reverse-split transforms and recurring Forward Paper orchestration.

Until event-specific reconciliation is implemented, detected CA continues to block blind execution.
