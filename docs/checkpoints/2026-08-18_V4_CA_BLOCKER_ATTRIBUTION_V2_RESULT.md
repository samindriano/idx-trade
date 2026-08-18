# V4 CA Blocker Attribution V2 — Result

## Decision

`OPTIMISTIC_ATTRIBUTION_V2_MULTIPLE_MINIMAL_CLEARING_SCENARIOS`

This is an offline diagnostic, not a continuity certification. The exact
baseline remains below the frozen 90% gate. The passing non-baseline scenarios
are optimistic upper bounds that assume selected blocker rows resolve; they
must not be treated as evidence that those rows are actually resolved.

Branch: `data/idx-v4-ca-blocker-attribution-v2`
Input branch HEAD before result documentation:
`620d4efe1165a1e40e4302b5719684664a8cf415`
Scientific/code-test anchor:
`7a70f0643296019bc7bf3150137b65b000a0b344`
Input continuity-ledger SHA-256:
`9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`

## Validation

- Focused pytest: `13 passed`.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Fresh output root was absent before the run.
- Provider/network calls: `0`.
- The exact post-KSEI ledger was used; no source, CA semantic, threshold,
  universe, target, model, or outcome change was made.

## Eight scenarios

All rates below are minimum rates over the six hundred frozen dates. Every
non-baseline scenario is an optimistic upper bound only.

| Scenario | H5 pass/min | H10 pass/min | Consensus pass/min | Worst H5 | Worst H10/consensus | Newly resolved rows assumed | All 600 pass |
|---|---:|---:|---:|---|---|---:|---|
| BASELINE | 462 / 0.8814102564 | 461 / 0.8789808917 | 461 / 0.8789808917 | 2026-07-02 | 2026-06-30 | 0 | NO |
| SCHEDULE_ONLY_CEILING | 600 / 0.9615384615 | 600 / 0.9585987261 | 600 / 0.9585987261 | 2026-07-02 | 2026-06-30 | 24,212 | YES |
| KSEI_COVERAGE_ONLY_CEILING | 600 / 0.9022222222 | 597 / 0.8991228070 | 597 / 0.8991228070 | 2025-04-28 | 2025-05-21 | 6,844 | NO |
| CROSS_SOURCE_ONLY_CEILING | 515 / 0.8846153846 | 504 / 0.8821656051 | 504 / 0.8821656051 | 2026-07-02 | 2026-06-30 | 1,200 | NO |
| ALL_COVERAGE_CEILING | 600 / 0.9066666667 | 600 / 0.9035087719 | 600 / 0.9035087719 | 2025-04-28 | 2025-05-21 | 8,044 | YES |
| SCHEDULE_PLUS_KSEI_COVERAGE_CEILING | 600 / 0.9834024896 | 600 / 0.9792531120 | 600 / 0.9792531120 | 2025-07-02 | 2025-06-24 | 31,056 | YES |
| SCHEDULE_PLUS_CROSS_SOURCE_CEILING | 600 / 0.9647435897 | 600 / 0.9617834395 | 600 / 0.9617834395 | 2026-07-02 | 2026-06-30 | 25,412 | YES |
| SCHEDULE_PLUS_ALL_COVERAGE_CEILING | 600 / 0.9871794872 | 600 / 0.9834024896 | 600 / 0.9834024896 | 2026-07-02 | 2025-06-24 | 32,256 | YES |

Minimal clearing scenarios reported by the frozen runner:
`ALL_COVERAGE_CEILING` and `SCHEDULE_ONLY_CEILING`.

Known mechanical-crossing rows preserved and never waived: `240`.

## Current blocker attribution counts

- `NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL`: `312,294`
- `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED`: `24,212`
- `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED`: `6,844`
- `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`: `240`
- `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY`: `1,200`

## Artifacts

Promoted small artifacts under
`docs/artifacts/v4_ca_blocker_attribution_20260818_v2/`:

- `summary.json`: SHA-256
  `cdbb60c4e69348c1d8084e66e6cd463e390801ad04a6bf379247b4d278ea97d0`
- `MANIFEST.json`: SHA-256
  `d690276b4e94bdd029b9c450a7cbbd85fad64d64baca1f65560184a9f314a02a`
- `blocker_attribution_v2_per_date.csv`: SHA-256
  `9ec4fdeff545f03820fd4e5764f896014199b8b1679a13913a644bdbc4a85d1c`

The 344,790-row input ledger remains external and was not copied into Git.

## Boundary confirmation

No provider/network calls, KSEI retry, schedule acquisition, cross-source
repair, CA semantic change, target/rank materialization, model fit, prediction,
performance, bootstrap, or protected/fresh-forward outcome access occurred.
