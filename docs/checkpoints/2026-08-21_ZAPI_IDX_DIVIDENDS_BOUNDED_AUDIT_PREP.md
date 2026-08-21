# Zapi IDX `/dividends` — Bounded Audit Preparation

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Status: `AUDIT_PREPARED_LIVE_PROBE_REQUIRED_V1_1_NOT_AUTHORIZED`

## Purpose

Audit the newly announced Zapi dedicated IDX `dividends` endpoint before it is allowed to participate in Forward CA V1.1 or paper cash-dividend accounting.

The user explicitly requested the order:

1. audit Zapi `/dividends`;
2. only if it passes, prepare V1.1.

No V1.1 promotion is authorized by this preparation alone.

## Existing authority boundary

Forward CA V1 primary authority remains direct official IDX through pinned:

`nichsedge/idx-bei@75d6c0f74fa360d225794c70c383348977de6798`

Zapi may become a structured extraction/parity helper. It may not silently replace official IDX evidence. A future direct-IDX/Zapi disagreement must fail closed until explicitly resolved.

## Why `/dividends` is being audited

Cash-dividend accounting requires structured values for:

- ticker;
- gross cash dividend per share;
- regular-market cum date;
- regular-market ex date;
- recording date;
- payment date.

Official publication timestamp and immutable official-source evidence remain sourced/certified from direct IDX. Therefore the Zapi helper does not need to independently provide the announcement publication timestamp to pass this bounded helper audit.

## Public evidence before live probe

The Zapi changelog supplied by the user announces a dedicated IDX endpoint named `dividends` together with rights offerings, stock splits, additional listings and delistings.

The currently indexed Zapi IDX documentation still exposes the older API surface, but confirms the production API namespace pattern is `https://api.zpi.web.id/v1/finance:idx/...`, authenticated by `x-api-key`.

The public `zeative/zpi-sdk` catalog implementation confirms no-auth discovery routes exist for endpoint metadata/schema under `/api/public/scrapers/...`.

The indexed Zapi `company-profile` example already demonstrates structured dividend semantics such as `cashPerShare`, `cumDate`, `exDate`, `recordDate`, and `paymentDate`. This is encouraging but is not evidence that the dedicated `/dividends` endpoint has the same contract.

## Frozen probe procedure

Repository runner:

`scripts/run_zapi_idx_dividends_audit_v1.ps1`

It performs:

1. one unauthenticated public catalog-schema request for `idx/dividends`;
2. requires the discovered schema to expose a ticker-scoping parameter (`code`, `ticker`, or `symbol`);
3. performs at most one authenticated GET to `https://api.zpi.web.id/v1/finance:idx/dividends` for `BBCA`;
4. uses zero retries;
5. reads `ZAPI_API_KEY` only from process memory / local secure prompt;
6. never writes the key or a key hash to disk;
7. stores raw response bytes and SHA-256 externally;
8. immediately runs an offline semantic reviewer.

Default evidence root:

`D:\Documents\Project\idx-zapi-dividends-probe-<YYYYMMDD>-v1`

Existing output directories are never overwritten.

## Preregistered PASS gate

The reviewer may return:

`PASS_ELIGIBLE_FOR_V1_1_STRUCTURED_HELPER`

only if all hard conditions pass:

- manifest/probe contract intact;
- exactly one authenticated request and zero retries;
- HTTP 200;
- JSON response;
- raw SHA-256 matches;
- public catalog exposed ticker scoping;
- a dividend row can be unambiguously associated with the requested ticker;
- gross cash dividend/share is positive;
- cum date parses;
- ex date parses;
- recording date parses;
- payment date parses;
- ordering satisfies `cum < ex <= recording <= payment`;
- if response declares `provider`, it must be `idx`;
- if response declares `dataset`, it must identify dividends.

Missing provider/dataset labels are warnings rather than hard failures because Zapi is being evaluated only as a helper, not as authority.

The reviewer records the observed response structural fingerprint and row-field union but does not automatically freeze or promote it.

## FAIL semantics

Any hard-gate failure returns:

`FAIL_NOT_ELIGIBLE_FOR_V1_1`

and no V1.1 should be created from this endpoint.

If the public catalog schema is stale/missing and does not expose a ticker filter, the probe stops before spending an authenticated request.

## What a PASS would authorize next

A PASS authorizes preparation—not automatic deployment—of Forward CA V1.1 with:

- direct IDX remaining authority;
- Zapi `/dividends` admitted as structured helper/parity source;
- direct-vs-Zapi disagreement fail-closed;
- cash-dividend event certification combining structured amount/dates with official IDX announcement/calendar evidence;
- dividend receivable state/accounting implementation and tests.

A PASS does not authorize dividend-adjusted V4-X1 alpha, historical PnL, historical CA backfill, or silent fallback to Zapi.
