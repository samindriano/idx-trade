# 504-session blocker diagnosis — targeted repair plan

Date: 2026-08-08

Starting failed runtime: `db7cce412dd211335f8ea7967d9ce1c1c722bc93`

The 504-session gate (`2024-06-21 -> 2026-07-31`) failed only for FREN, MASA,
and MFIN. The 126-session certified baseline continued to reproduce 963/963 PASS.

## FREN — historical identity gap, not a universe exclusion

FREN is a historical common share and must remain in scope for dates when it was
listed.

Authoritative issuer evidence establishes:

- ticker: FREN;
- company: PT Smartfren Telecom Tbk;
- share listing date: 2006-11-29;
- official merger schedule / deletion of FREN trading on IDX: 2025-04-17.

Because `listed_to` is inclusive in the project security-master contract, the
historical listing interval ends at 2025-04-16. From 2025-04-17 the security is
DELISTED for this project ontology.

A generic curated historical identity registry was added. It supplements only a
still-missing common-share identity and never overwrites a primary IDX/KSEI
identity already present.

Evidence sources:

- official Smartfren annual report;
- official Smartfren/XL merger plan.

## MASA / MFIN — Yahoo historical-symbol loss, not missing exchange prices

Both are defensible IDX common-share identities:

- MASA: Multistrada Arah Sarana Tbk, listing date 2005-06-09;
- MFIN: Mandala Multifinance Tbk, listing date 2005-09-06.

The 504 runtime proved official ACTIVE sessions for the missing dates, but Yahoo
returned `NO_PROVIDER_ROWS` after the securities became historical/delisted
symbols. Therefore Yahoo absence is a provider-history limitation, not evidence
that the exchange price never existed.

The official IDX Stock Summary payload includes daily regular-market price fields
including `OpenPrice`, `FirstTrade`, `High`, `Low`, `Close`, `Volume`, and
`Frequency`, while non-regular metrics are separate. A secondary official price
fallback was added with these rules:

1. use only an official Stock Summary row with positive Regular-Market Volume and
   Frequency;
2. prefer positive `OpenPrice`;
3. if `OpenPrice` is zero/missing, accept a positive `FirstTrade` as the first
   session execution price;
4. High/Low/Close must be positive and satisfy OHLC envelope invariants;
5. invalid/missing official OHLC remains unresolved;
6. existing Yahoo/provider rows are never overwritten;
7. fallback fills absent dates only and records `IDX_PUBLIC_STOCK_SUMMARY` source
   provenance.

The repair should be run only on the exact missing ACTIVE session set:

- MASA: 22 rows;
- MFIN: 249 rows;
- total: 271 missing ACTIVE price rows before repair.

## Decision

Do not run the 252-session diagnostic yet. The 504 failure has already been
localized to three securities with concrete repair paths.

Next runtime:

1. supplement FREN from `config/curated_security_identities.csv`;
2. rebuild the PIT master and verify FREN listing boundary;
3. derive the exact missing ACTIVE sessions for MASA/MFIN from the failed 504
   gate artifacts;
4. run the official IDX price fallback only for those dates/tickers;
5. re-run raw-price semantics and the 126/504 ladder;
6. if 504 PASS, freeze the 504 panel/manifest;
7. if any official OHLC row remains invalid/missing, stop with the exact dates and
   diagnostics instead of weakening the price gate.

No modelling, IDX-VAL-002, 1260-session expansion, or merge to main until 504 is
certified.
