# O2 Forward Flat-Range Runtime Result

Date: 2026-08-12 (Asia/Jakarta)

Branch: `integration/forward-eod-automation-monitoring`

## Scope

This was a bounded runtime alignment against the frozen O2 Open-geometry
contract. No recapture, provider call, V2/V3-B artifact rewrite, outcome read,
or `FORWARD_OUTCOME_ACCESS_STARTED` access occurred.

True flat-range bars (`open == high == low > 0`) remain in the immutable
session OHLCV and score artifacts, but are row-level O2-ineligible. No
synthetic `open_position` was created. O2 and paired V3-B scores were produced
only for the exact O2-eligible subset.

## 2026-08-12 result

- Certified EOD source: existing `session_ohlcv.parquet`, SHA-256
  `0714942c7cc72a7ff93537a31847e451628dffa59112cce87a031bd9d14449e5`.
- Total input/model rows: `836`.
- O2-eligible rows: `806`.
- Flat-range exclusions: `30` (`FLAT_RANGE_ZERO_DENOMINATOR`).
- Other exclusions: `0`.
- O2 scored rows: `806`.
- Paired frozen V3-B scored rows: `806`.
- Flat rows retained and unscored: `30`.
- Official session index: `1268`, derived from the certified official
  exchange-session calendar; it was not hard-coded as `1`.
- Counter: `0 -> 1`, required horizon `100`,
  `first_post_freeze_session_index=1268`, `outcomes_accessed=false`.
- SQLite model state: `DONE`.

## Artifacts

- O2 score artifact:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-08-12\o2-geometry-full3-v1-candidate-001\score_artifact.parquet`
  SHA-256 `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d`.
- O2 manifest:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-08-12\o2-geometry-full3-v1-candidate-001\manifest.json`
  SHA-256 `4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2`.
- Existing model input was not rewritten:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-08-12\model_input.parquet`
  SHA-256 `51cfe9abacd322f330025b0bcd43d569f6fbb715b53aea3c27ead7588d16b00b`.
- O2 counter:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\o2_forward_counter.json`
  SHA-256 `a5042850223e465cee347a8851698df552c3646334a8dfa41af27cd53a850071`.

The O2 manifest records the frozen model SHA
`42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`, feature
order SHA `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`,
and paired V3-B model SHA
`1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`.

## Validation

- Focused forward/OHLCV/model-runtime tests: `20 passed`.
- Full pytest: `319 passed, 0 failed, 3 warnings, 14.88s`.
- Next.js production build: passed; one existing non-blocking Turbopack file
  tracing warning.
- Runtime status: all three sessions are `DATA_READY`; V2, V3-B, and O2 for
  2026-08-12 are `DONE`.
- Outcome state remains `LOCKED`; the O2 and counter manifests are explicitly
  outcome-clean.
