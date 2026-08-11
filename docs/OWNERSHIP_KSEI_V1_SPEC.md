# Ownership / KSEI V1

Status: initial PIT ownership-snapshot contract implemented; bounded IDX/KSEI/Zapi source audit completed on 2026-08-12. Source discovery and per-security semantics are usable, but publication-time PIT and complete historical coverage remain fail-closed pending a source-timestamp/version solution.

## Goal

Build a provenance-aware, point-in-time ownership layer that can answer:

> At decision timestamp `t`, which issuer ownership snapshot was actually knowable, what date did that snapshot describe, and which ownership facts did that exact version contain?

The source's ownership `as_of_date` is not automatically its research knowledge time.

## Initial scope

Prioritize official ownership data that may support:

- local versus foreign ownership;
- investor-category ownership;
- large-holder / ownership-band information;
- named-holder information where officially exposed;
- free-float-related percentages where the source semantics are explicit.

Do not infer one category from another. A KSEI local/foreign aggregate is not silently treated as named-holder or free-float data.

## Snapshot contract

Each immutable snapshot version requires:

- ticker;
- source ownership `as_of_date`;
- timezone-aware official `published_at`;
- `knowledge_at`, defaulting only to that same publication timestamp when no later supporting evidence is required;
- official source/ref/HTTPS URL;
- SHA-256 of the exact raw file/response used.

A correction or revised file is a new snapshot version. It must never overwrite what was knowable before the revision.

Same-ticker/as-of-date conflicting source versions with the same knowledge time fail closed.

## Long-form fact contract

Facts are permanently bound to one snapshot version and use explicit dimensions.

Supported initial dimensions:

- `RESIDENCY`;
- `INVESTOR_TYPE`;
- `HOLDER_BAND`;
- `NAMED_HOLDER`;
- `FREE_FLOAT`.

Supported metrics:

- `SHARES` with unit `SHARES`;
- `PERCENT` with unit `PERCENT`;
- `HOLDER_COUNT` with unit `COUNT`.

The contract does not convert holder counts, percentages, and share quantities into one another without separately proven denominators.

## PIT rules

For an as-of decision timestamp:

1. discard snapshot versions with `knowledge_at > t`;
2. for each `(ticker, as_of_date)`, keep the latest remaining version;
3. expose only facts belonging to those selected versions.

A later correction therefore cannot leak backward into an earlier decision.

## Source policy

Preferred hierarchy:

1. official IDX/KSEI ownership artifact or API;
2. Zapi as transport/discovery when it exposes the same upstream official data;
3. other providers only as reconciliation evidence unless separately accepted.

Raw captures should remain outside Git. Preserve source URLs/refs, hashes, capture timestamps, and source field semantics.

## Local source-audit questions

The local audit must first discover what the currently available sources actually contain. In particular:

1. Which Zapi IDX ownership-file endpoints or raw IDX endpoints expose ownership artifacts?
2. Which KSEI Zapi endpoints expose local/foreign ownership, and are they market-wide aggregates or per-security records?
3. What date does each file/row represent: month-end, record date, publication date, or another reference date?
4. Is an explicit publication timestamp available and timezone-resolvable?
5. Are historical files retained, and how far back?
6. Are revised/replaced files separately discoverable or silently overwritten?
7. Do file categories such as >5%, >1%, investor classification, or free float have stable semantics over time?
8. Can representative Zapi-returned artifacts be byte/field cross-checked against direct official IDX/KSEI sources?
9. Does every expected issuer appear, or are some categories intentionally sparse?
10. Is there any bounded period whose source discovery, publication timing, and revision policy are defensibly complete?

Do not bulk-download years of ownership files before those metadata gates are understood.

## Initial implementation

`src/idx_trade/ownership_pit.py` provides:

- immutable ownership snapshot canonicalization;
- timezone-aware publication/knowledge validation;
- revision-aware as-of snapshot selection;
- long-form fact validation with explicit dimension/metric/unit semantics;
- fact selection bound to the selected snapshot version;
- fail-closed conflict, orphan-fact, duplicate-fact, and percentage validation.

`tests/test_ownership_pit.py` covers publication leakage, later revisions, same-time conflicts, timezone requirements, metric/unit semantics, orphan facts, and revision-bound fact selection.

## Acceptance gates

Before Ownership / KSEI V1 can be promoted for historical research use:

- source `as_of_date` semantics must be explicit;
- first-publication/knowledge timing must be defensible;
- source categories and units must be documented rather than inferred;
- historical revisions/replacements must not silently overwrite prior states;
- representative Zapi/direct-official parity must pass;
- missing-row/file semantics must be understood;
- a bounded historical completeness window must be demonstrated or explicitly remain incomplete;
- focused and full pytest must pass.

No ownership feature engineering, model experiment, realized-outcome access, execution/PnL, or main merge is authorized by this data gate.
