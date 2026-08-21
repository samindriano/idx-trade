# Forward CA Dividend Runtime Persistence V1.1

Date: 2026-08-21
Lane: `integration/forward-ca-attestation-v1`
Owner: `ChatGPT/Forward-CA-Attestation`

## Verdict

`DIVIDEND_RUNTIME_PERSISTENCE_V1_1_VALIDATED_ORCHESTRATOR_STILL_BLOCKED`

The durable-state gap identified after the Dividend Engine V1.1 accounting and cash-dividend-specific CA admission work is closed at the persistence-contract level.

Forward Paper V1.1 remains **not authorized**. The remaining separate work is real POST_EOD/PREOPEN orchestrator binding plus an end-to-end restart rehearsal through that orchestrator.

## Validation anchors

Persistence code HEAD validated by GitHub Actions:

`9ba619916c37d28121c39f61148ab0d03ac21bf0`

Workflow:

- run ID: `32459699635`
- job ID: `96703976541`
- Python: `3.12.14`
- full pytest: **456 passed, 38 warnings in 32.47s**
- conclusion: `success`

The immediately prior persistence revision also passed the full suite, but the final accepted anchor is the append-only/monotonic hardening revision above.

Earlier user-local focused validation for the accounting + cash-dividend admission layers was:

- `23 passed`

## Files

Runtime persistence:

`src/idx_trade/forward_dividend_runtime_v1_1.py`

Adversarial persistence tests:

`tests/test_forward_dividend_runtime_v1_1.py`

Existing additive layers retained unchanged:

- `src/idx_trade/forward_dividend_v1.py`
- `src/idx_trade/forward_dividend_execution_v1_1.py`

## Frozen boundary preserved

This work does not modify:

- frozen V4-X1 alpha/model identity;
- Decision V1 rules;
- legacy `PaperPortfolioState` schema;
- legacy `paper_state_hash()`;
- `V4_X1_EXECUTION_V1` behavior;
- protected outcomes;
- historical PnL;
- model features/ranks;
- dividend-aware alpha logic.

Dividend V1.1 remains an additive execution/accounting layer.

## Durable runtime contract

Each execution-session state is persisted as an immutable deterministic JSON snapshot under:

`<runtime_root>/forward_execution_v1_1/state_snapshots/YYYY-MM-DD.json`

A snapshot binds:

1. legacy executable paper state;
2. dividend entitlement/receivable/settlement ledger;
3. certified dividend evidence registry;
4. deterministic component hashes;
5. previous snapshot path/SHA/runtime-state hash.

### Same-session semantics

An exact byte-identical rerun is idempotent and may reuse the existing immutable snapshot.

A different state for the same session fails closed with a session conflict. The runtime never silently overwrites an existing snapshot.

### Parent hash chain

Child snapshots bind the exact parent file SHA and parent runtime-state hash. Every load recursively verifies the ancestor chain.

The latest-state loader rejects forked histories: every earlier snapshot must be an ancestor of the selected latest snapshot.

### Certified dividend registry

Certified events persist independently from the daily CA window so an announcement discovered before cum date remains available on cum/ex/payment sessions.

Each registry row stores the official evidence locator and is reverified on load through the admitted direct-IDX attachment verifier. Review SHA, attachment bytes, certified event semantics, and announcement identity therefore cannot silently drift.

The registry is append-only across snapshots:

- a previously registered event cannot disappear;
- a previously registered event cannot change identity/evidence;
- conflicting different events for the same ticker + cum date fail closed.

### Ledger-to-registry binding

Every entitlement must map exactly to a certified registered event for:

- ticker;
- dividend/share;
- cum date;
- ex date;
- record date;
- payment date;
- source evidence SHA.

An unregistered or semantically changed event cannot be persisted in the dividend ledger.

### Monotonic dividend lifecycle

Across parent -> child snapshots:

- entitlements cannot disappear or mutate;
- settlements cannot disappear or mutate;
- an outstanding receivable may remain unchanged;
- a receivable may disappear only by becoming the matching settlement;
- arbitrary receivable deletion fails closed.

This prevents a crash/restart path from losing or double-booking the economic claim.

### Decision shadow reconstruction

The persisted actual paper portfolio is not naively treated as Decision V1 shadow state when paper non-fills exist.

The additive runtime reconstructs shadow holdings as:

`(actual positions - pending sells) + pending buys`

This preserves the frozen Decision V1 semantics while allowing actual paper execution to remain behind the intended transition during partial/non-fills.

## Current authorization boundary

Resolved:

- direct official IDX dividend authority;
- cash-dividend accounting core;
- cash-dividend-specific relevant-event admission;
- durable hash-verified runtime persistence;
- certified-event memory across sessions;
- persistence-level restart/idempotency invariants.

Still blocked:

1. real POST_EOD/PREOPEN orchestrator integration;
2. end-to-end orchestrator crash/restart/idempotency rehearsal;
3. controlled operational activation review.

`forward_ca_v1_1_authorized=false` therefore remains correct.

## Source migration note

The generic Forward CA capture still contains the legacy announcement leg `/NewsAnnouncement/GetAllAnnouncement`, while the admitted forward dividend authority is `/ListedCompany/GetAnnouncement` + hashed official attachments.

Do not mix that source migration into this persistence checkpoint. It remains a separate runtime/source integration concern and must not be used to reinterpret the persistence verdict.
