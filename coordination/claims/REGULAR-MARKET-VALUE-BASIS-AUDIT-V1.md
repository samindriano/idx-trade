# Regular-Market Value Basis Audit V1

Status: `ACTIVE`
Owner: `ChatGPT/Regular-Market-Value-Basis-Audit`
Branch: `audit/regular-market-value-basis-v1`
Parent: `data/price-basis-remediation-v1`

## Scope

Outcome-blind, provider-free audit of frozen research-panel `regular_market_value` against immutable official IDX Stock Summary `Value` witnesses already present in the local external artifact store.

The lane measures exact ticker/date overlap, value parity, source/provenance seams, `close*volume`-like behavior, bounded impact on `log_regular_value_relative_20`, cross-sectional/market-relative value representation, and `V4_PRIMARY_LIQUID_CAUSAL_V1` eligibility.

## Hard boundaries

- no provider calls;
- no model fit or scoring;
- no target/outcome access;
- no protected-forward access;
- no parent-panel overwrite;
- no HLC remediation changes;
- no Volume/Value remediation is authorized by this audit;
- any confirmed material issue requires independent review and a separate preregistered remediation.
