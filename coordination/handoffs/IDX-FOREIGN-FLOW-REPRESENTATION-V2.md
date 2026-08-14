# Handoff — Foreign Flow Representation V2

from: ChatGPT/Foreign-Flow-Representation-V2  
to: local runtime reviewer / Codex  
task_id: IDX-FOREIGN-FLOW-REPRESENTATION-V2  
source_repository: samindriano/idx-trade  
branch: `research/idx-foreign-flow-representation-v2`

## Scope completed

Outcome-blind Foreign Flow V2 representation has been implemented after an economic-semantics audit of V1. V1's `FOREIGN_FLOW_V1_NO_SURVIVOR` verdict remains valid for V1 and must not be reinterpreted as a V2 result.

Files:

- `src/idx_trade/foreign_flow_features_v2.py`
- `tests/test_foreign_flow_features_v2.py`
- `docs/checkpoints/2026-08-14_FOREIGN_FLOW_REPRESENTATION_V2_AUDIT_AND_CONTRACT.md`

The frozen V2 family separates:

1. same-session participation pressure;
2. historical economic flow shock using close-valued net shares versus strictly prior regular-market-value baseline;
3. own-history abnormality percentile;
4. Clean-V2-style source-session cross-sectional foreign preference;
5. magnitude-weighted accumulation persistence, signed streak, and 5-vs-20 acceleration;
6. source-session flow-price divergence.

Listing intervals are enforced before any historical state is formed. Primary-liquid flags fail closed. Every feature row uses source session `t` and is assigned to only the immediately next official session `t+1`.

Free-float/effective-float/HSC normalization is explicitly recorded as a high-priority future feature but is blocked until a PIT-safe historical effective-float/share-count lineage exists. Current free float must not be backfilled historically.

## Validation already performed

Isolated synthetic validation: `10 passed`.

The tests cover current-volume dilution separation, pure stock-split scale invariance, own-history exclusion of current observation, cross-sectional rank semantics, non-primary exclusion, accumulation dynamics, source-session divergence, outcome-column rejection, strict boolean parsing, and pre-listing contamination prevention.

## Result — 2026-08-15 offline census

The bounded outcome-blind materialization is complete and the lane is now
`REVIEW`. The new runner is
`src/idx_trade/foreign_flow_representation_v2_runner.py` with focused tests in
`tests/test_foreign_flow_representation_v2_runner.py`.

Authoritative output root:
`D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001`

Output manifest SHA-256:
`4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`

The census materialized 1,102,400 rows, 979 tickers, and 1,259 feature
sessions from flow-through 2021-04-29 through 2026-07-30. It used the full
canonical causal market panel for primary-liquid ranking, not the 292k H10
support subset. There were 318,592 fully available rows, 783,240 partial rows,
and 568 all-missing rows. There were 22,534 verified archive rows across 28
archive sessions outside the pinned 2021-04-29 through 2026-07-31 official
calendar; these are explicitly recorded in the manifest and were not passed to
the builder. One pre-listing panel row (`KOCI`, 2023-10-06) was excluded.

The exact per-feature finite counts, yearly/session availability,
warm-up/source-data split, distributions, and all artifact hashes are in
`docs/checkpoints/2026-08-15_FOREIGN_FLOW_REPRESENTATION_V2_OFFLINE_CENSUS_RESULT.md`
and the external manifest. Causality, own-history current-observation
exclusion, primary-liquid rank scope, zero duplicates, and zero infinities all
passed.

Focused tests passed 15/15. Full pytest remains 63 passed / 1 unrelated
pre-existing failure in `tests/test_storage.py` because that test expects one
revision conflict while the current storage contract reports two; no storage
file was changed in this lane. `git diff --check` passed.

No provider call, model fit/scoring, outcome/label access, V1-alpha access,
free-float/effective-supply work, O2 work, or TradingView work occurred.

## Next local-only action

Run an **offline materialization and availability census only** using the accepted external historical Foreign Flow archive and the canonical causal market context/security master. Do not call a provider.

Before running locally:

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md` and claim this lane if the canonical ledger does not yet contain it.
2. Use the accepted official Foreign Flow historical archive; do not redownload.
3. Locate the causal source-session market context that provides at minimum:
   - `ticker`
   - `date`
   - strict `universe_primary_liquid`
   - `close`
   - `regular_market_value`
   - `close_return_5`
   - `close_return_20`
4. Use the accepted listing-aware security master with `ticker`, `listed_from`, `listed_to`.
5. Use only an explicit official session calendar.
6. Confirm context contains no target/outcome columns before invoking the builder.

Census must report at minimum:

- rows / tickers / feature sessions;
- per-feature finite availability;
- fully available / partial / all-missing rows;
- availability by year;
- primary-liquid coverage by source session;
- minimum history/warm-up missingness separately from source-data missingness;
- count of rows removed by listing intervals;
- causality assertion `feature_session = next_official(flow_through_session)` for every output row;
- no infinity / no duplicate ticker-feature-session keys;
- hashes for every input and output artifact.

Stop after census and tests. No model fitting, no H10 metrics, no V1-alpha predictions, no protected/fresh-forward outcomes, no feature subset search, and no promotion decision are authorized.
