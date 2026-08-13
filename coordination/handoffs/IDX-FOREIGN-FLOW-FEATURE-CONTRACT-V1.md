# Handoff

from: Codex / Luna xhigh
to: ChatGPT reviewer
task_id: IDX-FOREIGN-FLOW-FEATURE-CONTRACT-V1
model_used: Luna xhigh
reasoning_level: LIGHT
source_repository: samindriano/idx-trade
source_commit: f4d997c55f90c86a72dbad2719c6ad30a08919d4
branch: research/idx-foreign-flow-feature-contract-v1
head_commit: pending remediation commit
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
- Remediated materialization: 1,102,650 rows, 979 tickers, 1,259 feature
  sessions, 964,078 fully available, 137,592 partial, 980 missing.
- The exact 28 accepted archive sessions lacking an existing canonical volume
  artifact are recorded programmatically in the external audit manifest; no
  weekday/calendar inference was used.
- Exact dates are also listed in
  `docs/checkpoints/2026-08-14_FOREIGN_FLOW_FEATURE_CONTRACT_CAUSAL_REMEDIATION.md`.

## Decisions

- Causal availability starts at the next official session.
- Zero foreign flow is valid; zero/missing regular-volume denominators are
  missing, never zero-filled or forward-filled.
- No clipping, performance selection, outcome access, provider calls, model
  fitting, or protected-artifact access occurred.
- `foreign_gross_to_volume_1` now uses ForeignBuy/ForeignSell/regular volume
  from the prior official session, matching the causal one-session net path.

## Artifact hashes

- remediated feature parquet: `059471948ad9efb5b2343d9aed729d04c5e3f2c01881153679db579b3a1d1733`
- remediated materialization manifest:
  `8c45bb42cc9bda4002967f8bc5fd5509842947dbaa3e1f764e925cbe0f8ccd1a`
- remediated offline audit manifest:
  `2341df7d7ff646dc8a13da2a45e9220e0c4c569017b373ca72daed18dcb377e4`

## Validation

- focused feature tests: 9 passed;
- full IDX-Trade pytest: 49 collected, 48 passed, 1 failed (unrelated
  `tests/test_storage.py` expectation; the unrelated prior test change was
  reverted as requested);
- `git diff --check`: passed.

## Blocking risks / review points

- Materialization does not claim the full accepted archive window because
  official volume cache coverage is narrower. No provider expansion was done.
- Feature contract has not been tested against outcomes and must not be used
  for model/performance decisions until separately authorized.

## Recommended next action

Independent ChatGPT re-review of the causal remediation, exact 28-session
coverage gap, missingness policy, and artifact provenance. Keep the branch in
REVIEW until accepted.
