# Financial PIT Feature Contract V1 — Design Review Checkpoint

**Date:** 2026-08-14 (Asia/Jakarta)

**Branch:** `data/financial-pit-feature-contract-v1`

**Status:** `REVIEW`

**Decision:** `FINANCIAL_PIT_FEATURE_CONTRACT_DESIGN_REVIEW_PERIOD_METADATA_BLOCKED`

## Scope completed

The branch defines a conservative PIT-safe feature contract over the accepted
offline Financial PIT fact corpus. It covers instant versus duration facts,
cumulative Q1/H1/9M/FY semantics, same-period YoY matching, revision-aware
as-of selection, missing/denominator behavior, applicability by issuer class,
and provenance to exact filing versions and attachment hashes.

Candidate families are limited to size, leverage/capital structure,
liquidity, profitability, cash-flow quality, margins, and YoY growth. No
feature values were materialized, no performance metric was computed, and no
model or protected outcome was accessed.

The accepted numeric parser behavior for `1,2E3` is covered by a regression
test and remains `12000` after comma stripping; no locale interpretation was
introduced.

## Offline inputs and run

The run reused the accepted immutable remediation corpus only:

- `5,965` filing diagnostics;
- `37,246` fact rows;
- no provider/network calls;
- protected outcomes untouched.

Output root:
`D:\Documents\Project\idx-financial-pit-feature-contract-20260814-v2`

The dry-run found `20,471` instant and `16,775` duration-shaped rows, but
`0` rows have explicit valid `instant_date` or `period_start/period_end`.
Therefore `0` candidate rows are marked available and the materialization gate
is `BLOCKED_UNRESOLVED_PERIOD_METADATA`. This is a metadata-readiness result,
not a claim that the underlying financial values are all unavailable.

Artifacts:

- `availability.json` SHA-256:
  `3e035b3576dfc36eff51a150271cd49a0721f9ade5b064e7ab172df465a9d97c`
- `MANIFEST.json` SHA-256:
  `2d998548c1da15862c78f4bdf36b46707a14b21d65532507dbf641ae55d62d70`

The source pins and complete per-feature status table are in
`docs/FINANCIAL_PIT_FEATURE_CONTRACT_V1.md` and the external manifest.

Validation completed:

- focused Financial PIT/feature tests: `42 passed`;
- full repository pytest: `540 passed, 0 failed, 3 existing FutureWarnings`
  in `23.60s`;
- `git diff --check`: PASS.

## Remaining blockers

1. The accepted fact records must preserve explicit period boundaries (or a
   separately proven equivalent context-to-boundary mapping) before any
   feature materialization can be considered.
2. Financial/sharia and separate-scope applicability require a dedicated
   semantic approval; they must not be mixed with general consolidated facts.
3. TTM/standalone-quarter transformations are not part of this contract and
   require a separately frozen, boundary-complete formula and availability
   gate.

## Next action

Independent ChatGPT review of this contract and the period-metadata blocker.
No parser/network repair, fact materialization, feature selection, model work,
O2 changes, or outcome access is authorized by this checkpoint.
