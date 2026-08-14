# Handoff: Financial PIT Alpha V1 financial-era run blocked

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-ALPHA-V1-FINANCIAL-ERA-RUN-BLOCKED
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 564139800df72ff1ca7391008f80b004309ae918
branch: research/idx-financial-pit-alpha-v1
head_commit: pending until documentation push

## Scope

Execute the single frozen Financial-era historical experiment on identical
Financial-support rows for V2F4/V2F5/V2F6:
`CONTROL_FINANCIAL_ERA`, `V2_PLUS_FINANCIAL`, and diagnostic-only
`FINANCIAL_ONLY`.

## Frozen preflight result

- Contract: `FINANCIAL_PIT_ALPHA_V1_FINANCIAL_ERA_CONTRACT_FROZEN`
- Contract SHA-256:
  `cabeb0db3db44996bda91472576855cb549965d19791f640717502cdd321993c`
- Eligible folds exactly: `V2F4`, `V2F5`, `V2F6`
- No fold, feature, target, preprocessing, hyperparameter, support rule, or
  gate changes.

## Run result

The run accessed the pinned historical H10 labels and fit 9 expected models,
then stopped during prediction identity verification with:

`KeyError: ('ticker', 'date', 'signal_session_index')`

The defect was tuple-vs-list DataFrame column selection. The engineering fix
is `DataFrame[list(KEY_COLUMNS)]`; focused tests pass after the fix. No metrics,
paired deltas, gate, or verdict was persisted or inspected.

Partial artifacts remain at:
`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-run`
with 9 model files and no summary/metrics/prediction/manifest files.

## Validation

- Focused tests: `10 passed`.
- Full pytest: `61 passed, 1 failed`, the same unrelated storage fixture
  expecting one conflict instead of the current two independent conflicts.
- Fresh-forward/O2/protected forward outcomes: untouched.

## Decision needed

The atomic run is consumed and scientific result is undetermined. ChatGPT must
authorize a new run before the corrected runner may reopen the pinned historical
labels. Do not change folds, candidates, support thresholds, or gates.
