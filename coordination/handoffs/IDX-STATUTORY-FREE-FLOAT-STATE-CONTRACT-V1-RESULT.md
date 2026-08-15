# Handoff — Statutory Free-Float Knowledge-State Contract V1 Result

from: Codex/Statutory-Free-Float-State-Contract
to: ChatGPT/review
task_id: IDX-STATUTORY-FREE-FLOAT-STATE-CONTRACT-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `ed17ec840cf7cdcffd586f3f12bdd37b0044b004`
branch: `data/idx-statutory-free-float-state-contract-v1`
status: `REVIEW`
head_commit: see the final branch tip reported with this handoff

## Scope

Implemented a query-level PIT knowledge-state resolver for official statutory
free-float observations. The resolver consumes explicit official IDX session
dates and existing immutable LBRE/market observations. It does not acquire
data or materialize a full historical session panel.

## Implementation

`src/idx_trade/statutory_free_float_state.py` provides:

- strict official-session normalization and duplicate rejection;
- Asia/Jakarta publication-date conversion and strict post-publication
  eligibility;
- append-only lineage replay through the accepted historical free-float
  contract;
- maximum eligible economic-position selection;
- separate LBRE/market evidence and provenance fields;
- cross-source share validation, percentage-only disagreement, and genuine
  share-conflict handling;
- positive-denominator eligibility without changing official zero values;
- knowledge-age and economic-position-age diagnostics.

Frozen contract:
`docs/STATUTORY_FREE_FLOAT_KNOWLEDGE_STATE_CONTRACT_V1.md`

## Required behavior verified

- same-day publication is not usable on that session;
- weekend publication waits for the next official session;
- corrections take effect only after their own publication eligibility;
- late old-period corrections cannot regress a newer economic state;
- conflicts discovered after a newer economic snapshot do not poison that
  newer state;
- LBRE and market-first ordering both preserve the later validation event;
- percentage disagreement alone does not block an identical share denominator;
- genuine share-count disagreement surfaces no selected denominator;
- market-only evidence can establish a state;
- no state and invalid/zero denominator are explicit;
- duplicate/ambiguous inputs and timezone-naive timestamps fail closed.

## Validation

- Focused:
  `python -m pytest tests/test_statutory_free_float_state.py tests/test_historical_statutory_free_float.py tests/test_statutory_free_float.py -q`
  — `33 passed`.
- Full: `python -m pytest -q` — `87 collected; 86 passed; 1 failed`.
- Unrelated failure:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict but receives independent `raw_close` and
  `vendor_adj_close` conflicts. No storage change was made.
- `git diff --check`: required before final commit/push and will be reported
  after staging.

## Decision and stop boundary

Result: `STATUTORY_FREE_FLOAT_KNOWLEDGE_STATE_CONTRACT_V1_IMPLEMENTED_READY_FOR_REVIEW`.

Do not start full historical state materialization, daily state, effective
supply, Foreign Flow integration, features, models, O2/counters, or outcomes
until ChatGPT reviews this contract and the underlying source gaps.
