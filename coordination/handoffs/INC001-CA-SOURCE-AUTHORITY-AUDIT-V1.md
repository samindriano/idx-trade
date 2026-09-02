# Handoff: INC-001 CA Source Authority Audit V1

from: MAIN / Codex
to: ChatGPT independent review
task_id: `IDX-CA-SOURCE-AUTHORITY-AUDIT-V1`
source_repository: `samindriano/idx-trade`
source_branch: `data/ca-aware-feature-basis-remediation-v1`
reviewed_implementation_head: `a4e644b655fb7b7980b59c008b7d3dd26f364371`

## Decision

`STOP`: retained/local evidence does not close the real 716-ticker source
authority gap. Phase-E is not run and no provider/network acquisition is
authorized by this handoff.

## Evidence

- final fit union: `240,344` rows / `629` tickers;
- cross-sectional application: `276,153` rows / `716` tickers;
- observed dependency closure: `365,968` rows / `716` tickers;
- KSEI: `610` captured, `567` certified, `43` unresolved, `106` application/
  closure absent;
- retained IDX issued-history evidence is positive/candidate-only and covers
  `533` application tickers, not a no-event census;
- frozen structural family authority is partial/unknown, with no full negative
  coverage authority;
- no full per-session/date-level historical as-of attestation exists;
- all strict 26 transition rows remain `UNRESOLVED`;
- merger mapping remains `UNKNOWN`, and `ISAT`, `MEGA`, `SCMA` remain conflict
  identities.

## Guardrails

```text
PROVIDER_CALLS=FALSE
OUTCOMES_ACCESSED=FALSE
TARGET_VALUES_ACCESSED=FALSE
MODEL_FIT=FALSE
MODEL_SCORING=FALSE
PHASE_E_RUN=FALSE
COUNTER_MUTATED=FALSE
CANONICAL_DATA_REWRITTEN=FALSE
```

## Immutable artifact

Root: `D:\Documents\Project\idx-ca-source-authority-audit-20260829-v6-final`
Manifest SHA-256: `b8fb556061eb53ca6ac00a71b6551d4e28282a779a07262a6481d76dc928c9eb`
Summary SHA-256: `9435d08118a62c3ccc51033efdd14b6ffdbb3b1520d608487d2f77a37235a820`

Fresh-root deterministic rerun:
`D:\Documents\Project\idx-ca-source-authority-audit-20260829-deterministic-rerun-v3`.
All 9 file SHA-256 values match the final root exactly.

The complete source inventory, family authority matrix, population
reconciliation, temporal matrix, transition reconciliation, gap matrix, and
acquisition requirements are in that root. The scientific verdict remains:

```text
DATA_ADMISSION=FAIL
RESEARCH_ADMISSION=FAIL
MODEL_PROMOTION=NOT_EVALUATED
HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED=FALSE
COUNTER_ACTION=NONE
```

## Validation

The source-audit tests passed (`4`), the focused CA/integrity selection passed
(`99`), and the final local full pytest completed successfully. `py_compile`
and `git diff --check` passed. The fresh-root deterministic rerun matched all
`9/9` artifact file hashes.

The exact-head GitHub Actions pytest result was `353 passed, 5 warnings`.
The warnings did not fail the job; GitHub additionally reported the expected
Node.js 20 deprecation annotation for the pinned checkout/setup actions.

No merge of PR #108/#103 is requested.
