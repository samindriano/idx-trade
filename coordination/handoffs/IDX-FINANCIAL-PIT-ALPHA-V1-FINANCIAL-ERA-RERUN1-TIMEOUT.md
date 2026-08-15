# Handoff: Financial PIT Alpha V1 exact rerun timeout

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-ALPHA-V1-FINANCIAL-ERA-RERUN1-TIMEOUT
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 507aaf8bca3286996eb30f3f8e7ea161d8892cc1
branch: research/idx-financial-pit-alpha-v1
head_commit: 507aaf8bca3286996eb30f3f8e7ea161d8892cc1

## Scope

Run the one explicitly reauthorized exact-contract Financial-era rerun from
the corrected runner, preserving the failed directory and using a new output
root.

## Preflight

Passed: exact HEAD, contract SHA, common-support SHA, selected-matrix SHA,
historical label SHA, 70,520/321 support, and eligibility exactly V2F4/V2F5/V2F6.

## Result

The corrected command was terminated by the execution wrapper with exit 124
after approximately 124 seconds. Six model files were written for F4 and F5
(three candidates per fold); F6 and all result artifacts were absent. No
metrics, paired deltas, gate, or verdict can be interpreted.

Rerun output:
`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-rerun1`

No third automatic run is permitted. Fresh-forward/O2/protected outcomes and
the prior failed output directory remain untouched.

## Validation

Focused tests: `10 passed`. Full pytest: `61 passed, 1 failed` on the existing
unrelated storage expectation. `git diff --check`: passed.

## Decision needed

Scientific outcome remains `UNDETERMINED_EXECUTION_TIMEOUT`. Further execution
requires explicit authorization and sufficient runtime allowance.
