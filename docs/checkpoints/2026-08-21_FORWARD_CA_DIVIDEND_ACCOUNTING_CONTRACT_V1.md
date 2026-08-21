# Forward CA — Cash Dividend Accounting Contract V1

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Status: `PREREGISTERED_IMPLEMENTATION_REQUIRED_FAIL_CLOSED`

## Why this exists

Forward CA cannot stop at event detection. Cash dividends create a mechanical discontinuity between quoted price return and investor total return. On ex-date, the stock price can fall mechanically while an entitled holder simultaneously acquires a cash-dividend claim. If the paper portfolio marks only the lower stock price and waits until payment date to recognize the dividend, interim NAV and drawdown are understated/overstated incorrectly. If the eventual payment is then booked as fresh PnL, return is double-counted.

This contract separates that accounting problem from alpha research.

## Hard scientific boundary

V4-X1 is frozen. No dividend adjustment is authorized inside V4-X1 score inputs, feature definitions, training representation, rank logic or Decision V1.

A large dividend can therefore still influence raw-price features around ex-date. Fixing that potential alpha distortion requires a separately preregistered successor/challenger experiment (for example dividend-adjusted features or an event overlay). It must not be smuggled into Forward CA accounting.

Forward CA dividend accounting is permitted only to keep executable paper portfolio state and total-return NAV mechanically correct.

## Cash-dividend event contract

Before automatic reconciliation is allowed, one event must have defensible, hash-backed fields for:

- ticker;
- announcement/publication timestamp;
- gross cash dividend per share in IDR;
- regular-market cum date;
- regular-market ex date;
- recording date;
- payment date;
- immutable official-source evidence SHA-256.

Missing, conflicting, ambiguous or structurally changed fields remain fail-closed.

Direct official IDX evidence through the pinned `idx-bei` path remains authority. Zapi's new dedicated `dividends` endpoint is a high-value candidate for structured extraction/parity only after its own bounded audit. It may not silently override or replace official IDX evidence.

## Entitlement snapshot

For this paper strategy, execution occurs at the official Open and positions are represented in whole lots.

Frozen intended entitlement rule for implementation:

`entitled_shares = paper position shares at EOD of the regular-market cum-date, after all same-session simulated execution has been applied`

Consequences:

- a position already held and still held through cum-date EOD earns the dividend;
- a position bought at Open on cum date and still held at EOD earns the dividend;
- a position sold at Open on cum date does not earn the dividend in the paper ledger;
- a holder may sell on ex-date and still retain the previously established dividend receivable;
- a position first bought on ex-date does not receive that dividend.

If later settlement/market microstructure evidence shows this simplified paper rule is inconsistent with the broker/exchange contract, implementation must fail closed and this contract must be versioned rather than silently edited.

## NAV and cash accounting

At the transition into ex-date, once entitlement is certified:

`gross_dividend_receivable_idr = entitled_shares * gross_dividend_per_share_idr`

The receivable becomes a portfolio asset.

Paper total-return NAV must therefore be conceptually:

`NAV = spendable_cash + market_value_positions + outstanding_dividend_receivables + other future certified CA receivables`

The dividend receivable is **not spendable cash** before payment date. This prevents the sizing/execution engine from buying stocks with dividend money that has not yet been paid.

On payment date:

- reduce the matching dividend receivable by the paid amount;
- increase cash by the same amount;
- do not recognize a second gain at payment because economic recognition already occurred when the receivable was created.

## Tax boundary

Dividend taxation is deliberately not inferred here. Investor tax treatment can depend on investor type and other conditions. V1 must preserve the gross entitlement separately from any future tax/withholding model.

Until a tax policy is separately frozen:

- gross entitlement may be used for total-return research accounting;
- no claim may be made that the resulting cash/NAV is after-tax;
- a future net-cash implementation must represent withholding/tax explicitly rather than baking an undocumented haircut into dividend-per-share.

## Dividend trap / alpha behavior

This accounting fix does **not** protect the model from an economic or behavioral "dividend trap". A stock can rally into cum date and mechanically gap/drop on ex-date. Because V4-X1 remains on its frozen raw-price representation, that move may affect subsequent alpha scores.

Potential future research lanes, not authorized here:

- `days_to_cum_date` / `days_to_ex_date` structural features;
- trailing/forward indicated dividend yield;
- ex-date mechanical-return normalization;
- event-aware new-entry overlay;
- dividend-run-up / post-ex mean-reversion hypothesis.

Any such test must be preregistered and evaluated as an alpha/overlay challenger, not introduced through portfolio accounting.

## Execution interaction

Current Forward CA V1 correctly fails closed on any relevant event. That behavior remains until event-specific reconciliation is implemented and tested.

For a fully certified cash dividend, the intended future sequence is:

1. detect and certify event;
2. snapshot entitlement at cum-date EOD;
3. create dividend receivable at ex-date;
4. preserve receivable independent of later selling;
5. allow ordinary execution only after the CA state transition is verified;
6. settle receivable into cash on payment date;
7. retain immutable event/source/state-transition hashes.

Stock splits, stock dividends, rights/HMETD and other share-changing actions remain separate transformations and must not reuse the cash-dividend processor blindly.

## Promotion requirements

Automatic cash-dividend reconciliation remains blocked until all of the following exist:

1. admitted structured extraction for dividend amount + dates from official evidence;
2. tests for buy/sell on cum date, sell/buy on ex date, payment-date settlement and duplicate-event idempotency;
3. receivable included in paper state hash and NAV but excluded from spendable cash;
4. restart/replay-safe immutable event identifiers;
5. conflict behavior for direct IDX vs any future Zapi parity source;
6. focused and randomized invariants showing no double-counting or missing entitlement.

Until then: `RELEVANT_EVENT_DETECTED -> reconciliation required -> no blind execution`.
