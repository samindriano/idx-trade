# Handoff

from: Codex
to: ChatGPT reviewer / MAIN
task_id: IDX-CORPORATE-ACTION-PIT-DETERMINISTIC-LINKAGE-V1
model_used: GPT-5.6 Luna xhigh with read-only semantic/provenance audits
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: ec7261b3ddae9c2fb2cfd98fb9ea59b01ce57586
branch: data/corporate-action-pit-deterministic-linkage-v1
head_commit: `87e0304709b9b3cdc3e413f74c2dcf7630cb539e`

## Scope

Implemented and validated deterministic corporate-action PIT linkage semantics
on a bounded official KSEI document sample. No market-wide backfill, canonical
table, OHLC adjustment, models, outcomes, AKSes credentials, Foreign Flow, or
Financial PIT work was performed.

## Files changed

- `src/idx_trade/corporate_action_pit_linkage.py`
- `src/idx_trade/corporate_action_pit_documents.py`
- `tests/test_corporate_action_pit_linkage.py`
- `tests/test_corporate_action_pit_linkage_semantics.py`
- `tests/test_corporate_action_pit_documents.py`
- dated result checkpoint

## Findings

- parent source-audit manifest verified: SHA
  `d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf`
- bounded final manifest: SHA
  `1db444f6ceb815bdc29f1f80c8158c7a2050ebf7a5fe0ec0c4230e65940bb195`
- 5/5 KSEI documents parsed and 5/5 schedule-locator/document identity rows
  exact
- families: rights 1, bonus 2, stock split 2
- MEGA base/follow-up revision: exact via explicit prior KSEI reference
- SINI: exact rights identity and explicit 2:3 rights schedule
- MLPT: exact stock-split identity, 1:25, schedule subject overrides
  `Mandatory Conversion`
- RAJA: exact stock-split identity, 1:5, schedule subject overrides
  `Mandatory Conversion`
- KSEI evidence is DATE_ONLY; no intraday publication time fabricated
- MLPT IDX correction timestamp is retained separately as exact event-specific
  IDX evidence with a caveat that the IDX attachment does not cite the KSEI ref
- TRST cancellation remains unresolved because current status is not dated
  historical knowledge
- synthetic locator mismatch returns conflict and preserves both identities

## Decisions made

`CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_DATE_ONLY`.

The core is ready for another bounded validation, but canonical PIT event
materialization remains blocked on stronger cross-source publication linkage and
historical cancellation evidence.

## Validation

Focused linkage/parser tests: 20 passed.
Full pytest: 64 passed, 1 failed, 0 warnings (65 collected). The only failure
is the pre-existing unrelated storage revision-conflict expectation in
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`;
this lane did not touch `storage.py`.

`git diff --check`: clean after final staging. Working tree is expected clean
after this handoff metadata commit and push.

## Recommended next action

Independent ChatGPT review of the semantic changes and bounded artifact
manifest. Do not start market-wide materialization or OHLC adjustment from this
handoff.
