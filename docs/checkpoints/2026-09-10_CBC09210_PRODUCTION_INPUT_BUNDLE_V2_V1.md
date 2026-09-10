# CBC09210 Production Input Bundle V2

Date: 2026-09-10 Asia/Jakarta
Status: `DONE`
Technical verdict: `CBC09210_PRODUCTION_INPUT_V2_BOUND_PR123_REVIEW_READY`

## Immutable bundle identity

The accepted runtime remains
`codex/e2e-dual-calendar-runtime-v1@cbc09210d6a097f2d96c86ada1e58a7c5e591015`.
The prior production input manifest was read only at
`e2e-paper-v1/inputs/manifest.json` and verified as
`858327909343a887c54fbc5e3bea4dafe6f7a8b89f2422a313b954dee04c08ee`.
Its 10 declared artifacts were read back from R2 and each matched its
manifest SHA-256.

The new bundle is published in the separate namespace
`e2e-paper-v2/cbc09210`. Its manifest is
`e2e-paper-v2/cbc09210/inputs/manifest.json` with SHA-256
`f23f45d8b48d386b6755cd272c5c013c04b2c9ee5df0d35473585f878afb2762` and
payload SHA-256
`3ccf679021414884bb9ab9a70aef1cfbcb44bb96ba93cff34c5ce089982fc101`.
The manifest contains 16 required role-bound objects: the 10 byte-preserved v1
inputs plus the historical-official and forward-observed calendar triplets.

The 17 new R2 objects were checked for exact-key absence, created with
`If-None-Match: *`, written in child-first order with the manifest last, and
read back immediately. Every readback byte length and SHA-256 matched the
local bundle. No old v1 object was overwritten.

## Calendar and provenance bindings

Historical source package:
`D:\Documents\Project\idx-trade-data-gate-20260910-historical-calendar-recertification-v2`

- provenance manifest: `4178e1c3ff412d278ac1ad997c49868257a84d6b687364912d656e7cfa313666`;
- package integrity manifest: `ae6b1494df307c7b2c13eaded4d880d46022e8d989f135143e1463683f2f36cf`;
- effective historical calendar file: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- normalized calendar sessions SHA: `5dae391a1b4068a71b0f0dd40edda207356a917f74dc860c50e4080fa7bd268f`;
- coverage: 1,260 sessions, `2021-04-29` through `2026-07-31`, including the
  separately recertified `2021-04-29` and `2021-04-30` dates.

Forward observed package:
`D:\Documents\Project\idx-trade-data-gate-20260909-official-calendar-retrieval-v1`

- calendar file: `7eadc499b356b24e770298ec49dd77855ccd69fc19d3adec48eb2be6265dc827`;
- normalized calendar sessions SHA: `0df5639fce01fdbb22bd1c5c25f996e0572d29da2fceef066fe1d6015e276fa2`;
- coverage: 26 sessions, `2026-08-03` through `2026-09-09`.

The Python `CloudInputBundle.load` and `materialize` contract accepted all 16
roles. The historical and forward roles remain separate and their contiguous
weekday-aware union is 1,286 sessions.

## Offline verification and boundaries

The exact cbc09210 offline replay passed:

- bundle load/materialization: 16/16 roles;
- calendar -> POST_EOD boundary: `WAITING_UPSTREAM_EOD_SCORE`, with no
  POST_EOD commit written;
- calendar probe: 1,286 sessions, first `2021-04-29`, last `2026-09-09`,
  August session gap covered, two source rows;
- canonical Intraday reader: `DATA_READY` for the offline 2026-08-03 fixture;
- provider calls: `0`; protected outcomes: not accessed.

PR #123 consumers are bound to the v2 namespace and manifest SHA in the E2E
orchestration, synthetic rehearsal, Stockbit bridge/preflight/production
workflows, runner dry-run diagnostics, smoke reservations, and Cloudflare E2E
archive prefix/manifest contract. No merge, deployment, scheduler activation,
capture, provider access, model fit/score, outcome access, or recovery action
was performed.
