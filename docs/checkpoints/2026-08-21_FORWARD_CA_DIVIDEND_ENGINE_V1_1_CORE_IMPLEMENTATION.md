# Forward CA — Dividend Engine V1.1 Core Implementation

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Status: `CORE_IMPLEMENTED_AWAITING_LOCAL_VALIDATION_EVENT_ADMISSION_STILL_BLOCKED`

## Source gate resolved

The forward/current cash-dividend source gate is now admitted from direct official IDX evidence:

- discovery/publication: `/ListedCompany/GetAnnouncement`;
- authority for terms: immutable official IDX announcement attachments;
- authority review: `PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1`;
- authority recommendation: `DIRECT_IDX_ANNOUNCEMENT_PLUS_HASHED_ATTACHMENT`.

Admitted BBCA event:

- announcement timestamp: `2026-08-19T18:31:03`;
- gross dividend/share: IDR 25;
- cum regular/negotiated: 2026-08-28;
- ex regular/negotiated: 2026-08-31;
- record date: 2026-09-01;
- payment: 2026-09-16.

Announcement raw SHA-256:
`6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473`

Attachment SHA-256 set:

- `4ee38c989b3ff09c5d721e6d56340d873e8183822eadd3c87cd8dbfa576e092c`
- `1d8b37031c4a0c23baeb6d511e8270c3f2be160c9c40c3102c7faaffdf54b94b`
- `93ff2e663af91ac6d87ed29c6a192725f2b4b86b0fc0432610ff7bdaad0c1949`

`LINK_DIVIDEND` remains a lagging corroboration/history helper, not forward authority. Zapi remains optional parity only.

## Scientific boundary

V4-X1 alpha/model/Decision V1 is unchanged.

The legacy `PaperPortfolioState` and `paper_state_hash()` are intentionally unchanged. V1.1 is additive and wraps legacy state instead of mutating the frozen V1 contract.

This prevents a dividend-accounting fix from silently rewriting the scientific/execution identity of existing V1 paper state.

## New core

Added `src/idx_trade/forward_dividend_v1.py` with:

- `CertifiedCashDividend`;
- `PaperDividendEntitlement`;
- `PaperDividendReceivable`;
- `PaperDividendSettlement`;
- `DividendLedger`;
- `DividendAwarePaperState`;
- deterministic ledger/state hashing;
- direct-IDX attachment-review certification with byte-level SHA re-verification;
- cum-date EOD entitlement snapshot;
- ex-date receivable creation;
- payment-date receivable-to-cash settlement;
- restart/replay idempotency checks;
- conflict detection for competing event identities on the same ticker/cum date;
- total-return NAV including outstanding receivables;
- additive `prepare_execution_v1_1()` / `execute_open_v1_1()` wrappers.

## Frozen accounting semantics implemented

Entitlement:

`entitled_shares = paper shares held EOD cum date after same-session execution`

Therefore:

- held/bought at Open cum date and still held EOD => entitled;
- sold at Open cum date => no entitlement;
- sold on ex date => previously earned receivable remains;
- first buy on ex date => no entitlement.

At/after ex date:

`gross_receivable = entitled_shares * gross_dividend_per_share_idr`

Total-return NAV:

`cash + market value + outstanding dividend receivables`

Outstanding receivables affect NAV but not available/spendable cash for sizing.

At/after payment date, the outstanding receivable moves into gross paper cash exactly once. Tax remains explicitly unresolved under `UNRESOLVED_GROSS_PAPER_CREDIT`.

## Compatibility design

`DividendAwarePaperState` contains:

- the unchanged legacy `PaperPortfolioState`;
- a separately hashed `DividendLedger`.

The V1.1 prepare wrapper first obtains the legacy V1 execution plan, then recomputes entry sizing only when a receivable causes total-return NAV to differ. It keeps legacy projected spendable cash unchanged.

The V1.1 execute wrapper calls legacy `execute_open_v1()` and reattaches the verified dividend ledger to the resulting base state.

## Tests added but not yet locally observed

Added `tests/test_forward_dividend_v1.py` covering:

- source review + attachment SHA certification;
- attachment tamper fail-closed;
- cum-date entitlement + replay idempotency;
- cum-date sold/no-position case;
- sell on ex date retaining receivable;
- first buy ex date not receiving prior dividend;
- receivable in NAV but not cash;
- payment settlement exactly once;
- event conflict fail-closed;
- separate dividend-aware hash while legacy paper hash remains unchanged;
- V1.1 sizing receives corrected NAV while available cash remains unchanged;
- V1.1 execution wrapper preserves ledger.

These tests have not yet been observed running in the user's local runtime. Do not claim them PASS until that evidence exists.

## Still blocked

This core implementation does **not** authorize Forward Paper execution through a dividend event yet.

The existing CA verifier and legacy `execute_open_v1()` still admit only `NO_RELEVANT_EVENTS`. That fail-closed behavior is intentionally retained until the next lane implements event-specific certified cash-dividend reconciliation/admission.

Remaining gates:

1. focused local tests for `forward_dividend_v1`;
2. event-specific CA attestation admission for a certified cash dividend;
3. POST_EOD/PREOPEN orchestrator integration;
4. end-to-end restart/idempotency validation;
5. only then consider `forward_ca_v1_1_authorized=true`.

No paper mutation is authorized by this checkpoint alone.
