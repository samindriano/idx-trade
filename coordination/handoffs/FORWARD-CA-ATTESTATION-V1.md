# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `CALENDAR_SCHEMA_FROZEN_DIVIDEND_ACCOUNTING_PREREGISTERED`
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

## Cash dividend accounting — now explicit requirement

Cash dividend handling is not optional. A large ex-date price drop can be mechanical while the entitled holder simultaneously owns a dividend claim. If paper NAV marks only the lower share price until cash payment, drawdown/return is wrong.

Preregistered contract:
`docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ACCOUNTING_CONTRACT_V1.md`

Required future state semantics:

- entitlement snapshot = paper shares at EOD cum date after same-session execution;
- on ex date create a gross dividend receivable asset;
- receivable contributes to total-return NAV but is not spendable cash;
- selling on ex date does not erase already-earned receivable;
- buying first on ex date does not receive that dividend;
- on payment date transfer receivable to cash without recognizing PnL a second time;
- dividend tax/withholding remains an explicit unresolved policy, not a hidden haircut.

Automatic dividend reconciliation is still `NOT_IMPLEMENTED_FAIL_CLOSED` until event amount/date extraction, paper-state receivables and tests are implemented.

## Alpha boundary around dividend traps

Do not adjust V4-X1 price inputs or ranks for dividends through this lane. V4-X1 is frozen.

A run-up before cum date or mechanical ex-date drop may therefore affect its raw-price alpha features. Any attempt to normalize ex-date returns, add days-to-ex/cum features, or avoid dividend-trap entries is a separately preregistered alpha/overlay challenger, not an accounting patch.

## Zapi status

The user-supplied Zapi changelog added dedicated IDX endpoints including `dividends`, `rights-offerings`, `stock-splits`, `issued-history`, `additional-listings`, `delistings` and updated `calendar`.

Decision:

- do not replace direct IDX V1;
- do not silently fallback in V1;
- Zapi `dividends` is especially valuable as a future structured-extraction/parity helper for dividend amount and dates;
- it must receive a bounded response/provenance audit before influencing execution/accounting;
- official direct IDX evidence remains authority; disagreement must fail closed until explicitly resolved.

## Prepared entry points

- provider setup: `scripts/setup_idx_bei_forward_ca_provider.ps1`
- direct capture: `scripts/capture_forward_ca_idx_bei.py`
- offline merge/attestation: `scripts/build_forward_ca_attestation_v1.py`
- source verifier/classifier: `src/idx_trade/forward_ca_attestation_v1.py`
- Execution CA verifier: `src/idx_trade/v4_x1_execution_v1_verify.py`
- config: `config/forward_ca_attestation_v1.json`
- schema freeze checkpoint: `docs/checkpoints/2026-08-21_FORWARD_CA_ATTESTATION_V1_SCHEMA_FREEZE.md`
- dividend contract: `docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ACCOUNTING_CONTRACT_V1.md`

## Next lane action

Before calling the Forward Paper Orchestrator production-ready, implement the minimum event-state processor in this order:

1. cash dividend extraction/certification and dividend receivable state;
2. split/reverse-split quantity transform;
3. Forward CA POST_EOD/PREOPEN orchestration;
4. relevant-event reconciliation path into Execution V1;
5. tests for restart/idempotency, cum/ex transitions, payment settlement and no double-counting.

Until those transformations are implemented, a detected CA continues to block blind execution.

Do not rerun the 2026-08-21 schema probe unless a deliberate schema re-certification is required.
