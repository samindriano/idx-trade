# O2.1 Sealed Shadow Implemented

Date: 2026-08-12
Branch: `integration/o2-1-sealed-shadow-v1`
Authorization: `research/idx-ranking-ohlcv-o2-1-flat-range-v1` at `051c6da`
Historical verdict: `O2_1_NO_SURVIVOR` (unchanged)

## Scope

Implemented exactly one outcome-blind O2.1 shadow model from the accepted
expanded support. The model uses the canonical V3-B 33-feature base plus
`open_position_o21`, `open_to_high`, `open_to_low`, and `flat_range`, with the
accepted HGB preprocessing, parameters, and seed. Genuine flat rows use the
sealed encoding `(0.5, 0, 0, 1)` and are included; raw OHLCV is not modified.

The forward lane is subordinate to the existing O2/V3-B/V2 runtime. It reads
existing certified session artifacts, writes shadow artifacts beside the
existing forward archive, and does not register O2.1 in `FROZEN_MODELS`, the
official model counter, promotion eligibility, leaderboard, or outcome path.
No provider call, recapture, data repair, historical rerun, tuning, or
outcome access was performed.

## Frozen fingerprints

- model SHA-256: `318d8b988f3689109a1f808781c4aa8e8b478f7ee9324e8405c4641586da1ea7`
- feature-order SHA-256: `f0259e82240f3db76bab8929669082a422e124c8cb37a08cd94c6cff9220b3b3`
- canonical V3-B prefix SHA-256: `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`
- training-support SHA-256: `8c6429253d84d1e355c536c0c4b715f00d20ae0344c304aa2d7a218b323c596d`
- support rows: `280044`
- support true-flat rows: `1876` (`0.6698947%`)
- feature manifest SHA-256: `58517a0d623c33d7c3d851f6ceea657ac32a04ac5e93f1c8cc7c091e5184c4db`
- training-support manifest SHA-256: `82beb1d147c3a3496f56cb4d7d548a1dd8a767bf101de862daabd51de561d483`

Runtime model bundle (outside Git):
`D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_1_sealed_shadow_v1_20260812`

## Certified 2026-08-12 alignment

The existing stored session artifact was scored after the model was frozen;
no capture or provider refresh was used.

- shadow sessions aligned: `1 / 100`
- O2 coverage: `806 / 836`
- O2.1 shadow coverage: `836 / 836`
- flat-range rows included: `30`
- flat share: `3.5885%`
- score artifact SHA-256: `20925d72546f35ccce3a355fdc02d31789c90d20437cffd1db6068481ddd2c34`
- score artifact: `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\shadow_runs\o2_1_flat_range\2026-08-12\score_artifact.parquet`
- O2.1 artifact is labeled exploratory shadow and has no independent official counter.

The operator status endpoint now derives the shadow archive from the existing
`forward_monitoring` store, so these stored counts are visible in O2 detail
without changing the primary three-card monitoring layout.

## Validation

- focused Python tests: `14 passed`
- full pytest: `268 passed, 3 warnings`
- Next.js production build: passed
- route smoke on the feature dev server: `/`, `/monitoring`, `/monitoring/models/o2`, `/compare` all returned `200`
- build emitted one non-blocking Turbopack filesystem-tracing warning from the existing runtime adapter import path.

## Review boundary

No PR-AUC, return, hit-rate, winner/loser, fresh-forward outcome, or
promotion conclusion is produced by this lane. Stop for independent ChatGPT
review before any further shadow expansion or interpretation.
