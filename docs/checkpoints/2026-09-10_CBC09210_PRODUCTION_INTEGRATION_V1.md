# CBC09210 Production Candidate Integration V1

Date: 2026-09-10 Asia/Jakarta
Status: `REVIEW_READY`
Technical verdict: `CBC09210_PRODUCTION_CANDIDATE_REVIEW_READY`

## Candidate boundary

This candidate starts from clean `origin/main` at
`1cf1d6429044aa25ff0b9cb0f560565abaa80da3` in branch
`codex/cbc09210-production-candidate-v1`.

The exact E2E runtime is independently addressable at
`codex/e2e-dual-calendar-runtime-v1@cbc09210d6a097f2d96c86ada1e58a7c5e591015`
with parent `8bc3ee3efd65e8b16478e404e4b226451b105c48`. Active Stockbit bridge,
E2E workflow, preflight, rehearsal, test, status, and runtime-contract
references are bound to `cbc09210`.

No merge, deployment, recovery activation, capture dispatch, provider access,
model access, outcome access, scheduler mutation, or production R2 mutation was
performed.

## Calendar package binding

The sealed external recertification package is:

`D:\Documents\Project\idx-trade-data-gate-20260910-historical-calendar-recertification-v2`

- provenance manifest SHA-256:
  `4178e1c3ff412d278ac1ad997c49868257a84d6b687364912d656e7cfa313666`
- package integrity manifest SHA-256:
  `ae6b1494df307c7b2c13eaded4d880d46022e8d989f135143e1463683f2f36cf`
- effective historical calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- effective source coverage: `1260/1260` sessions, including the exact
  recertification of `2021-04-29` and `2021-04-30`.

The cbc09210 input manifest contract keeps the historical official calendar and
the forward-observed session calendar as separate roles. Each role is bound to
its own calendar CSV, summary JSON, source report, coverage interval, session
count, source identity set, source references, and normalized calendar SHA-256;
calendar materialization is create-only and rejects role confusion or local
byte collisions. The package's effective calendar is bound to the historical
role; the forward-observed role remains a separately sourced prospective
calendar and is not inferred from the historical package.

## Cloudflare contract audit

The candidate's Cloudflare Wrangler configurations, profile contract, config
contract tests, deployment-readiness tests, and staging readback fixture
explicitly embed `E2E_EXPECTED_CODE_COMMIT`. They are updated to cbc09210 in
this candidate only. No Wrangler command, Worker deployment, secret operation,
or live readback was executed.

## Validation boundary

Acceptance requires the exact offline calendar -> POST_EOD -> canonical
Intraday-reader replay, focused and full repository tests, compileall, diff
check, and stale-pin classification. Static or offline evidence does not
substitute for genuine scheduled production trigger or provider/capture proof;
that proof remains pending and outside this candidate integration.

Validation completed: cbc offline replay passed; focused Python contracts passed;
candidate-wide pytest exited 0; Cloudflare contract tests passed `126/126`;
compileall exited 0; all 10 workflow YAML files parsed; and `git diff --check`
was clean. PR #123 hosted `pytest` passed in 2m29s. The hosted E2E preflight was
skipped by workflow policy and no production-facing preflight was dispatched.
