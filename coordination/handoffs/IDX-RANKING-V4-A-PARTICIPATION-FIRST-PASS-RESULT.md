# Handoff

from: Codex
to: ChatGPT
task_id: IDX-RANKING-V4-A-PARTICIPATION-FIRST-PASS
model_used: Codex Luna xhigh orchestra profile
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: `61dbfb19001598ee955430db9ee3a5b21e8290c5`
branch: `research/idx-ranking-v2-spec-v1`
head_commit: final branch HEAD after documentation commit

## Scope

Executed exactly one invocation of the frozen V4-A first-pass runner:
V3-B control ordinal `012`, A1 Impact/Absorption ordinal `013`, and A2
Persistent Directional Participation ordinal `014`, over V2F1..V2F6. No
redesign, rescue, alternate variant, or integration was executed.

## Result

- full pytest: `337 passed, 0 failed, 3 warnings, 28.97s`;
- control equivalence: `PASS`, `144,223` rows, max score diff `0.0`;
- max metric diffs were all at or below `8.326672684688674e-17`;
- A1 absolute sanity: `PASS`; paired gate: `FAIL`; final: `FAIL`;
- A2 absolute sanity: `PASS`; paired gate: `FAIL`; final: `FAIL`;
- survivors: `[]`;
- `integration_authorized_by_result=false`;
- `integration_executed=false`;
- cumulative historical evaluated-candidate count: `12`.

Gate blockers:

| Challenger | PR nonnegative | Median PR | Q25 PR | Worst PR | Median ROC | Median Q5-Q1 | Q5-Q1 nonnegative |
|---|---:|---:|---:|---:|---:|---:|---:|
| A1-013 | 3/6 | +0.000080 | -0.001431 | -0.011678 | -0.001787 | -0.002847 | 1/6 |
| A2-014 | 4/6 | +0.001017 | -0.003829 | -0.007239 | -0.003027 | -0.006740 | 1/6 |

A1 F5/F6 paired PR changes were `-0.001450` and `-0.011678`; A2 F5/F6
paired PR changes were `+0.001414` and `+0.000620`. Complete per-fold metrics,
paired deltas, gate details, top-decile diagnostics, and model hashes are in
the result checkpoint.

## Input and output identities

Input cache SHA: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`
Input manifest SHA: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`
Spec Git blob: `e32fa69596291f418ae797613da219bd0d3cf69c`

Main output hashes:

- summary: `eea9f1b9b8c0ed8a4d29e133e14621c2dbf9bf028e73e75b0096382bf4fe30da`;
- equivalence: `ed15bef7b6bed9922bd0fafc68a6136dfa667b77e825759c5f9622fc76b821bd`;
- metrics: `2cdb44edf23f97a50c73ad12aa4e19277705caeee27b4e8507fa09fe2ac79a78`;
- predictions: `6c08c324deb38df5b1d4712a1e9e9a140698b281df18330e432a35bef5f7d8c7`;
- paired: `6fedb0ccebea548c9e93ba6c14ee5276c9909294eccae503ecc8f283d89a1796`;
- overlap: `1b13cde9ade3753b550468b54c63617cfa271a2f08183cea07656f5548796e80`;
- verdict: `5e03cb3e154096e1f4d7266e091bb273931765e1eb67491606e051919731a09e`;
- runtime: `1311a9ad5906f44c7d121bbee1db72fc9a161827a709a4b528d9b3b1ae883395`.

Run directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v4_a_participation_first_pass_run_20260810_001/`

## Boundary confirmation

- session `1225+` was not materialized or scored;
- post-2026-07-31 fresh-forward outcomes were untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- no integration, V4-B, calibration, Stage 6, `IDX-VAL-002`, execution/PnL,
  Kelly, paper/live, or main merge was started.

Checkpoint:
`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`

Recommended next action: ChatGPT reviews the failed frozen-gate result. Do not
rescue A1/A2 or start integration automatically.
