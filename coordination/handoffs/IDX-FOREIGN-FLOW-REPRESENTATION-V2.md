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
