# Handoff

from: Codex / Luna xhigh
to: ChatGPT reviewer
task_id: IDX-FOREIGN-FLOW-FEATURE-CONTRACT-V1
model_used: Luna xhigh
reasoning_level: LIGHT
source_repository: samindriano/idx-trade
source_commit: f4d997c55f90c86a72dbad2719c6ad30a08919d4
branch: research/idx-foreign-flow-feature-contract-v1
head_commit: pending push
scope: feature contract and offline materialization/coverage audit only

## Files changed

- `src/idx_trade/foreign_flow_features.py`
- `tests/test_foreign_flow_features.py`
- `tests/test_storage.py` (stale assertion aligned with existing independent
  raw/vendor-adjusted revision-conflict contract)
- `docs/checkpoints/2026-08-14_FOREIGN_FLOW_FEATURE_CONTRACT_OFFLINE_AUDIT.md`
- this handoff

## Findings

- Official accepted flow archive: 1,288 sessions, 983 tickers, unit SHARES,
  manifest SHA `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`.
- Official IDX Stock Summary regular `volume` was used as the denominator;
  Yahoo/raw OHLCV and NonRegularVolume were not used.
- Materialized: 1,102,650 rows, 979 tickers, 1,259 feature sessions,
  951,315 fully available, 150,355 partial, 980 missing.
- 28 accepted archive sessions lack an existing canonical volume artifact and
  are explicitly not materialized.

## Decisions

- Causal availability starts at the next official session.
- Zero foreign flow is valid; zero/missing regular-volume denominators are
  missing, never zero-filled or forward-filled.
- No clipping, performance selection, outcome access, provider calls, model
  fitting, or protected-artifact access occurred.

## Artifact hashes

- feature parquet: `fbfe79290270d3f9955a81366352e9b3615dd4bd61e73848bdb345154ac056f9`
- materialization manifest:
  `09102f0cd41a59dbd4392b6e15356ccb9bcc3e23ccd8ada3977b3a0fa0050957`
- offline audit manifest:
  `55a983fa0f9463429b10e493cef7da95b96f589ab6a6d9de7a52ad7d4bb6a714`

## Validation

- focused feature tests: 7 passed;
- full IDX-Trade pytest: 47 passed;
- `git diff --check`: passed.

## Blocking risks / review points

- Materialization does not claim the full accepted archive window because
  official volume cache coverage is narrower. No provider expansion was done.
- Feature contract has not been tested against outcomes and must not be used
  for model/performance decisions until separately authorized.

## Recommended next action

Independent ChatGPT review of the formulas, denominator semantics, explicit
28-session coverage gap, missingness policy, and artifact provenance. Keep the
branch in REVIEW until accepted.
