# Handoff
from: Codex worker
to: MAIN / integrator
task_id: IDX-CA-JOURNAL-CROSS-BATCH-LIFECYCLE-V1
model_used: Codex
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `28f9ffc21dd1268cbf3641291a23891e123705eb`
branch: `worker/idx-ca-journal-cross-batch-lifecycle-v1`
head_commit: `28f9ffc21dd1268cbf3641291a23891e123705eb`

## scope

Phase 1 Corporate Action cross-batch journal lifecycle gap: generalized
append-only blocker-resolution history for A1 -> A2 correction resolution.
The separate E2E restart acceptance orchestrator, providers, scheduler,
outcomes, alpha, Decision, sizing, and execution policy were not changed.

## files_changed

- `src/idx_trade/forward_dividend_orchestration_v1.py`
- `scripts/run_forward_dividend_acquisition_batch_v1.py`
- `tests/test_forward_dividend_orchestration_v1.py`
- `coordination/handoffs/IDX-CA-JOURNAL-CROSS-BATCH-LIFECYCLE-V1-CODEX.md`

## findings

The prior journal only allowed a blocker to disappear when the exact same
announcement identity became certified. A correction with a new identity
(A1 -> A2) could not be resolved across batches without dropping blocker
lineage. A historical resolver also had no journal representation that could
clear the blocker without being treated as a new live cash event.

## decisions_made

- Added optional `blocker_resolution_history` to the immutable journal.
- Each resolution binds the parent blocker identity/ticker/classification to a
  resolver announcement identity, ticker, event ID, event SHA, evidence path,
  review SHA, and explicit `CERTIFIED_LIVE` or `HISTORICAL_OBSERVED` status.
- Child journals retain prior resolution rows exactly and may append only
  parent-blocker-backed resolutions. Missing/wrong resolver, source blocker,
  ticker, event SHA, evidence, status, or conflicting rows fail closed.
- Live resolvers must be present as identical active certified events.
  Historical resolvers clear the blocker but cannot enter active certified
  events, preserving no-new-cash semantics.
- Empty resolution history is omitted from serialized payloads for compatible
  empty-journal hashes; readers accept the optional field.
- The CA acquisition batch runner maps `SUPERSEDED` dispositions to history
  only when the superseded identity was an active blocker in the prior
  journal. No provider or E2E acceptance call was run.

## blocking_risks

- No live/provider batch was run; this was intentionally limited to offline
  code and focused tests.
- Five validation-only pytest basetemp directories remain untracked under the
  worker worktree because the environment rejected explicit recursive cleanup
  commands. They contain no source changes and should be removed or ignored by
  the integrator before staging.

## validation_run

- `python -m py_compile src/idx_trade/forward_dividend_orchestration_v1.py scripts/run_forward_dividend_acquisition_batch_v1.py`: PASS
- `python -m pytest ... tests/test_forward_dividend_orchestration_v1.py`: `36 passed`
- `python -m pytest ... tests/test_forward_dividend_acquisition_batch_v1.py`: `8 passed`
- Focused CA suite (`test_idx_corporate_actions_provider.py`,
  `test_forward_ca_attestation_v1.py`, and all `test_forward_dividend_*.py`):
  `147 passed`
- `git diff --check`: PASS

## recommended_next_action

Review the three implementation/test diffs, remove the validation-only temp
directories, and integrate on the requested E2E lane. Do not commit or push
this worker branch.
