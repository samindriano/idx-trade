# PIT Security Identity / Listing-Domain V1 — Stage A Preparation

## Frozen audit contract

Policy: `RESTORE_AUTHORITATIVE_HISTORICAL_MASTER_RIGHT_ONLY_IDENTITIES_V1`.

This is an outcome-blind, provider-free representation audit. It does not
fit, score, tune, load target values, access protected/fresh-forward outcomes,
modify parent artifacts, reset any counter, or create a model identity.

Parent lineage: `origin/research/price-basis-clean-refit-v1` at
`a56265e452541e4d205376bbe8194f4887a920b4`.

Frozen feature-builder blob:
`59ad05f815870ae00480dc7945fe18371d8eff9c`.

## Pinned inputs

| Input | Path | SHA-256 |
|---|---|---|
| calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| frozen security master | `D:\Documents\Project\idx-trade-data-gate-20260808v\listings\security_master.csv` | `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240` |
| reconciled historical master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv` | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| pre-reconcile master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260_pre_reconcile.csv` | `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240` |

The historical masters contain `979` rows versus `977` frozen rows. Before
Stage B, the generic right-only policy derives all authoritative rows in the
reconciled historical master whose security identity and ticker are absent from
the frozen master. Current known candidates are FINN and FREN, but no ticker
allow-list is used. KOCI boundaries are not changed.

## Restoration guardrails

- require the same six identity columns and valid inclusive listing intervals;
- require unique security IDs and tickers in each master;
- add only right-only historical identities;
- fail closed if a missing historical identity overlaps a frozen ticker;
- fail closed on duplicate or overlapping intervals;
- do not infer active state from panel rows;
- use the exact frozen V4 feature builder and calendar/panel unchanged.

## Stage B metrics and decision

Build the base and generic-overlay counterfactual representations. Compare
listing-domain diagnostics, direct newly admitted rows, FREN diagnostics,
all shared ticker/date representation columns at absolute tolerance `1e-12`,
per-column changed-row counts, and primary-liquid membership.

If no restored identity becomes primary-liquid and no shared representation
cell changes, return:
`PIT_SECURITY_IDENTITY_OMISSION_CONFIRMED_REPRESENTATION_INERT`.

Otherwise return:
`PIT_SECURITY_IDENTITY_OMISSION_CHANGES_V4_REPRESENTATION_TRAINING_SUPPORT_INTERSECTION_REQUIRED`
and stop before fitting. Stage C may proceed only from exact frozen support
identity artifacts without loading target values.

## Preparation validation

The helper, runner, and adversarial tests are committed before the Stage B
runtime. Runtime output must be fresh and external; only small summaries,
manifests, and diagnostics may be promoted later.
