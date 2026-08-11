# Foreign Flow V1

Status: initial revision-aware contract implemented; official IDX/Zapi source audit pending local runtime.

## Goal

Build a provenance-aware, point-in-time daily foreign-flow layer for IDX securities without silently mixing units, revised historical values, or source-specific timing semantics.

The first question is not whether foreign flow predicts returns. The first question is whether the official source can provide a historically consistent per-ticker buy/sell series whose unit, date, availability time, and coverage are understood well enough for research.

## V1 observation contract

Each canonical observation is one `(ticker, session_date, unit)` version with:

- ticker;
- exchange session date;
- explicit unit (`SHARES`, `LOTS`, or `IDR`);
- foreign buy;
- foreign sell;
- foreign net, exactly equal to buy minus sell;
- source publication time when available;
- `knowledge_at` as the first defensible time the observation can be used;
- official source/ref/HTTPS URL;
- SHA-256 of the exact raw source payload/file.

Unit conversion is not part of V1. Shares, lots, and rupiah value must never be silently merged.

## Revision semantics

Historical exchange/API values can change after first publication. V1 therefore permits multiple versions of the same `(ticker, session_date, unit)` only when they have distinct knowledge times.

A later version does not overwrite an earlier one. `foreign_flow_asof(t)` selects the latest version knowable at decision timestamp `t`.

Two conflicting versions with the same knowledge time fail closed and require explicit evidence reconciliation.

## PIT timing

A trading-session date is not automatically a knowledge timestamp.

The local source audit must establish whether IDX/Zapi exposes:

- an explicit publication/update timestamp;
- only an end-of-day date;
- or a live/current value whose historical availability time cannot be reconstructed.

Do not infer a same-day close timestamp merely because a record is labelled with that trading date. If publication timing cannot be established, retain the source for discovery/diagnostics but do not promote it to intraday or next-session PIT use without an explicit rule.

## Source policy

Preferred hierarchy:

1. direct official IDX endpoint/file;
2. Zapi only as an access/discovery transport to the same upstream IDX facts;
3. other providers only as reconciliation evidence unless separately promoted.

Representative Zapi/raw results should be compared against direct IDX where practical.

## Completeness questions

The local audit must determine:

1. exact upstream IDX endpoint(s) behind Zapi foreign-flow data;
2. field meanings and units for buy/sell/net;
3. whether values are shares, lots, rupiah value, or another basis;
4. whether all listed securities are returned or only securities with nonzero foreign activity;
5. whether a missing row means zero flow, unavailable data, suspended/no-trade, or source omission;
6. historical date range and pagination/batching behavior;
7. whether old dates are revision-sensitive;
8. publication/knowledge-time semantics;
9. whether current and historical payloads can be reproducibly hash-pinned;
10. strongest bounded date range for which coverage can be defended.

## Initial implementation

`src/idx_trade/foreign_flow.py` provides:

- strict ticker/unit/value/provenance validation;
- revision-aware observation identity;
- fail-closed same-knowledge conflicts;
- timezone-aware knowledge-time validation;
- as-of revision selection.

`tests/test_foreign_flow.py` covers unit ambiguity, buy/sell/net identity, impossible knowledge timing, revision visibility, same-time conflicts, and timezone-aware as-of selection.

## Acceptance gates

Before Foreign Flow V1 is promoted for research use:

- unit semantics must be explicit;
- missing-row semantics must be established;
- direct IDX/Zapi representative parity must pass;
- publication/knowledge timing must be documented;
- revision behavior must be tested on repeated historical queries or preserved captures;
- coverage by session/ticker must be measured against a defensible expected universe or traded-security set;
- a bounded completeness verdict must be stated;
- focused and full pytest must pass.

No foreign-flow feature engineering, model experiment, realized-outcome access, OPEN work, execution/PnL, or main merge is authorized by this data gate.
