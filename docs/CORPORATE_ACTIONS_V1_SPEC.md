# Corporate Actions V1

Status: initial data-foundation scaffold; real IDX/Zapi source acquisition pending local runtime audit.

## Goal

Build a provenance-aware corporate-action event layer that can explain structural discontinuities in raw IDX price/share data before those discontinuities are mistaken for market moves, bad data, or model signal.

This lane does not change the frozen model or automatically adjust the existing price panel.

## Initial V1 scope

Focus on share-structure events with direct relevance to raw price/share comparability:

- stock split;
- reverse split;
- rights issue;
- bonus shares;
- stock dividend;
- capital reduction;
- other explicitly documented share-structure events.

Cash-dividend research, suspension/tradability history, sector classification, listing-lifecycle reconstruction, and model features are separate lanes.

## Canonical event semantics

Each event must identify:

- ticker;
- normalized action type;
- `market_effective_date`: the first exchange date/session on which the relevant share/price basis changes;
- announcement/knowledge time where available;
- type-specific ratio/economic terms;
- official source provenance.

Source-specific fields such as `exDate`, `effectiveDate`, `distributionDate`, or similarly named provider fields must not be mapped to `market_effective_date` until their upstream semantics are verified.

## Ratio semantics

For `STOCK_SPLIT` and `REVERSE_SPLIT`, `ratio_old : ratio_new` means old shares converted into new shares. Example: 1 old share -> 2 new shares is `ratio_old=1`, `ratio_new=2`.

For rights/bonus/stock-dividend events, the ratio is the source-stated entitlement basis and must be interpreted according to event type. V1 deliberately does not apply a simple split adjustment to those events.

Only split/reverse-split events receive a deterministic mechanical diagnostic:

- `share_multiplier = ratio_new / ratio_old`;
- `expected_post_price_ratio = ratio_old / ratio_new`.

No automatic historical-price rewrite is authorized by this spec.

## Provenance contract

Direct official IDX evidence is canonical when available. Zapi may be used as an IDX access/discovery transport, but it is not silently promoted as an independent authority.

A canonical V1 row requires:

- `source`;
- `source_ref`;
- HTTPS `source_url`;
- SHA-256 of the exact raw response/file used for the mapped facts.

Duplicate logical events from multiple sources must be reconciled explicitly before canonicalization. The canonicalizer fails closed instead of choosing one silently.

## Knowledge time

`announced_at` is the official publication/announcement timestamp when available. `knowledge_at` is when the decision-critical evidence is actually knowable to the research system.

If the same official source establishes the event and no later evidence is required, `knowledge_at = announced_at`. If supporting evidence is published later, the later knowledge time must be preserved.

This allows the event history to remain useful for ex-post data-quality diagnostics without creating PIT leakage if the same data is later used in research.

## Initial implementation

`src/idx_trade/corporate_actions.py` provides:

- strict event canonicalization;
- action-type and ratio validation;
- provenance validation;
- fail-closed duplicate-event handling;
- split/reverse-split factor diagnostics;
- adjacent raw-price discontinuity audit without automatic correction.

`tests/test_corporate_actions.py` contains synthetic/adversarial contract tests.

## Local source-acquisition milestone

The next task must use local IDX/Zapi access to discover the actual available corporate-action sources and determine coverage before any dataset is promoted.

The source audit should answer:

1. Which official IDX/Zapi endpoints or official files expose stock split, reverse split, rights, bonus shares, stock dividend, and capital-reduction events?
2. What are the exact semantics of each returned date and ratio field?
3. How far back does each event type go, and is pagination/archive coverage demonstrably complete?
4. Can Zapi-returned facts be cross-checked against direct IDX on representative events?
5. For the existing research price panel, how many large raw-price discontinuities are explained by verified corporate actions?
6. Which event types/periods remain incomplete and must stay fail-closed?

## Acceptance gates

Corporate Actions V1 may be promoted only for event types and date ranges whose discovery method is demonstrably capable of finding the relevant events.

A source that returns plausible events but provides no defensible completeness basis may still be retained as discovery/reconciliation evidence, but must not be labeled complete.

Before promotion:

- event schemas and date semantics must be documented;
- official source lineage must be preserved;
- duplicate/conflicting events must be reconciled explicitly;
- representative direct-IDX cross-checks must pass;
- price-panel diagnostics must be run;
- focused and full pytest must pass.

No model, feature, adjusted-price rewrite, outcome access, execution/PnL, or main merge is authorized by passing this data gate.
