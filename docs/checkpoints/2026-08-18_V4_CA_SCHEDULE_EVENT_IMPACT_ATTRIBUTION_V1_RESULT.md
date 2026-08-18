# V4 CA Schedule-Event Impact Attribution V1 — Result

## Decision

`V4_CA_SCHEDULE_EVENT_IMPACT_ATTRIBUTION_COMPLETE`

This is a deterministic offline acquisition-priority diagnostic, not a
continuity certification. The selected subset is inclusion-minimal under the
frozen optimistic semantics; global minimum cardinality was not proven.

Branch: `data/idx-v4-ca-schedule-event-impact-attribution-v1`
Input branch HEAD before result documentation:
`a38791863cee7e17365942e6dc202e26692a593f`
Scientific/code-test anchor:
`b28eaab4aca4a2ffb9741b89115ba1fc3b21ebec`

## Validation and inputs

- Focused pytest: `13 passed`.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Continuity ledger SHA-256:
  `9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`.
- Schedule-needs SHA-256:
  `1988f2bb679b09835e045235fa7aa46f4d8c62cf9531e76a5b5b889d848a127a`.
- Provider/network calls: `0`.
- Frozen population: `344,790` rows, `610` tickers, `600` dates,
  horizons `{5, 10}`.
- Schedule events: `39`; critical events: `34`.
- Known mechanical-crossing rows never waived: `240`.

## Gate attribution

| Scenario | H5 pass/min | H10 pass/min | Consensus pass/min | Resolved schedule rows | All 600 pass |
|---|---:|---:|---:|---:|---|
| Baseline | 462 / 0.8814102564 | 461 / 0.8789808917 | 461 / 0.8789808917 | 0 | NO |
| Schedule-only ceiling | 600 / 0.9615384615 | 600 / 0.9585987261 | 600 / 0.9585987261 | 24,212 | YES |
| Selected 7-event subset | 600 / 0.9038461538 | 600 / 0.9012738854 | 600 / 0.9012738854 | 8,372 | YES |

The selected subset passes only as an optimistic counterfactual. It does not
certify that the underlying schedule evidence exists or is exact.

## Impact and selection

- Greedy selection count: `7`.
- Selected basis: `DETERMINISTIC_INCLUSION_MINIMAL_NOT_GLOBAL_CARDINALITY_PROVEN`.
- Exact-search status: `NOT_RUN_CRITICAL_UNIVERSE_ABOVE_EXACT_BOUND`.
- Exact-search evaluations: `0`.
- Global minimum cardinality: not proven.
- Reverse-pruned events: none.
- Zero-blocking-row events: none.
- 6,844 KSEI-coverage rows, 1,200 cross-source rows, and 240 mechanical rows
  were untouched/not waived.

Selected ordered event IDs and tickers:

1. `10e24d3621e0f5e65833655b2e11938fc53d64e68c03e6c87658eb74bb2ae26b` — NISP
2. `1285d019c8831fae39ad2909e699680df9071d5ebc38701a71a5a5dba951c60d` — ISAT
3. `41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58` — ADRO
4. `82e09144ecfe0d4375a9260156fe75dd74ed01a2cd72262f55e14cd85ce6ebc7` — PANI
5. `072cf4b8b2f7f86f3c7a55a1128c85f338cbe7b41307b57a3240ad94dba0afae` — RAJA
6. `9b21df59be9d68e088059e2dae04d2d0bd8832d9d1cb5e9dd5a300f05f369610` — PTRO
7. `6df97832e47c00fc5653e90659f525a5c8258752f9fc2245803498bdeb30b45e` — CUAN

### Top 10 events by emitted impact order

| # | Ticker | Family | Blocking rows | Affected baseline-failing dates | Single-event deficit reduction |
|---:|---|---|---:|---:|---:|
| 1 | NISP | VOLUNTARY_CONVERSION | 1,200 | 139 | 416 |
| 2 | ISAT | MANDATORY_CONVERSION | 1,200 | 139 | 416 |
| 3 | ADRO | RIGHT_DISTRIBUTION | 1,200 | 139 | 416 |
| 4 | PANI | RIGHT_DISTRIBUTION | 1,200 | 139 | 416 |
| 5 | RAJA | MANDATORY_CONVERSION | 1,198 | 139 | 416 |
| 6 | PTRO | MANDATORY_CONVERSION | 1,198 | 139 | 416 |
| 7 | CUAN | MANDATORY_CONVERSION | 1,176 | 139 | 416 |
| 8 | CYBR | MANDATORY_CONVERSION | 1,062 | 139 | 416 |
| 9 | MSIN | MANDATORY_CONVERSION | 868 | 139 | 416 |
| 10 | PACK | RIGHT_DISTRIBUTION | 622 | 139 | 416 |

## Artifacts

Promoted small artifacts under
`docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/`:

- `summary.json`: SHA-256
  `b38be0874c61d6ef071a3ccb5cd873fea440a360e9d25d4ddf1afe6951f668d3`
- `MANIFEST.json`: SHA-256
  `9f8a08058b452c8e7c86f651a343dd015a56668adcfa2c2ce5ae20d76ffe6b4f`
- `schedule_event_impact.csv`: SHA-256
  `c8abddfb4004b5fc2a3daf2d13f90129d1287a3c4e987a952603aaaa2c3a72b1`
- `selected_schedule_event_subset.csv`: SHA-256
  `f6650daf7256196f976b0a9d161dbf0cf896d0d349306be4fe4c76b1d2168529`
- `selected_subset_per_date.csv`: SHA-256
  `483408e1ebc8c4418b28c71924e4f34e22e23b3025ca0db893cbcee18eb24c4e`
- `greedy_selection_trace.csv`: SHA-256
  `a9cbed0220605b9e6639ac4df5bf4dfae5743c04c27f0ed8f6e53d02552242d8`

## Boundary confirmation

No provider/schedule acquisition, KSEI retry, parser or semantic change,
cross-source repair, target/rank materialization, model fit, prediction,
performance/bootstrap, or protected/fresh-forward outcome access occurred.
