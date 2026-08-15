# Foreign Flow Forward Context Bridge V1 — Calendar Contract Remediation

Date: 2026-08-15
Branch: `data/foreign-flow-forward-context-bridge-v1`
Starting HEAD: `1c4fb1a7044b797ecf4ffcb93cc36a9dc6b18700`

## Scope and boundary

This remediation addresses only the calendar contract identified by the
independent review. Previously captured bridge and canonical EOD artifacts were
not recaptured, rewritten, or re-hashed. The accepted Foreign Flow
Representation V2 formulas, Setup State thresholds, capture logic, O2 counter,
models, and outcome vault were not changed or accessed.

## Calendar contract

The runner now verifies two independent pinned inputs:

| Role | Path | SHA-256 | Range |
|---|---|---|---|
| historical market/session calendar | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\research_feasibility_1260_20260809\\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` | 2021-04-29..2026-07-31, 1,260 sessions |
| bridge extension calendar | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\forward_monitoring\\context_bridge\\calendar\\ranges\\2026-07-31_2026-08-13\\exchange_sessions.csv` | `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e` | 2026-07-31..2026-08-13, 10 sessions |

The seam is exactly `2026-07-31`; no other dates overlap. The full materializer
session index is constructed in memory as the validated union, not written as
a new calendar authority:

- combined sessions: `1,269`;
- combined range: `2021-04-29..2026-08-13`;
- combined session-set SHA-256:
  `dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`;
- source-to-target transition: `2026-08-12 -> 2026-08-13`.

Bridge manifest verification continues to use the original 10-session bridge
calendar and SHA. Bridge capture context is resolved for 2026-08-03 through
2026-08-10, while the existing canonical EOD artifacts are used for
2026-08-11 and 2026-08-12.

The accepted Foreign Flow archive contains 19 sessions before the pinned
historical market/calendar start (`2021-04-01..2021-04-28`). Those rows are
excluded from the materializer input because they have no validated market or
volume context in this pinned lineage; the external archive remains unchanged.

## Controlled local smoke

Exactly one corrected local smoke was run for completed source session
`2026-08-12`. It did not require or create a canonical target-session
directory, target-session market data, or target-session Foreign Flow data.

Result: `FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_READY` and
`FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY`.

| Artifact | Path | Rows | Tickers | SHA-256 |
|---|---|---:|---:|---|
| Representation V2 | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\forward_monitoring\\prospective\\foreign_flow_representation_v2\\2026-08-13\\foreign_flow_representation_v2.parquet` | 963 | 963 | `3622b23886cfb47b9e7b0c1d137cba33ac9f0767f390a35439a504d7672d9e13` |
| Representation manifest | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\forward_monitoring\\prospective\\foreign_flow_representation_v2\\2026-08-13\\foreign_flow_representation_v2.manifest.json` | — | — | `4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d` |
| Setup State | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\forward_monitoring\\prospective\\foreign_flow_representation_v2\\2026-08-13\\idx_foreign_flow_setup.parquet` | 963 | 963 | `b8791011659b33c62cf0890340e86de4abfb397eaa1b99c3639a6c240b682284` |
| Setup manifest | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\forward_monitoring\\prospective\\foreign_flow_representation_v2\\2026-08-13\\idx_foreign_flow_setup.manifest.json` | — | — | `3c94eede15c35e4997643ef931538779940d6839136f7afca4b819402f17caed` |

The Representation V2 output has only the frozen 15 feature columns plus the
session keys. The Setup State output has 963 rows, `681` indeterminate rows,
`provider_calls=0`, `forward_outcomes_accessed=false`, and is pinned to both
Representation artifact hashes. The canonical target directory was absent at
verification time.

## Validation

- focused bridge/context/plan tests: `9 passed`;
- full repository pytest: `126 passed, 1 failed, 5 warnings`;
- unrelated failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` expects one conflict, while current shared storage returns the two independent conflicts `raw_close` and `vendor_adj_close`;
- `git diff --check`: PASS.

The failed first invocation of the smoke command was an import-path preflight
(`src` layout without `PYTHONPATH=src`) and produced no output artifact. The
corrected smoke above is the only runner attempt that reached execution after
the final code change.

## Decision

The calendar-contract remediation is complete and the prospective bridge is
runtime-ready for the verified local source/target transition. The lane remains
`REVIEW` pending independent ChatGPT review. No routine capture, scheduler,
counter, model, or outcome action was started.
