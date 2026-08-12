# Margin Summary Deep Public-Source Audit

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/broker-margin-source-audit-v0`
Status: `SEMANTICS_NOT_CERTIFIED_LIKELY_ELIGIBILITY_SUMMARY_LIVE_PARITY_REQUIRED`

## Scope

Deep public-source audit of the IDX/Zapi `margin-summary` lane after the preliminary broker/margin audit. No billed provider call, no use of the user's `ZAPI_API_KEY`, no bulk acquisition, no automation change, no model/feature work, and no forward-outcome access.

This checkpoint supersedes the preliminary *interpretive* optimism that Margin Summary may represent actual margin-financed transaction flow. That possibility remains technically possible, but current public evidence does not certify it and the safer working interpretation is that the dataset may instead be a stock-summary view for the margin-eligible universe.

## Public-source facts established

### Zapi contract

Reference: `https://zpi.web.id/api/finance/idx/llms.txt`

Zapi documents:

- endpoint: `GET /v1/finance:idx/margin-summary`;
- description: `Ringkasan perdagangan efek margin`;
- explicit cadence warning: `Terbit per periode margin, bukan harian — perhatikan tanggal pada respons`;
- `date` parameter description: `Tanggal periode`, not `Tanggal bursa`;
- maximum page length: 300;
- example period: `2026-07-14`;
- example universe: `total=220`;
- fields: `code`, `low`, `high`, `close`, `change`, `value`, `volume`, `frequency`;
- provider label: `idx`.

The contract exposes no field explicitly describing financed amount, margin balance, margin buy quantity, outstanding margin position, margin-order count, broker financing, or another margin-specific quantity.

### Official IDX structure

Official IDX public pages expose:

1. `Stock Summary`, with distinct views/tabs for `All Stock`, `Margin`, and `Short Selling`;
2. a separate `Margin and Short Selling Stock List` archive, published by month; the 2026 page exposes monthly files including July 2026;
3. trading-mechanism rules under which a margin transaction is a purchase financed by a Securities Company, only eligible securities may be used, and the trading order carries a specific margin sign.

The existence of a margin transaction sign proves that margin-tagged transactions exist in exchange mechanics. It does **not** prove that the public `Margin` Stock Summary view reports the subset of margin-tagged executions.

## Deep semantic assessment

Two hypotheses remain:

### H1 — actual margin-tagged transaction subset

Under H1, each row's `low/high/close/value/volume/frequency` is computed only over executions carrying the margin transaction sign.

If H1 is true, ratios against All Stock could expose genuinely new leverage/crowding information, e.g. margin-volume share, margin-value share, and margin-frequency share.

### H2 — ordinary Stock Summary restricted to margin-eligible securities

Under H2, Margin Summary is a category/filter view: ordinary trading statistics for securities in the applicable margin-eligible list/period.

If H2 is true, `value/volume/frequency` do **not** measure actual margin financing and must never be interpreted as margin usage, leverage, crowding, or financed-flow intensity. The new information would be primarily periodic membership/eligibility, not transaction flow.

## Evidence weighting

Current public evidence favors H2 enough that H1 must fail closed until directly proven:

1. Zapi calls the date a **period date** and explicitly says the dataset is not daily. This differs from its daily foreign-flow/stock-summary contracts.
2. The returned schema is generic trading OHLC/value/volume/frequency with no explicit margin-specific quantity.
3. IDX separately publishes monthly Margin and Short Selling eligible-security lists.
4. IDX exposes `Margin` as a view inside Stock Summary, which is compatible with an eligibility-filtered summary.
5. `total=220` is a plausible eligible-security-universe scale, though exact equality to the July 2026 official list has **not** yet been established.

Counterweight:

- exchange rules do require a specific margin sign for margin orders, so an actual transaction-subset dataset is technically possible;
- the preliminary checkpoint stated that example margin values appeared materially different from an all-stock comparison, but this comparison has not been independently reproduced in this deep public-source audit and therefore is **not accepted as decisive evidence** here.

## Current verdict

`SEMANTICS_NOT_CERTIFIED_LIKELY_MARGIN_ELIGIBILITY_SUMMARY_NOT_SAFE_AS_MARGIN_FLOW`

Consequences:

- do **not** call the endpoint `margin flow`;
- do **not** derive margin-share / leverage / crowding features;
- do **not** automate or bulk-backfill it for modelling yet;
- do **not** assume the returned period date is a publication timestamp, effective-from timestamp, or first-knowable time;
- treat historical PIT as unresolved.

## Minimal decisive live audit

A bounded local audit using the existing `ZAPI_API_KEY` is justified because public documentation cannot settle H1 vs H2. It should use very few calls and stop once semantics are decisive.

For one certified period first (preferably 2026-07-14 because Zapi provides a documented example):

1. fetch the full `margin-summary` (`length=300` should cover the documented 220-row example in one wrapper call);
2. fetch same-date full `stock-summary`;
3. obtain the official margin-eligible list applicable to that period;
4. compare ticker sets exactly;
5. compare `low/high/close/value/volume/frequency` exactly for every intersecting ticker.

### Decisive H2 test

If Margin Summary ticker membership matches the applicable eligible list and the generic trading metrics equal same-date All Stock metrics across the intersecting rows, classify as:

`ELIGIBILITY_FILTER_CONFIRMED_NO_MARGIN_FLOW_SIGNAL`

Then stop margin-flow research. Any future use should be a separate PIT membership/eligibility hypothesis.

### Decisive H1 candidate test

If the rows are a strict numeric subset of same-date All Stock activity (for example values/volumes/frequencies differ systematically and never exceed total activity) and this cannot be explained by market-segment filtering, then resolve the upstream raw IDX path and perform direct-source parity before accepting H1.

Additional bounded checks only if needed:

- query adjacent non-period dates to see whether the endpoint snaps/returns the same period;
- one or two older periods to establish historical depth;
- repeated capture of one old period for byte/revision stability;
- search for official publication/effective-date evidence.

## PIT boundary

Even if transaction-subset semantics eventually pass, historical model use remains blocked unless publication/effective timing is defensible. Retrieval time today is only an observation-time upper bound and must not be backdated as historical `knowledge_at`.

A future prospective archive may record actual acquisition time, but should only be considered after source semantics are certified and should integrate with the existing canonical archive rather than creating a duplicate scheduler.

## Research value conditional on outcome

- If H1 passes: potentially meaningful new leverage/crowding/fragility information; worth a separately preregistered research lane later.
- If H2 passes: modest structural information only — margin eligibility/member changes — likely correlated with liquidity/financial-health criteria and therefore lower priority than a genuine margin-usage signal.

## Authorization boundary

This checkpoint authorizes no provider call, no automation, no backfill, no feature generation, no model experiment, and no outcome access. The only reasonable next gate is the minimal H1-vs-H2 live parity audit above.
