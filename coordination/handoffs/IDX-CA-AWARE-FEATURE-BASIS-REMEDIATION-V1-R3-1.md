# Handoff

from: MAIN / Codex  
to: ChatGPT review  
task_id: IDX-CA-AWARE-FEATURE-BASIS-REMEDIATION-V1-R3-1  
branch: `data/ca-aware-feature-basis-remediation-v1`

## Scope

Narrow outcome-blind R3.1 red-team correction only. Candidate/source dates no
longer prove `OUTSIDE_DEPENDENCY_AFTER_CLOSURE`; only a certified
source-specific transition lower bound can do so. The population gate now
proves identity containment and full expanded-scope source/date certification,
without requiring `application_tickers == fit_tickers` or
`closure_tickers == fit_tickers`.

No Phase-E, provider, outcome, model fit/refit/scoring, counter mutation, or
canonical historical rewrite was performed.

## Results

- Event scope: `5` rows changed from `OUTSIDE_DEPENDENCY_AFTER_CLOSURE` to
  `UNKNOWN_UNRESOLVED_AFTER_CLOSURE`; total 26-row counts are recorded in the
  R3.1 checkpoint and artifact.
- Population architecture: regression coverage proves `629` fit,
  `716` application, and `716` closure can pass only with complete expanded
  identity/source/date evidence; incomplete evidence fails closed.
- Support lineage: `1,380/1,380` UNION `OLD_ONLY` rows are classified as
  clean security-master admission plus CA80 date-gate flip. Per-row numerator
  attribution is `UNKNOWN`.
- Current data/research admission remains blocked; no Phase-E authorization is
  implied.

## Artifacts

```text
primary root: D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260828-r3_1-final
manifest SHA256: 9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b
summary SHA256: e370b33e39627b1024d1cae9655684e60b2975d456df717e8a13accd5bc69cbb
deterministic rerun: D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260828-r3_1-final-rerun
```

The pre-existing R3 root was not overwritten.

## Validation

- Focused R3.1 regressions: 22 passed.
- Full pytest: **337 passed**, exit 0 (337 tests collected; terminal reached 100%).
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Exact-head baseline GitHub Actions run `33089485270`: **334 passed, 5
  warnings**. Warnings are not reported as zero.

## Review boundary

PR #108 remains unmerged. Review the code diff, tests, R3.1 manifest/summary,
both artifact roots, and the explicit guardrails before any later work. Do not
run Phase-E, access outcomes/providers, refit/score, mutate counters, or rewrite
canonical historical data as part of this handoff.
