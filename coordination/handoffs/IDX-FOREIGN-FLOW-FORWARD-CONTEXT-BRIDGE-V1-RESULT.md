# Handoff — Foreign Flow Forward Context Bridge V1 Local Runtime Result

from: Codex local runtime
to: ChatGPT independent review
task_id: IDX-FOREIGN-FLOW-FORWARD-CONTEXT-BRIDGE-V1-RESULT
source_repository: samindriano/idx-trade
branch: data/foreign-flow-forward-context-bridge-v1
head_commit_before_result: 56b5b3c8041b87020f8cbfc25296eff3aeeacc4a
scope: bounded local bridge calendar/capture/planner execution only

## Result

Status: `CONTEXT_BRIDGE_READY_BUT_SMOKE_BLOCKED_FULL_CALENDAR_CONTRACT`.

The planner reached `CONTEXT_BRIDGE_READY` after six authorized captures:
2026-08-03..2026-08-07 and 2026-08-10. 2026-08-11 and 2026-08-12 were verified
from existing canonical EOD artifacts. No post-2026-08-10 bridge capture was
attempted, and no `NEED_CANONICAL_EOD` row appeared in the bounded source
horizon through 2026-08-12.

The one smoke execution for source 2026-08-12 failed before output creation
because the extension-only calendar did not cover the full pinned historical
panel required by the accepted V2 materializer. Existing bridge manifests are
immutably pinned to that extension calendar and were not rewritten. The
combined full-calendar diagnostic was preserved separately but not substituted
after the failure.

## External artifacts

Runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v`

Bridge calendar:
`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge\calendar\ranges\2026-07-31_2026-08-13\exchange_sessions.csv`

Bridge calendar SHA-256:
`51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`

Combined full-calendar diagnostic SHA-256:
`b3fbbed7f4dcea83fe7cd60c2b9ec98e4227ed309e50ea4cd8af105a0116594e`

Captured session manifest hashes:

```text
2026-08-03 70eb58dc5daf1472ffae665131cfd472cc7aa3c44168ef8d8e26bcad185ab926
2026-08-04 7616bf321268f18321d429e22f5e8d5448de8882f09480ac95c8362c9cee79c4
2026-08-05 ce1a5c1bcfee158c30cac29250320265683cc9c2c9b0adfb5d5251d4ec1979e1
2026-08-06 c5781f840437f58363388b1fef590b2c1bf42a7d58708be1a9194f7b9b903a75
2026-08-07 dba2a9ec87458001d7996da2292db361bc8948f3bb2f4f49e72840911ca126f7
2026-08-10 87ea8e115bcf186118629695c1caafb432d4d158a7978460b713fd3337ae9c13
```

Each capture has 963 official Stock Summary rows and validated Yahoo market
rows of 831, 834, 833, 835, 834, and 837 respectively. All are bridge-only,
immutable, outcome-blind, and separate from canonical 2026-08-10/11/12 bytes.

## Validation

- focused bridge/V2/setup tests: `24 passed, 5 warnings`;
- full pytest: `118 collected, 117 passed, 1 unrelated storage expectation
  failure, 5 warnings`;
- `git diff --check`: PASS.

## Boundaries preserved

No outcomes, labels, O2/counter, model fit/scoring, scheduler, HSC/free-float,
price-state, or unrelated storage changes. No provider call was made after the
single smoke attempt failed. No smoke output pair exists.

Recommended review decision: resolve the full-calendar versus extension-
calendar provenance contract before any further smoke attempt. Do not treat
the planner-ready state as a completed prospective Representation/Setup State
run.
